"""
メッセージタイプごとの処理を管理するハンドラーモジュール
"""

from typing import Dict, Any, Optional, Callable, Union
from loguru import logger

from src.models.schema import MessageType, AgentMessage
from src.core.exceptions import MessageProcessingError

class MessageTypeHandler:
    """
    メッセージタイプごとの処理を管理するハンドラークラス
    """
    
    def __init__(self):
        self._handlers = {}
        self._fallback_handler = None
    
    def register_handler(self, message_type: Union[str, MessageType], handler_func: Callable):
        """
        特定のメッセージタイプに対するハンドラー関数を登録する
        
        Args:
            message_type: 処理するメッセージタイプ
            handler_func: メッセージを処理するコールバック関数
                          (message: AgentMessage, context: Dict) -> Dict[str, Any]
        """
        if isinstance(message_type, MessageType):
            message_type = message_type.value
        
        self._handlers[message_type] = handler_func
    
    def register_fallback_handler(self, handler_func: Callable):
        """
        どのメッセージタイプにも一致しない場合のフォールバックハンドラーを登録
        
        Args:
            handler_func: メッセージを処理するコールバック関数
        """
        self._fallback_handler = handler_func
    
    def handle_message(self, message: AgentMessage, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        メッセージのタイプに基づいて適切なハンドラーを呼び出す
        
        Args:
            message: 処理するメッセージ
            context: 追加のコンテキスト情報（オプション）
        
        Returns:
            処理結果を含む辞書
        
        Raises:
            MessageProcessingError: 適切なハンドラーがなく、フォールバックもない場合
        """
        if context is None:
            context = {}
        
        message_type = message.message_type
        
        if message_type in self._handlers:
            return self._handlers[message_type](message, context)
        elif self._fallback_handler:
            return self._fallback_handler(message, context)
        else:
            raise MessageProcessingError(f"メッセージタイプ '{message_type}' のハンドラーが登録されていません") 