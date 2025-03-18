"""
エージェント管理サービスモジュール

このモジュールは、エージェントの管理と制御のための統合サービスを提供します。
API層とコア機能を橋渡しする中間レイヤーとして機能し、エージェント管理の機能重複を解消します。
改善版: 単一責任の原則に基づいた設計とエージェント管理機能の統合
"""

import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum

from loguru import logger

# 依存関係の逆転のため、より具体的な実装への依存を避ける
# AgentManagerとAgentControllerへの直接依存を削除
from src.models.schema import AgentRole, AgentStatus, MessageType, MessagePriority
from src.core.messaging import MessageClient
from src.core.conversation_context import ConversationManager


class AgentManagementService:
    """
    エージェント管理サービス（改善版）
    
    このサービスクラスは以下の役割を持ちます:
    1. API層とコア機能の橋渡し
    2. エージェント管理機能の一元化
    3. エージェント関連の操作の統合インターフェース提供
    
    改善点:
    - 機能重複の解消
    - 単一責任の原則の適用
    - 統一されたデータモデルの使用
    """
    
    _instance = None
    
    def __new__(cls):
        """シングルトンパターンを実装"""
        if cls._instance is None:
            cls._instance = super(AgentManagementService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """サービスの初期化（シングルトンなので1回だけ実行）"""
        if self._initialized:
            return
            
        self._initialized = True
        
        # 内部データストア - AgentManagerの機能を統合
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.tasks: Dict[str, Dict[str, Any]] = {}
        
        # コントローラの機能を統合するためのデータ構造
        self.agent_roles: Dict[str, AgentRole] = {}
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_assignments: Dict[str, set] = {}
        
        # 共有サービス
        self.message_client = MessageClient("agent_management_service")
        self.conversation_manager = ConversationManager()
        
        # エージェント情報の追加キャッシュ
        self.agent_metadata: Dict[str, Dict[str, Any]] = {}
        
        logger.info("統合エージェント管理サービスを初期化しました")
    
    def register_agent(
        self, 
        agent_id: str, 
        agent_type: str,
        agent_role: Optional[AgentRole] = None,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        エージェントを登録します。
        
        Args:
            agent_id: エージェントID
            agent_type: エージェントタイプ
            agent_role: エージェントの役割（オプション）
            capabilities: エージェントの機能一覧（オプション）
            metadata: 追加メタデータ（オプション）
            
        Returns:
            bool: 登録成功したかどうか
        """
        # 既存のエージェントをチェック
        if agent_id in self.agents:
            logger.warning(f"エージェント {agent_id} は既に登録されています")
            return False
            
        # 現在日時
        current_time = datetime.now().isoformat()
        
        # 基本的なエージェント情報
        self.agents[agent_id] = {
            "id": agent_id,
            "type": agent_type,
            "status": "idle",
            "current_task": None,
            "registered_at": current_time,
            "last_active": current_time
        }
        
        # 追加情報の保存
        agent_meta = {
            "role": agent_role,
            "capabilities": capabilities or [],
            "metadata": metadata or {},
            "registered_at": current_time
        }
        
        # メタデータを統合
        self.agent_metadata[agent_id] = agent_meta
        self.agents[agent_id].update(agent_meta)
        
        # 役割情報を保存
        if agent_role:
            self.agent_roles[agent_id] = agent_role
            
        logger.info(f"エージェント {agent_id} を登録しました（タイプ: {agent_type}, 役割: {agent_role}）")
        return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        エージェントの登録を解除します。
        
        Args:
            agent_id: エージェントID
            
        Returns:
            bool: 登録解除成功したかどうか
        """
        # エージェントの存在確認
        if agent_id not in self.agents:
            logger.warning(f"エージェント {agent_id} は登録されていません")
            return False
            
        # アクティブなタスクの確認
        if any(task["assigned_agent"] == agent_id for task in self.tasks.values()):
            logger.warning(f"エージェント {agent_id} にはアクティブなタスクがあります")
            return False
            
        # エージェント関連のデータを削除
        if agent_id in self.agents:
            del self.agents[agent_id]
            
        if agent_id in self.agent_metadata:
            del self.agent_metadata[agent_id]
            
        if agent_id in self.agent_roles:
            del self.agent_roles[agent_id]
            
        logger.info(f"エージェント {agent_id} の登録を解除しました")
        return True
    
    def assign_task(
        self, 
        task_id: str, 
        agent_id: str, 
        task_data: Dict[str, Any],
        task_type: Optional[str] = None,
        workflow_id: Optional[str] = None,
        context_id: Optional[str] = None,
        priority: int = 1
    ) -> bool:
        """
        タスクをエージェントに割り当てます。
        
        Args:
            task_id: タスクID
            agent_id: エージェントID
            task_data: タスクデータ
            task_type: タスクタイプ（オプション）
            workflow_id: ワークフローID（オプション）
            context_id: コンテキストID（オプション）
            priority: 優先度（デフォルト: 1）
            
        Returns:
            bool: 割り当て成功したかどうか
        """
        # エージェントの存在確認
        if agent_id not in self.agents:
            logger.error(f"エージェント {agent_id} が見つかりません")
            return False
            
        # エージェントがビジー状態かどうか確認
        if self.agents[agent_id]["status"] != "idle":
            logger.warning(f"エージェント {agent_id} は現在ビジー状態です")
            return False
            
        # タスク情報の作成
        self.tasks[task_id] = {
            "id": task_id,
            "data": task_data,
            "status": "assigned",
            "assigned_agent": agent_id,
            "type": task_type,
            "workflow_id": workflow_id,
            "context_id": context_id,
            "priority": priority,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # エージェントの状態を更新
        self.agents[agent_id]["status"] = "busy"
        self.agents[agent_id]["current_task"] = task_id
        self.agents[agent_id]["last_active"] = datetime.now().isoformat()
        
        # タスク割り当て情報を更新
        if task_id not in self.task_assignments:
            self.task_assignments[task_id] = set()
        self.task_assignments[task_id].add(agent_id)
        
        # アクティブタスクに追加
        self.active_tasks[task_id] = self.tasks[task_id]
        
        logger.info(f"タスク {task_id} をエージェント {agent_id} に割り当てました")
        return True
    
    def update_task_status(self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None) -> bool:
        """
        タスクの状態を更新します。
        
        Args:
            task_id: タスクID
            status: 新しい状態
            result: タスク結果（オプション）
            
        Returns:
            bool: 更新成功したかどうか
        """
        # タスクの存在確認
        if task_id not in self.tasks:
            logger.error(f"タスク {task_id} が見つかりません")
            return False
            
        # 現在のタスク情報を取得
        task = self.tasks[task_id]
        
        # 状態を更新
        task["status"] = status
        task["updated_at"] = datetime.now().isoformat()
        
        # 結果が提供された場合は保存
        if result:
            task["result"] = result
            
        # タスクが完了または失敗した場合
        if status in ["completed", "failed"]:
            agent_id = task["assigned_agent"]
            if agent_id and agent_id in self.agents:
                # エージェントをアイドル状態に戻す
                self.agents[agent_id]["status"] = "idle"
                self.agents[agent_id]["current_task"] = None
                
                # アクティブタスクから削除
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
        
        logger.info(f"タスク {task_id} の状態を {status} に更新しました")
        return True
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        エージェントの状態を取得します。
        
        Args:
            agent_id: エージェントID
            
        Returns:
            Optional[Dict[str, Any]]: エージェントの状態情報
        """
        # エージェントの存在確認
        if agent_id not in self.agents:
            logger.warning(f"エージェント {agent_id} が見つかりません")
            return None
            
        # エージェント情報を取得
        agent_info = self.agents[agent_id].copy()
        
        # 追加のメタデータがあれば統合
        if agent_id in self.agent_metadata:
            # 重複を避けるためにメタデータセクションのみ更新
            metadata = self.agent_metadata[agent_id].get("metadata", {})
            if "metadata" in agent_info:
                agent_info["metadata"].update(metadata)
            else:
                agent_info["metadata"] = metadata
        
        return agent_info
    
    def get_agent_tasks(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        エージェントのタスク一覧を取得します。
        
        Args:
            agent_id: エージェントID
            
        Returns:
            List[Dict[str, Any]]: タスク情報のリスト
        """
        # エージェントの存在確認
        if agent_id not in self.agents:
            logger.warning(f"エージェント {agent_id} が見つかりません")
            return []
            
        # エージェントのタスクを検索
        return [
            task for task in self.tasks.values()
            if task.get("assigned_agent") == agent_id
        ]
    
    def get_all_agents(self) -> List[Dict[str, Any]]:
        """
        すべてのエージェント情報を取得します。
        
        Returns:
            List[Dict[str, Any]]: エージェント情報のリスト
        """
        return list(self.agents.values())
    
    def get_all_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        すべてのタスク情報を取得します。
        
        Args:
            status: フィルターするステータス（オプション）
            
        Returns:
            List[Dict[str, Any]]: タスク情報のリスト
        """
        if status:
            return [
                task for task in self.tasks.values()
                if task.get("status") == status
            ]
        return list(self.tasks.values())
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        タスクの状態を取得します。
        
        Args:
            task_id: タスクID
            
        Returns:
            Optional[Dict[str, Any]]: タスク情報
        """
        return self.tasks.get(task_id)
    
    def create_conversation(self, topic: str, workflow_id: Optional[str] = None) -> str:
        """
        新しい会話コンテキストを作成します。
        
        Args:
            topic: 会話トピック
            workflow_id: ワークフローID（オプション）
            
        Returns:
            str: 作成された会話のコンテキストID
        """
        context = self.conversation_manager.create_context(topic=topic, workflow_id=workflow_id)
        return context.context_id
    
    def send_message(
        self, 
        from_agent_id: str, 
        to_agent_id: str, 
        message_type: str, 
        content: Dict[str, Any],
        workflow_id: Optional[str] = None,
        context_id: Optional[str] = None,
        priority: str = "normal",
        requires_response: bool = False
    ) -> str:
        """
        エージェント間でメッセージを送信します。
        
        Args:
            from_agent_id: 送信元エージェントID
            to_agent_id: 送信先エージェントID
            message_type: メッセージタイプ
            content: メッセージ内容
            workflow_id: ワークフローID（オプション）
            context_id: コンテキストID（オプション）
            priority: 優先度（オプション）
            requires_response: 応答が必要かどうか（オプション）
            
        Returns:
            str: メッセージID
        """
        # メッセージID生成
        message_id = f"msg-{uuid.uuid4().hex}"
        
        # メッセージブローカーにメッセージを追加
        self.message_client.send_message(
            message_type=message_type,
            content=content,
            recipient_id=to_agent_id,
            context_id=context_id,
            workflow_id=workflow_id,
            priority=priority,
            requires_response=requires_response
        )
        
        logger.info(f"メッセージを送信: {from_agent_id} → {to_agent_id} (タイプ: {message_type})")
        return message_id


# シングルトンインスタンスを提供する関数
def get_agent_management_service() -> AgentManagementService:
    """
    エージェント管理サービスのシングルトンインスタンスを取得します。
    
    Returns:
        AgentManagementService: サービスのインスタンス
    """
    return AgentManagementService()


# FastAPI依存関係提供関数
def get_agent_management_service_dependency() -> AgentManagementService:
    """
    FastAPIの依存関係注入のためのプロバイダー関数
    
    Returns:
        AgentManagementService: サービスのインスタンス
    """
    return get_agent_management_service()


# 後方互換性のためのラッパー関数（非推奨）
def get_agent_manager():
    """
    旧APIとの後方互換性のためのラッパー関数（非推奨）
    
    Returns:
        AgentManagementService: エージェント管理サービスのインスタンス
        
    Deprecated:
        代わりに get_agent_management_service() を使用してください。
    """
    import warnings
    warnings.warn(
        "get_agent_manager関数は非推奨です。代わりにget_agent_management_service()を使用してください。",
        DeprecationWarning,
        stacklevel=2
    )
    return get_agent_management_service() 