"""
エージェント間通信機能のテスト
"""

import asyncio
import uuid
import time
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from loguru import logger

from src.core.agent_base import AgentBase, AgentState
from src.core.messaging import MessageClient, AgentMessage, MessageBroker
from src.core.context_manager import ContextClient, SharedContext
from src.models.schema import MessageType, MessagePriority
from src.models.repositories import MessageLogRepository
from src.utils.audit_trail_utils import record_message_log, get_agent_conversation
from src.tests.conftest import mock_llm, patch_llm_client


# 警告を回避するために通常のクラスとして定義し、テストクラスとしては使用しない
class CustomAgentState(AgentState):
    """テスト用のエージェント状態"""
    task_results: List[Dict[str, Any]] = []
    received_contexts: List[str] = []


# 警告を回避するために通常のクラスとして定義し、テストクラスとしては使用しない
class CustomAgent(AgentBase[CustomAgentState]):
    """テスト用のエージェント実装"""
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        メッセージ処理
        
        Args:
            message: 処理するメッセージ
            
        Returns:
            処理結果
        """
        logger.info(f"エージェント {self.agent_id} がメッセージを処理: {message['message_type']}")
        
        # メッセージタイプに応じた処理
        result = {"status": "processed", "agent_id": self.agent_id}
        
        if message["message_type"] == MessageType.COMMAND:
            command = message["content"].get("command")
            
            if command == "create_context":
                # コンテキスト作成
                workflow_id = message["content"].get("workflow_id", f"wf-{uuid.uuid4().hex[:8]}")
                initial_data = message["content"].get("data", {})
                
                context = self.create_context(workflow_id, initial_data)
                result["context_id"] = context.context_id
                result["workflow_id"] = workflow_id
                
            elif command == "update_context":
                # コンテキスト更新
                context_id = message["content"].get("context_id")
                data_updates = message["content"].get("data", {})
                
                if context_id:
                    updated = self.update_context_data(data_updates, context_id)
                    result["updated"] = updated
                    result["context_id"] = context_id
                else:
                    result["error"] = "コンテキストIDが指定されていません"
            
            elif command == "echo":
                # エコー（単純な応答）
                result["echo_content"] = message["content"].get("data", {})
        
        elif message["message_type"] == MessageType.NOTIFICATION:
            # 通知メッセージ - 情報を記録するだけ
            result["notification_received"] = True
            result["notification_content"] = message["content"]
        
        # コンテキストIDがある場合は記録
        if message.get("context_id") and message["context_id"] not in self.state.received_contexts:
            self.state.received_contexts.append(message["context_id"])
        
        # 処理結果を状態に保存
        self.state.task_results.append(result)
        
        return result


@pytest.fixture
def reset_agent_state():
    """テスト間でエージェント状態をリセットするフィクスチャ"""
    # テスト前の処理
    CustomAgentState.task_results = []
    CustomAgentState.received_contexts = []
    
    yield
    
    # テスト後の処理
    CustomAgentState.task_results = []
    CustomAgentState.received_contexts = []


@pytest.mark.asyncio
async def test_agent_messaging(clean_test_data, reset_agent_state):
    """エージェント間のメッセージング機能をテスト"""
    # 複数のエージェントを作成
    agent_a = CustomAgent("agent_a", CustomAgentState)
    agent_b = CustomAgent("agent_b", CustomAgentState)
    agent_c = CustomAgent("agent_c", CustomAgentState)
    
    # ワークフローIDを生成
    workflow_id = f"wf-test-{uuid.uuid4().hex[:8]}"
    
    # エージェントAからBへコマンドメッセージを送信
    message_id = agent_a.send_message(
        to_agent="agent_b",
        message_type=MessageType.COMMAND,
        content={
            "command": "create_context",
            "workflow_id": workflow_id,
            "data": {"task": "テストタスク", "priority": "high"}
        },
        workflow_id=workflow_id,
        requires_response=True
    )
    
    # エージェントBがメッセージを処理
    results = await agent_b.get_and_process_messages()
    
    # 処理結果を確認
    assert len(results) == 1
    assert results[0]["status"] == "processed"
    assert "context_id" in results[0]
    assert results[0]["workflow_id"] == workflow_id
    
    # 作成されたコンテキストIDを取得
    context_id = results[0]["context_id"]
    
    # エージェントBからCへコンテキスト情報を含むメッセージを送信
    agent_b.send_message(
        to_agent="agent_c",
        message_type=MessageType.NOTIFICATION,
        content={
            "message": "新しいコンテキストが作成されました",
            "context_details": {"task": "テストタスク"}
        },
        context_id=context_id,
        workflow_id=workflow_id
    )
    
    # エージェントCがメッセージを処理
    results_c = await agent_c.get_and_process_messages()
    
    # 処理結果を確認
    assert len(results_c) == 1
    assert results_c[0]["notification_received"] is True
    
    # エージェントCからコンテキストを確認
    context = agent_c.get_context_data(context_id)
    assert context["task"] == "テストタスク"
    assert context["priority"] == "high"
    
    # エージェントCがコンテキストを更新
    agent_c.update_context_data(
        {"status": "in_progress", "assigned_to": "agent_c"},
        context_id
    )
    
    # エージェントCからAへコンテキスト更新を通知
    agent_c.send_response(
        to_agent="agent_a",
        in_response_to=message_id,
        message_type=MessageType.RESPONSE,
        content={
            "message": "コンテキストを更新しました",
            "updated_fields": ["status", "assigned_to"]
        }
    )
    
    # エージェントAがメッセージを処理
    results_a = await agent_a.get_and_process_messages()
    
    # 処理結果を確認 - 少なくとも1つのメッセージが処理されていることを確認
    assert len(results_a) >= 1
    
    # エージェントAがコンテキストを確認
    context = agent_a.get_context_data(context_id)
    assert context["status"] == "in_progress"
    assert context["assigned_to"] == "agent_c"
    
    logger.info("エージェント間通信テスト成功")


@pytest.mark.asyncio
async def test_priority_messaging(clean_test_data, reset_agent_state):
    """メッセージの優先度機能をテスト"""
    # エージェントを作成
    agent_a = CustomAgent("agent_a", CustomAgentState)
    agent_b = CustomAgent("agent_b", CustomAgentState)
    
    # エージェントBに複数の優先度の異なるメッセージを送信
    agent_a.send_message(
        to_agent="agent_b",
        message_type=MessageType.COMMAND,
        content={"command": "echo", "data": {"order": 3}},
        priority=MessagePriority.LOW
    )
    
    agent_a.send_message(
        to_agent="agent_b",
        message_type=MessageType.COMMAND,
        content={"command": "echo", "data": {"order": 2}},
        priority=MessagePriority.NORMAL
    )
    
    agent_a.send_message(
        to_agent="agent_b",
        message_type=MessageType.COMMAND,
        content={"command": "echo", "data": {"order": 1}},
        priority=MessagePriority.HIGH
    )
    
    # エージェントBがメッセージを処理
    results = await agent_b.get_and_process_messages()
    
    # 処理結果を確認（優先度順にメッセージが処理されることを確認）
    # 少なくとも3つのメッセージが処理されていることを確認
    assert len(results) >= 3
    
    # エコーメッセージを抽出
    echo_results = [r for r in results if "echo_content" in r]
    assert len(echo_results) == 3
    
    # 優先度の高いメッセージから処理されるため、結果は[1, 2, 3]の順になるはず
    assert echo_results[0]["echo_content"]["order"] == 1
    assert echo_results[1]["echo_content"]["order"] == 2
    assert echo_results[2]["echo_content"]["order"] == 3
    
    logger.info("メッセージ優先度テスト成功")


@pytest.mark.asyncio
async def test_context_inheritance(clean_test_data, reset_agent_state):
    """コンテキスト継承機能をテスト"""
    # エージェントを作成
    agent_a = CustomAgent("agent_a", CustomAgentState)
    
    # 親コンテキストを作成
    workflow_id = f"wf-test-{uuid.uuid4().hex[:8]}"
    parent_context = agent_a.create_context(workflow_id, {
        "project": "テストプロジェクト",
        "deadline": "2023-12-31",
        "status": "planning",
        "team": ["member1", "member2"]
    })
    
    parent_id = parent_context.context_id
    
    # 子コンテキストを作成（特定のデータのみを継承）
    child_context = agent_a.create_child_context(
        parent_id, ["project", "deadline"]
    )
    
    child_context_id = child_context.context_id
    
    # 子コンテキストを取得して確認
    child_data = agent_a.get_context_data(child_context_id)
    
    # 継承されたデータが存在することを確認
    assert child_data["project"] == "テストプロジェクト"
    assert child_data["deadline"] == "2023-12-31"
    
    # 継承から除外されたデータが存在しないことを確認
    assert "status" not in child_data
    assert "team" not in child_data
    
    # 子コンテキストを更新
    agent_a.update_context_data(
        {"task": "サブタスク1", "assigned_to": "member1"},
        child_context_id
    )
    
    # 更新後のデータを確認
    updated_child_data = agent_a.get_context_data(child_context_id)
    assert updated_child_data["task"] == "サブタスク1"
    
    # 親コンテキストは影響を受けていないことを確認
    parent_data = agent_a.get_context_data(parent_id)
    assert "task" not in parent_data
    
    logger.info("コンテキスト継承テスト成功")


@pytest.mark.asyncio
async def test_context_merging(clean_test_data, reset_agent_state):
    """コンテキストマージ機能をテスト"""
    # エージェントを作成
    agent_a = CustomAgent("agent_a", CustomAgentState)
    
    # 複数のコンテキストを作成
    workflow_id = f"wf-test-{uuid.uuid4().hex[:8]}"
    
    context1 = agent_a.create_context(workflow_id, {
        "project": "テストプロジェクト",
        "phase1_complete": True,
        "phase1_results": {"score": 85}
    })
    
    context2 = agent_a.create_context(workflow_id, {
        "phase2_complete": True,
        "phase2_results": {"score": 92}
    })
    
    context3 = agent_a.create_context(workflow_id, {
        "phase3_complete": False,
        "phase3_progress": 0.6
    })
    
    # コンテキストをマージ
    merged_context = agent_a.context.merge_contexts([
        context1.context_id, context2.context_id, context3.context_id
    ])
    
    # マージされたコンテキストのデータを確認
    merged_data = merged_context.data
    
    assert merged_data["project"] == "テストプロジェクト"
    assert merged_data["phase1_complete"] is True
    assert merged_data["phase1_results"]["score"] == 85
    assert merged_data["phase2_complete"] is True
    assert merged_data["phase2_results"]["score"] == 92
    assert merged_data["phase3_complete"] is False
    assert merged_data["phase3_progress"] == 0.6
    
    # マージメタデータの確認
    assert "merged_from" in merged_context.metadata
    assert len(merged_context.metadata["merged_from"]) == 3
    assert context1.context_id in merged_context.metadata["merged_from"]
    assert context2.context_id in merged_context.metadata["merged_from"]
    assert context3.context_id in merged_context.metadata["merged_from"]
    
    logger.info("コンテキストマージテスト成功")


class MockMessageBroker:
    """メッセージブローカーのモッククラス"""
    
    def __init__(self):
        self.messages = {}
        self.removed_messages = []
        self.registered_agents = set()
        self.responses = {}
        self.all_messages = []  # すべてのメッセージを保存
    
    def register_agent(self, agent_id):
        """エージェントの登録をモック"""
        self.registered_agents.add(agent_id)
        if agent_id not in self.messages:
            self.messages[agent_id] = []
        return True
    
    def send_message(
        self, from_agent: str, to_agent: str, message_type: str, content: Dict[str, Any],
        context_id: Optional[str] = None, workflow_id: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        requires_response: bool = False, in_response_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        実際のMessageBrokerと同じインターフェースでメッセージ送信をモック
        """
        # メッセージオブジェクトを作成
        message_id = str(uuid.uuid4())
        message = AgentMessage(
            id=message_id,
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            created_at=datetime.now(),
            context_id=context_id,
            workflow_id=workflow_id,
            priority=priority,
            requires_response=requires_response,
            in_response_to=in_response_to,
            metadata=metadata or {}
        )
        
        # メッセージを保存
        if to_agent not in self.messages:
            self.messages[to_agent] = []
        self.messages[to_agent].append(message)
        self.all_messages.append(message)
        
        # 応答待ちの設定
        if requires_response:
            if message_id not in self.responses:
                self.responses[message_id] = set()
            self.responses[message_id].add(to_agent)
            
        return message_id
    
    # 既存の実装をサポートするための互換メソッド
    def send_message_object(self, message):
        """
        メッセージオブジェクトを受け取るレガシーメソッド
        """
        to_agent = message.to_agent
        if to_agent not in self.messages:
            self.messages[to_agent] = []
        self.messages[to_agent].append(message)
        self.all_messages.append(message)
        
        # 応答待ちの設定
        if message.requires_response:
            if message.id not in self.responses:
                self.responses[message.id] = set()
            self.responses[message.id].add(to_agent)
            
        return message.id
    
    def get_messages(self, agent_id):
        """エージェント宛のメッセージ取得をモック"""
        return self.messages.get(agent_id, [])
    
    def remove_message(self, agent_id, message_id):
        """メッセージ削除をモック"""
        if agent_id in self.messages:
            self.messages[agent_id] = [m for m in self.messages[agent_id] if m.id != message_id]
            self.removed_messages.append((agent_id, message_id))
            return True
        return False
        
    def wait_for_responses(self, agent_id, message_id, timeout=60.0, check_interval=0.5):
        """
        メッセージに対する応答を待機するメソッドをモック
        """
        # すぐに結果を返すシンプルな実装
        responses = []
        for msg in self.all_messages:
            if msg.in_response_to == message_id and msg.to_agent == agent_id:
                responses.append(msg)
        return responses
    
    def get_message_by_id(self, message_id):
        """
        IDによるメッセージ取得をモック
        """
        for messages in self.messages.values():
            for msg in messages:
                if msg.id == message_id:
                    return msg
        return None
    
    def receive_message(self, agent_id):
        """
        エージェント宛のメッセージ受信をモック
        MessageClient.receive_messageが使用するメソッド
        """
        messages = self.messages.get(agent_id, [])
        if not messages:
            return None
            
        # 優先度順にソート (HIGH -> NORMAL -> LOW)
        priority_order = {
            MessagePriority.HIGH: 0,
            MessagePriority.URGENT: 0,  # URGENTはHIGHと同等の優先度とみなす
            MessagePriority.NORMAL: 1,
            MessagePriority.LOW: 2
        }
        
        sorted_messages = sorted(messages, key=lambda m: priority_order.get(m.priority, 1))
        if sorted_messages:
            # 最優先のメッセージを返し、キューから削除
            message = sorted_messages[0]
            self.remove_message(agent_id, message.id)
            return message
            
        return None
    
    def get_message_history(self, from_agent=None, to_agent=None, message_type=None, 
                          context_id=None, workflow_id=None, limit=None):
        """メッセージ履歴取得をモック"""
        # フィルタリング
        filtered = self.all_messages
        if from_agent:
            filtered = [m for m in filtered if m.from_agent == from_agent]
        if to_agent:
            filtered = [m for m in filtered if m.to_agent == to_agent]
        if message_type:
            filtered = [m for m in filtered if m.message_type == message_type]
        if context_id:
            filtered = [m for m in filtered if m.context_id == context_id]
        if workflow_id:
            filtered = [m for m in filtered if m.workflow_id == workflow_id]
            
        # ソートと制限
        filtered.sort(key=lambda m: m.created_at, reverse=True)
        if limit:
            filtered = filtered[:limit]
            
        return filtered


