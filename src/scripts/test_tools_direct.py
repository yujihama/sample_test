"""
ユースケーステスト用スクリプト - 補助ツールを直接呼び出して2つのユースケースシナリオをテストする

実行方法:
    python -m src.scripts.test_tools_direct
"""

import os
import sys
import json
import asyncio
import uuid
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import traceback

# パスの追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent.absolute()))

from loguru import logger
from src.core.config import settings
from src.tools.tool_registry import registry
from src.tools.image_processor import ImageProcessor
from src.tools.data_validator import DataValidator
from src.tools.excel_analyzer import ExcelAnalyzer
from src.tools.document_parser import DocumentParser

class DirectToolTester:
    """ツール直接呼び出しによるテスト実行クラス"""
    
    def __init__(self):
        """初期化"""
        # テスト用データディレクトリ
        self.data_dir = os.path.join(Path(__file__).parent.parent.parent, "data")
        self.test_dir = os.path.join(self.data_dir, "test")
        self.sample_dir = os.path.join(self.data_dir, "samples")
        
        os.makedirs(self.test_dir, exist_ok=True)
        os.makedirs(self.sample_dir, exist_ok=True)
        
        # ツールレジストリの初期化
        self._initialize_tools()
        
        logger.info("直接ツールテスター初期化完了")
    
    def _initialize_tools(self):
        """ツールの初期化"""
        # 各ツールのインスタンスを作成
        self.image_tool = ImageProcessor("test_image_processor")
        self.data_tool = DataValidator("test_data_validator")
        self.excel_tool = ExcelAnalyzer("test_excel_analyzer")
        self.doc_tool = DocumentParser("test_document_parser")
        
        # ツールをレジストリに登録
        registry.register_tool(self.image_tool)
        registry.register_tool(self.data_tool)
        registry.register_tool(self.excel_tool)
        registry.register_tool(self.doc_tool)
        
        logger.info("テスト用ツールを初期化しました")
    
    def _prepare_sample_data(self):
        """テスト用サンプルデータの準備"""
        # サンプルID-001: 出張精算書類
        expense_report_file = os.path.join(self.sample_dir, "sample-001_expense_report.txt")
        with open(expense_report_file, "w", encoding="utf-8") as f:
            f.write("出張精算書\n")
            f.write("申請日: 2025年2月15日\n")
            f.write("社員番号: E003\n")
            f.write("氏名: 鈴木一郎\n")
            f.write("所属部署: 営業部\n")
            f.write("出張期間: 2025年2月10日～2025年2月12日\n")
            f.write("出張先: 大阪支社\n")
            f.write("出張目的: 顧客訪問・商談\n")
            f.write("\n")
            f.write("【精算内容】\n")
            f.write("交通費（往復）: 28,000円\n")
            f.write("宿泊費（2泊）: 24,000円\n")
            f.write("日当（3日）: 9,000円\n")
            f.write("その他経費: 5,000円\n")
            f.write("--------------\n")
            f.write("合計: 66,000円\n")
            f.write("\n")
            f.write("承認者: 田中部長\n")
            f.write("承認日: 2025年2月17日\n")
        
        # 領収書画像（テキストファイルで代用）
        receipt_file = os.path.join(self.sample_dir, "sample-001_hotel_receipt.txt")
        with open(receipt_file, "w", encoding="utf-8") as f:
            f.write("領収書\n")
            f.write("2025年2月12日\n")
            f.write("宛名: 鈴木一郎様\n")
            f.write("金額: 24,000円\n")
            f.write("但し: 宿泊料金（2泊）として\n")
            f.write("大阪ビジネスホテル\n")
        
        # サンプルID-005: 取引記録検証
        transaction_file = os.path.join(self.sample_dir, "sample-005_transaction.csv")
        with open(transaction_file, "w", encoding="utf-8") as f:
            f.write("取引ID,取引日付,取引種別,取引金額,取引先,承認者,処理担当者\n")
            f.write("T-20250214-0023,2025-02-14,機器購入,820000,株式会社テックサプライ,佐藤次郎,田中三郎\n")
            f.write("T-20250214-0024,2025-02-14,消耗品,35000,株式会社オフィスマテリアル,佐藤次郎,田中三郎\n")
            f.write("T-20250215-0025,2025-02-15,ソフトウェア,450000,デジタルソリューション株式会社,山田太郎,田中三郎\n")
        
        logger.info("テスト用サンプルデータを準備しました")
        
        return {
            "sample_001": {
                "expense_report": expense_report_file,
                "receipt": receipt_file
            },
            "sample_005": {
                "transaction": transaction_file
            }
        }
    
    async def test_expense_report_tools(self):
        """出張精算書類検証シナリオのツールテスト"""
        logger.info("==== 出張精算書類検証シナリオのツールテスト開始 ====")
        results = {}
        
        try:
            # サンプルデータ準備
            sample_data = self._prepare_sample_data()
            expense_report_file = sample_data["sample_001"]["expense_report"]
            receipt_file = sample_data["sample_001"]["receipt"]
            
            # 1. 文書解析ツールで出張精算書を解析
            doc_params = {
                "operation": "extract_text",
                "file_path": expense_report_file
            }
            doc_result = await self.doc_tool.execute(doc_params)
            results["document_extraction"] = doc_result.data
            logger.info(f"出張精算書テキスト抽出結果: {doc_result.status}")
            
            # 2. 文書フォーマット検証（出張精算書）
            format_params = {
                "operation": "check_format",
                "file_path": expense_report_file,
                "format_name": "expense_application"
            }
            format_result = await self.doc_tool.execute(format_params)
            results["format_validation"] = format_result.data
            logger.info(f"フォーマット検証結果: {format_result.status}")
            
            # 3. 領収書テキスト抽出
            receipt_params = {
                "operation": "extract_text",
                "file_path": receipt_file
            }
            receipt_result = await self.doc_tool.execute(receipt_params)
            results["receipt_extraction"] = receipt_result.data
            logger.info(f"領収書テキスト抽出結果: {receipt_result.status}")
            
            # 4. 社員情報照会
            employee_params = {
                "operation": "verify_employee",
                "employee_id": "E003"
            }
            employee_result = await self.data_tool.execute(employee_params)
            results["employee_verification"] = employee_result.data
            logger.info(f"社員情報照会結果: {employee_result.status}")
            
            # 5. 承認権限の検証
            auth_params = {
                "operation": "validate_approval",
                "category": "出張申請",
                "amount": "66000",
                "approver_id": "E004"  # 田中部長と仮定 (実際のデータでは適宜変更)
            }
            auth_result = await self.data_tool.execute(auth_params)
            results["approval_validation"] = auth_result.data
            logger.info(f"承認権限検証結果: {auth_result.status}")
            
            # 総合評価（ここでは単純に全ツールが成功したかどうかで判定）
            all_success = all([
                doc_result.status == "success",
                format_result.status == "success",
                receipt_result.status == "success",
                employee_result.status == "success",
                auth_result.status == "success"
            ])
            
            # 画像処理ツールは省略（テキストファイルでは正しく動作しないため）
            
            logger.info(f"出張精算書類検証シナリオのツールテスト結果: {'成功' if all_success else '失敗'}")
            return {
                "status": "success" if all_success else "failure",
                "results": results
            }
            
        except Exception as e:
            logger.error(f"出張精算書類シナリオエラー: {e}")
            logger.debug(f"例外詳細: {traceback.format_exc()}")
            return {
                "status": "error",
                "error": str(e),
                "results": results
            }
    
    async def test_transaction_record_tools(self):
        """取引記録検証シナリオのツールテスト"""
        logger.info("==== 取引記録検証シナリオのツールテスト開始 ====")
        results = {}
        
        try:
            # サンプルデータ準備
            sample_data = self._prepare_sample_data()
            transaction_file = sample_data["sample_005"]["transaction"]
            
            # 1. Excelファイル（CSVファイル）の構造解析
            excel_params = {
                "operation": "analyze_structure",
                "file_path": transaction_file
            }
            structure_result = await self.excel_tool.execute(excel_params)
            results["file_structure"] = structure_result.data
            logger.info(f"取引記録ファイル構造解析結果: {structure_result.status}")
            
            # 2. データ抽出
            extract_params = {
                "operation": "extract_data",
                "file_path": transaction_file,
                "sheet_name": "Sheet1"  # CSVの場合はデフォルトシート名
            }
            extract_result = await self.excel_tool.execute(extract_params)
            results["data_extraction"] = extract_result.data
            logger.info(f"取引記録データ抽出結果: {extract_result.status}")
            
            # 3. 特定の取引データを検索
            search_params = {
                "operation": "search_values",
                "file_path": transaction_file,
                "search_value": "820000",
                "case_sensitive": False,
                "sheet_name": "Sheet1"
            }
            search_result = await self.excel_tool.execute(search_params)
            results["data_search"] = search_result.data
            logger.info(f"取引記録検索結果: {search_result.status}")
            
            # 4. 承認者権限の検証（佐藤次郎の権限確認）
            auth_check_params = {
                "operation": "check_authority",
                "employee_id": "E005"  # 佐藤次郎と仮定 (実際のデータでは適宜変更)
            }
            auth_result = await self.data_tool.execute(auth_check_params)
            results["approver_authority"] = auth_result.data
            logger.info(f"承認者権限検証結果: {auth_result.status}")
            
            # 5. 承認権限と金額の整合性確認
            validation_params = {
                "operation": "validate_approval",
                "category": "機器購入",
                "amount": "820000",
                "approver_id": "E005"  # 佐藤次郎と仮定
            }
            validation_result = await self.data_tool.execute(validation_params)
            results["approval_validation"] = validation_result.data
            logger.info(f"承認権限と金額の整合性確認結果: {validation_result.status}")
            
            # 総合評価（ここでは単純に全ツールが成功したかどうかで判定）
            all_success = all([
                structure_result.status == "success",
                extract_result.status == "success",
                search_result.status == "success",
                auth_result.status == "success",
                validation_result.status == "success"
            ])
            
            logger.info(f"取引記録検証シナリオのツールテスト結果: {'成功' if all_success else '失敗'}")
            return {
                "status": "success" if all_success else "failure",
                "results": results
            }
            
        except Exception as e:
            logger.error(f"取引記録シナリオエラー: {e}")
            logger.debug(f"例外詳細: {traceback.format_exc()}")
            return {
                "status": "error",
                "error": str(e),
                "results": results
            }
    
    async def run_all_tests(self):
        """すべてのツールテストシナリオを実行"""
        results = {}
        
        # 出張精算書類検証シナリオ
        expense_results = await self.test_expense_report_tools()
        results["expense_report"] = expense_results
        
        # 取引記録検証シナリオ
        transaction_results = await self.test_transaction_record_tools()
        results["transaction_record"] = transaction_results
        
        # 結果サマリー
        summary = {
            "expense_report_status": expense_results.get("status", "error"),
            "transaction_record_status": transaction_results.get("status", "error"),
            "timestamp": datetime.now().isoformat()
        }
        
        # 結果をJSONファイルに出力
        output_file = os.path.join(self.test_dir, f"direct_tool_test_results_{int(time.time())}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "details": results}, f, ensure_ascii=False, indent=2)
        
        logger.info(f"テスト結果を保存しました: {output_file}")
        return results, summary

async def main():
    """メイン処理"""
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    logger.info("ツール直接呼び出しによるユースケーステストを開始します")
    
    # テスター作成
    tester = DirectToolTester()
    
    # すべてのテスト実行
    results, summary = await tester.run_all_tests()
    
    # 結果をコンソールに表示
    print("\n===== テスト結果サマリー =====")
    print(f"出張精算書類検証シナリオ: {summary['expense_report_status']}")
    print(f"取引記録検証シナリオ: {summary['transaction_record_status']}")
    
    # 各ツールのステータスを詳細に表示
    print("\n=== 出張精算書類検証 - ツール実行結果 ===")
    expense_results = results["expense_report"]["results"]
    for tool_name, result in expense_results.items():
        tool_status = "成功" if isinstance(result, dict) and result.get("error") is None else "失敗"
        print(f"- {tool_name}: {tool_status}")
    
    print("\n=== 取引記録検証 - ツール実行結果 ===")
    transaction_results = results["transaction_record"]["results"]
    for tool_name, result in transaction_results.items():
        tool_status = "成功" if isinstance(result, dict) and result.get("error") is None else "失敗"
        print(f"- {tool_name}: {tool_status}")
    
    print("\nすべてのテストが完了しました")

if __name__ == "__main__":
    asyncio.run(main()) 