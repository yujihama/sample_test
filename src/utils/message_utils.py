"""
メッセージング関連のユーティリティ

警告：このモジュールのMessageClientクラスは非推奨です。
代わりに `src.core.messaging import MessageClient` を使用してください。
"""

import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import asyncio
from loguru import logger
import json
import warnings

from src.utils import json_utils
from src.core.messaging import MessageClient as CoreMessageClient

# 後方互換性のために残すが、非推奨
class MessageClient(CoreMessageClient):
    """
    エージェント間メッセージングクライアント（非推奨）
    
    このクラスは後方互換性のために残されていますが、新しいコードでは
    src.core.messagingのMessageClientを使用してください。
    """
    
    def __init__(self, sender_id: str, **kwargs):
        """
        初期化
        
        Args:
            sender_id: 送信者ID
        """
        warnings.warn(
            "src.utils.message_utilsのMessageClientは非推奨です。"
            "src.core.messagingのMessageClientを使用してください。",
            DeprecationWarning, 
            stacklevel=2
        )
        super().__init__(client_id=sender_id, **kwargs)
        
        # 追加属性の互換性維持
        self.sender_id = sender_id
        self.agent_id = sender_id  # CoreMessageClientはclient_idを使用
        self.message_queue = {}
        self.listeners = {}
        self.received_message_history = []
        self.sent_message_history = []
        self.conversation_cache = {}
        
        logger.info(f"Deprecated MessageClient initialized for {sender_id}")

    # 以下は互換性のためのラッパーメソッド
    def send_message(
        self, 
        recipient_id: str, 
        message_type: str, 
        content: Dict[str, Any],
        context_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        priority: str = "normal",
        requires_response: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        メッセージを送信する (非推奨)
        
        Args:
            recipient_id: 宛先エージェントID
            message_type: メッセージタイプ
            content: メッセージ内容
            context_id: 関連するコンテキストID
            workflow_id: 関連するワークフローID
            priority: メッセージの優先度
            requires_response: 応答が必要かどうか
            metadata: メタデータ
            **kwargs: その他のパラメータ
            
        Returns:
            str: メッセージID
        """
        # CoreMessageClient.send_messageへ委譲するための準備
        # CoreはBooleanを返すが、このクラスのインターフェースはstrを返す
        
        message_id = f"msg-{uuid.uuid4().hex}"
        
        # メッセージオブジェクトを作成（互換性のため）
        message = {
            "id": message_id,
            "from_agent": self.sender_id,
            "to_agent": recipient_id,
            "message_type": message_type,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
            "context_id": context_id,
            "workflow_id": workflow_id,
            "priority": priority,
            "requires_response": requires_response
        }
        
        # 送信履歴を更新
        if hasattr(self, 'sent_message_history'):
            self.sent_message_history.append(message)
        
        # CoreMessageClientのメソッドを呼び出し
        super().send_message(
            message_type=message_type,
            content=content,
            recipient_id=recipient_id,
            context_id=context_id,
            workflow_id=workflow_id,
            priority=priority,
            requires_response=requires_response,
            metadata=metadata,
            **kwargs
        )
        
        logger.info(f"Message sent via deprecated client: {message_id} from {self.sender_id} to {recipient_id}")
        return message_id

    def receive_message(self):
        """
        メッセージを受信する (非推奨)
        
        Returns:
            受信したメッセージ、または None
        """
        message = super().receive_message()
        
        # 受信履歴を更新
        if message and hasattr(self, 'received_message_history'):
            self.received_message_history.append(message)
            
        return message
        
    # 以下は旧インタフェースで使用されていたメソッド
    async def get_messages(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        指定エージェント宛のメッセージを取得 (非推奨)
        """
        warnings.warn(
            "get_messagesメソッドは非推奨です。receive_messageを使用してください。",
            DeprecationWarning
        )
        
        # CoreのAPIを使って取得
        messages = self.broker.get_messages(agent_id or self.client_id)
        return messages
    
    def clear_processed_messages(self, agent_id: Optional[str] = None) -> int:
        """処理済みメッセージをクリア (非推奨)"""
        warnings.warn(
            "clear_processed_messagesメソッドは非推奨です。",
            DeprecationWarning
        )
        return 0  # 実際の処理は行わない
    
    def register_listener(self, agent_id: str, callback):
        """メッセージリスナーを登録 (非推奨)"""
        warnings.warn(
            "register_listenerメソッドは非推奨です。subscribeを使用してください。",
            DeprecationWarning
        )
        
    def unregister_listener(self, agent_id: str):
        """メッセージリスナーを登録解除 (非推奨)"""
        warnings.warn(
            "unregister_listenerメソッドは非推奨です。",
            DeprecationWarning
        )
    
    async def _notify_listener(self, agent_id: str, message: Dict[str, Any]):
        """リスナーに通知 (非推奨、内部メソッド)"""
        warnings.warn(
            "_notify_listenerメソッドは非推奨です。",
            DeprecationWarning
        )
    
    def update_message_status(self, message_id: str, status: str, result: Optional[Dict[str, Any]] = None):
        """メッセージのステータスを更新 (非推奨)"""
        warnings.warn(
            "update_message_statusメソッドは非推奨です。",
            DeprecationWarning
        )
        return False
    
    def serialize_messages(self, agent_id: Optional[str] = None) -> str:
        """メッセージをJSON文字列にシリアライズ (非推奨)"""
        warnings.warn(
            "serialize_messagesメソッドは非推奨です。",
            DeprecationWarning
        )
        return "{}"
    
    def deserialize_messages(self, json_str: str, agent_id: Optional[str] = None):
        """JSON文字列からメッセージをデシリアライズしてキューに追加 (非推奨)"""
        warnings.warn(
            "deserialize_messagesメソッドは非推奨です。",
            DeprecationWarning
        )
        return False
    
    def wait_for_response(self, message_id: str, timeout: float = 10.0) -> List[Dict[str, Any]]:
        """
        特定のメッセージに対する応答を待機
        
        Args:
            message_id: 応答を待つメッセージID
            timeout: 最大待機時間（秒）
            
        Returns:
            List[Dict[str, Any]]: 応答メッセージのリスト
        """
        # 互換性のために維持
        responses = []
        # 実際のCore実装には、wait_for_responseメソッドがないため簡易実装
        messages = self.broker.get_messages(self.client_id)
        for msg in messages:
            if msg.get("in_response_to") == message_id:
                responses.append(msg)
        return responses

# 後方互換性のために残す
class MessageManager:
    """
    システム全体のメッセージング管理クラス（非推奨）
    
    この機能はsrc.core.messagingに統合されました。
    """
    
    _instance = None
    
    def __new__(cls):
        warnings.warn(
            "MessageManagerは非推奨です。",
            DeprecationWarning, 
            stacklevel=2
        )
        if cls._instance is None:
            cls._instance = super(MessageManager, cls).__new__(cls)
            cls._instance.clients = {}
            cls._instance.history = []
            cls._instance.max_history = 1000
            logger.info("Deprecated MessageManager initialized")
        return cls._instance
    
    def register_client(self, agent_id: str) -> MessageClient:
        """クライアントを登録（非推奨）"""
        if agent_id in self.clients:
            return self.clients[agent_id]
        
        client = MessageClient(agent_id)
        self.clients[agent_id] = client
        return client
    
    def unregister_client(self, agent_id: str):
        """クライアントの登録を解除（非推奨）"""
        if agent_id in self.clients:
            del self.clients[agent_id]
    
    def log_message(self, message: Dict[str, Any]):
        """メッセージを履歴に記録（非推奨）"""
        self.history.append(message)
        
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_client(self, agent_id: str) -> Optional[MessageClient]:
        """エージェントIDからクライアントを取得（非推奨）"""
        return self.clients.get(agent_id)
    
    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """メッセージ履歴を取得（非推奨）"""
        return self.history[-limit:] if self.history else []
    
    def broadcast_message(self, from_agent: str, message_type: str, content: Dict[str, Any]) -> List[str]:
        """すべてのエージェントにメッセージをブロードキャスト（非推奨）"""
        message_ids = []
        
        sender_client = self.get_client(from_agent)
        if not sender_client:
            logger.error(f"Sender client {from_agent} not found")
            return message_ids
        
        for agent_id in self.clients:
            if agent_id != from_agent:
                message_id = sender_client.send_message(
                    recipient_id=agent_id,
                    message_type=message_type,
                    content=content
                )
                message_ids.append(message_id)
        
        return message_ids 