class TestMessageClient:
    """MessageClientの基本機能テスト"""
    
    def test_message_client_initialization(self):
        """MessageClientの初期化テスト"""
        client = MessageClient("test-agent")
        assert client.agent_id == "test-agent"
        assert client.received_message_history == []
        assert client.sent_message_history == []
        assert client.conversation_cache == {}
    
    def test_send_message(self):
        """メッセージ送信テスト"""
        mock_broker = MockMessageBroker()
        client = MessageClient("sender", broker=mock_broker)
        
        # メッセージ送信
        msg_id = client.send_message(
            to_agent="receiver",
            message_type="TEST",
            content={"data": "test_content"},
            priority=MessagePriority.NORMAL
        )
        
        # 送信履歴の確認
        assert len(client.sent_message_history) == 1
        assert client.sent_message_history[0].from_agent == "sender"
        assert client.sent_message_history[0].to_agent == "receiver"
        assert client.sent_message_history[0].message_type == "TEST"
        assert client.sent_message_history[0].content["data"] == "test_content"
        
        # ブローカーにメッセージが渡されたか確認
        assert len(mock_broker.messages["receiver"]) == 1
        assert mock_broker.messages["receiver"][0].id == msg_id
    
    def test_receive_message(self):
        """メッセージ受信テスト"""
        mock_broker = MockMessageBroker()
        sender = MessageClient("sender", broker=mock_broker)
        receiver = MessageClient("receiver", broker=mock_broker)
        
        # 送信者からメッセージを送信
        msg_id = sender.send_message(
            to_agent="receiver",
            message_type="REQUEST",
            content={"query": "test_query"}
        )
        
        # 受信者がメッセージを受信
        message = receiver.receive_message()
        
        # 受信したメッセージの確認
        assert message is not None
        assert message.id == msg_id
        assert message.from_agent == "sender"
        assert message.to_agent == "receiver"
        assert message.message_type == "REQUEST"
        assert message.content["query"] == "test_query"
        
        # 受信履歴の確認
        assert len(receiver.received_message_history) == 1
        assert receiver.received_message_history[0].id == msg_id
        
        # ブローカーからメッセージが削除されたか確認
        assert len(mock_broker.messages["receiver"]) == 0
        assert len(mock_broker.removed_messages) == 1
        assert mock_broker.removed_messages[0] == ("receiver", msg_id)
    
    def test_message_standardization(self):
        """メッセージ標準化テスト"""
        mock_broker = MockMessageBroker()
        client = MessageClient("test-agent", broker=mock_broker)
        
        # 基本的なメッセージのみを指定して送信
        msg_id = client.send_message(
            to_agent="other-agent",
            message_type="INFO",
            content={"info": "basic_info"}
        )
        
        # 送信されたメッセージを取得
        message = mock_broker.messages["other-agent"][0]
        
        # 標準化されたメッセージの確認
        assert message.id is not None
        assert message.from_agent == "test-agent"
        assert message.to_agent == "other-agent"
        assert message.message_type == "INFO"
        assert message.content["info"] == "basic_info"
        assert message.created_at is not None  # 自動設定される
        assert message.priority == MessagePriority.NORMAL  # デフォルト値
        assert message.requires_response is False  # デフォルト値
        assert message.in_response_to is None  # デフォルト値
    
    def test_wait_for_response(self):
        """応答待機テスト"""
        mock_broker = MockMessageBroker()
        client_a = MessageClient("agent-a", broker=mock_broker)
        client_b = MessageClient("agent-b", broker=mock_broker)
        
        # リクエスト送信
        msg_id = client_a.send_message(
            to_agent="agent-b",
            message_type="REQUEST",
            content={"query": "need_response"},
            requires_response=True
        )
        
        # 応答がない場合は空リストが返る
        responses = client_a.wait_for_response(msg_id, timeout=0)
        assert len(responses) == 0
        
        # クライアントBがメッセージを受信して応答
        message = client_b.receive_message()
        client_b.send_message(
            to_agent="agent-a",
            message_type="RESPONSE",
            content={"answer": "test_answer"},
            in_response_to=msg_id
        )
        
        # 応答を取得
        responses = client_a.wait_for_response(msg_id, timeout=0)
        assert len(responses) == 1
        assert responses[0].message_type == "RESPONSE"
        assert responses[0].content["answer"] == "test_answer"
        assert responses[0].in_response_to == msg_id
    
    def test_get_conversation_history(self):
        """会話履歴取得テスト"""
        mock_broker = MockMessageBroker()
        client_a = MessageClient("agent-a", broker=mock_broker)
        client_b = MessageClient("agent-b", broker=mock_broker)
        
        # 複数のメッセージを送受信
        for i in range(3):
            # A -> B
            client_a.send_message(
                to_agent="agent-b",
                message_type="MESSAGE",
                content={"from_a": f"message_{i}"}
            )
            message = client_b.receive_message()
            
            # B -> A
            client_b.send_message(
                to_agent="agent-a",
                message_type="REPLY",
                content={"from_b": f"reply_{i}"}
            )
            client_a.receive_message()
        
        # Aから見た会話履歴
        a_history = client_a.get_conversation_history("agent-b")
        assert len(a_history) == 6  # 送信3 + 受信3
        
        # Bから見た会話履歴
        b_history = client_b.get_conversation_history("agent-a")
        assert len(b_history) == 6  # 送信3 + 受信3
        
        # 時系列順にソートされているか確認
        for i in range(1, len(a_history)):
            assert a_history[i].created_at >= a_history[i-1].created_at
    
    def test_priority_handling(self):
        """優先度処理テスト"""
        mock_broker = MockMessageBroker()
        sender = MessageClient("sender", broker=mock_broker)
        receiver = MessageClient("receiver", broker=mock_broker)
        
        # 異なる優先度のメッセージを送信
        sender.send_message(
            to_agent="receiver",
            message_type="LOW",
            content={"priority": "low"},
            priority=MessagePriority.LOW
        )
        
        sender.send_message(
            to_agent="receiver",
            message_type="HIGH",
            content={"priority": "high"},
            priority=MessagePriority.HIGH
        )
        
        sender.send_message(
            to_agent="receiver",
            message_type="NORMAL",
            content={"priority": "normal"},
            priority=MessagePriority.NORMAL
        )
        
        # 優先度順（HIGH->NORMAL->LOW）に取得されることを確認
        message1 = receiver.receive_message()
        assert message1.message_type == "HIGH"
        
        message2 = receiver.receive_message()
        assert message2.message_type == "NORMAL"
        
        message3 = receiver.receive_message()
        assert message3.message_type == "LOW"


