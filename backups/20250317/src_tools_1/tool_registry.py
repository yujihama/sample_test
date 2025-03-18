"""
ツールレジストリ - ツールの登録と管理
"""

import os
from typing import Dict, List, Any, Optional, Type, Union
import yaml
import importlib
from loguru import logger

from src.core.tool_base import ToolBase, ToolResult


class ToolRegistry:
    """ツールレジストリクラス"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """シングルトンパターン実装"""
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        """
        レジストリの初期化
        
        Args:
            config_path: 設定ファイルのパス（省略時はデフォルト位置から読み込み）
        """
        if self._initialized:
            return
            
        self.tools: Dict[str, ToolBase] = {}
        self.tool_classes: Dict[str, Type[ToolBase]] = {}
        self.config: Dict[str, Any] = {}
        
        # 設定ファイルのパス
        self.config_path = config_path or os.path.join("config", "tools_config.yaml")
        
        # 登録済みツールの情報
        self.registered_info: Dict[str, Dict[str, Any]] = {}
        
        # 初期化処理を実行
        self._load_config()
        self._initialized = True
        logger.info("ツールレジストリが初期化されました")
    
    def _load_config(self):
        """設定ファイルの読み込み"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config = yaml.safe_load(f)
                logger.info(f"ツール設定を読み込みました: {self.config_path}")
            else:
                self.config = {"tools": {}}
                logger.warning(f"ツール設定ファイルが見つかりません: {self.config_path}")
        except Exception as e:
            logger.error(f"ツール設定の読み込みに失敗: {e}")
            self.config = {"tools": {}}
    
    def register_tool_class(self, tool_class: Type[ToolBase], name: Optional[str] = None):
        """
        ツールクラスを登録
        
        Args:
            tool_class: 登録するツールクラス
            name: 登録名（省略時はクラス名）
        """
        name = name or tool_class.__name__
        self.tool_classes[name] = tool_class
        logger.info(f"ツールクラスを登録: {name}")
    
    def create_tool_instance(self, tool_class_name: str, tool_id: Optional[str] = None) -> Optional[ToolBase]:
        """
        ツールインスタンスを作成
        
        Args:
            tool_class_name: ツールクラス名
            tool_id: 指定するツールID
            
        Returns:
            ToolBase: 作成されたツールインスタンス
        """
        if tool_class_name not in self.tool_classes:
            logger.error(f"ツールクラスが未登録です: {tool_class_name}")
            return None
            
        try:
            tool_class = self.tool_classes[tool_class_name]
            tool_instance = tool_class(tool_id=tool_id)
            return tool_instance
        except Exception as e:
            logger.error(f"ツールインスタンス作成エラー: {e}")
            return None
    
    def register_tool(self, tool: ToolBase):
        """
        ツールインスタンスを登録
        
        Args:
            tool: 登録するツールインスタンス
        """
        self.tools[tool.tool_id] = tool
        self.registered_info[tool.tool_id] = tool.get_info()
        logger.info(f"ツールを登録: {tool.tool_id}")
    
    def get_tool(self, tool_id: str) -> Optional[ToolBase]:
        """
        ツールを取得
        
        Args:
            tool_id: ツールID
            
        Returns:
            ToolBase: ツールインスタンス
        """
        if tool_id not in self.tools:
            logger.warning(f"ツールが見つかりません: {tool_id}")
            return None
        return self.tools[tool_id]
    
    def get_all_tools(self) -> Dict[str, ToolBase]:
        """
        全ツールを取得
        
        Returns:
            Dict[str, ToolBase]: ツール辞書
        """
        return self.tools
    
    def get_tool_info(self, tool_id: str = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        ツール情報を取得
        
        Args:
            tool_id: ツールID（省略時は全ツール情報）
            
        Returns:
            Union[Dict[str, Any], List[Dict[str, Any]]]: ツール情報
        """
        if tool_id:
            if tool_id in self.registered_info:
                return self.registered_info[tool_id]
            return None
        
        return list(self.registered_info.values())
    
    async def execute_tool(self, tool_id: str, params: Dict[str, Any]) -> ToolResult:
        """
        ツールを実行
        
        Args:
            tool_id: ツールID
            params: 実行パラメータ
            
        Returns:
            ToolResult: 実行結果
        """
        tool = self.get_tool(tool_id)
        if not tool:
            return ToolResult(
                tool_id=tool_id,
                status="error",
                data={},
                error_message=f"ツールが見つかりません: {tool_id}"
            )
        
        try:
            if not tool.validate_params(params):
                return ToolResult(
                    tool_id=tool_id,
                    status="error",
                    data={},
                    error_message="無効なパラメータです"
                )
                
            return await tool.execute(params)
        except Exception as e:
            return await tool.handle_error(e, params)
    
    def load_tools_from_config(self):
        """設定ファイルからツールを読み込み"""
        if not self.config or "tools" not in self.config:
            logger.warning("ツール設定がありません")
            return
            
        for tool_name, tool_config in self.config.get("tools", {}).items():
            try:
                # モジュールとクラスをインポート
                module_path = tool_config.get("module", f"src.tools.{tool_name.lower()}")
                class_name = tool_config.get("class", tool_name)
                
                module = importlib.import_module(module_path)
                tool_class = getattr(module, class_name)
                
                # クラス登録
                self.register_tool_class(tool_class, name=tool_name)
                
                # インスタンス作成＆登録（設定で有効なもののみ）
                if tool_config.get("enabled", True):
                    tool_id = f"{tool_name}_{tool_config.get('id_suffix', '')}"
                    tool_instance = self.create_tool_instance(tool_name, tool_id=tool_id)
                    if tool_instance:
                        # 設定から追加メタデータを適用
                        if "metadata" in tool_config:
                            tool_instance.metadata.update(tool_config["metadata"])
                        
                        self.register_tool(tool_instance)
                
            except Exception as e:
                logger.error(f"ツール {tool_name} の読み込みに失敗: {e}")


# シングルトンインスタンス
registry = ToolRegistry() 