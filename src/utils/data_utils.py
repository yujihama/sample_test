"""
データ操作のためのユーティリティモジュール
"""

import os
import uuid
import json
from src.utils import json_utils
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from pathlib import Path

from loguru import logger


def load_sample_data(file_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    サンプルデータをロードし、DataFrameとメタデータを返す
    
    Args:
        file_path: データファイルのパス
        
    Returns:
        (DataFrame, メタデータ辞書)
    """
    file_path = Path(file_path)
    file_extension = file_path.suffix.lower()
    
    # メタデータの基本情報
    metadata = {
        "id": f"sample-{os.path.basename(file_path).split('_')[0]}",
        "filename": file_path.name,
        "file_size": file_path.stat().st_size,
        "file_type": file_extension,
        "upload_time": datetime.now().isoformat(),
    }
    
    try:
        # ファイル形式に応じたロード処理
        if file_extension in ['.csv', '.txt']:
            df = pd.read_csv(file_path, encoding='utf-8')
            with open(file_path, 'r', encoding='utf-8') as f:
                sample = '\n'.join(f.readlines()[:10])  # 最初の10行をサンプルとして保存
            
        elif file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
            wb = openpyxl.load_workbook(file_path, read_only=True)
            sheet_names = wb.sheetnames
            sample = f"シート名: {', '.join(sheet_names)}"
            metadata["sheets"] = sheet_names
            
        elif file_extension == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            df = pd.json_normalize(data)
            sample = json_utils.json_serialize(data[:5] if isinstance(data, list) else data, indent=2, ensure_ascii=False)[:500]
            
        else:
            # サポートされていないファイル形式
            df = pd.DataFrame()
            sample = "サポートされていないファイル形式です"
            metadata["supported"] = False
            logger.warning(f"Unsupported file format: {file_extension}")
            return df, metadata
        
        # メタデータに詳細情報を追加
        metadata.update({
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": df.columns.tolist(),
            "dtypes": {col: str(df[col].dtype) for col in df.columns},
            "sample": sample,
            "supported": True,
        })
        
        # 数値型カラムの基本統計
        numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_columns:
            metadata["numeric_columns"] = numeric_columns
            metadata["statistics"] = {
                col: {
                    "min": float(df[col].min()) if not pd.isna(df[col].min()) else None,
                    "max": float(df[col].max()) if not pd.isna(df[col].max()) else None,
                    "mean": float(df[col].mean()) if not pd.isna(df[col].mean()) else None,
                    "null_count": int(df[col].isna().sum())
                } for col in numeric_columns
            }
        
        # カテゴリカルカラムの情報
        categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
        if categorical_columns:
            metadata["categorical_columns"] = categorical_columns
            metadata["categories"] = {
                col: df[col].value_counts().head(10).to_dict() for col in categorical_columns
            }
        
        logger.info(f"Successfully loaded sample data: {file_path}")
        return df, metadata
        
    except Exception as e:
        logger.error(f"Error loading sample data: {e}")
        # エラーが発生した場合は空のDataFrameとエラー情報を含むメタデータを返す
        metadata.update({
            "error": str(e),
            "supported": False
        })
        return pd.DataFrame(), metadata


def validate_dataframe(
    df: pd.DataFrame, required_columns: List[str]
) -> Tuple[bool, Optional[str]]:
    """
    DataFrameが必要な列を含んでいるか検証
    
    Args:
        df: 検証するDataFrame
        required_columns: 必要な列のリスト
        
    Returns:
        (検証結果, エラーメッセージ)
    """
    columns = df.columns.tolist()
    missing_columns = [col for col in required_columns if col not in columns]
    
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"
    
    return True, None


def extract_column_types(df: pd.DataFrame) -> Dict[str, str]:
    """
    DataFrameの各列のデータ型を抽出
    
    Args:
        df: 対象のDataFrame
        
    Returns:
        列名とデータ型の辞書
    """
    type_mapping = {
        'int64': 'integer',
        'float64': 'number',
        'bool': 'boolean',
        'object': 'string',  # 文字列はobjectとして保存される
        'datetime64[ns]': 'date',
    }
    
    column_types = {}
    for column in df.columns:
        dtype = str(df[column].dtype)
        if 'datetime' in dtype:
            column_types[column] = 'date'
        else:
            column_types[column] = type_mapping.get(dtype, 'string')
    
    return column_types


def execute_test_item(df: pd.DataFrame, test_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    テスト項目を実行し、結果を返す
    
    Args:
        df: 対象のDataFrame
        test_item: テスト項目の辞書
        
    Returns:
        テスト結果の辞書
    """
    test_id = test_item.get("id", f"test-{uuid.uuid4().hex[:8]}")
    test_name = test_item.get("name", "未名称テスト")
    test_logic = test_item.get("test_steps", [])
    expected_result = test_item.get("expected_results", "")
    pass_criteria = test_item.get("pass_criteria", "")
    
    # リスク領域情報の取得
    risk_addressed = test_item.get("risk_addressed", "")
    
    logger.info(f"テスト項目 {test_id} を実行中: {test_name}")
    
    # テストロジックが文字列の場合はリストに変換
    if isinstance(test_logic, str):
        test_logic = [test_logic]
    
    # 必要なカラムを抽出（テストステップから推測）
    required_columns = []
    for step in test_logic:
        # カラム名を抽出（簡易的な方法）
        words = step.split()
        for word in words:
            # カンマや括弧を除去
            clean_word = word.strip(",.()[]{}").strip()
            if clean_word in df.columns:
                required_columns.append(clean_word)
    
    # カラムのユニーク化
    required_columns = list(set(required_columns))
    
    # 必要な列が存在するか確認
    if required_columns:
        valid, error_msg = validate_dataframe(df, required_columns)
        if not valid:
            return {
                "test_item_id": test_id,
                "test_name": test_name,
                "result": "error",
                "details": error_msg,
                "affected_rows": [],
                "exception_data": {},
                "risk_addressed": risk_addressed
            }
    
    try:
        # 結果を格納するためのフラグ
        failed_indices = []
        test_details = []
        
        # 各種テストロジックを実行
        for step in test_logic:
            step_result = _evaluate_test_step(df, step)
            if step_result["status"] == "success":
                # テスト条件を満たさない行を特定
                condition_result = step_result["result"]
                if isinstance(condition_result, pd.Series):
                    current_failed = df.index[~condition_result].tolist()
                    failed_indices.extend(current_failed)
                    if len(current_failed) > 0:
                        test_details.append(f"テストステップ「{step}」: {len(current_failed)}行が条件を満たしていません")
                    else:
                        test_details.append(f"テストステップ「{step}」: すべての行が条件を満たしています")
            else:
                # エラーの場合
                test_details.append(f"テストステップ「{step}」の実行中にエラー: {step_result['error']}")
                # 全ての行を失敗とマーク
                failed_indices = list(df.index)
                break
        
        # 失敗した行の重複を除去
        failed_indices = list(set(failed_indices))
        failed_rows = [int(idx) for idx in failed_indices]
        
        # 例外データの収集
        exception_data = {}
        if failed_rows:
            for idx in failed_indices:
                row_dict = df.loc[idx].to_dict()
                exception_data[str(idx)] = row_dict
        
        # 合格基準のチェック
        result = "pass"
        if failed_rows:
            # 合格基準に基づいて判定
            if pass_criteria and "%" in pass_criteria:
                # 割合ベースの判定（例: "未承認または承認者の無い申請が全体の5%未満"）
                try:
                    # 数値を抽出
                    percentage = float(''.join(c for c in pass_criteria if c.isdigit() or c == '.'))
                    actual_percentage = (len(failed_rows) / len(df)) * 100
                    
                    if "未満" in pass_criteria:
                        result = "pass" if actual_percentage < percentage else "fail"
                    elif "以下" in pass_criteria:
                        result = "pass" if actual_percentage <= percentage else "fail"
                    else:
                        # デフォルトは未満として扱う
                        result = "pass" if actual_percentage < percentage else "fail"
                        
                    test_details.append(f"合格基準: {pass_criteria}, 実際: {actual_percentage:.2f}%")
                except Exception as e:
                    logger.error(f"合格基準の解析エラー: {e}")
                    result = "fail"  # エラーの場合は失敗として扱う
            else:
                # デフォルトは厳格判定（1件でも失敗があればfail）
                result = "fail"
        
        # 結果の詳細
        details = "\n".join(test_details)
        if result == "pass":
            details += f"\n合格: {expected_result}"
        else:
            details += f"\n不合格: {expected_result}が満たされていません"
            
        return {
            "test_item_id": test_id,
            "test_name": test_name,
            "result": result,
            "details": details,
            "affected_rows": failed_rows,
            "exception_data": exception_data,
            "risk_addressed": risk_addressed
        }
    
    except Exception as e:
        logger.error(f"テスト項目 {test_id} の実行中にエラー: {e}")
        return {
            "test_item_id": test_id,
            "test_name": test_name,
            "result": "error",
            "details": f"テスト実行中にエラーが発生しました: {str(e)}",
            "affected_rows": [],
            "exception_data": {},
            "risk_addressed": risk_addressed
        }


def _evaluate_test_step(df: pd.DataFrame, test_step: str) -> Dict[str, Any]:
    """
    単一のテストステップを評価する
    
    Args:
        df: データフレーム
        test_step: テストステップの説明
        
    Returns:
        評価結果 {"status": "success|error", "result": 結果データ, "error": エラーメッセージ}
    """
    try:
        # 列名リストと値を変数として保持
        locals_dict = {col: df[col] for col in df.columns}
        
        # 様々なパターンのテストステップを処理
        
        # 1. 空値チェック
        if "空でない" in test_step or "空白でない" in test_step or "NULL" in test_step:
            for col in df.columns:
                if col in test_step:
                    return {
                        "status": "success",
                        "result": ~df[col].isna()
                    }
                    
        # 2. 特定の値を含むかチェック
        elif "が含まれる" in test_step or "を含む" in test_step:
            for col in df.columns:
                if col in test_step:
                    # 含む値を抽出
                    parts = test_step.split("が含まれる" if "が含まれる" in test_step else "を含む")
                    value = parts[1].strip() if len(parts) > 1 else parts[0].split(col)[1].strip()
                    value = value.strip('"\'.,;:()[] ')
                    return {
                        "status": "success",
                        "result": df[col].astype(str).str.contains(value)
                    }
        
        # 3. 数値比較
        elif any(op in test_step for op in ["以上", "以下", "超える", "未満", "等しい", ">", "<", "=", "=="]):
            for col in df.columns:
                if col in test_step:
                    # 数値を抽出して比較
                    if "以上" in test_step:
                        value = float(''.join(c for c in test_step.split("以上")[0].split(col)[1] if c.isdigit() or c == '.'))
                        return {"status": "success", "result": pd.to_numeric(df[col], errors='coerce') >= value}
                    elif "以下" in test_step:
                        value = float(''.join(c for c in test_step.split("以下")[0].split(col)[1] if c.isdigit() or c == '.'))
                        return {"status": "success", "result": pd.to_numeric(df[col], errors='coerce') <= value}
                    elif "超える" in test_step:
                        value = float(''.join(c for c in test_step.split("超える")[0].split(col)[1] if c.isdigit() or c == '.'))
                        return {"status": "success", "result": pd.to_numeric(df[col], errors='coerce') > value}
                    elif "未満" in test_step:
                        value = float(''.join(c for c in test_step.split("未満")[0].split(col)[1] if c.isdigit() or c == '.'))
                        return {"status": "success", "result": pd.to_numeric(df[col], errors='coerce') < value}
                    elif "等しい" in test_step or "==" in test_step or "=" in test_step:
                        value_part = test_step.split("等しい")[1] if "等しい" in test_step else (
                            test_step.split("==")[1] if "==" in test_step else test_step.split("=")[1]
                        )
                        value = value_part.strip('"\'.,;:()[] ')
                        # 数値に変換可能か試みる
                        try:
                            num_value = float(value)
                            return {"status": "success", "result": pd.to_numeric(df[col], errors='coerce') == num_value}
                        except ValueError:
                            # 文字列として比較
                            return {"status": "success", "result": df[col].astype(str) == value}
        
        # 4. 承認状態のチェック
        elif "承認" in test_step:
            for col in df.columns:
                if "承認" in col or "状態" in col:
                    if "承認済" in test_step:
                        return {"status": "success", "result": df[col] == "承認済"}
                    elif "未承認" in test_step:
                        return {"status": "success", "result": df[col] == "未承認"}
                    elif "がある" in test_step or "が存在" in test_step:
                        return {"status": "success", "result": ~df[col].isna()}
        
        # 5. カラム間比較
        elif "一致" in test_step:
            # 二つのカラムの値が一致するかチェック
            columns = [col for col in df.columns if col in test_step]
            if len(columns) >= 2:
                return {"status": "success", "result": df[columns[0]] == df[columns[1]]}
        
        # デフォルト: すべての行に対してTrueを返す
        logger.warning(f"対応していないテストステップパターン: {test_step}")
        return {"status": "success", "result": pd.Series([True] * len(df))}
        
    except Exception as e:
        logger.error(f"テストステップの評価中にエラー: {e}")
        return {"status": "error", "error": str(e)}


def generate_test_summary(test_results: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    テスト結果のサマリーを生成
    
    Args:
        test_results: テスト結果のリスト
        
    Returns:
        結果のカテゴリー別集計
    """
    summary = {
        "total": len(test_results),
        "pass": 0,
        "fail": 0,
        "warning": 0,
        "error": 0,
        "skipped": 0,
    }
    
    for result in test_results:
        result_type = result["result"]
        if result_type in summary:
            summary[result_type] += 1
    
    return summary 


def analyze_sample_data(df: pd.DataFrame) -> Dict[str, Any]:
    """
    DataFrameを分析し、分析結果を返す
    
    Args:
        df: 分析対象のDataFrame
        
    Returns:
        Dict[str, Any]: 分析結果
    """
    if df.empty:
        return {"error": "空のデータフレームです"}
    
    analysis = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": df.columns.tolist(),
        "missing_values": {col: int(df[col].isna().sum()) for col in df.columns},
        "total_missing": int(df.isna().sum().sum()),
        "missing_percentage": float(df.isna().sum().sum() / (df.shape[0] * df.shape[1]) * 100),
    }
    
    # 数値型カラムの分析
    numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
    if numeric_columns:
        analysis["numeric_columns"] = numeric_columns
        analysis["descriptive_stats"] = df[numeric_columns].describe().to_dict()
        
        # 異常値の検出（標準偏差の3倍を超える値）
        outliers = {}
        for col in numeric_columns:
            mean = df[col].mean()
            std = df[col].std()
            lower_bound = mean - 3 * std
            upper_bound = mean + 3 * std
            outlier_count = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
            if outlier_count > 0:
                outliers[col] = {
                    "count": int(outlier_count),
                    "percentage": float(outlier_count / len(df) * 100),
                    "lower_bound": float(lower_bound),
                    "upper_bound": float(upper_bound)
                }
        if outliers:
            analysis["outliers"] = outliers
    
    # カテゴリカルカラムの分析
    categorical_columns = df.select_dtypes(include=['object', 'category']).columns.tolist()
    if categorical_columns:
        analysis["categorical_columns"] = categorical_columns
        analysis["unique_counts"] = {col: int(df[col].nunique()) for col in categorical_columns}
        analysis["top_categories"] = {
            col: df[col].value_counts().head(5).to_dict() for col in categorical_columns
        }
    
    # 時間系カラムの検出と分析
    datetime_columns = []
    for col in df.columns:
        if df[col].dtype == 'datetime64[ns]':
            datetime_columns.append(col)
        elif df[col].dtype == 'object':
            # 文字列からの日付検出を試みる
            try:
                pd.to_datetime(df[col], errors='raise')
                datetime_columns.append(col)
            except:
                pass
    
    if datetime_columns:
        analysis["datetime_columns"] = datetime_columns
        date_ranges = {}
        for col in datetime_columns:
            if df[col].dtype != 'datetime64[ns]':
                df[col] = pd.to_datetime(df[col], errors='coerce')
            
            if not df[col].isna().all():
                date_ranges[col] = {
                    "min": df[col].min().isoformat() if not pd.isna(df[col].min()) else None,
                    "max": df[col].max().isoformat() if not pd.isna(df[col].max()) else None,
                    "range_days": (df[col].max() - df[col].min()).days if not (pd.isna(df[col].min()) or pd.isna(df[col].max())) else None,
                }
        if date_ranges:
            analysis["date_ranges"] = date_ranges
    
    # 重複行の検出
    duplicates = int(df.duplicated().sum())
    if duplicates > 0:
        analysis["duplicate_rows"] = {
            "count": duplicates,
            "percentage": float(duplicates / len(df) * 100)
        }
    
    logger.info(f"Completed data analysis: {len(df)} rows, {len(df.columns)} columns")
    return analysis


def transform_data(df: pd.DataFrame, transformations: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    DataFrameに変換処理を適用し、変換後のDataFrameを返す
    
    Args:
        df: 変換対象のDataFrame
        transformations: 適用する変換処理のリスト
            例: [{"type": "rename", "source": "old_name", "target": "new_name"},
                 {"type": "drop", "source": "column_to_drop"},
                 {"type": "filter", "column": "age", "operator": ">", "value": 18}]
        
    Returns:
        pd.DataFrame: 変換後のDataFrame
    """
    if df.empty:
        logger.warning("Empty DataFrame provided for transformation")
        return df
    
    result_df = df.copy()
    
    for transform in transformations:
        transform_type = transform.get("type", "").lower()
        
        try:
            if transform_type == "rename":
                # カラム名変更
                source = transform.get("source")
                target = transform.get("target")
                if source and target and source in result_df.columns:
                    result_df = result_df.rename(columns={source: target})
                    logger.info(f"Renamed column: {source} -> {target}")
            
            elif transform_type == "drop":
                # カラム削除
                source = transform.get("source")
                if source and source in result_df.columns:
                    result_df = result_df.drop(columns=[source])
                    logger.info(f"Dropped column: {source}")
            
            elif transform_type == "filter":
                # 行フィルタリング
                column = transform.get("column")
                operator = transform.get("operator")
                value = transform.get("value")
                
                if column and operator and value is not None and column in result_df.columns:
                    before_count = len(result_df)
                    
                    if operator == "==":
                        result_df = result_df[result_df[column] == value]
                    elif operator == "!=":
                        result_df = result_df[result_df[column] != value]
                    elif operator == ">":
                        result_df = result_df[result_df[column] > value]
                    elif operator == ">=":
                        result_df = result_df[result_df[column] >= value]
                    elif operator == "<":
                        result_df = result_df[result_df[column] < value]
                    elif operator == "<=":
                        result_df = result_df[result_df[column] <= value]
                    elif operator == "in":
                        if isinstance(value, list):
                            result_df = result_df[result_df[column].isin(value)]
                    elif operator == "not in":
                        if isinstance(value, list):
                            result_df = result_df[~result_df[column].isin(value)]
                    elif operator == "contains":
                        result_df = result_df[result_df[column].astype(str).str.contains(str(value), na=False)]
                    
                    after_count = len(result_df)
                    logger.info(f"Filtered by {column} {operator} {value}: removed {before_count - after_count} rows")
            
            elif transform_type == "create":
                # 新規カラム作成
                target = transform.get("target")
                expression = transform.get("expression")
                
                if target and expression:
                    # 注意: evalは安全でない場合があるため、実際のアプリケーションではより安全な方法を検討すべき
                    result_df[target] = result_df.eval(expression)
                    logger.info(f"Created column: {target} = {expression}")
            
            elif transform_type == "convert":
                # データ型変換
                source = transform.get("source")
                data_type = transform.get("data_type")
                
                if source and data_type and source in result_df.columns:
                    if data_type == "int":
                        result_df[source] = pd.to_numeric(result_df[source], errors='coerce').astype('Int64')
                    elif data_type == "float":
                        result_df[source] = pd.to_numeric(result_df[source], errors='coerce')
                    elif data_type == "datetime":
                        result_df[source] = pd.to_datetime(result_df[source], errors='coerce')
                    elif data_type == "string":
                        result_df[source] = result_df[source].astype(str)
                    elif data_type == "category":
                        result_df[source] = result_df[source].astype('category')
                    
                    logger.info(f"Converted {source} to {data_type}")
            
            elif transform_type == "fill_na":
                # 欠損値の補完
                source = transform.get("source")
                value = transform.get("value")
                method = transform.get("method")
                
                if source and source in result_df.columns:
                    if method:
                        if method == "mean":
                            fill_value = result_df[source].mean()
                        elif method == "median":
                            fill_value = result_df[source].median()
                        elif method == "mode":
                            fill_value = result_df[source].mode()[0]
                        else:
                            fill_value = value
                    else:
                        fill_value = value
                    
                    na_count = result_df[source].isna().sum()
                    result_df[source] = result_df[source].fillna(fill_value)
                    logger.info(f"Filled {na_count} NA values in {source}")
        
        except Exception as e:
            logger.error(f"Error applying transformation {transform_type}: {e}")
    
    logger.info(f"Completed data transformation: {len(transformations)} transformations applied")
    return result_df


def save_data(df: pd.DataFrame, file_path: str, file_format: str = "csv") -> str:
    """
    DataFrameをファイルに保存する
    
    Args:
        df: 保存するDataFrame
        file_path: 保存先ファイルパス（拡張子なし）
        file_format: 保存形式 (csv, excel, json)
        
    Returns:
        str: 保存したファイルの完全パス
    """
    if df.empty:
        logger.warning("Empty DataFrame provided for saving")
        return None
    
    try:
        # パスのディレクトリ部分が存在することを確認
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 現在の日時を含むファイル名を作成
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"{os.path.basename(file_path)}_{timestamp}"
        full_path = os.path.join(os.path.dirname(file_path), filename)
        
        # ファイル形式に応じた保存処理
        if file_format.lower() == "csv":
            save_path = f"{full_path}.csv"
            df.to_csv(save_path, index=False, encoding='utf-8')
        elif file_format.lower() == "excel":
            save_path = f"{full_path}.xlsx"
            df.to_excel(save_path, index=False)
        elif file_format.lower() == "json":
            save_path = f"{full_path}.json"
            df.to_json(save_path, orient='records', force_ascii=False, indent=2)
        else:
            logger.error(f"Unsupported file format: {file_format}")
            return None
        
        logger.info(f"Data saved to {save_path}")
        return save_path
    
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        return None 