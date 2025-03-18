"""
予算変更承認シナリオのエンドツーエンドテスト

このモジュールでは、予算変更承認に関する監査シナリオを
エンドツーエンドでテストし、以下の機能を検証します：
1. エージェント間のメッセージ連携
2. 監査人（人間）との対話
3. 規程情報の取得と判断
4. 結果の評価と報告
"""

import os
import uuid
import asyncio
import pytest
import pytest_asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from loguru import logger

from src.core.config import settings
from src.agents.agent_a import AgentA
from src.agents.agent_b import AgentB
from src.agents.agent_c import AgentC
from src.agents.agent_d import AgentD
from src.core.messaging import MessageBroker, MessageClient
from src.core.message_handler import MessageTypeHandler
from src.models.schema import MessageType, MessagePriority, AuditSample, AgentMessage
from src.core.agent_workflow import run_workflow


# 人間対話マネージャーのモッククラス - これは外部依存のため最小限のモックとして残す
class HumanInteractionManager:
    """人間との対話を管理するモッククラス"""
    
    async def get_human_response(self, query_id: str, query: str = None) -> str:
        """人間からの応答を取得する（モック）"""
        # テスト用のモック応答を返す
        return f"モック応答: 予算変更承認規程によると、申請金額から20%以内の減額は部長権限で調整可能です。{query or ''}"
    
    async def request_information(self, query: str, context: Dict[str, Any] = None) -> str:
        """人間に情報を要求する（モック）"""
        # テスト用のクエリIDを生成して返す
        query_id = str(uuid.uuid4())
        logger.info(f"人間に情報要求を送信: {query}, query_id: {query_id}")
        return query_id


