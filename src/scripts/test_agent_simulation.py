"""
エージェント間のやり取りシミュレーションテスト - APIサーバーを使用せずにエージェント間の対話をシミュレート

実行方法:
    python -m src.scripts.test_agent_simulation
"""

import os
import sys
import json
from src.utils import json_utils
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


class AgentSimulator:
    """エージェント間のやり取りをシミュレートするクラス"""
    
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
        
        # 会話履歴の初期化
        self.conversation_history = []
        
        logger.info("エージェントシミュレータが初期化されました")
    
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
            f.write("2025年2月11日\n")
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
    
    async def agent_a_to_agent_b_instruction(self, sample_id, files):
        """エージェントAからエージェントBへの指示シミュレーション"""
        instruction = f"""【エージェントA】{sample_id}の指示発行
「サンプルID-{sample_id}の出張精算書類を検証してください。出張申請書、領収書キャプチャ、精算承認画面を照合し、金額、日付、承認者情報の整合性を確認してください。判断基準は以下の通りです：
- 出張期間と領収書日付の整合性
- 申請金額と領収書金額の一致
- 承認者の適切性（権限者による承認）
」"""
        
        self.conversation_history.append({
            "agent": "A",
            "to_agent": "B",
            "message_type": "instruction",
            "content": instruction,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"エージェントAがエージェントBに指示を送信しました: {sample_id}")
        return instruction
    
    async def agent_b_challenges_to_agent_a(self, sample_id, files):
        """エージェントBからエージェントAへの課題提起シミュレーション"""
        # 課題を発見する
        challenges = f"""【エージェントB】{sample_id}の課題と対応策提案
「サンプルID-{sample_id}の領収書キャプチャに関して以下の課題があります：
1. 領収書の日付（2月11日）と精算書の出張期間（2月10日～12日）の一致確認が必要
2. 領収書の宿泊料金（24,000円）と精算書の宿泊費（24,000円）の一致確認が必要
3. 承認者（田中部長）の適切な権限があるか確認が必要

対応策として提案します：
1. 日付検証ツールで出張期間内に領収書日付が含まれるか確認
2. 金額照合ツールで領収書金額と精算書記載額が一致するか検証
3. 承認者権限照合ツールで田中部長の決裁権限を確認
これらのツールを実行してよろしいでしょうか？」"""
        
        self.conversation_history.append({
            "agent": "B",
            "to_agent": "A",
            "message_type": "challenge",
            "content": challenges,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"エージェントBがエージェントAに課題と対応策を送信しました: {sample_id}")
        return challenges
    
    async def agent_a_approval(self, sample_id):
        """エージェントAがツール実行を承認するシミュレーション"""
        approval = f"""【エージェントA】ツール実行承認
「提案された対応策を実行してください：
1. 日付検証ツールで出張期間（2月10日～12日）と領収書日付（2月11日）の整合性を確認
2. 金額照合ツールで領収書金額（24,000円）と精算書記載額（24,000円）の一致を検証
3. 承認者名「田中部長」について社員マスタと照合し役職・決裁権限を確認
実行結果を報告してください。」"""
        
        self.conversation_history.append({
            "agent": "A",
            "to_agent": "B",
            "message_type": "approval",
            "content": approval,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"エージェントAがツール実行を承認しました: {sample_id}")
        return approval
    
    async def agent_b_tool_execution(self, sample_id, files, tool_name, params):
        """エージェントBがツールを実行するシミュレーション"""
        tool_request = f"""【エージェントB】{tool_name}呼び出し
「以下のパラメータでツールを実行します：
{json_utils.json_serialize(params)}
」"""
        
        self.conversation_history.append({
            "agent": "B",
            "to_agent": "tool",
            "tool_name": tool_name,
            "message_type": "tool_request",
            "content": tool_request,
            "params": params,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"エージェントBがツールを呼び出しました: {tool_name}")
        
        # 実際のツール実行
        result = None
        if tool_name == "image_processor":
            result = await self.image_tool.execute(params)
        elif tool_name == "data_validator":
            result = await self.data_tool.execute(params)
        elif tool_name == "excel_analyzer":
            result = await self.excel_tool.execute(params)
        elif tool_name == "document_parser":
            result = await self.doc_tool.execute(params)
        
        tool_response = f"""【{tool_name}】処理結果
「処理完了：
{json_utils.json_serialize(result.data if result else {})}
ステータス: {result.status if result else 'error'}
」"""
        
        self.conversation_history.append({
            "agent": "tool",
            "to_agent": "B",
            "tool_name": tool_name,
            "message_type": "tool_response",
            "content": tool_response,
            "result": result.data if result else {},
            "status": result.status if result else "error",
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"ツールが結果を返しました: {tool_name}")
        return tool_response
    
    async def agent_b_to_agent_a_results(self, sample_id):
        """エージェントBからエージェントAへの結果報告シミュレーション"""
        # ツール実行結果を基に報告を作成
        results = f"""【エージェントB】ツール実行結果と分析
「ツール実行結果の分析：
1. 日付検証ツールの結果：領収書日付（2月11日）は出張期間（2月10日～12日）内に含まれており整合性を確認
2. 金額照合ツールの結果：領収書金額（24,000円）と精算書記載額（24,000円）の一致を確認
3. 承認者権限照合ツールの結果：田中部長は部長職で決裁権限が10万円以下であることを確認

総合判断：出張精算は適切に処理されていると判断します。ただし、追加で以下の確認が必要です：
- 出張規程に基づく日当の妥当性確認
- 交通費の領収書確認（現在のサンプルには含まれていない）

これらの追加確認は必要でしょうか？」"""
        
        self.conversation_history.append({
            "agent": "B",
            "to_agent": "A",
            "message_type": "results",
            "content": results,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"エージェントBがエージェントAに結果を報告しました: {sample_id}")
        return results
    
    async def agent_a_additional_info(self, sample_id):
        """エージェントAからエージェントBへの追加情報提供シミュレーション"""
        additional_info = f"""【エージェントA】追加情報の提供
「出張規程情報を照会しました：
- 日当は1日3,000円で正しいです
- 交通費については後日領収書提出予定と備考欄に記載があるため、現段階では問題ありません
この情報を踏まえて最終判断を行ってください。」"""
        
        self.conversation_history.append({
            "agent": "A",
            "to_agent": "B",
            "message_type": "additional_info",
            "content": additional_info,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"エージェントAがエージェントBに追加情報を提供しました: {sample_id}")
        return additional_info
    
    async def agent_b_final_report(self, sample_id):
        """エージェントBからエージェントCへの最終報告シミュレーション"""
        final_report = f"""【エージェントB】{sample_id}の検証結果
「サンプルID-{sample_id}の検証結果：
- 出張期間（2025/2/10-2/12）と領収書日付（2025/2/11）の整合性を確認
- 宿泊費24,000円は領収書金額と一致
- 日当は規程通り1日3,000円×3日=9,000円で適切
- 承認者（田中部長）は当該金額（66,000円）に対して適切な権限を保有
- 交通費領収書は後日提出予定と備考欄に記載あり

判定: 全項目について適切に処理されていることを確認。承認権限、金額整合性、書類の適切性をツールにより詳細検証済み。
検証完了タイムスタンプ: {datetime.now().isoformat()}」"""
        
        self.conversation_history.append({
            "agent": "B",
            "to_agent": "C",
            "message_type": "final_report",
            "content": final_report,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"エージェントBがエージェントCに最終報告を送信しました: {sample_id}")
        return final_report
    
    async def agent_c_acknowledgement(self, sample_id):
        """エージェントCからの確認応答シミュレーション"""
        ack = f"""【エージェントC】{sample_id}の報告受領確認
「サンプルID-{sample_id}の検証結果を受領しました。結果は監査結果データベースに記録され、最終報告書に含められます。」"""
        
        self.conversation_history.append({
            "agent": "C",
            "to_agent": "B",
            "message_type": "acknowledgement",
            "content": ack,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"エージェントCが報告を確認しました: {sample_id}")
        return ack
    
    async def simulate_expense_report_scenario(self):
        """出張精算書類検証シナリオのシミュレーション"""
        logger.info("==== 出張精算書類検証シナリオのシミュレーション開始 ====")
        
        # サンプルデータの準備
        sample_data = self._prepare_sample_data()
        sample_id = "001"
        files = sample_data["sample_001"]
        
        # エージェント間のやり取りをシミュレート
        steps = []
        
        # ステップ1: エージェントAからエージェントBへの指示
        steps.append({
            "description": "エージェントAからエージェントBへの指示",
            "content": await self.agent_a_to_agent_b_instruction(sample_id, files)
        })
        
        # ステップ2: エージェントBがエージェントAに課題と対応策を提案
        steps.append({
            "description": "エージェントBからエージェントAへの課題と対応策提案",
            "content": await self.agent_b_challenges_to_agent_a(sample_id, files)
        })
        
        # ステップ3: エージェントAがツール実行を承認
        steps.append({
            "description": "エージェントAからのツール実行承認",
            "content": await self.agent_a_approval(sample_id)
        })
        
        # ステップ4: エージェントBが日付検証ツールを実行
        date_params = {
            "operation": "verify_date_range",
            "date_value": "2025-02-11",
            "date_range_start": "2025-02-10",
            "date_range_end": "2025-02-12"
        }
        steps.append({
            "description": "日付検証ツールの実行",
            "content": await self.agent_b_tool_execution(sample_id, files, "data_validator", date_params)
        })
        
        # ステップ5: エージェントBが金額照合ツールを実行
        amount_params = {
            "operation": "verify_amount",
            "amount1": "24000",
            "amount2": "24000",
            "comparison_type": "equal"
        }
        steps.append({
            "description": "金額照合ツールの実行",
            "content": await self.agent_b_tool_execution(sample_id, files, "data_validator", amount_params)
        })
        
        # ステップ6: エージェントBが承認者権限確認ツールを実行
        auth_params = {
            "operation": "check_authority",
            "employee_id": "E004",
            "approval_category": "travel_expense",
            "amount": "66000"
        }
        steps.append({
            "description": "承認者権限確認ツールの実行",
            "content": await self.agent_b_tool_execution(sample_id, files, "data_validator", auth_params)
        })
        
        # ステップ7: エージェントBがエージェントAに分析結果と追加質問を送信
        steps.append({
            "description": "エージェントBからエージェントAへの結果報告と追加質問",
            "content": await self.agent_b_to_agent_a_results(sample_id)
        })
        
        # ステップ8: エージェントAが追加情報を提供
        steps.append({
            "description": "エージェントAからの追加情報提供",
            "content": await self.agent_a_additional_info(sample_id)
        })
        
        # ステップ9: エージェントBがエージェントCに最終報告
        steps.append({
            "description": "エージェントBからエージェントCへの最終報告",
            "content": await self.agent_b_final_report(sample_id)
        })
        
        # ステップ10: エージェントCが確認応答
        steps.append({
            "description": "エージェントCからの確認応答",
            "content": await self.agent_c_acknowledgement(sample_id)
        })
        
        logger.info(f"出張精算書類検証シナリオのシミュレーション完了: {len(steps)}ステップ")
        
        return {
            "scenario": "expense_report",
            "sample_id": sample_id,
            "steps": steps,
            "conversation_history": self.conversation_history
        }
    
    async def simulate_transaction_record_scenario(self):
        """取引記録検証シナリオのシミュレーション"""
        logger.info("==== 取引記録検証シナリオのシミュレーション開始 ====")
        
        # サンプルデータの準備
        sample_data = self._prepare_sample_data()
        sample_id = "005"
        files = sample_data["sample_005"]
        
        # エージェント間のやり取りをシミュレート（エクセル解析ツールを使用するケース）
        steps = []
        
        # エージェントAからエージェントBへの指示（エクセル解析を含む）
        instruction = f"""【エージェントA】{sample_id}の指示発行
「サンプルID-{sample_id}の取引記録検証を行ってください。ただし、取引履歴がCSV形式で構造化されています。最初にエクセル解析ツールを使用して取引データを構造化し、以下の検証を行ってください：
- 取引ID T-20250214-0023 の取引情報の整合性
- 取引金額の適切性
- 承認者の適切性（権限者による承認）
これらの検証には、まずCSVデータの構造解析が必要です。」"""
        
        self.conversation_history.append({
            "agent": "A",
            "to_agent": "B",
            "message_type": "instruction",
            "content": instruction,
            "timestamp": datetime.now().isoformat()
        })
        
        steps.append({
            "description": "エージェントAからエージェントBへの指示（エクセル解析を含む）",
            "content": instruction
        })
        
        # エージェントBがエクセル解析ツールを使用
        excel_params = {
            "operation": "analyze_structure",
            "file_path": files["transaction"]
        }
        
        excel_analysis = await self.agent_b_tool_execution(sample_id, files, "excel_analyzer", excel_params)
        steps.append({
            "description": "エージェントBがエクセル解析ツールを使用",
            "content": excel_analysis
        })
        
        # エージェントBがデータ抽出ツールを使用
        data_params = {
            "operation": "extract_data",
            "file_path": files["transaction"],
            "filter": {"取引ID": "T-20250214-0023"}
        }
        
        data_extraction = await self.agent_b_tool_execution(sample_id, files, "excel_analyzer", data_params)
        steps.append({
            "description": "エージェントBがデータ抽出ツールを使用",
            "content": data_extraction
        })
        
        # エージェントBからエージェントAへの不明点（金額変更の妥当性）
        question = f"""【エージェントB】{sample_id}の課題と対応策提案
「サンプルID-{sample_id}の取引データ解析結果から以下の課題があります：
1. 取引金額が820,000円と高額なため、承認者の権限確認が必要
2. 機器購入のカテゴリでの承認プロセスの適切性確認が必要

対応策として提案します：
1. 承認者「佐藤次郎」の役職・決裁権限確認
2. 機器購入カテゴリの承認ルール確認
これらのツールを実行してよろしいでしょうか？」"""
        
        self.conversation_history.append({
            "agent": "B",
            "to_agent": "A",
            "message_type": "challenge",
            "content": question,
            "timestamp": datetime.now().isoformat()
        })
        
        steps.append({
            "description": "エージェントBからエージェントAへの不明点（金額変更の妥当性）",
            "content": question
        })
        
        # エージェントAからの追加情報提供
        info = f"""【エージェントA】ツール実行承認
「提案された対応策を実行してください：
1. 承認者「佐藤次郎」の役職・決裁権限確認ツールを実行
2. 機器購入カテゴリの承認ルール確認ツールを実行
実行結果を報告してください。」"""
        
        self.conversation_history.append({
            "agent": "A",
            "to_agent": "B",
            "message_type": "approval",
            "content": info,
            "timestamp": datetime.now().isoformat()
        })
        
        steps.append({
            "description": "エージェントAからの追加情報提供",
            "content": info
        })
        
        # エージェントBが承認者権限確認ツールを実行
        auth_params = {
            "operation": "check_authority",
            "employee_id": "E005",
            "approval_category": "equipment_purchase",
            "amount": "820000"
        }
        
        auth_result = await self.agent_b_tool_execution(sample_id, files, "data_validator", auth_params)
        steps.append({
            "description": "エージェントBが承認者権限確認ツールを実行",
            "content": auth_result
        })
        
        # エージェントBが機器購入カテゴリ承認ルール確認ツールを実行
        rule_params = {
            "operation": "check_approval_rule",
            "category": "equipment_purchase",
            "amount": "820000"
        }
        
        rule_result = await self.agent_b_tool_execution(sample_id, files, "data_validator", rule_params)
        steps.append({
            "description": "エージェントBが機器購入カテゴリ承認ルール確認ツールを実行",
            "content": rule_result
        })
        
        # エージェントBからエージェントAへの結果報告
        report = f"""【エージェントB】ツール実行結果と分析
「ツール実行結果の分析：
1. 承認者「佐藤次郎」は購買部長で、決裁権限は100万円までであることを確認
2. 機器購入カテゴリでは、50万円以上の取引は部長以上の承認が必要というルールを確認
3. 取引金額820,000円は佐藤次郎の決裁権限内（100万円以下）であることを確認
4. 取引は適切に承認されていると判断

追加質問はありません。検証を完了します。」"""
        
        self.conversation_history.append({
            "agent": "B",
            "to_agent": "A",
            "message_type": "results",
            "content": report,
            "timestamp": datetime.now().isoformat()
        })
        
        steps.append({
            "description": "エージェントBからエージェントAへの結果報告",
            "content": report
        })
        
        # エージェントBからエージェントCへの最終報告
        final_report = f"""【エージェントB】{sample_id}の検証結果
「サンプルID-{sample_id}の検証結果：
- 取引ID T-20250214-0023 の取引情報（機器購入、820,000円）を確認
- 承認者（佐藤次郎・購買部長）の決裁権限（100万円以下）は適切
- 機器購入カテゴリでの承認プロセス（50万円以上は部長以上の承認が必要）を遵守

判定: すべての項目が適切に処理・承認されていることを確認。エクセル解析と権限照合ツールにより詳細検証済み。
検証完了タイムスタンプ: {datetime.now().isoformat()}」"""
        
        self.conversation_history.append({
            "agent": "B",
            "to_agent": "C",
            "message_type": "final_report",
            "content": final_report,
            "timestamp": datetime.now().isoformat()
        })
        
        steps.append({
            "description": "エージェントBからエージェントCへの最終報告",
            "content": final_report
        })
        
        # エージェントCからの確認応答
        ack = f"""【エージェントC】{sample_id}の報告受領確認
「サンプルID-{sample_id}の検証結果を受領しました。結果は監査結果データベースに記録され、最終報告書に含められます。」"""
        
        self.conversation_history.append({
            "agent": "C",
            "to_agent": "B",
            "message_type": "acknowledgement",
            "content": ack,
            "timestamp": datetime.now().isoformat()
        })
        
        steps.append({
            "description": "エージェントCからの確認応答",
            "content": ack
        })
        
        logger.info(f"取引記録検証シナリオのシミュレーション完了: {len(steps)}ステップ")
        
        return {
            "scenario": "transaction_record",
            "sample_id": sample_id,
            "steps": steps,
            "conversation_history": self.conversation_history
        }
    
    async def simulate_all_scenarios(self):
        """すべてのシナリオをシミュレート"""
        results = {}
        
        # 出張精算書類検証シナリオ
        expense_result = await self.simulate_expense_report_scenario()
        results["expense_report"] = expense_result
        
        # 会話履歴を一度リセット
        self.conversation_history = []
        
        # 取引記録検証シナリオ
        transaction_result = await self.simulate_transaction_record_scenario()
        results["transaction_record"] = transaction_result
        
        # 結果をJSONファイルに出力
        output_file = os.path.join(self.test_dir, f"agent_simulation_results_{int(time.time())}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"シミュレーション結果を保存しました: {output_file}")
        return results


def format_simulation_results(results):
    """シミュレーション結果を表示用にフォーマット"""
    output = []
    
    # 出張精算書類シナリオ
    output.append("# 出張精算書類検証シナリオ")
    output.append("")
    
    expense_steps = results["expense_report"]["steps"]
    for i, step in enumerate(expense_steps, 1):
        output.append(f"## ステップ {i}: {step['description']}")
        output.append("```")
        output.append(step['content'])
        output.append("```")
        output.append("")
    
    # 取引記録検証シナリオ
    output.append("# 取引記録検証シナリオ")
    output.append("")
    
    transaction_steps = results["transaction_record"]["steps"]
    for i, step in enumerate(transaction_steps, 1):
        output.append(f"## ステップ {i}: {step['description']}")
        output.append("```")
        output.append(step['content'])
        output.append("```")
        output.append("")
    
    return "\n".join(output)


async def main():
    """メイン処理"""
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    logger.info("エージェント間のやり取りシミュレーションを開始します")
    
    # シミュレータ作成
    simulator = AgentSimulator()
    
    # すべてのシナリオをシミュレート
    results = await simulator.simulate_all_scenarios()
    
    # 結果を表示
    formatted_results = format_simulation_results(results)
    
    # 結果をファイルに保存
    output_markdown = os.path.join(Path(__file__).parent.parent.parent, "data", "test", f"agent_simulation_results_{int(time.time())}.md")
    with open(output_markdown, "w", encoding="utf-8") as f:
        f.write(formatted_results)
    
    print("\n===== シミュレーション結果サマリー =====")
    print(f"出張精算書類検証シナリオ: {len(results['expense_report']['steps'])}ステップ")
    print(f"取引記録検証シナリオ: {len(results['transaction_record']['steps'])}ステップ")
    print(f"\n詳細な結果はこちらに保存されました: {output_markdown}")
    print("\nすべてのシミュレーションが完了しました")


if __name__ == "__main__":
    asyncio.run(main()) 