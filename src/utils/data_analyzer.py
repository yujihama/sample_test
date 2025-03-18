#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
サンプルデータの分析ユーティリティ

このモジュールはサンプルデータを分析するための関数を提供します。
Agent Aノードから利用されます。
"""

import asyncio
import json
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Callable

from datetime import datetime

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_sample_data(sample_data: Any, understanding: Dict[str, Any] = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    サンプルデータを分析する同期バージョンの関数
    
    Args:
        sample_data: 分析対象のサンプルデータ
        understanding: 監査手続きの理解情報
        metadata: 追加のメタデータ
    
    Returns:
        Dict[str, Any]: 分析結果
    """
    # 非同期関数を同期的に実行
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_analyze_sample_data_async(sample_data, understanding, metadata))
    finally:
        loop.close()


async def analyze_sample_data_async(sample_data: Any, understanding: Dict[str, Any] = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    サンプルデータを分析する非同期バージョンの関数
    
    Args:
        sample_data: 分析対象のサンプルデータ
        understanding: 監査手続きの理解情報
        metadata: 追加のメタデータ
    
    Returns:
        Dict[str, Any]: 分析結果
    """
    return await _analyze_sample_data_async(sample_data, understanding, metadata)


async def _analyze_sample_data_async(sample_data: Any, understanding: Dict[str, Any] = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    サンプルデータを分析する内部実装の非同期関数
    
    Args:
        sample_data: 分析対象のサンプルデータ
        understanding: 監査手続きの理解情報
        metadata: 追加のメタデータ
    
    Returns:
        Dict[str, Any]: 分析結果
    """
    # 分析結果を格納する辞書
    result = {
        "timestamp": datetime.now().isoformat(),
        "sample_id": getattr(sample_data, "id", "unknown"),
        "statistics": {},
        "issues": [],
        "summary": ""
    }
    
    try:
        logger.info(f"サンプルデータの分析を開始: {result['sample_id']}")
        
        # サンプルデータの属性を取得
        data_source = getattr(sample_data, "data_source", "unknown")
        sample_name = getattr(sample_data, "name", "unknown")
        
        # メタデータに基本情報を追加
        result["metadata"] = metadata or {}
        result["metadata"].update({
            "data_source": data_source,
            "sample_name": sample_name,
            "analyzed_at": datetime.now().isoformat()
        })
        
        # データの内容に基づいて分析
        # 実際のデータはデータベースから取得したり、ファイルから読み込んだりする必要がありますが、
        # このサンプルでは簡易的に属性にアクセスするだけとします
        
        # 分析タイプの決定（例：売掛金データ、仕入データなど）
        if hasattr(sample_data, "data") and isinstance(sample_data.data, dict):
            # 属性から直接データを取得
            data = sample_data.data
        else:
            # テスト用のダミーデータ
            data = {
                "accounts_receivable": [
                    {"customer_id": "C001", "customer_name": "株式会社A", "balance": 5000000, "due_date": "2023-12-31"},
                    {"customer_id": "C002", "customer_name": "株式会社B", "balance": 3500000, "due_date": "2023-12-15"}
                ],
                "confirmation_responses": [
                    {"customer_id": "C001", "confirmed_balance": 5000000, "status": "matched"},
                    {"customer_id": "C002", "confirmed_balance": 3400000, "status": "difference", "difference": 100000}
                ]
            }
        
        # 売掛金データの分析
        if "accounts_receivable" in data:
            ar_results = analyze_accounts_receivable(data["accounts_receivable"])
            result["statistics"]["accounts_receivable"] = ar_results
        
        # 確認状の回答の分析
        if "confirmation_responses" in data:
            cr_results = analyze_confirmation_responses(data["confirmation_responses"])
            result["statistics"]["confirmation_responses"] = cr_results
        
        # その他のデータテーブルの分析
        for key, value in data.items():
            if key not in ["accounts_receivable", "confirmation_responses"] and isinstance(value, list):
                table_results = analyze_data_table(value, key)
                result["statistics"][key] = table_results
        
        # 基本的な統計情報を生成
        result["statistics"]["general"] = generate_basic_statistics(data)
        
        # 問題点や特記事項の検出
        result["issues"] = detect_issues(result["statistics"])
        
        # 要約を生成
        summary_parts = []
        summary_parts.append(f"サンプルデータ「{sample_name}」の分析結果")
        
        if "accounts_receivable" in result["statistics"]:
            ar_stats = result["statistics"]["accounts_receivable"]
            summary_parts.append(f"売掛金合計: {ar_stats.get('total_balance', 0):,}円、件数: {ar_stats.get('count', 0)}件")
        
        if "confirmation_responses" in result["statistics"]:
            cr_stats = result["statistics"]["confirmation_responses"]
            summary_parts.append(f"残高確認回答: 一致 {cr_stats.get('matched_count', 0)}件、差異あり {cr_stats.get('difference_count', 0)}件、未回答 {cr_stats.get('no_response_count', 0)}件")
        
        if result["issues"]:
            summary_parts.append(f"検出された問題点: {len(result['issues'])}件")
        
        result["summary"] = " ".join(summary_parts)
        
        logger.info(f"サンプルデータの分析が完了: {result['sample_id']}")
        return result
        
    except Exception as e:
        logger.error(f"サンプルデータの分析でエラーが発生: {str(e)}")
        result["error"] = str(e)
        result["status"] = "error"
        return result


def analyze_accounts_receivable(ar_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """売掛金データを分析する"""
    result = {
        "count": len(ar_data),
        "total_balance": sum(item.get("balance", 0) for item in ar_data),
        "avg_balance": 0,
        "max_balance": 0,
        "min_balance": 0,
        "overdue_count": 0,
        "top_customers": []
    }
    
    if ar_data:
        balances = [item.get("balance", 0) for item in ar_data]
        result["avg_balance"] = sum(balances) / len(balances)
        result["max_balance"] = max(balances)
        result["min_balance"] = min(balances)
        
        # 期日超過の項目をカウント
        today = datetime.now().date()
        result["overdue_count"] = sum(
            1 for item in ar_data 
            if "due_date" in item and datetime.strptime(item["due_date"], "%Y-%m-%d").date() < today
        )
        
        # 残高上位顧客
        sorted_ar = sorted(ar_data, key=lambda x: x.get("balance", 0), reverse=True)
        result["top_customers"] = [
            {"customer_id": item.get("customer_id"), 
             "customer_name": item.get("customer_name"), 
             "balance": item.get("balance")}
            for item in sorted_ar[:5]  # 上位5社
        ]
    
    return result


def analyze_confirmation_responses(cr_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """残高確認の回答を分析する"""
    result = {
        "total_count": len(cr_data),
        "matched_count": 0,
        "difference_count": 0,
        "no_response_count": 0,
        "total_difference": 0,
        "discrepancies": []
    }
    
    for item in cr_data:
        status = item.get("status", "unknown")
        
        if status == "matched":
            result["matched_count"] += 1
        elif status == "difference":
            result["difference_count"] += 1
            difference = item.get("difference", 0)
            result["total_difference"] += abs(difference)
            
            # 差異の詳細を記録
            result["discrepancies"].append({
                "customer_id": item.get("customer_id"),
                "customer_name": item.get("customer_name", "不明"),
                "book_balance": item.get("confirmed_balance", 0) + difference,
                "confirmed_balance": item.get("confirmed_balance", 0),
                "difference": difference,
                "reason": item.get("reason", "不明")
            })
        elif status == "no_response":
            result["no_response_count"] += 1
    
    return result


def analyze_data_table(table_data: List[Dict[str, Any]], table_name: str) -> Dict[str, Any]:
    """一般的なデータテーブルを分析する"""
    result = {
        "table_name": table_name,
        "row_count": len(table_data),
        "column_count": 0,
        "columns": {},
        "numeric_columns": {}
    }
    
    if not table_data:
        return result
    
    # カラム情報を収集
    all_columns = set()
    for row in table_data:
        all_columns.update(row.keys())
    
    result["column_count"] = len(all_columns)
    result["columns"] = {col: {"type": "unknown", "null_count": 0} for col in all_columns}
    
    # 各カラムの統計情報を収集
    for col in all_columns:
        # 型の判定
        non_null_values = [row.get(col) for row in table_data if col in row and row.get(col) is not None]
        if non_null_values:
            col_type = type(non_null_values[0]).__name__
            result["columns"][col]["type"] = col_type
            result["columns"][col]["null_count"] = len(table_data) - len(non_null_values)
            
            # 数値カラムの場合は基本統計量を計算
            if col_type in ("int", "float") or all(isinstance(v, (int, float)) for v in non_null_values):
                numeric_values = [float(v) for v in non_null_values if isinstance(v, (int, float))]
                if numeric_values:
                    result["numeric_columns"][col] = {
                        "min": min(numeric_values),
                        "max": max(numeric_values),
                        "avg": sum(numeric_values) / len(numeric_values),
                        "sum": sum(numeric_values)
                    }
    
    return result


def generate_basic_statistics(data: Dict[str, Any]) -> Dict[str, Any]:
    """基本的な統計情報を生成"""
    result = {
        "table_count": 0,
        "total_records": 0,
        "data_types": {}
    }
    
    for key, value in data.items():
        if isinstance(value, list):
            result["table_count"] += 1
            result["total_records"] += len(value)
            result["data_types"][key] = f"リスト({len(value)}項目)"
        elif isinstance(value, dict):
            result["data_types"][key] = "辞書"
    
    return result


def detect_issues(statistics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """統計情報から問題点を検出"""
    issues = []
    
    # 売掛金の問題検出
    if "accounts_receivable" in statistics:
        ar_stats = statistics["accounts_receivable"]
        
        # 期日超過項目の検出
        if ar_stats.get("overdue_count", 0) > 0:
            issues.append({
                "severity": "medium",
                "category": "accounts_receivable",
                "description": f"期日を超過した売掛金が{ar_stats['overdue_count']}件あります。回収可能性を検討してください。",
                "recommendation": "期日超過項目のリストを作成し、個別に回収状況を確認してください。"
            })
    
    # 残高確認の問題検出
    if "confirmation_responses" in statistics:
        cr_stats = statistics["confirmation_responses"]
        
        # 差異がある項目の検出
        if cr_stats.get("difference_count", 0) > 0:
            issues.append({
                "severity": "high",
                "category": "confirmation_responses",
                "description": f"残高確認で{cr_stats['difference_count']}件の差異が検出されました。合計差異額: {cr_stats.get('total_difference', 0):,}円",
                "recommendation": "差異の原因を調査し、必要に応じて修正仕訳を検討してください。"
            })
        
        # 未回答の項目の検出
        if cr_stats.get("no_response_count", 0) > 0:
            issues.append({
                "severity": "medium",
                "category": "confirmation_responses",
                "description": f"残高確認で{cr_stats['no_response_count']}件の未回答があります。",
                "recommendation": "未回答の取引先に対して再依頼を検討するか、代替手続きを実施してください。"
            })
    
    return issues 