class TestMessageBroker:
    """MessageBrokerクラスのテスト"""
    
    def test_broker_initialization(self):
        """MessageBrokerの初期化テスト"""
        broker = MessageBroker()
        # 基本的なメソッドが実装されているかテスト
        assert hasattr(broker, "register_agent"), "register_agentメソッドが存在しません"
        assert hasattr(broker, "send_message"), "send_messageメソッドが存在しません"
        assert hasattr(broker, "get_messages"), "get_messagesメソッドが存在しません"
    
    def test_broker_send_message(self):
        """MessageBrokerのメッセージ送信テスト"""
        broker = MessageBroker()
        
        # 送信者と受信者の登録
        broker.register_agent("test-sender")
        broker.register_agent("test-receiver")
        
        # メッセージ送信（パラメータ分割版）
        msg_id = broker.send_message(
            from_agent="test-sender",
            to_agent="test-receiver",
            message_type="TEST",
            content={"test": "content"},
            priority=MessagePriority.NORMAL,
            requires_response=False
        )
        
        # 送信結果の確認
        assert msg_id is not None
        # 送信後のメッセージ確認（get_messagesの代わりにpeek_messagesを使用）
        messages = broker.peek_messages("test-receiver")
        assert len(messages) == 1
        assert messages[0].from_agent == "test-sender"
        assert messages[0].message_type == "TEST"
        assert messages[0].content["test"] == "content"
    
    def test_broker_priority_messages(self):
        """MessageBrokerの優先度付きメッセージ取得テスト"""
        broker = MessageBroker()
        
        # エージェント登録
        broker.register_agent("sender-1")
        broker.register_agent("sender-2")
        broker.register_agent("receiver")
        
        # メッセージ送信（通常優先度とHIGH優先度）
        broker.send_message(
            from_agent="sender-1",
            to_agent="receiver",
            message_type="TEST1",
            content={},
            priority=MessagePriority.NORMAL
        )
        
        broker.send_message(
            from_agent="sender-2",
            to_agent="receiver",
            message_type="TEST2",
            content={},
            priority=MessagePriority.HIGH
        )
        
        # 優先度付きメッセージ取得
        priority_messages = broker.get_priority_messages("receiver")
        
        # 結果確認（優先度順に並んでいるか）
        assert len(priority_messages) == 2
        assert priority_messages[0].from_agent == "sender-2"  # HIGH優先度が先
        assert priority_messages[1].from_agent == "sender-1"  # NORMAL優先度が後
        
        # 存在しないエージェントの場合は空リスト
        empty_messages = broker.get_priority_messages("nonexistent")
        assert empty_messages == []
    
    def test_broker_message_history(self):
        """MessageBrokerのメッセージ履歴テスト（remove_messageの代わり）"""
        broker = MessageBroker()
        
        # エージェント登録
        broker.register_agent("sender")
        broker.register_agent("receiver")
        
        # メッセージ送信
        msg_id = broker.send_message(
            from_agent="sender",
            to_agent="receiver",
            message_type="HISTORY_TEST",
            content={}
        )
        
        # メッセージ履歴から確認
        history = broker.get_message_history(from_agent="sender", to_agent="receiver")
        assert len(history) == 1
        assert history[0].message_type == "HISTORY_TEST"
        
        # 送受信後の状態確認
        messages = broker.get_messages("receiver")
        assert len(messages) == 1  # メッセージを受信したらキューから削除される
        
        # キューがクリアされているか確認
        empty_queue = broker.peek_messages("receiver")
        assert len(empty_queue) == 0


