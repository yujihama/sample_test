"""
エージェントコントローラモジュール

このモジュールは、会話コンテキストを活用して複数のエージェント間の
協力的な問題解決を管理します。各エージェントの役割と責任を明確にし、
効率的な連携を実現します。
"""

from typing import Dict, List, Any, Optional, Set, Union, Tuple
from datetime import datetime
import uuid
from enum import Enum

from loguru import logger

from src.models.schema import MessageType, MessagePriority, AgentRole
from src.core.conversation_context import ConversationContext, ConversationManager
from src.core.agent_coordination import AgentCoordinator, CoordinationProtocol
from src.core.messaging import MessageClient
from src.core.auto_resolution import AutoResolutionEngine


class AgentControllerState(str, Enum):
    """エージェントコントローラの状態を表す列挙型"""
    INITIALIZING = "initializing"  # 初期化中
    READY = "ready"  # 準備完了
    PROCESSING = "processing"  # 処理中
    PAUSED = "paused"  # 一時停止
    ERROR = "error"  # エラー状態
    TERMINATED = "terminated"  # 終了


class AgentController:
    """
    エージェント間の連携を統括的に管理するコントローラ
    
    このクラスは以下の責務を持ちます：
    1. エージェントの登録と管理
    2. 会話コンテキストの管理
    3. エージェント間の連携プロトコルの調整
    4. タスクの割り当てと進捗管理
    5. エラーハンドリングと自動復旧
    """
    
    def __init__(
        self,
        controller_id: str,
        message_client: MessageClient,
        conversation_manager: Optional[ConversationManager] = None
    ):
        """
        Args:
            controller_id: コントローラの一意識別子
            message_client: メッセージング用クライアント
            conversation_manager: 会話管理用マネージャ（省略時は新規作成）
        """
        self.controller_id = controller_id
        self.message_client = message_client
        self.conversation_manager = conversation_manager or ConversationManager()
        
        # エージェント管理
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.agent_roles: Dict[str, AgentRole] = {}
        self.agent_coordinators: Dict[str, AgentCoordinator] = {}
        
        # タスク管理
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.task_assignments: Dict[str, Set[str]] = {}  # タスクID -> エージェントIDのセット
        
        # 状態管理
        self.state = AgentControllerState.INITIALIZING
        self.error_count = 0
        self.last_error: Optional[Dict[str, Any]] = None
        
        logger.info(f"エージェントコントローラを初期化: {controller_id}")
    
    def register_agent(
        self,
        agent_id: str,
        agent_role: AgentRole,
        capabilities: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        新しいエージェントを登録
        
        Args:
            agent_id: エージェントの一意識別子
            agent_role: エージェントの役割
            capabilities: エージェントの機能リスト
            metadata: エージェントに関する追加情報
            
        Returns:
            登録が成功したかどうか
        """
        if agent_id in self.registered_agents:
            logger.warning(f"エージェントは既に登録されています: {agent_id}")
            return False
        
        # エージェント情報を登録
        self.registered_agents[agent_id] = {
            "role": agent_role,
            "capabilities": capabilities,
            "metadata": metadata or {},
            "status": "active",
            "registered_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat()
        }
        
        # 役割を記録
        self.agent_roles[agent_id] = agent_role
        
        # コーディネーターを作成
        coordinator = AgentCoordinator(
            agent_id=agent_id,
            message_client=self.message_client,
            agent_role=agent_role
        )
        self.agent_coordinators[agent_id] = coordinator
        
        logger.info(f"新しいエージェントを登録: {agent_id} (役割: {agent_role.value})")
        return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        エージェントの登録を解除
        
        Args:
            agent_id: エージェントの一意識別子
            
        Returns:
            解除が成功したかどうか
        """
        if agent_id not in self.registered_agents:
            logger.warning(f"エージェントが見つかりません: {agent_id}")
            return False
        
        # アクティブなタスクの確認
        active_tasks = [
            task_id for task_id, agents in self.task_assignments.items()
            if agent_id in agents
        ]
        
        if active_tasks:
            logger.warning(f"エージェントにアクティブなタスクが存在します: {agent_id}, タスク: {active_tasks}")
            return False
        
        # 登録情報を削除
        del self.registered_agents[agent_id]
        del self.agent_roles[agent_id]
        del self.agent_coordinators[agent_id]
        
        logger.info(f"エージェントの登録を解除: {agent_id}")
        return True
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        エージェントの情報を取得
        
        Args:
            agent_id: エージェントの一意識別子
            
        Returns:
            エージェント情報、存在しない場合はNone
        """
        return self.registered_agents.get(agent_id)
    
    def get_agents_by_role(self, role: AgentRole) -> List[str]:
        """
        指定した役割を持つエージェントのリストを取得
        
        Args:
            role: エージェントの役割
            
        Returns:
            エージェントIDのリスト
        """
        return [
            agent_id for agent_id, agent_role in self.agent_roles.items()
            if agent_role == role
        ]
    
    def get_agent_coordinator(self, agent_id: str) -> Optional[AgentCoordinator]:
        """
        エージェントのコーディネーターを取得
        
        Args:
            agent_id: エージェントの一意識別子
            
        Returns:
            エージェントコーディネーター、存在しない場合はNone
        """
        return self.agent_coordinators.get(agent_id)
    
    def create_conversation(
        self,
        topic: str,
        workflow_id: Optional[str] = None,
        parent_context_id: Optional[str] = None
    ) -> ConversationContext:
        """
        新しい会話コンテキストを作成
        
        Args:
            topic: 会話のトピック
            workflow_id: 関連するワークフローID
            parent_context_id: 親コンテキストID
            
        Returns:
            作成された会話コンテキスト
        """
        return self.conversation_manager.create_context(
            topic=topic,
            workflow_id=workflow_id,
            parent_context_id=parent_context_id
        )
    
    def get_conversation(self, context_id: str) -> Optional[ConversationContext]:
        """
        会話コンテキストを取得
        
        Args:
            context_id: コンテキストID
            
        Returns:
            会話コンテキスト、存在しない場合はNone
        """
        return self.conversation_manager.get_context(context_id)
    
    def start(self) -> bool:
        """
        コントローラを起動
        
        Returns:
            起動が成功したかどうか
        """
        if self.state != AgentControllerState.INITIALIZING:
            logger.warning(f"不正な状態からの起動: {self.state}")
            return False
        
        try:
            # 各コンポーネントの初期化チェック
            if not self.message_client:
                raise ValueError("MessageClientが設定されていません")
            
            # 状態を更新
            self.state = AgentControllerState.READY
            logger.info("エージェントコントローラを起動しました")
            return True
            
        except Exception as e:
            self.state = AgentControllerState.ERROR
            self.last_error = {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "state": self.state.value
            }
            logger.error(f"起動中にエラーが発生: {e}")
            return False
    
    def stop(self) -> bool:
        """
        コントローラを停止
        
        Returns:
            停止が成功したかどうか
        """
        if self.state == AgentControllerState.TERMINATED:
            logger.warning("コントローラは既に終了しています")
            return False
        
        try:
            # アクティブなタスクの確認
            if self.active_tasks:
                logger.warning(f"アクティブなタスクが存在します: {len(self.active_tasks)}件")
                return False
            
            # 状態を更新
            self.state = AgentControllerState.TERMINATED
            logger.info("エージェントコントローラを停止しました")
            return True
            
        except Exception as e:
            self.state = AgentControllerState.ERROR
            self.last_error = {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "state": self.state.value
            }
            logger.error(f"停止中にエラーが発生: {e}")
            return False 
    
    def create_task(
        self,
        task_type: str,
        description: str,
        required_roles: List[AgentRole],
        workflow_id: Optional[str] = None,
        context_id: Optional[str] = None,
        priority: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        新しいタスクを作成
        
        Args:
            task_type: タスクの種類
            description: タスクの説明
            required_roles: 必要なエージェントの役割リスト
            workflow_id: 関連するワークフローID
            context_id: 関連するコンテキストID
            priority: タスクの優先度（1-5、5が最高）
            metadata: タスクに関する追加情報
            
        Returns:
            作成されたタスクのID
        """
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        
        # タスク情報を作成
        task_info = {
            "id": task_id,
            "type": task_type,
            "description": description,
            "required_roles": [role.value for role in required_roles],
            "workflow_id": workflow_id,
            "context_id": context_id,
            "priority": priority,
            "status": "created",
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "assigned_agents": []
        }
        
        # タスクを登録
        self.active_tasks[task_id] = task_info
        self.task_assignments[task_id] = set()
        
        logger.info(f"新しいタスクを作成: {task_id} (種類: {task_type})")
        return task_id
    
    def assign_task(
        self,
        task_id: str,
        agent_ids: Union[str, List[str]],
        force: bool = False
    ) -> bool:
        """
        タスクをエージェントに割り当て
        
        Args:
            task_id: タスクID
            agent_ids: 割り当てるエージェントのIDまたはIDリスト
            force: 役割チェックを無視して強制的に割り当てるかどうか
            
        Returns:
            割り当てが成功したかどうか
        """
        if task_id not in self.active_tasks:
            logger.warning(f"タスクが見つかりません: {task_id}")
            return False
        
        if isinstance(agent_ids, str):
            agent_ids = [agent_ids]
        
        task_info = self.active_tasks[task_id]
        required_roles = [AgentRole(role) for role in task_info["required_roles"]]
        
        # エージェントの役割チェック
        if not force:
            for agent_id in agent_ids:
                if agent_id not in self.agent_roles:
                    logger.warning(f"エージェントが登録されていません: {agent_id}")
                    return False
                
                agent_role = self.agent_roles[agent_id]
                if agent_role not in required_roles:
                    logger.warning(
                        f"エージェントの役割が不適切です: {agent_id} "
                        f"(必要: {[r.value for r in required_roles]}, 実際: {agent_role.value})"
                    )
                    return False
        
        # タスクを割り当て
        for agent_id in agent_ids:
            self.task_assignments[task_id].add(agent_id)
            task_info["assigned_agents"].append({
                "agent_id": agent_id,
                "assigned_at": datetime.now().isoformat(),
                "status": "assigned"
            })
        
        # タスク状態を更新
        task_info["status"] = "assigned"
        task_info["updated_at"] = datetime.now().isoformat()
        
        logger.info(f"タスクを割り当て: {task_id} -> {agent_ids}")
        return True
    
    def start_task(self, task_id: str) -> bool:
        """
        タスクを開始
        
        Args:
            task_id: タスクID
            
        Returns:
            開始が成功したかどうか
        """
        if task_id not in self.active_tasks:
            logger.warning(f"タスクが見つかりません: {task_id}")
            return False
        
        task_info = self.active_tasks[task_id]
        
        if task_info["status"] != "assigned":
            logger.warning(f"タスクは割り当て済みではありません: {task_id}")
            return False
        
        # タスク状態を更新
        task_info["status"] = "in_progress"
        task_info["started_at"] = datetime.now().isoformat()
        task_info["updated_at"] = datetime.now().isoformat()
        
        # 会話コンテキストを作成（存在しない場合）
        if not task_info.get("context_id"):
            context = self.create_conversation(
                topic=f"Task: {task_info['type']} - {task_info['description'][:50]}",
                workflow_id=task_info.get("workflow_id")
            )
            task_info["context_id"] = context.context_id
        
        # 各エージェントに開始通知を送信
        for agent_id in self.task_assignments[task_id]:
            coordinator = self.get_agent_coordinator(agent_id)
            if coordinator:
                coordinator.coordinate(
                    to_agent_id=agent_id,
                    message_type=MessageType.WORKFLOW_START,
                    content={
                        "task_id": task_id,
                        "task_type": task_info["type"],
                        "description": task_info["description"],
                        "context_id": task_info["context_id"]
                    },
                    workflow_id=task_info.get("workflow_id"),
                    context_id=task_info["context_id"]
                )
        
        logger.info(f"タスクを開始: {task_id}")
        return True
    
    def complete_task(
        self,
        task_id: str,
        result: Dict[str, Any],
        agent_id: Optional[str] = None
    ) -> bool:
        """
        タスクを完了
        
        Args:
            task_id: タスクID
            result: タスクの結果
            agent_id: 完了を報告するエージェントID（省略時は全エージェントから完了）
            
        Returns:
            完了処理が成功したかどうか
        """
        if task_id not in self.active_tasks:
            logger.warning(f"タスクが見つかりません: {task_id}")
            return False
        
        task_info = self.active_tasks[task_id]
        
        if task_info["status"] != "in_progress":
            logger.warning(f"タスクは進行中ではありません: {task_id}")
            return False
        
        # 特定のエージェントからの完了報告の場合
        if agent_id:
            if agent_id not in self.task_assignments[task_id]:
                logger.warning(f"エージェントはこのタスクに割り当てられていません: {agent_id}")
                return False
            
            # エージェントの状態を更新
            for agent_info in task_info["assigned_agents"]:
                if agent_info["agent_id"] == agent_id:
                    agent_info["status"] = "completed"
                    agent_info["completed_at"] = datetime.now().isoformat()
                    break
            
            # 全エージェントが完了しているか確認
            all_completed = all(
                agent_info["status"] == "completed"
                for agent_info in task_info["assigned_agents"]
            )
            
            if not all_completed:
                logger.info(f"エージェントがタスクを完了: {agent_id} (タスク: {task_id})")
                return True
        
        # タスクを完了状態に更新
        task_info["status"] = "completed"
        task_info["result"] = result
        task_info["completed_at"] = datetime.now().isoformat()
        task_info["updated_at"] = datetime.now().isoformat()
        
        # 会話コンテキストを完了状態に更新
        if task_info.get("context_id"):
            context = self.get_conversation(task_info["context_id"])
            if context:
                self.conversation_manager.mark_context_completed(task_info["context_id"])
        
        # 各エージェントに完了通知を送信
        for assigned_agent_id in self.task_assignments[task_id]:
            coordinator = self.get_agent_coordinator(assigned_agent_id)
            if coordinator:
                coordinator.coordinate(
                    to_agent_id=assigned_agent_id,
                    message_type=MessageType.WORKFLOW_COMPLETE,
                    content={
                        "task_id": task_id,
                        "result": result
                    },
                    workflow_id=task_info.get("workflow_id"),
                    context_id=task_info.get("context_id")
                )
        
        logger.info(f"タスクを完了: {task_id}")
        return True
    
    def handle_task_error(
        self,
        task_id: str,
        error: Dict[str, Any],
        agent_id: str,
        should_retry: bool = True
    ) -> bool:
        """
        タスクのエラーを処理
        
        Args:
            task_id: タスクID
            error: エラー情報
            agent_id: エラーを報告したエージェントID
            should_retry: 再試行するかどうか
            
        Returns:
            エラー処理が成功したかどうか
        """
        if task_id not in self.active_tasks:
            logger.warning(f"タスクが見つかりません: {task_id}")
            return False
        
        task_info = self.active_tasks[task_id]
        
        # エラー情報を記録
        error_info = {
            "error": error,
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat()
        }
        
        if "errors" not in task_info:
            task_info["errors"] = []
        task_info["errors"].append(error_info)
        
        # エージェントの状態を更新
        for agent_info in task_info["assigned_agents"]:
            if agent_info["agent_id"] == agent_id:
                agent_info["status"] = "error"
                agent_info["error"] = error
                break
        
        # タスク状態を更新
        task_info["status"] = "error"
        task_info["updated_at"] = datetime.now().isoformat()
        
        # 他のエージェントに通知
        for assigned_agent_id in self.task_assignments[task_id]:
            if assigned_agent_id != agent_id:
                coordinator = self.get_agent_coordinator(assigned_agent_id)
                if coordinator:
                    coordinator.coordinate(
                        to_agent_id=assigned_agent_id,
                        message_type=MessageType.ERROR,
                        content={
                            "task_id": task_id,
                            "error": error,
                            "from_agent": agent_id
                        },
                        workflow_id=task_info.get("workflow_id"),
                        context_id=task_info.get("context_id"),
                        priority=MessagePriority.HIGH
                    )
        
        # 自動復旧を試みる
        if should_retry:
            recovery_result = self._attempt_task_recovery(task_id, error)
            if recovery_result:
                logger.info(f"タスクの自動復旧に成功: {task_id}")
                return True
        
        logger.error(f"タスクでエラーが発生: {task_id}, エージェント: {agent_id}")
        return False
    
    def _attempt_task_recovery(self, task_id: str, error: Dict[str, Any]) -> bool:
        """
        タスクの自動復旧を試みる
        
        Args:
            task_id: タスクID
            error: エラー情報
            
        Returns:
            復旧が成功したかどうか
        """
        task_info = self.active_tasks[task_id]
        
        # 復旧戦略を決定（実際の実装ではより洗練された戦略を使用）
        if task_info.get("retry_count", 0) >= 3:
            logger.warning(f"最大再試行回数を超過: {task_id}")
            return False
        
        # 再試行カウントを更新
        task_info["retry_count"] = task_info.get("retry_count", 0) + 1
        
        # タスク状態をリセット
        task_info["status"] = "assigned"
        task_info["updated_at"] = datetime.now().isoformat()
        
        # エージェントの状態をリセット
        for agent_info in task_info["assigned_agents"]:
            agent_info["status"] = "assigned"
            if "error" in agent_info:
                del agent_info["error"]
        
        # タスクを再開
        return self.start_task(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        タスクの状態を取得
        
        Args:
            task_id: タスクID
            
        Returns:
            タスク情報、存在しない場合はNone
        """
        return self.active_tasks.get(task_id)
    
    def get_agent_tasks(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        エージェントに割り当てられているタスクを取得
        
        Args:
            agent_id: エージェントID
            
        Returns:
            タスク情報のリスト
        """
        return [
            task_info for task_id, task_info in self.active_tasks.items()
            if agent_id in self.task_assignments.get(task_id, set())
        ]
    
    def coordinate_agents(
        self,
        task_id: str,
        coordination_type: str,
        content: Dict[str, Any],
        from_agent_id: Optional[str] = None,
        to_agent_ids: Optional[List[str]] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> bool:
        """
        エージェント間の連携を調整
        
        Args:
            task_id: タスクID
            coordination_type: 連携の種類
            content: 連携内容
            from_agent_id: 送信元エージェントID
            to_agent_ids: 送信先エージェントIDリスト（Noneの場合は全エージェント）
            priority: メッセージの優先度
            
        Returns:
            調整が成功したかどうか
        """
        if task_id not in self.active_tasks:
            logger.warning(f"タスクが見つかりません: {task_id}")
            return False
        
        task_info = self.active_tasks[task_id]
        
        # 送信先エージェントの決定
        if to_agent_ids is None:
            to_agent_ids = list(self.task_assignments[task_id])
            if from_agent_id:
                to_agent_ids.remove(from_agent_id)
        
        # 連携内容にメタデータを追加
        coordination_content = {
            **content,
            "coordination_type": coordination_type,
            "task_id": task_id,
            "timestamp": datetime.now().isoformat()
        }
        
        if from_agent_id:
            coordination_content["from_agent"] = from_agent_id
        
        # 各エージェントに連携メッセージを送信
        success = True
        for to_agent_id in to_agent_ids:
            coordinator = self.get_agent_coordinator(to_agent_id)
            if coordinator:
                try:
                    coordinator.coordinate(
                        to_agent_id=to_agent_id,
                        message_type=MessageType.COORDINATION,
                        content=coordination_content,
                        workflow_id=task_info.get("workflow_id"),
                        context_id=task_info.get("context_id"),
                        priority=priority,
                        protocol=CoordinationProtocol.TARGETED
                    )
                except Exception as e:
                    logger.error(f"エージェント連携中にエラーが発生: {e}")
                    success = False
        
        return success
    
    def broadcast_message(
        self,
        message_type: MessageType,
        content: Dict[str, Any],
        from_agent_id: Optional[str] = None,
        exclude_agents: Optional[List[str]] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> bool:
        """
        全エージェントにメッセージをブロードキャスト
        
        Args:
            message_type: メッセージタイプ
            content: メッセージ内容
            from_agent_id: 送信元エージェントID
            exclude_agents: 除外するエージェントIDリスト
            priority: メッセージの優先度
            
        Returns:
            送信が成功したかどうか
        """
        if exclude_agents is None:
            exclude_agents = []
        
        if from_agent_id:
            exclude_agents.append(from_agent_id)
        
        # 送信先エージェントの決定
        target_agents = [
            agent_id for agent_id in self.registered_agents.keys()
            if agent_id not in exclude_agents
        ]
        
        # メッセージ内容にメタデータを追加
        broadcast_content = {
            **content,
            "broadcast": True,
            "timestamp": datetime.now().isoformat()
        }
        
        if from_agent_id:
            broadcast_content["from_agent"] = from_agent_id
        
        # 各エージェントにメッセージを送信
        success = True
        for agent_id in target_agents:
            coordinator = self.get_agent_coordinator(agent_id)
            if coordinator:
                try:
                    coordinator.coordinate(
                        to_agent_id=agent_id,
                        message_type=message_type,
                        content=broadcast_content,
                        priority=priority,
                        protocol=CoordinationProtocol.BROADCAST
                    )
                except Exception as e:
                    logger.error(f"ブロードキャスト中にエラーが発生: {e}")
                    success = False
        
        return success
    
    def request_agent_assistance(
        self,
        task_id: str,
        from_agent_id: str,
        required_role: AgentRole,
        assistance_type: str,
        details: Dict[str, Any],
        priority: MessagePriority = MessagePriority.HIGH
    ) -> Optional[str]:
        """
        他のエージェントに支援を要請
        
        Args:
            task_id: タスクID
            from_agent_id: 要請元エージェントID
            required_role: 必要なエージェントの役割
            assistance_type: 支援の種類
            details: 支援の詳細
            priority: 要請の優先度
            
        Returns:
            支援を引き受けたエージェントのID、または失敗時はNone
        """
        if task_id not in self.active_tasks:
            logger.warning(f"タスクが見つかりません: {task_id}")
            return None
        
        task_info = self.active_tasks[task_id]
        
        # 適切なエージェントを探す
        potential_helpers = [
            agent_id for agent_id, role in self.agent_roles.items()
            if role == required_role and agent_id != from_agent_id
        ]
        
        if not potential_helpers:
            logger.warning(f"適切な役割のエージェントが見つかりません: {required_role.value}")
            return None
        
        # 支援要請の内容を作成
        assistance_request = {
            "task_id": task_id,
            "from_agent": from_agent_id,
            "assistance_type": assistance_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        # 各候補エージェントに要請を送信
        for helper_id in potential_helpers:
            coordinator = self.get_agent_coordinator(helper_id)
            if coordinator:
                try:
                    # 支援要請を送信
                    coordinator.coordinate(
                        to_agent_id=helper_id,
                        message_type=MessageType.ASSISTANCE_REQUEST,
                        content=assistance_request,
                        workflow_id=task_info.get("workflow_id"),
                        context_id=task_info.get("context_id"),
                        priority=priority,
                        protocol=CoordinationProtocol.TARGETED
                    )
                    
                    # タスクにエージェントを追加
                    self.assign_task(task_id, helper_id, force=True)
                    
                    logger.info(f"支援要請を送信: {from_agent_id} -> {helper_id}")
                    return helper_id
                    
                except Exception as e:
                    logger.error(f"支援要請中にエラーが発生: {e}")
                    continue
        
        return None
    
    def share_knowledge(
        self,
        from_agent_id: str,
        knowledge_type: str,
        knowledge: Dict[str, Any],
        target_roles: Optional[List[AgentRole]] = None,
        context_id: Optional[str] = None
    ) -> bool:
        """
        エージェント間で知識を共有
        
        Args:
            from_agent_id: 共有元エージェントID
            knowledge_type: 知識の種類
            knowledge: 共有する知識
            target_roles: 共有先エージェントの役割リスト（Noneの場合は全エージェント）
            context_id: 関連するコンテキストID
            
        Returns:
            共有が成功したかどうか
        """
        # 共有先エージェントの決定
        if target_roles:
            target_agents = [
                agent_id for agent_id, role in self.agent_roles.items()
                if role in target_roles and agent_id != from_agent_id
            ]
        else:
            target_agents = [
                agent_id for agent_id in self.registered_agents.keys()
                if agent_id != from_agent_id
            ]
        
        if not target_agents:
            logger.warning("共有先のエージェントが見つかりません")
            return False
        
        # 知識共有の内容を作成
        knowledge_content = {
            "knowledge_type": knowledge_type,
            "knowledge": knowledge,
            "from_agent": from_agent_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # 各エージェントに知識を共有
        success = True
        for agent_id in target_agents:
            coordinator = self.get_agent_coordinator(agent_id)
            if coordinator:
                try:
                    coordinator.coordinate(
                        to_agent_id=agent_id,
                        message_type=MessageType.KNOWLEDGE_SHARE,
                        content=knowledge_content,
                        context_id=context_id,
                        protocol=CoordinationProtocol.BROADCAST
                    )
                except Exception as e:
                    logger.error(f"知識共有中にエラーが発生: {e}")
                    success = False
        
        return success
    
    def synchronize_context(
        self,
        context_id: str,
        agent_ids: Optional[List[str]] = None
    ) -> bool:
        """
        エージェント間で会話コンテキストを同期
        
        Args:
            context_id: 同期するコンテキストID
            agent_ids: 同期先エージェントIDリスト（Noneの場合は全エージェント）
            
        Returns:
            同期が成功したかどうか
        """
        context = self.get_conversation(context_id)
        if not context:
            logger.warning(f"コンテキストが見つかりません: {context_id}")
            return False
        
        # 同期先エージェントの決定
        if agent_ids is None:
            agent_ids = list(self.registered_agents.keys())
        
        # コンテキストの要約を取得
        context_summary = context.get_summary()
        
        # 同期内容を作成
        sync_content = {
            "context_id": context_id,
            "summary": context_summary,
            "timestamp": datetime.now().isoformat()
        }
        
        # 各エージェントとコンテキストを同期
        success = True
        for agent_id in agent_ids:
            coordinator = self.get_agent_coordinator(agent_id)
            if coordinator:
                try:
                    coordinator.coordinate(
                        to_agent_id=agent_id,
                        message_type=MessageType.CONTEXT_SYNC,
                        content=sync_content,
                        context_id=context_id,
                        protocol=CoordinationProtocol.TARGETED
                    )
                except Exception as e:
                    logger.error(f"コンテキスト同期中にエラーが発生: {e}")
                    success = False
        
        return success 