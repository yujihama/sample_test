"""
ユースケーステスト用スクリプト - 2つのユースケースシナリオをAPIベースでテストする

実行方法:
    python -m src.scripts.test_usecase
"""

import os
import sys
import json
import asyncio
import requests
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

# APIのベースURL - ローカルホストとポートが正しいか確認
API_BASE_URL = "http://127.0.0.1:8000/api"
# 詳細なデバッグ情報表示
DEBUG_MODE = True

class UseCaseTester:
    """ユースケーステスト実行クラス"""
    
    def __init__(self):
        """初期化"""
        self.api_base_url = API_BASE_URL
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # テスト用データディレクトリ
        self.data_dir = os.path.join(Path(__file__).parent.parent.parent, "data")
        self.test_dir = os.path.join(self.data_dir, "test")
        self.sample_dir = os.path.join(self.data_dir, "samples")
        
        os.makedirs(self.test_dir, exist_ok=True)
        os.makedirs(self.sample_dir, exist_ok=True)
        
        # ツールレジストリの初期化
        self._initialize_tools()
        
        # APIの疎通確認
        self._check_api_connection()
        
        logger.info("ユースケーステスター初期化完了")
    
    def _check_api_connection(self):
        """APIサーバーとの疎通確認"""
        try:
            logger.info(f"APIサーバー ({self.api_base_url}) への接続を確認しています...")
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("APIサーバーに正常に接続できました")
            else:
                logger.warning(f"APIサーバーからステータスコード {response.status_code} が返されました")
        except requests.exceptions.RequestException as e:
            logger.warning(f"APIサーバーへの接続に失敗しました: {e}")
            if DEBUG_MODE:
                logger.debug(f"接続先: {self.api_base_url}")
                logger.debug(f"例外詳細: {traceback.format_exc()}")
    
    def _initialize_tools(self):
        """ツールの初期化"""
        # 各ツールのインスタンスを作成
        image_tool = ImageProcessor("test_image_processor")
        data_tool = DataValidator("test_data_validator")
        excel_tool = ExcelAnalyzer("test_excel_analyzer")
        doc_tool = DocumentParser("test_document_parser")
        
        # ツールをレジストリに登録
        registry.register_tool(image_tool)
        registry.register_tool(data_tool)
        registry.register_tool(excel_tool)
        registry.register_tool(doc_tool)
        
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
    
    def _create_audit_procedure(self, title: str, description: str, risk_areas: List[str]) -> str:
        """監査手続きを作成"""
        url = f"{self.api_base_url}/audit-procedures"
        payload = {
            "title": title,
            "description": description,
            "risk_areas": risk_areas,
            "required_data_fields": []
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            if response.status_code != 200:
                logger.error(f"監査手続き作成エラー: {response.text}")
                raise Exception(f"監査手続き作成に失敗しました: {response.status_code}")
            
            response_data = response.json()
            procedure_id = response_data.get("procedure_id")
            logger.info(f"監査手続きを作成しました: {procedure_id}")
            
            return procedure_id
        except requests.exceptions.RequestException as e:
            logger.error(f"API接続エラー: {e}")
            if DEBUG_MODE:
                logger.debug(f"接続先URL: {url}")
                logger.debug(f"リクエストペイロード: {payload}")
                logger.debug(f"例外詳細: {traceback.format_exc()}")
            raise Exception(f"API接続エラー: {e}")
    
    def _upload_sample(self, procedure_id: str, file_path: str) -> str:
        """サンプルデータをアップロード"""
        url = f"{self.api_base_url}/upload-sample?procedure_id={procedure_id}"
        
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f)}
                response = requests.post(url, files=files)
            
            if response.status_code != 200:
                logger.error(f"サンプルアップロードエラー: {response.text}")
                raise Exception(f"サンプルアップロードに失敗しました: {response.status_code}")
            
            response_data = response.json()
            sample_id = response_data.get("sample_id")
            logger.info(f"サンプルをアップロードしました: {sample_id}")
            
            return sample_id
        except Exception as e:
            logger.error(f"サンプルアップロードエラー: {e}")
            if DEBUG_MODE:
                logger.debug(f"アップロード対象ファイル: {file_path}")
                logger.debug(f"例外詳細: {traceback.format_exc()}")
            raise
    
    def _start_workflow(self, procedure_id: str, sample_id: str) -> str:
        """ワークフローを開始"""
        url = f"{self.api_base_url}/start-workflow?procedure_id={procedure_id}&sample_id={sample_id}"
        
        try:
            response = requests.post(url, headers=self.headers)
            if response.status_code != 200:
                logger.error(f"ワークフロー開始エラー: {response.text}")
                raise Exception(f"ワークフロー開始に失敗しました: {response.status_code}")
            
            response_data = response.json()
            workflow_id = response_data.get("workflow_id")
            logger.info(f"ワークフローを開始しました: {workflow_id}")
            
            return workflow_id
        except Exception as e:
            logger.error(f"ワークフロー開始エラー: {e}")
            if DEBUG_MODE:
                logger.debug(f"例外詳細: {traceback.format_exc()}")
            raise
    
    def _poll_workflow_status(self, workflow_id: str, max_wait_time: int = 300) -> Dict[str, Any]:
        """ワークフローの状態を定期的に確認"""
        url = f"{self.api_base_url}/workflow/{workflow_id}"
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                response = requests.get(url, headers=self.headers)
                if response.status_code != 200:
                    logger.error(f"ワークフロー状態取得エラー: {response.text}")
                    time.sleep(5)
                    continue
                
                workflow_data = response.json()
                status = workflow_data.get("status")
                
                if status in ["completed", "error", "failed"]:
                    logger.info(f"ワークフロー完了: {status}")
                    return workflow_data
                
                logger.info(f"ワークフロー進行中... 状態: {status}, エージェント: {workflow_data.get('current_agent')}")
                time.sleep(10)
            except Exception as e:
                logger.error(f"ワークフロー状態取得エラー: {e}")
                if DEBUG_MODE:
                    logger.debug(f"例外詳細: {traceback.format_exc()}")
                time.sleep(5)
        
        logger.warning(f"ワークフローの待機時間が{max_wait_time}秒を超えました。強制終了します。")
        return {"status": "timeout", "workflow_id": workflow_id}
    
    def _get_workflow_results(self, workflow_id: str) -> Dict[str, Any]:
        """ワークフロー結果を取得"""
        url = f"{self.api_base_url}/results/{workflow_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                logger.error(f"結果取得エラー: {response.text}")
                return {"error": "結果取得に失敗しました", "workflow_id": workflow_id}
            
            return response.json()
        except Exception as e:
            logger.error(f"結果取得エラー: {e}")
            if DEBUG_MODE:
                logger.debug(f"例外詳細: {traceback.format_exc()}")
            return {"error": str(e), "workflow_id": workflow_id}
    
    def _check_human_interventions(self, workflow_id: str) -> List[Dict[str, Any]]:
        """人間介入リクエストを確認"""
        url = f"{self.api_base_url}/human-intervention?workflow_id={workflow_id}&status=pending"
        
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                logger.error(f"人間介入リクエスト取得エラー: {response.text}")
                return []
            
            response_data = response.json()
            return response_data.get("interventions", [])
        except Exception as e:
            logger.error(f"人間介入リクエスト取得エラー: {e}")
            if DEBUG_MODE:
                logger.debug(f"例外詳細: {traceback.format_exc()}")
            return []
    
    def _respond_to_intervention(self, intervention_id: str, content: str) -> Dict[str, Any]:
        """人間介入リクエストに応答"""
        url = f"{self.api_base_url}/human-intervention/{intervention_id}/response"
        
        payload = {
            "responder": "test_user",
            "response_type": "text",
            "content": content,
            "attachment_urls": [],
            "comment": "テスト用の応答"
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            if response.status_code != 200:
                logger.error(f"人間介入応答エラー: {response.text}")
                return {"error": "応答に失敗しました", "intervention_id": intervention_id}
            
            return response.json()
        except Exception as e:
            logger.error(f"人間介入応答エラー: {e}")
            if DEBUG_MODE:
                logger.debug(f"例外詳細: {traceback.format_exc()}")
            return {"error": str(e), "intervention_id": intervention_id}
    
    def test_expense_report_scenario(self):
        """出張精算書類検証シナリオのテスト"""
        logger.info("==== 出張精算書類検証シナリオのテスト開始 ====")
        
        try:
            # サンプルデータ準備
            sample_data = self._prepare_sample_data()
            expense_report_file = sample_data["sample_001"]["expense_report"]
            
            # 監査手続き作成
            procedure_id = self._create_audit_procedure(
                title="出張経費の適正性検証",
                description="出張精算書類が社内規程に準拠しているかを検証する。特に金額の適正性、承認プロセスの適切性を確認する。",
                risk_areas=["経費精算", "不正支出", "承認プロセス"]
            )
            
            # サンプルアップロード
            sample_id = self._upload_sample(procedure_id, expense_report_file)
            
            # ワークフロー開始
            workflow_id = self._start_workflow(procedure_id, sample_id)
            
            # ワークフロー状態監視
            workflow_status = self._poll_workflow_status(workflow_id)
            
            # 人間介入が必要な場合の対応
            interventions = self._check_human_interventions(workflow_id)
            for intervention in interventions:
                logger.info(f"人間介入が必要です: {intervention['title']}")
                # シンプルな応答
                self._respond_to_intervention(
                    intervention["id"], 
                    "これは適切な出張経費です。承認します。"
                )
            
            # 最終的なワークフロー状態を再度確認
            if interventions:
                workflow_status = self._poll_workflow_status(workflow_id)
            
            # 結果取得
            results = self._get_workflow_results(workflow_id)
            
            logger.info(f"出張精算書類検証シナリオの実行結果: {workflow_status['status']}")
            return {
                "workflow_id": workflow_id,
                "status": workflow_status["status"],
                "results": results
            }
        except Exception as e:
            logger.error(f"出張精算書類シナリオエラー: {e}")
            if DEBUG_MODE:
                logger.debug(f"例外詳細: {traceback.format_exc()}")
            return {"error": str(e)}
    
    def test_transaction_record_scenario(self):
        """取引記録検証シナリオのテスト"""
        logger.info("==== 取引記録検証シナリオのテスト開始 ====")
        
        try:
            # サンプルデータ準備
            sample_data = self._prepare_sample_data()
            transaction_file = sample_data["sample_005"]["transaction"]
            
            # 監査手続き作成
            procedure_id = self._create_audit_procedure(
                title="取引記録の検証",
                description="取引記録が適切に承認され、正確に記録されているかを検証する。特に高額取引における承認権限の適切性を確認する。",
                risk_areas=["取引記録", "承認権限", "不正取引"]
            )
            
            # サンプルアップロード
            sample_id = self._upload_sample(procedure_id, transaction_file)
            
            # ワークフロー開始
            workflow_id = self._start_workflow(procedure_id, sample_id)
            
            # ワークフロー状態監視
            workflow_status = self._poll_workflow_status(workflow_id)
            
            # 人間介入が必要な場合の対応
            interventions = self._check_human_interventions(workflow_id)
            for intervention in interventions:
                logger.info(f"人間介入が必要です: {intervention['title']}")
                # シンプルな応答
                self._respond_to_intervention(
                    intervention["id"], 
                    "この取引記録は適切に承認されています。承認します。"
                )
            
            # 最終的なワークフロー状態を再度確認
            if interventions:
                workflow_status = self._poll_workflow_status(workflow_id)
            
            # 結果取得
            results = self._get_workflow_results(workflow_id)
            
            logger.info(f"取引記録検証シナリオの実行結果: {workflow_status['status']}")
            return {
                "workflow_id": workflow_id,
                "status": workflow_status["status"],
                "results": results
            }
        except Exception as e:
            logger.error(f"取引記録シナリオエラー: {e}")
            if DEBUG_MODE:
                logger.debug(f"例外詳細: {traceback.format_exc()}")
            return {"error": str(e)}
    
    def run_all_tests(self):
        """すべてのテストシナリオを実行"""
        results = {}
        
        # 出張精算書類検証シナリオ
        try:
            results["expense_report"] = self.test_expense_report_scenario()
        except Exception as e:
            logger.error(f"出張精算書類シナリオエラー: {e}")
            results["expense_report"] = {"error": str(e)}
        
        # 取引記録検証シナリオ
        try:
            results["transaction_record"] = self.test_transaction_record_scenario()
        except Exception as e:
            logger.error(f"取引記録シナリオエラー: {e}")
            results["transaction_record"] = {"error": str(e)}
        
        # 結果サマリー
        summary = {
            "expense_report_status": results.get("expense_report", {}).get("status", "error"),
            "transaction_record_status": results.get("transaction_record", {}).get("status", "error"),
            "timestamp": datetime.now().isoformat()
        }
        
        # 結果をJSONファイルに出力
        output_file = os.path.join(self.test_dir, f"usecase_test_results_{int(time.time())}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({"summary": summary, "details": results}, f, ensure_ascii=False, indent=2)
        
        logger.info(f"テスト結果を保存しました: {output_file}")
        return results

async def main():
    """メイン処理"""
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    logger.info("ユースケーステストを開始します")
    
    # テスター作成
    tester = UseCaseTester()
    
    # すべてのテスト実行
    results = tester.run_all_tests()
    
    # 結果をコンソールに表示
    print("\n===== テスト結果サマリー =====")
    expense_status = results.get("expense_report", {}).get("status", "エラー")
    transaction_status = results.get("transaction_record", {}).get("status", "エラー")
    
    print(f"出張精算書類検証シナリオ: {expense_status}")
    print(f"取引記録検証シナリオ: {transaction_status}")
    
    print("\nすべてのテストが完了しました")

if __name__ == "__main__":
    asyncio.run(main()) 