@pytest.mark.asyncio
class TestAsyncCommunication:
    """非同期通信のテスト"""
    
    async def test_async_message_exchange(self):
        """非同期メッセージ交換テスト"""
        mock_broker = MockMessageBroker()
        client_a = MessageClient("agent-a", broker=mock_broker)
        client_b = MessageClient("agent-b", broker=mock_broker)
        
        # タスクを作成
        async def agent_a_send():
            return client_a.send_message(
                to_agent="agent-b",
                message_type="ASYNC_TEST",
                content={"data": "async_test"},
                requires_response=True
            )
        
        async def agent_b_respond(msg_id):
            message = client_b.receive_message()
            assert message is not None
            assert message.message_type == "ASYNC_TEST"
            
            return client_b.send_message(
                to_agent="agent-a",
                message_type="ASYNC_RESPONSE",
                content={"result": "async_success"},
                in_response_to=msg_id
            )
        
        async def agent_a_receive(msg_id):
            # 応答を待機（非同期）
            responses = []
            for _ in range(10):  # 最大10回試行
                responses = client_a.wait_for_response(msg_id, timeout=0)
                if responses:
                    break
                await asyncio.sleep(0.1)
            
            assert len(responses) == 1
            assert responses[0].message_type == "ASYNC_RESPONSE"
            assert responses[0].content["result"] == "async_success"
            return responses[0]
        
        # 実行
        msg_id = await agent_a_send()
        response_id = await agent_b_respond(msg_id)
        response = await agent_a_receive(msg_id)
        
        # 履歴確認
        assert len(client_a.sent_message_history) == 1
        assert len(client_a.received_message_history) == 1
        assert len(client_b.sent_message_history) == 1
        assert len(client_b.received_message_history) == 1
    
    async def test_multiple_agents_communication(self):
        """複数エージェント間の通信テスト"""
        mock_broker = MockMessageBroker()
        
        # 3つのエージェント
        agent_a = MessageClient("agent-a", broker=mock_broker)
        agent_b = MessageClient("agent-b", broker=mock_broker)
        agent_c = MessageClient("agent-c", broker=mock_broker)
        
        # エージェントAがBとCにメッセージを送信
        msg_to_b = agent_a.send_message(
            to_agent="agent-b",
            message_type="REQUEST",
            content={"task": "task_b"}
        )
        
        msg_to_c = agent_a.send_message(
            to_agent="agent-c",
            message_type="REQUEST",
            content={"task": "task_c"}
        )
        
        # エージェントBとCが受信して応答
        b_message = agent_b.receive_message()
        assert b_message.content["task"] == "task_b"
        
        c_message = agent_c.receive_message()
        assert c_message.content["task"] == "task_c"
        
        # 応答の送信
        agent_b.send_message(
            to_agent="agent-a",
            message_type="RESPONSE",
            content={"result": "done_b"},
            in_response_to=msg_to_b
        )
        
        agent_c.send_message(
            to_agent="agent-a",
            message_type="RESPONSE",
            content={"result": "done_c"},
            in_response_to=msg_to_c
        )
        
        # エージェントAが応答を受信
        responses = []
        for _ in range(2):
            response = agent_a.receive_message()
            if response:
                responses.append(response)
        
        # 両方の応答を取得できたか確認
        assert len(responses) == 2
        results = [r.content["result"] for r in responses]
        assert "done_b" in results
        assert "done_c" in results


