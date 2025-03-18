"""
メッセージング機能を提供するモジュール

このモジュールは、エージェント間のメッセージング機能を提供します。
"""

from enum import Enum, auto
from typing import Any, Dict, Optional, List, Callable
from collections import defaultdict
from src.utils.logger import get_logger
from datetime import datetime
import uuid

logger = get_logger(__name__)

class MessageType(Enum):
    """メッセージタイプを定義する列挙型"""
    TASK_REQUEST = auto()
    TASK_ASSIGNMENT = auto()
    TASK_STATUS = auto()
    HUMAN_QUERY = auto()
    ERROR_REPORT = auto()
    STATUS_CHECK = auto()
    STATUS_RESPONSE = auto()
    DATA_REQUEST = auto()
    QUERY = auto()
    COMMAND = auto()

class MessageBroker:
    """メッセージブローカー"""

    _instance = None

    def __new__(cls):
        """シングルトンパターンを実装"""
        if cls._instance is None:
            cls._instance = super(MessageBroker, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """メッセージブローカーを初期化します。"""
        if self._initialized:
            return
        
        self._initialized = True
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.messages: List[Dict[str, Any]] = []
        self.registered_agents: Dict[str, Any] = {}
        logger.info("メッセージブローカーを初期化しました")

    def register_agent(self, agent_id: str, agent_instance: Any = None) -> None:
        """
        エージェントをブローカーに登録します。
        
        Args:
            agent_id (str): エージェントID
            agent_instance (Any, optional): エージェントのインスタンス
        """
        self.registered_agents[agent_id] = agent_instance
        logger.info(f"エージェント {agent_id} を登録しました")
        
    def subscribe(self, message_type: MessageType, callback: Callable) -> None:
        """
        メッセージタイプに対するコールバックを登録します。

        Args:
            message_type (MessageType): メッセージタイプ
            callback (Callable): コールバック関数
        """
        self.subscribers[message_type.name].append(callback)
        logger.debug(f"コールバックを登録: {message_type.name}")

    def publish(self, message: Dict[str, Any]) -> None:
        """
        メッセージを配信します。

        Args:
            message (Dict[str, Any]): 配信するメッセージ
        """
        message_type = message.get("type")
        if not message_type:
            logger.error("メッセージタイプが指定されていません")
            return

        self.messages.append(message)
        for callback in self.subscribers[message_type]:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"コールバックの実行中にエラーが発生: {e}")

        logger.debug(f"メッセージを配信: {message}")
        
    def add_message(
        self, 
        recipient_id: str, 
        sender_id: str, 
        message_type: str, 
        content: Dict[str, Any],
        workflow_id: Optional[str] = None,
        priority: str = "normal",
        message_id: Optional[str] = None,
        requires_response: bool = False,
        context_id: Optional[str] = None,
        from_agent: Optional[str] = None
    ) -> str:
        """
        特定のエージェント宛にメッセージを追加します。
        主にテスト用に使用されます。

        Args:
            recipient_id (str): 受信者ID
            sender_id (str): 送信者ID
            message_type (str): メッセージタイプ
            content (Dict[str, Any]): メッセージの内容
            workflow_id (Optional[str]): ワークフローID（省略可能）
            priority (str): メッセージの優先度（省略可能）
            message_id (Optional[str]): メッセージID（省略可能、指定がない場合は自動生成）
            requires_response (bool): 応答が必要かどうか
            context_id (Optional[str]): コンテキストID（省略可能）
            from_agent (Optional[str]): 送信元エージェントID（省略可能、デフォルトはsender_id）
            
        Returns:
            str: 生成または使用されたメッセージID
        """
        if message_id is None:
            message_id = str(uuid.uuid4())
            
        message = {
            "id": message_id,
            "type": message_type,
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "content": content,
            "workflow_id": workflow_id,
            "priority": priority,
            "timestamp": datetime.now().isoformat(),
            "requires_response": requires_response,
            "context_id": context_id,
            "from_agent": from_agent or sender_id
        }
        
        self.messages.append(message)
        logger.info(f"メッセージを追加: 送信者={sender_id}, 受信者={recipient_id}, タイプ={message_type}")
        return message_id

    def get_messages(self, recipient_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        メッセージを取得します。

        Args:
            recipient_id (Optional[str]): 受信者ID（省略可能）

        Returns:
            List[Dict[str, Any]]: メッセージのリスト
        """
        if recipient_id:
            return [
                msg for msg in self.messages
                if msg.get("recipient_id") == recipient_id
            ]
        return self.messages.copy()

    def clear_messages(self) -> None:
        """メッセージをクリアします。"""
        self.messages.clear()
        logger.debug("メッセージをクリアしました")

    def send_message(self, message: Dict[str, Any]) -> None:
        """
        メッセージを送信します（publish のエイリアス）
        
        Args:
            message (Dict[str, Any]): 送信するメッセージ
        """
        self.publish(message)

class MessageClient:
    """メッセージングクライアント"""

    def __init__(self, client_id: str, broker: Optional[MessageBroker] = None):
        """
        メッセージングクライアントを初期化します。

        Args:
            client_id (str): クライアントID
            broker (Optional[MessageBroker]): メッセージブローカー（省略時は新しいインスタンスを作成）
        """
        self.client_id = client_id
        self.connected = False
        self.broker = broker if broker is not None else MessageBroker()
        logger.info(f"メッセージングクライアント {client_id} を初期化しました")

    def connect(self) -> bool:
        """
        メッセージングシステムに接続します。

        Returns:
            bool: 接続が成功したかどうか
        """
        self.connected = True
        logger.info(f"クライアント {self.client_id} が接続しました")
        return True

    def disconnect(self) -> bool:
        """
        メッセージングシステムから切断します。

        Returns:
            bool: 切断が成功したかどうか
        """
        self.connected = False
        logger.info(f"クライアント {self.client_id} が切断しました")
        return True

    def send_message(
        self,
        message_type: str,
        content: Dict[str, Any],
        recipient_id: Optional[str] = None,
        context_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        priority: str = "normal",
        requires_response: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> bool:
        """
        メッセージを送信します。

        Args:
            message_type (str): メッセージタイプ
            content (Dict[str, Any]): メッセージの内容
            recipient_id (Optional[str]): 受信者ID（省略可能）
            context_id (Optional[str]): コンテキストID
            workflow_id (Optional[str]): ワークフローID
            priority (str): 優先度
            requires_response (bool): 応答が必要かどうか
            metadata (Optional[Dict[str, Any]]): メタデータ
            **kwargs: その他のパラメータ

        Returns:
            bool: 送信が成功したかどうか

        Raises:
            RuntimeError: 接続されていない場合
        """
        if not self.connected:
            raise RuntimeError("メッセージングシステムに接続されていません")

        message = {
            "type": message_type,
            "sender_id": self.client_id,
            "recipient_id": recipient_id,
            "content": content,
            "context_id": context_id,
            "workflow_id": workflow_id,
            "priority": priority,
            "requires_response": requires_response
        }

        # メタデータがあれば追加
        if metadata:
            message["metadata"] = metadata
            
        # その他のパラメータがあれば追加
        for key, value in kwargs.items():
            if key not in message:
                message[key] = value

        self.broker.publish(message)
        logger.info(f"メッセージを送信: {message}")
        return True

    def receive_message(self) -> Optional[Dict[str, Any]]:
        """
        メッセージを受信します。

        Returns:
            Optional[Dict[str, Any]]: 受信したメッセージ、または None（メッセージがない場合）

        Raises:
            RuntimeError: 接続されていない場合
        """
        if not self.connected:
            raise RuntimeError("メッセージングシステムに接続されていません")

        messages = self.broker.get_messages(self.client_id)
        return messages[0] if messages else None

    def subscribe(self, message_type: MessageType, callback: Callable) -> None:
        """
        メッセージタイプに対するコールバックを登録します。

        Args:
            message_type (MessageType): メッセージタイプ
            callback (Callable): コールバック関数
        """
        self.broker.subscribe(message_type, callback)
        
    def get_priority_messages(self) -> List[Dict[str, Any]]:
        """
        優先度の高いメッセージを取得します。
        現在の実装では単にすべてのメッセージを返します。

        Returns:
            List[Dict[str, Any]]: 取得したメッセージのリスト

        Raises:
            RuntimeError: 接続されていない場合
        """
        if not self.connected:
            raise RuntimeError("メッセージングシステムに接続されていません")
            
        # 現在の実装では単にすべてのメッセージを返す
        # 将来的には優先度に基づいてソートする機能を追加する
        return self.broker.get_messages(self.client_id)

    def send_response(
        self,
        recipient_id: str,
        in_response_to: str,
        message_type: str,
        content: Dict[str, Any],
        context_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        priority: str = "high",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        特定のメッセージへの応答を送信します。

        Args:
            recipient_id (str): 受信者ID
            in_response_to (str): 応答先メッセージID
            message_type (str): メッセージタイプ
            content (Dict[str, Any]): メッセージの内容
            context_id (Optional[str]): コンテキストID
            workflow_id (Optional[str]): ワークフローID
            priority (str): 優先度
            metadata (Optional[Dict[str, Any]]): メタデータ

        Returns:
            bool: 送信が成功したかどうか
        """
        # コンテンツに応答情報を追加
        response_content = {
            **content,
            "in_response_to": in_response_to
        }
        
        # 通常のメッセージ送信メソッドを使用
        return self.send_message(
            message_type=message_type,
            content=response_content,
            recipient_id=recipient_id,
            context_id=context_id,
            workflow_id=workflow_id,
            priority=priority,
            requires_response=False,  # 応答へのさらなる応答は通常不要
            metadata=metadata
        ) 