# 規程リポジトリのモッククラス - これも外部依存のため最小限のモックとして残す
class RegulationRepository:
    """規程情報を管理するモッククラス"""
    
    def __init__(self, db_session=None):
        """初期化 - db_sessionは実際には使わないがインターフェース互換性のために残す"""
        self.db_session = db_session
    
    async def search_regulations(self, query: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """規程情報を検索する（モック）"""
        # テスト用のモック結果を返す
        logger.info(f"規程の検索: {query}")
        return [{
            "id": "REG-001",
            "title": "予算変更承認規程",
            "content": "1. 申請金額から20%以内の減額は部長権限で調整可能\n2. 20%超の減額は申請書の再提出が必要\n3. 減額理由と承認者の記録が必須",
            "effective_date": "2022-01-01"
        }]
    
    async def get_regulation_by_id(self, regulation_id: str) -> Dict[str, Any]:
        """規程IDから規程情報を取得する（モック）"""
        # テスト用のモック結果を返す
        logger.info(f"規程IDによる取得: {regulation_id}")
        return {
            "id": regulation_id,
            "title": "予算変更承認規程",
            "content": "1. 申請金額から20%以内の減額は部長権限で調整可能\n2. 20%超の減額は申請書の再提出が必要\n3. 減額理由と承認者の記録が必須",
            "effective_date": "2022-01-01"
        }


# マークを設定
pytestmark = [
    pytest.mark.smoke,  # 疎通テスト用マーカーを追加
    pytest.mark.e2e,
    pytest.mark.scenario,
    pytest.mark.asyncio,
]


class TestBudgetApprovalScenario:
    """予算変更承認シナリオのテストクラス"""
    
    @pytest_asyncio.fixture
    async def setup_test_environment(self):
        """テスト環境のセットアップ"""
        # テスト用のサンプルデータ
        sample_id = "ID-005"
        sample_data = {
            "id": sample_id,
            "type": "budget_approval",
            "application_amount": 820000,  # 申請金額
            "approved_amount": 780000,     # 承認金額
            "approval_type": "条件付承認",
            "approver": "佐藤次郎",
            "approver_title": "購買部長",
            "approval_date": "2023-02-16",
            "execution_date": "2023-02-20",
            "remarks": "予算調整のため減額",
        }
        
        # 実際のメッセージブローカーを初期化
        broker = MessageBroker()
        broker.message_queue = {}
        broker.priority_queue = {}
        broker.message_history = []
        
        # サンプルの作成
        audit_sample = AuditSample(**sample_data)
        
        # エージェントを初期化
        agent_a = AgentA(message_client=MessageClient(broker=broker, agent_id="agent_a"))
        agent_b = AgentB(message_client=MessageClient(broker=broker, agent_id="agent_b"))
        agent_c = AgentC(message_client=MessageClient(broker=broker, agent_id="agent_c"))
        agent_d = AgentD(message_client=MessageClient(broker=broker, agent_id="agent_d"))
        
        # メッセージタイプハンドラーの初期化
        message_handler = MessageTypeHandler()
        
        # メッセージハンドラーの登録
        for agent in [agent_a, agent_b, agent_c, agent_d]:
            agent.message_client.register_message_handlers(message_handler)
        
        # テスト用の設定
        settings.TESTING = True
        settings.MOCK_HUMAN_INTERACTION = True
        
        yield {
            "agents": {
                "a": agent_a,
                "b": agent_b,
                "c": agent_c,
                "d": agent_d
            },
            "broker": broker,
            "sample": audit_sample,
            "message_handler": message_handler
        }
        
        # クリーンアップとモックの復元
        broker.message_queue = {}
        broker.priority_queue = {}
        broker.message_history = []
    
    @pytest.mark.e2e
    async def test_budget_approval_scenario(self, setup_test_environment):
        """予算変更承認シナリオのE2Eテスト"""
        env = setup_test_environment
        agent_a = env["agents"]["a"]
        agent_b = env["agents"]["b"]
        agent_c = env["agents"]["c"]
        agent_d = env["agents"]["d"]
        sample = env["sample"]
        broker = env["broker"]
        message_handler = env["message_handler"]
        
        logger.info("予算変更承認シナリオのE2Eテストを開始します")
        
        # メッセージハンドラーの設定
        message_handler.register_handler(MessageType.WORKFLOW_START, lambda msg, ctx: {"status": "handled"})
        message_handler.register_handler(MessageType.WORKFLOW_UPDATE, lambda msg, ctx: {"status": "handled"})
        message_handler.register_handler(MessageType.WORKFLOW_COMPLETE, lambda msg, ctx: {"status": "handled"})
        message_handler.register_handler(MessageType.HUMAN_QUERY, lambda msg, ctx: {"status": "handled", "response": "承認"})
        message_handler.register_handler(MessageType.DATA_REQUEST, lambda msg, ctx: {"status": "handled"})
        message_handler.register_handler(MessageType.DATA_RESPONSE, lambda msg, ctx: {"status": "handled"})
        
        # テストデータの準備
        budget_change_data = {
            "department": "IT部門",
            "current_budget": 1000000,
            "requested_budget": 1500000,
            "reason": "クラウドインフラの拡張",
            "urgency": "high",
            "submitted_by": "山田太郎",
            "submitted_at": datetime.now().isoformat()
        }
        
        # ワークフローの開始
        workflow_id = str(uuid.uuid4())
        context_id = str(uuid.uuid4())
        
        # エージェントAがワークフローを開始
        start_message = await agent_a.message_client.send_message(
            to_agent="agent_b",
            message_type=MessageType.WORKFLOW_START,
            content={
                "workflow_id": workflow_id,
                "context_id": context_id,
                "data": budget_change_data
            }
        )
        
        assert start_message is not None, "ワークフロー開始メッセージの送信に失敗しました"
        
        # エージェントBが予算変更の評価を実行
        evaluation_result = await agent_b.evaluate_budget_change(budget_change_data)
        assert evaluation_result["status"] == "completed", "予算変更の評価に失敗しました"
        
        # エージェントCが結果を分析
        analysis_result = await agent_c.analyze_evaluation(evaluation_result)
        assert analysis_result["status"] == "completed", "評価結果の分析に失敗しました"
        
        # エージェントDが報告書を生成
        report = await agent_d.generate_report(analysis_result)
        assert report["status"] == "completed", "報告書の生成に失敗しました"
        
        # ワークフローの完了確認
        workflow_complete = await agent_a.message_client.send_message(
            to_agent="all",
            message_type=MessageType.WORKFLOW_COMPLETE,
            content={
                "workflow_id": workflow_id,
                "status": "success",
                "summary": report["summary"]
            }
        )
        
        assert workflow_complete is not None, "ワークフロー完了メッセージの送信に失敗しました"
        
        # メッセージ履歴の確認
        message_history = broker.message_history
        assert len(message_history) > 0, "メッセージ履歴が空です"
        
        # 各ステップでのメッセージタイプを確認
        message_types = [msg.message_type for msg in message_history]
        expected_types = [
            MessageType.WORKFLOW_START,
            MessageType.DATA_REQUEST,
            MessageType.DATA_RESPONSE,
            MessageType.HUMAN_QUERY,
            MessageType.WORKFLOW_UPDATE,
            MessageType.WORKFLOW_COMPLETE
        ]
        
        for expected_type in expected_types:
            assert expected_type in message_types, f"期待されるメッセージタイプ {expected_type} が履歴に存在しません"
        
        logger.info("予算変更承認シナリオのE2Eテストが正常に完了しました") 