class TestMessageClientDbIntegration:
    """MessageClientとDBの統合テスト"""
    
    def test_message_client_db_logging(self, db_session):
        """MessageClientがDBに監査ログを記録するかテスト"""
        # モックブローカーの設定
        mock_broker = MockMessageBroker()
        
        # DBセッションを持つMessageClient
        client_a = MessageClient("db-agent-a", broker=mock_broker, db=db_session)
        client_b = MessageClient("db-agent-b", broker=mock_broker, db=db_session)
        
        # テスト用ワークフローID
        workflow_id = f"test-workflow-{uuid.uuid4()}"
        
        # 外部キー制約を満たすためにワークフローエントリを作成
        from src.models.db_models import Workflow
        workflow = Workflow(
            id=workflow_id,
            status="active",
            current_agent="db-agent-a"
        )
        db_session.add(workflow)
        db_session.commit()
        
        # メッセージ送信（自動的にDBに記録される）
        msg_id = client_a.send_message(
            to_agent="db-agent-b",
            message_type="DB_TEST",
            content={"test": "db_integration"},
            workflow_id=workflow_id
        )
        
        # 受信（自動的にDBに記録される）
        message = client_b.receive_message()
        
        # DBからメッセージログを検索
        repo = MessageLogRepository(db_session)
        logs = repo.search(workflow_id=workflow_id)
        
        # ログが記録されたか確認
        assert len(logs) >= 1
        log = logs[0]
        assert log.message_id == msg_id
        assert log.from_agent == "db-agent-a"
        assert log.to_agent == "db-agent-b"
        assert log.workflow_id == workflow_id
        
        # 応答も記録されるか確認
        response_id = client_b.send_message(
            to_agent="db-agent-a",
            message_type="DB_RESPONSE",
            content={"result": "db_success"},
            workflow_id=workflow_id,
            in_response_to=msg_id
        )
        
        # 更新されたログを検索
        updated_logs = repo.search(workflow_id=workflow_id)
        assert len(updated_logs) >= 2  # 送信と応答
        
        # 会話の取得
        conversation = get_agent_conversation(db_session, "db-agent-a", "db-agent-b")
        assert len(conversation) >= 2


