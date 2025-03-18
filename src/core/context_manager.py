"""
エージェント間で共有するコンテキストを管理するモジュール
このモジュールでは、監査手続きの実行中にエージェント間で共有される情報を
効率的に管理するための機能を提供します。
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union
from loguru import logger
from pydantic import BaseModel, Field, ConfigDict
import asyncio


class SharedContext(BaseModel):
    """
    エージェント間で共有するコンテキスト情報
    """
    context_id: str = Field(..., description="コンテキストの一意識別子")
    workflow_id: str = Field(..., description="関連するワークフローID")
    parent_id: Optional[str] = Field(None, description="親コンテキストID（ある場合）")
    creator_agent_id: Optional[str] = Field(None, description="作成者エージェントID")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新日時")
    data: Dict[str, Any] = Field(default_factory=dict, description="コンテキストデータ")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="メタデータ")
    access_history: List[Dict[str, Any]] = Field(default_factory=list, description="アクセス履歴")
    
    # Pydantic v2スタイルの設定
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def record_access(self, agent_id: str, operation: str) -> None:
        """アクセス履歴を記録"""
        self.access_history.append({
            "agent_id": agent_id,
            "operation": operation,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """コンテキストをディクショナリに変換"""
        return {
            "context_id": self.context_id,
            "workflow_id": self.workflow_id,
            "parent_id": self.parent_id,
            "creator_agent_id": self.creator_agent_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "data": self.data,
            "metadata": self.metadata,
            "access_history": self.access_history
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SharedContext':
        """ディクショナリからコンテキストを復元"""
        # 日時文字列をdatetimeオブジェクトに変換
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


class ContextManager:
    """
    SharedContextを管理するクラス
    エージェント間でのコンテキスト共有とデータ継承を可能にする
    """
    def __init__(self):
        self.contexts: Dict[str, SharedContext] = {}
        self.workflow_contexts: Dict[str, Set[str]] = {}  # workflow_id -> Set[context_id]
        logger.info("ContextManager initialized")
    
    def create_context(self, workflow_id: str, initial_data: Optional[Dict[str, Any]] = None) -> SharedContext:
        """
        新しいコンテキストを作成
        
        Args:
            workflow_id: 関連するワークフローID
            initial_data: 初期データ
            
        Returns:
            作成されたSharedContextオブジェクト
        """
        context_id = f"ctx-{uuid.uuid4().hex[:8]}"
        context = SharedContext(
            context_id=context_id,
            workflow_id=workflow_id,
            creator_agent_id=None,
            data=initial_data or {},
        )
        
        self.contexts[context_id] = context
        
        if workflow_id not in self.workflow_contexts:
            self.workflow_contexts[workflow_id] = set()
        
        self.workflow_contexts[workflow_id].add(context_id)
        
        logger.info(f"Created context {context_id} for workflow {workflow_id}")
        return context
    
    def get_context(self, context_id: str, agent_id: str) -> Optional[SharedContext]:
        """
        コンテキストの取得
        
        Args:
            context_id: コンテキストID
            agent_id: アクセスするエージェントID
            
        Returns:
            SharedContextオブジェクト（存在しない場合はNone）
        """
        context = self.contexts.get(context_id)
        if context:
            context.record_access(agent_id, "get")
            logger.debug(f"Agent {agent_id} accessed context {context_id}")
        else:
            logger.warning(f"Context {context_id} not found")
        
        return context
    
    def update_context(
        self, context_id: str, agent_id: str, data_updates: Dict[str, Any], 
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> Optional[SharedContext]:
        """
        コンテキストの更新
        
        Args:
            context_id: コンテキストID
            agent_id: 更新するエージェントID
            data_updates: 更新するデータ
            metadata_updates: 更新するメタデータ
            
        Returns:
            更新されたSharedContextオブジェクト（存在しない場合はNone）
        """
        context = self.contexts.get(context_id)
        if not context:
            logger.warning(f"Context {context_id} not found for update")
            return None
        
        # データの更新（ネストされた辞書もマージ）
        self._deep_update(context.data, data_updates)
        
        # メタデータの更新
        if metadata_updates:
            self._deep_update(context.metadata, metadata_updates)
        
        context.updated_at = datetime.now()
        context.record_access(agent_id, "update")
        
        logger.info(f"Agent {agent_id} updated context {context_id}")
        return context
    
    def get_workflow_contexts(self, workflow_id: str) -> List[SharedContext]:
        """
        ワークフローに関連するすべてのコンテキストを取得
        
        Args:
            workflow_id: ワークフローID
            
        Returns:
            SharedContextオブジェクトのリスト
        """
        context_ids = self.workflow_contexts.get(workflow_id, set())
        contexts = [self.contexts[ctx_id] for ctx_id in context_ids if ctx_id in self.contexts]
        return contexts
    
    def _deep_update(self, d: Dict[str, Any], u: Dict[str, Any]) -> Dict[str, Any]:
        """
        ネストされた辞書の深い更新（再帰的にマージ）
        
        Args:
            d: 更新される辞書
            u: 更新する値を含む辞書
            
        Returns:
            更新された辞書
        """
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._deep_update(d[k], v)
            else:
                d[k] = v
        return d
    
    def delete_context(self, context_id: str) -> bool:
        """
        コンテキストの削除
        
        Args:
            context_id: 削除するコンテキストID
            
        Returns:
            削除成功の場合True、存在しない場合False
        """
        if context_id not in self.contexts:
            logger.warning(f"Context {context_id} not found for deletion")
            return False
        
        context = self.contexts.pop(context_id)
        
        # ワークフローとコンテキストの関連付けも削除
        workflow_id = context.workflow_id
        if workflow_id in self.workflow_contexts:
            self.workflow_contexts[workflow_id].discard(context_id)
            
            # 空になったら削除
            if not self.workflow_contexts[workflow_id]:
                del self.workflow_contexts[workflow_id]
        
        logger.info(f"Deleted context {context_id}")
        return True
    
    def create_child_context(
        self, parent_context_id: str, agent_id: str, data_filter: Optional[List[str]] = None
    ) -> Optional[SharedContext]:
        """
        親コンテキストから子コンテキストを作成（継承）
        
        Args:
            parent_context_id: 親コンテキストID
            agent_id: 作成するエージェントID
            data_filter: 継承するデータキーのリスト（指定がなければすべて継承）
            
        Returns:
            作成された子SharedContextオブジェクト、親が存在しない場合はNone
        """
        parent = self.contexts.get(parent_context_id)
        if not parent:
            logger.warning(f"Parent context {parent_context_id} not found")
            return None
        
        # 親からデータをフィルタリングして取得
        if data_filter:
            initial_data = {k: parent.data[k] for k in data_filter if k in parent.data}
        else:
            initial_data = parent.data.copy()
        
        # 親のワークフローIDを使って子コンテキストを作成
        child = self.create_context(parent.workflow_id, initial_data)
        
        # 親子関係をメタデータに記録
        child.parent_id = parent_context_id
        child.creator_agent_id = agent_id
        child.record_access(agent_id, "create_from_parent")
        
        logger.info(f"Agent {agent_id} created child context {child.context_id} from parent {parent_context_id}")
        return child

    def merge_contexts(
        self, source_contexts: List[str], agent_id: str, target_context_id: Optional[str] = None
    ) -> Optional[SharedContext]:
        """
        複数のコンテキストを一つにマージ
        
        Args:
            source_contexts: マージ元コンテキストIDのリスト
            agent_id: 操作を実行するエージェントID
            target_context_id: マージ先コンテキストID（未指定の場合は新規作成）
            
        Returns:
            マージされたコンテキスト
        """
        # 全ソースコンテキストの取得
        contexts = []
        workflow_id = None
        
        for ctx_id in source_contexts:
            ctx = self.get_context(ctx_id, agent_id)
            if ctx:
                contexts.append(ctx)
                if workflow_id is None:
                    workflow_id = ctx.workflow_id
                elif workflow_id != ctx.workflow_id:
                    logger.warning(f"異なるワークフローのコンテキストがマージされます: {workflow_id} と {ctx.workflow_id}")
        
        if not contexts:
            logger.warning("マージ可能なソースコンテキストがありません")
            return None
            
        if not workflow_id:
            workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        
        # マージ先コンテキストの準備
        target = None
        if target_context_id:
            target = self.get_context(target_context_id, agent_id)
        
        if not target:
            target_id = target_context_id or f"ctx-{uuid.uuid4().hex}"
            target = SharedContext(
                context_id=target_id,
                workflow_id=workflow_id,
                creator_agent_id=agent_id,
                metadata={"merged_from": source_contexts}
            )
        
        # データのマージ
        merged_data = {}
        for ctx in contexts:
            merged_data.update(ctx.data)
        
        target.data.update(merged_data)
        target.updated_at = datetime.now()
        
        # メタデータの更新
        target.metadata["merged_from"] = source_contexts
        target.metadata["merged_at"] = datetime.now().isoformat()
        
        target.record_access(agent_id, "merge")
        
        # コンテキストを保存
        self.contexts[target.context_id] = target
        
        # ワークフローコンテキストマップを更新
        if target.workflow_id not in self.workflow_contexts:
            self.workflow_contexts[target.workflow_id] = set()
        self.workflow_contexts[target.workflow_id].add(target.context_id)
        
        logger.info(f"コンテキストマージ: {len(contexts)}個のコンテキストを {target.context_id} にマージしました")
        return target


# シングルトンインスタンス
context_manager = ContextManager()


class ContextClient:
    """
    エージェントがContextManagerと通信するためのクライアント
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._context: Dict[str, Any] = {}
        
    async def get_context(self, key: str) -> Any:
        """Get context value."""
        await asyncio.sleep(0.1)  # Simulate context fetch
        return self._context.get(key)
        
    async def set_context(self, key: str, value: Any) -> None:
        """Set context value."""
        await asyncio.sleep(0.1)  # Simulate context update
        self._context[key] = value

    def create_context(self, workflow_id: str, initial_data: Optional[Dict[str, Any]] = None) -> SharedContext:
        """
        新しいコンテキストを作成
        
        Args:
            workflow_id: 関連するワークフローID
            initial_data: 初期データ
            
        Returns:
            作成されたSharedContextオブジェクト
        """
        return context_manager.create_context(workflow_id, initial_data)
    
    def get_context(self, context_id: str) -> Optional[SharedContext]:
        """
        コンテキストの取得
        
        Args:
            context_id: コンテキストID
            
        Returns:
            SharedContextオブジェクト
        """
        return context_manager.get_context(context_id, self.agent_id)
    
    def update_context(
        self, context_id: str, data_updates: Dict[str, Any], 
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> Optional[SharedContext]:
        """
        コンテキストの更新
        
        Args:
            context_id: コンテキストID
            data_updates: 更新するデータ
            metadata_updates: 更新するメタデータ
            
        Returns:
            更新されたSharedContextオブジェクト
        """
        return context_manager.update_context(context_id, self.agent_id, data_updates, metadata_updates)
    
    def get_workflow_contexts(self, workflow_id: str) -> List[SharedContext]:
        """
        ワークフローに関連するすべてのコンテキストを取得
        
        Args:
            workflow_id: ワークフローID
            
        Returns:
            SharedContextオブジェクトのリスト
        """
        return context_manager.get_workflow_contexts(workflow_id)
    
    def create_child_context(
        self, parent_context_id: str, data_filter: Optional[List[str]] = None
    ) -> Optional[SharedContext]:
        """
        親コンテキストから子コンテキストを作成
        
        Args:
            parent_context_id: 親コンテキストID
            data_filter: 継承するデータキーのリスト
            
        Returns:
            作成された子SharedContextオブジェクト
        """
        return context_manager.create_child_context(parent_context_id, self.agent_id, data_filter)
    
    def merge_contexts(
        self, source_contexts: List[str], target_context_id: Optional[str] = None
    ) -> Optional[SharedContext]:
        """
        複数のコンテキストを一つにマージ
        
        Args:
            source_contexts: マージ元コンテキストIDのリスト
            target_context_id: マージ先コンテキストID（未指定の場合は新規作成）
            
        Returns:
            マージされたコンテキスト
        """
        return context_manager.merge_contexts(source_contexts, self.agent_id, target_context_id) 