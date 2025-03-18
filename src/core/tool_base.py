"""
補助ツールの基本クラス
"""

import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from loguru import logger
from src.models.schema import MessageType, MessagePriority


class ToolResult(BaseModel):
    """ツール実行結果のモデル"""
    tool_id: str
    status: str  # success, error, partial
    data: Dict[str, Any]
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Pydantic v2スタイルの設定
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ToolBase(ABC):
    """補助ツール基底クラス"""
    
    def __init__(self, tool_id: str = None):
        """ツールの初期化"""
        self.tool_id = tool_id or f"{self.__class__.__name__}_{uuid.uuid4().hex[:8]}"
        self.description = "基本ツール"
        self.version = "1.0.0"
        self.capabilities = []
        self.metadata = {}
        logger.info(f"ツール初期化: {self.tool_id}")
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """
        ツール実行のメイン処理
        
        Args:
            params: 実行パラメータ
            
        Returns:
            ToolResult: 実行結果
        """
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        パラメータのバリデーション
        
        Args:
            params: 検証するパラメータ
            
        Returns:
            bool: 検証結果
        """
        # 基本実装はすべてのパラメータを許可
        return True
    
    def get_capabilities(self) -> List[str]:
        """
        ツールの機能リストを取得
        
        Returns:
            List[str]: 機能一覧
        """
        return self.capabilities
    
    def get_info(self) -> Dict[str, Any]:
        """
        ツールの情報を取得
        
        Returns:
            Dict[str, Any]: ツール情報
        """
        return {
            "tool_id": self.tool_id,
            "name": self.__class__.__name__,
            "description": self.description,
            "version": self.version,
            "capabilities": self.capabilities,
            "metadata": self.metadata
        }
    
    async def handle_error(self, error: Exception, params: Dict[str, Any]) -> ToolResult:
        """
        エラー処理
        
        Args:
            error: 発生したエラー
            params: 実行パラメータ
            
        Returns:
            ToolResult: エラー結果
        """
        error_message = f"{error.__class__.__name__}: {str(error)}"
        logger.error(f"ツール実行エラー - {self.tool_id}: {error_message}")
        
        return ToolResult(
            tool_id=self.tool_id,
            status="error",
            data={},
            error_message=error_message,
            metadata={
                "params": params,
                "error_type": error.__class__.__name__
            }
        ) 