class TestErrorHandling:
    """エラーハンドリングのテスト"""
    
    def test_message_validation(self):
        """メッセージバリデーションテスト"""
        client = MessageClient("validation-agent")
        
        # 無効なメッセージタイプ
        with pytest.raises(ValueError):
            client.send_message(
                to_agent="other-agent",
                message_type="INVALID_TYPE",  # 定義されていないタイプ
                content={"data": "test"}
            )
        
        # 無効なコンテンツ形式
        with pytest.raises(TypeError):
            client.send_message(
                to_agent="other-agent",
                message_type="INFO",
                content="string_not_dict"  # 辞書でない
            )
        
        # 必須フィールド不足
        with pytest.raises(ValueError):
            client.send_message(
                to_agent=None,  # Noneを渡す
                message_type="INFO",
                content={"data": "test"}
            )
    
    def test_broker_error_handling(self):
        """ブローカーのエラーハンドリングテスト"""
        # エラーを投げるモックブローカー
        class ErrorBroker:
            def register_agent(self, agent_id):
                """エージェント登録時にエラーをスロー"""
                raise ConnectionError("Broker connection failed during registration")
                
            def send_message(self, message):
                raise ConnectionError("Broker connection failed")

            def get_messages(self, agent_id):
                raise ConnectionError("Broker connection failed")

            def remove_message(self, agent_id, message_id):
                raise ConnectionError("Broker connection failed")

        # ConnectionErrorが発生することを期待
        with pytest.raises(ConnectionError):
            client = MessageClient("error-agent", broker=ErrorBroker())
    
    def test_timeout_handling(self):
        """タイムアウト処理テスト"""
        client = MessageClient("timeout-agent")
        
        # 存在しないメッセージIDを指定した場合のタイムアウト
        start_time = datetime.now()
        responses = client.wait_for_response("nonexistent-id", timeout=0.5)
        end_time = datetime.now()
        
        # 結果の確認
        assert len(responses) == 0
        assert (end_time - start_time).total_seconds() <= 1.0  # タイムアウトが発生したか


if __name__ == "__main__":
    # asyncioランナーでテストを実行
    asyncio.run(test_agent_messaging())
    asyncio.run(test_priority_messaging())
    asyncio.run(test_context_inheritance())
    asyncio.run(test_context_merging())
    
    print("全てのテストが成功しました！") 