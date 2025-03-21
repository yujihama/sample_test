"""
Excelファイル処理ツール

このモジュールは、Excelファイルに対する処理を行うクラスを提供します。
"""

import os
import re
import json
import pandas as pd
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from loguru import logger
import numpy as np
from datetime import datetime
import openpyxl

# プロジェクトのルートディレクトリを取得
ROOT_DIR = Path(__file__).parents[2].absolute()
DATA_DIR = os.path.join(ROOT_DIR, "data")


class ExcelProcessor:
    """
    Excelファイル処理クラス
    
    Excelファイルのデータ抽出、サマリー集計、値の検索、データ操作などの機能を提供します。
    """
    
    def __init__(self):
        """
        ExcelProcessorの初期化
        """
        logger.info("ツール初期化: excel_processor")
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        ツールを実行する
        
        Args:
            params: 実行パラメータ
                - process_type: 処理タイプ（analyze, extract, summarize, etc.）
                - target_file: 対象ファイルパス
                - operations: 実行する操作のリスト
                
        Returns:
            Dict[str, Any]: 処理結果
        """
        process_type = params.get("process_type", "analyze")
        target_file = params.get("target_file")
        operations = params.get("operations", [])
        
        # ファイルパスの設定（相対パスの場合はデータディレクトリからの相対パスと解釈）
        if target_file and not os.path.isabs(target_file):
            target_file = os.path.join(DATA_DIR, "test_samples", target_file)
        
        # ファイルの存在確認
        if not os.path.exists(target_file):
            return {
                "status": "error",
                "message": f"ファイルが見つかりません: {target_file}"
            }
        
        try:
            # 処理タイプに基づいて処理を実行
            if process_type == "analyze":
                result = self._analyze_excel(target_file, operations)
            elif process_type == "extract":
                result = self._extract_data(target_file, operations)
            elif process_type == "summarize":
                result = self._summarize_data(target_file, operations)
            else:
                return {
                    "status": "error",
                    "message": f"不明な処理タイプ: {process_type}"
                }
            
            return {
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Excel処理エラー: {e}")
            return {
                "status": "error",
                "message": f"Excel処理中にエラーが発生しました: {str(e)}"
            }
    
    def _analyze_excel(self, file_path: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Excelファイルを分析する
        
        Args:
            file_path: 対象ファイルパス
            operations: 実行する操作のリスト
            
        Returns:
            Dict[str, Any]: 分析結果
        """
        results = {}
        
        try:
            # Pandasでデータフレームとして読み込み
            df = pd.read_excel(file_path)
            
            # 基本情報を取得
            results["file_info"] = {
                "filename": os.path.basename(file_path),
                "sheet_count": len(pd.ExcelFile(file_path).sheet_names),
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": df.columns.tolist()
            }
            
            # 指定された操作を実行
            for operation in operations:
                op_type = operation.get("operation")
                
                if op_type == "extract_summary":
                    # 特定の列のサマリー情報を抽出
                    columns = operation.get("columns", [])
                    if columns:
                        summary = {}
                        for col in columns:
                            if col in df.columns:
                                col_data = df[col].dropna()
                                if col_data.dtype in [np.int64, np.float64]:
                                    summary[col] = {
                                        "min": float(col_data.min()) if not col_data.empty else None,
                                        "max": float(col_data.max()) if not col_data.empty else None,
                                        "mean": float(col_data.mean()) if not col_data.empty else None,
                                        "unique_values": col_data.unique().tolist()
                                    }
                                else:
                                    unique_vals = col_data.unique().tolist()
                                    # リスト内の要素を文字列化（JSONシリアライズ可能にするため）
                                    unique_vals = [str(val) for val in unique_vals]
                                    summary[col] = {
                                        "unique_values": unique_vals,
                                        "value_counts": {str(k): int(v) for k, v in col_data.value_counts().items()}
                                    }
                        results["column_summary"] = summary
                
                elif op_type == "find_discrepancies":
                    # 値の不一致を検出
                    threshold = operation.get("threshold", 0.0)
                    discrepancies = []
                    
                    # 数値列の不一致を検出
                    numeric_cols = df.select_dtypes(include=['number']).columns
                    for col in numeric_cols:
                        col_data = df[col].dropna()
                        if len(col_data) > 1:
                            # 同じ行のレコードで値が異なる場合を検出
                            for key_col in df.columns:
                                if key_col != col:
                                    # キー列でグループ化し、値の差異を検出
                                    grouped = df.groupby(key_col)[col].agg(['min', 'max'])
                                    diff_groups = grouped[grouped['min'] != grouped['max']]
                                    
                                    if not diff_groups.empty:
                                        for key, row in diff_groups.iterrows():
                                            min_val = float(row['min'])
                                            max_val = float(row['max'])
                                            diff_pct = 0
                                            if min_val != 0:
                                                diff_pct = abs(max_val - min_val) / abs(min_val)
                                            
                                            if diff_pct > threshold:
                                                # 閾値を超える差異を記録
                                                records = df[df[key_col] == key][[key_col, col]].to_dict('records')
                                                discrepancies.append({
                                                    "key_column": key_col,
                                                    "key_value": str(key),
                                                    "value_column": col,
                                                    "min_value": min_val,
                                                    "max_value": max_val,
                                                    "diff_percentage": round(diff_pct * 100, 2),
                                                    "records": records
                                                })
                    
                    results["discrepancies"] = discrepancies
            
            # 検出された金額の差異を文章で説明
            if "discrepancies" in results and results["discrepancies"]:
                discrepancy_descriptions = []
                
                for disc in results["discrepancies"]:
                    key_col = disc["key_column"]
                    key_val = disc["key_value"]
                    value_col = disc["value_column"]
                    min_val = disc["min_value"]
                    max_val = disc["max_value"]
                    
                    # 日本語での説明文を生成
                    if "金額" in value_col or "額" in value_col:
                        desc = f"{key_col}「{key_val}」の{value_col}に差異があります: 最小値 {min_val:,.0f}円、最大値 {max_val:,.0f}円"
                        discrepancy_descriptions.append(desc)
                
                results["discrepancy_descriptions"] = discrepancy_descriptions
            
            return results
            
        except Exception as e:
            logger.error(f"Excel分析エラー: {e}")
            return {"error": f"Excel分析中にエラーが発生しました: {str(e)}"}
    
    def _extract_data(self, file_path: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Excelファイルからデータを抽出する
        
        Args:
            file_path: 対象ファイルパス
            operations: 実行する操作のリスト
            
        Returns:
            Dict[str, Any]: 抽出結果
        """
        results = {}
        
        try:
            # Excelファイルを読み込み
            df = pd.read_excel(file_path)
            
            # 指定された操作を実行
            for operation in operations:
                op_type = operation.get("operation")
                
                if op_type == "extract_rows":
                    # 条件に一致する行を抽出
                    filter_column = operation.get("filter_column")
                    filter_value = operation.get("filter_value")
                    
                    if filter_column and filter_value is not None:
                        filtered_df = df[df[filter_column] == filter_value]
                        results["extracted_rows"] = filtered_df.to_dict('records')
                
                elif op_type == "extract_columns":
                    # 指定された列を抽出
                    columns = operation.get("columns", [])
                    if columns:
                        columns_to_extract = [col for col in columns if col in df.columns]
                        results["extracted_columns"] = df[columns_to_extract].to_dict('records')
            
            return results
            
        except Exception as e:
            logger.error(f"データ抽出エラー: {e}")
            return {"error": f"データ抽出中にエラーが発生しました: {str(e)}"}
    
    def _summarize_data(self, file_path: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Excelファイルのデータをサマリー集計する
        
        Args:
            file_path: 対象ファイルパス
            operations: 実行する操作のリスト
            
        Returns:
            Dict[str, Any]: 集計結果
        """
        results = {}
        
        try:
            # Excelファイルを読み込み
            df = pd.read_excel(file_path)
            
            # 指定された操作を実行
            for operation in operations:
                op_type = operation.get("operation")
                
                if op_type == "group_by":
                    # グループ化と集計
                    group_columns = operation.get("group_columns", [])
                    agg_column = operation.get("agg_column")
                    agg_function = operation.get("agg_function", "sum")
                    
                    if group_columns and agg_column:
                        valid_group_cols = [col for col in group_columns if col in df.columns]
                        if valid_group_cols and agg_column in df.columns:
                            # 集計関数を適用
                            if agg_function == "sum":
                                grouped = df.groupby(valid_group_cols)[agg_column].sum()
                            elif agg_function == "mean":
                                grouped = df.groupby(valid_group_cols)[agg_column].mean()
                            elif agg_function == "count":
                                grouped = df.groupby(valid_group_cols)[agg_column].count()
                            elif agg_function == "min":
                                grouped = df.groupby(valid_group_cols)[agg_column].min()
                            elif agg_function == "max":
                                grouped = df.groupby(valid_group_cols)[agg_column].max()
                            else:
                                grouped = df.groupby(valid_group_cols)[agg_column].sum()
                            
                            # 結果をJSONシリアライズ可能な形式に変換
                            results["grouped_data"] = grouped.reset_index().to_dict('records')
            
            return results
            
        except Exception as e:
            logger.error(f"データ集計エラー: {e}")
            return {"error": f"データ集計中にエラーが発生しました: {str(e)}"}


if __name__ == "__main__":
    # 動作確認用のコード
    processor = ExcelProcessor()
    
    # テスト用のファイルパス
    test_file = os.path.join(DATA_DIR, "test_samples", "サンプルID-005_取引履歴.xlsx")
    
    # 分析テスト
    analysis_result = processor.execute({
        "process_type": "analyze",
        "target_file": test_file,
        "operations": [
            {
                "operation": "extract_summary",
                "columns": ["申請金額", "承認金額"]
            },
            {
                "operation": "find_discrepancies",
                "threshold": 0.05
            }
        ]
    })
    
    print(json.dumps(analysis_result, indent=2, ensure_ascii=False)) 