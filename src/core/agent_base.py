"""
AIエージェントの基本クラス
"""

import uuid
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, TypeVar, Generic, Union, Set
from datetime import datetime

from loguru import logger
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field, ConfigDict

from src.core.messaging import MessageClient
from src.core.context_manager import ContextClient, SharedContext
from src.models.schema import MessageType, MessagePriority
from src.core.config import settings


T = TypeVar('T')


class AgentState(BaseModel):
    """
    エージェントの基本状態
    各エージェントはこのクラスを拡張して独自の状態を定義
    """
    agent_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: str = "idle"  # idle, busy, error
    current_task: Optional[str] = None
    procedure_id: Optional[str] = None
    procedure_text: Optional[str] = None
    procedure_understanding: Optional[Dict[str, Any]] = None
    sample_id: Optional[str] = None
    sample_analysis: Optional[Dict[str, Any]] = None
    test_plan: Optional[Dict[str, Any]] = None
    test_results: Optional[Dict[str, Any]] = None
    findings: Optional[List[Dict[str, Any]]] = None
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # コンテキスト関連のプロパティを追加
    current_context_id: Optional[str] = None
    current_workflow_id: Optional[str] = None
    child_context_ids: Set[str] = Field(default_factory=set)
    # 自律的なエージェント機能のための状態
    is_autonomous: bool = False
    last_activity_time: datetime = Field(default_factory=datetime.now)
    is_processing: bool = False
    autonomous_mode_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Pydantic v2スタイルの設定
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    def update(self, **kwargs):
        """状態の更新"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()


class AgentBase(ABC, Generic[T]):
    """
    エージェントの基本クラス
    このクラスを継承して各エージェントを実装する
    """
    
    def __init__(self, agent_id: str, state_class: type[T], message_client: Optional[MessageClient] = None, **kwargs):
        """
        Args:
            agent_id: エージェントの識別子
            state_class: 状態クラス
            message_client: メッセージクライアント（オプション）
            **kwargs: 追加の初期化パラメータ
        """
        self.agent_id = agent_id
        self.state = state_class(agent_id=agent_id, **kwargs)
        self.message_client = message_client or MessageClient(agent_id)
        self.context = ContextClient(agent_id)
        
        # 自律的なエージェント機能のための属性
        self._polling_task = None
        self._processing_loop = None
        self._shutdown_event = asyncio.Event()
        self._message_queue = asyncio.Queue()
        
        logger.info(f"Agent {agent_id} initialized")
    
    @abstractmethod
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        メッセージ処理の抽象メソッド
        各エージェントで実装する
        
        Args:
            message: 処理するメッセージ
            
        Returns:
            処理結果
        """
        pass
    
    async def get_and_process_messages(self) -> List[Dict[str, Any]]:
        """
        自分宛てのメッセージを取得して処理
        
        Returns:
            処理結果のリスト
        """
        # 優先度の高いメッセージから先に処理
        messages = self.message_client.get_priority_messages()
        results = []
        
        if messages:
            self.state.update(status="busy")
            logger.info(f"Agent {self.agent_id} processing {len(messages)} messages")
            
            for message in messages:
                try:
                    # メッセージに関連するコンテキストがあれば取得して設定
                    if message["context_id"] and message["context_id"] != self.state.current_context_id:
                        context = self.context.get_context(message["context_id"])
                        if context:
                            self.state.update(current_context_id=message["context_id"])
                            # コンテキストに含まれるワークフローIDも設定
                            self.state.update(current_workflow_id=context.workflow_id)
                    
                    # メッセージのワークフローIDを状態に反映
                    if message["workflow_id"] and message["workflow_id"] != self.state.current_workflow_id:
                        self.state.update(current_workflow_id=message["workflow_id"])
                    
                    # メッセージを処理
                    result = await self.process_message(message)
                    
                    # 応答が必要なメッセージに対して応答を送信
                    if message["requires_response"]:
                        self.send_response(
                            recipient_id=message["from_agent"],
                            in_response_to=message["id"],
                            message_type=MessageType.RESPONSE,
                            content=result
                        )
                    
                    results.append(result)
                    
                    # 最後のアクティビティ時間を更新
                    self.state.update(last_activity_time=datetime.now())
                    
                except Exception as e:
                    logger.error(f"Error processing message in agent {self.agent_id}: {e}")
                    self.state.update(status="error")
                    error_result = {
                        "error": str(e), 
                        "message_id": message["id"],
                        "status": "error"
                    }
                    results.append(error_result)
                    
                    # エラーが発生した場合も、応答が必要なメッセージには応答する
                    if message["requires_response"]:
                        self.send_response(
                            recipient_id=message["from_agent"],
                            in_response_to=message["id"],
                            message_type=MessageType.ERROR,
                            content=error_result
                        )
            
            self.state.update(status="idle")
        
        return results
    
    def send_message(
        self, recipient_id: str, message_type: str, content: Dict[str, Any],
        context_id: Optional[str] = None, workflow_id: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        requires_response: bool = False, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        他エージェントへのメッセージ送信
        
        Args:
            recipient_id: 宛先エージェントID
            message_type: メッセージタイプ
            content: メッセージ内容
            context_id: 関連するコンテキストID（指定がない場合は現在のコンテキスト）
            workflow_id: 関連するワークフローID（指定がない場合は現在のワークフロー）
            priority: メッセージの優先度
            requires_response: 応答が必要かどうか
            metadata: メタデータ
            
        Returns:
            送信したメッセージのID
        """
        # コンテキストとワークフローのデフォルト値
        if context_id is None and hasattr(self.state, "current_context_id"):
            context_id = self.state.current_context_id
            
        if workflow_id is None and hasattr(self.state, "current_workflow_id"):
            workflow_id = self.state.current_workflow_id
        
        return self.message_client.send_message(
            recipient_id=recipient_id,
            message_type=message_type,
            content=content,
            context_id=context_id,
            workflow_id=workflow_id,
            priority=priority,
            requires_response=requires_response,
            metadata=metadata
        )
    
    def send_response(
        self, recipient_id: str, in_response_to: str, message_type: str, content: Dict[str, Any],
        priority: MessagePriority = MessagePriority.HIGH,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        特定のメッセージへの応答を送信
        
        Args:
            recipient_id: 宛先エージェントID
            in_response_to: 応答先メッセージID
            message_type: メッセージタイプ
            content: メッセージ内容
            priority: メッセージの優先度
            metadata: メタデータ
            
        Returns:
            送信したメッセージのID
        """
        return self.message_client.send_response(
            recipient_id=recipient_id,
            in_response_to=in_response_to,
            message_type=message_type,
            content=content,
            context_id=self.state.current_context_id,
            workflow_id=self.state.current_workflow_id,
            priority=priority,
            metadata=metadata
        )
    
    def create_context(
        self, workflow_id: Optional[str] = None, initial_data: Optional[Dict[str, Any]] = None
    ) -> SharedContext:
        """
        新しいコンテキストを作成
        
        Args:
            workflow_id: 関連するワークフローID（指定がない場合は現在のワークフロー）
            initial_data: 初期データ
            
        Returns:
            作成されたコンテキスト
        """
        if workflow_id is None and hasattr(self.state, "current_workflow_id"):
            workflow_id = self.state.current_workflow_id
            
        if workflow_id is None:
            workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
            self.state.update(current_workflow_id=workflow_id)
        
        context = self.context.create_context(workflow_id, initial_data)
        context_id = context.context_id
        self.state.update(current_context_id=context_id)
        
        logger.info(f"Agent {self.agent_id} created context {context_id} for workflow {workflow_id}")
        return context
    
    def create_child_context(
        self, parent_context_id: Optional[str] = None, data_filter: Optional[List[str]] = None
    ) -> Optional[SharedContext]:
        """
        親コンテキストから子コンテキストを作成
        
        Args:
            parent_context_id: 親コンテキストID（指定がない場合は現在のコンテキスト）
            data_filter: 継承するデータキーのリスト
            
        Returns:
            作成された子コンテキスト、または作成に失敗した場合はNone
        """
        if parent_context_id is None and hasattr(self.state, "current_context_id"):
            parent_context_id = self.state.current_context_id
            
        if parent_context_id is None:
            logger.warning(f"Agent {self.agent_id} attempted to create child context without parent")
            return None
        
        child_context = self.context.create_child_context(parent_context_id, data_filter)
        
        if child_context:
            child_context_id = child_context.context_id
            self.state.child_context_ids.add(child_context_id)
            self.state.update(current_context_id=child_context_id)
            logger.info(
                f"Agent {self.agent_id} created child context {child_context_id} "
                f"from parent {parent_context_id}"
            )
            return child_context
        
        return None
    
    def get_context_data(self, context_id: Optional[str] = None) -> Dict[str, Any]:
        """
        コンテキストデータを取得
        
        Args:
            context_id: コンテキストID（指定がない場合は現在のコンテキスト）
            
        Returns:
            コンテキストデータ、または存在しない場合は空辞書
        """
        if context_id is None and hasattr(self.state, "current_context_id"):
            context_id = self.state.current_context_id
            
        if context_id is None:
            return {}
        
        context = self.context.get_context(context_id)
        return context.data if context else {}
    
    def update_context_data(
        self, data_updates: Dict[str, Any], context_id: Optional[str] = None,
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        コンテキストデータを更新
        
        Args:
            data_updates: 更新するデータ
            context_id: コンテキストID（指定がない場合は現在のコンテキスト）
            metadata_updates: 更新するメタデータ
            
        Returns:
            更新が成功した場合はTrue、失敗した場合はFalse
        """
        if context_id is None and hasattr(self.state, "current_context_id"):
            context_id = self.state.current_context_id
            
        if context_id is None:
            logger.warning(f"Agent {self.agent_id} attempted to update context without context_id")
            return False
        
        updated_context = self.context.update_context(
            context_id, data_updates, metadata_updates
        )
        
        return updated_context is not None
    
    def update_state(self, **kwargs):
        """
        状態の更新
        
        Args:
            **kwargs: 更新するフィールドと値
        """
        self.state.update(**kwargs)
    
    def get_state(self) -> Dict[str, Any]:
        """
        現在の状態を取得
        
        Returns:
            状態の辞書表現
        """
        return self.state.dict()
    
    def store_in_memory(self, key: str, value: Any):
        """
        メモリに値を保存
        
        Args:
            key: キー
            value: 値
        """
        if not hasattr(self.state, "memory"):
            self.state.memory = {}
        
        self.state.memory[key] = value
        self.state.updated_at = datetime.now()
    
    def retrieve_from_memory(self, key: str, default: Any = None) -> Any:
        """
        メモリから値を取得
        
        Args:
            key: キー
            default: キーが存在しない場合のデフォルト値
            
        Returns:
            メモリ内の値
        """
        if not hasattr(self.state, "memory") or key not in self.state.memory:
            return default
        
        return self.state.memory[key]
        
    # ここから自律的なエージェント機能の実装 ----------------
    
    async def start_autonomous_mode(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        自律的なエージェントモードを開始
        
        Args:
            config: 自律モードの設定（ポーリング間隔、タイムアウトなど）
            
        Returns:
            開始が成功したかどうか
        """
        if self.state.is_autonomous:
            logger.warning(f"Agent {self.agent_id} is already in autonomous mode")
            return False
            
        # デフォルト設定
        default_config = {
            "polling_interval": 1.0,  # メッセージポーリングの間隔(秒)
            "idle_timeout": 300,  # アイドル状態のタイムアウト(秒)
            "max_concurrent_tasks": 10,  # 同時に処理できるタスクの最大数
            "error_retry_count": 3,  # エラー時の再試行回数
            "error_retry_delay": 5.0,  # エラー時の再試行遅延(秒)
        }
        
        # 設定をマージ
        if config:
            default_config.update(config)
            
        self.state.update(
            is_autonomous=True,
            autonomous_mode_config=default_config,
            last_activity_time=datetime.now()
        )
        
        # シャットダウンイベントをクリア
        self._shutdown_event.clear()
        
        # メッセージポーリングタスクを開始
        if self._polling_task is None or self._polling_task.done():
            self._polling_task = asyncio.create_task(
                self._message_polling_loop(
                    polling_interval=default_config["polling_interval"]
                )
            )
            
        # メッセージ処理ループを開始
        if self._processing_loop is None or self._processing_loop.done():
            self._processing_loop = asyncio.create_task(
                self._message_processing_loop(
                    max_concurrent=default_config["max_concurrent_tasks"]
                )
            )
            
        logger.info(f"Agent {self.agent_id} started autonomous mode with config: {default_config}")
        return True
        
    async def stop_autonomous_mode(self) -> bool:
        """
        自律的なエージェントモードを停止
        
        Returns:
            停止が成功したかどうか
        """
        if not self.state.is_autonomous:
            logger.warning(f"Agent {self.agent_id} is not in autonomous mode")
            return False
            
        # シャットダウンイベントを設定
        self._shutdown_event.set()
        
        # ポーリングタスクの停止を待機
        if self._polling_task and not self._polling_task.done():
            try:
                self._polling_task.cancel()
                await asyncio.gather(self._polling_task, return_exceptions=True)
            except Exception as e:
                logger.error(f"Error stopping polling task for agent {self.agent_id}: {e}")
                
        # 処理ループの停止を待機
        if self._processing_loop and not self._processing_loop.done():
            try:
                self._processing_loop.cancel()
                await asyncio.gather(self._processing_loop, return_exceptions=True)
            except Exception as e:
                logger.error(f"Error stopping processing loop for agent {self.agent_id}: {e}")
                
        self.state.update(is_autonomous=False)
        logger.info(f"Agent {self.agent_id} stopped autonomous mode")
        return True
        
    async def _message_polling_loop(self, polling_interval: float = 1.0):
        """
        メッセージをポーリングするループ
        
        Args:
            polling_interval: ポーリング間隔(秒)
        """
        logger.info(f"Agent {self.agent_id} started message polling loop")
        
        while not self._shutdown_event.is_set():
            try:
                # メッセージをポーリング
                messages = self.message_client.get_priority_messages()
                
                if messages:
                    logger.debug(f"Agent {self.agent_id} received {len(messages)} messages")
                    
                    # メッセージをキューに追加
                    for message in messages:
                        await self._message_queue.put(message)
                    
                    # 最後のアクティビティ時間を更新
                    self.state.update(last_activity_time=datetime.now())
                    
                # 次のポーリングまで待機
                await asyncio.sleep(polling_interval)
                
            except asyncio.CancelledError:
                logger.info(f"Message polling loop for agent {self.agent_id} was cancelled")
                break
                
            except Exception as e:
                logger.error(f"Error in message polling loop for agent {self.agent_id}: {e}")
                await asyncio.sleep(polling_interval * 2)  # エラー時は間隔を長めに
        
        logger.info(f"Agent {self.agent_id} stopped message polling loop")
    
    async def _message_processing_loop(self, max_concurrent: int = 10):
        """
        メッセージを処理するループ
        
        Args:
            max_concurrent: 同時に処理できるタスクの最大数
        """
        logger.info(f"Agent {self.agent_id} started message processing loop")
        
        # 現在実行中のタスク
        active_tasks = set()
        
        try:
            while not self._shutdown_event.is_set():
                # 完了したタスクを削除
                active_tasks = {task for task in active_tasks if not task.done()}
                
                # キューがからの場合や、最大同時実行数に達している場合は待機
                if self._message_queue.empty() or len(active_tasks) >= max_concurrent:
                    await asyncio.sleep(0.1)
                    continue
                
                # メッセージを取得
                message = await self._message_queue.get()
                
                # 処理タスクを作成
                task = asyncio.create_task(self._process_message_task(message))
                active_tasks.add(task)
                
                # キューのタスク完了を通知
                self._message_queue.task_done()
        
        except asyncio.CancelledError:
            logger.info(f"Message processing loop for agent {self.agent_id} was cancelled")
            
            # 実行中のタスクをキャンセル
            for task in active_tasks:
                task.cancel()
                
            # キャンセルされたタスクを待機
            if active_tasks:
                await asyncio.gather(*active_tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"Error in message processing loop for agent {self.agent_id}: {e}")
            
        finally:
            logger.info(f"Agent {self.agent_id} stopped message processing loop")
    
    async def _process_message_task(self, message):
        """
        単一のメッセージを処理するタスク
        
        Args:
            message: 処理するメッセージ
        """
        if not isinstance(message, dict):
            logger.error(f"Agent {self.agent_id} received invalid message: {message}")
            return
            
        try:
            # 必須キーの存在を確認
            message_id = message.get('id', 'unknown')
            logger.debug(f"Agent {self.agent_id} processing message {message_id}")
            
            # メッセージに関連するコンテキストがあれば取得して設定
            context_id = message.get("context_id")
            if context_id and context_id != self.state.current_context_id:
                context = self.context.get_context(context_id)
                if context:
                    self.state.update(current_context_id=context_id)
                    self.state.update(current_workflow_id=context.workflow_id)
            
            # メッセージのワークフローIDを状態に反映
            workflow_id = message.get("workflow_id")
            if workflow_id and workflow_id != self.state.current_workflow_id:
                self.state.update(current_workflow_id=workflow_id)
            
            # メッセージを処理
            result = await self.process_message(message)
            
            # 応答が必要なメッセージに対して応答を送信
            if message.get("requires_response", False):
                from_agent = message.get("from_agent")
                if from_agent:
                    self.send_response(
                        recipient_id=from_agent,
                        in_response_to=message_id,
                        message_type=MessageType.RESPONSE,
                        content=result
                    )
                else:
                    logger.warning(f"応答が必要なメッセージですが、送信元エージェントが指定されていません: {message_id}")
                    
            # 最後のアクティビティ時間を更新
            self.state.update(last_activity_time=datetime.now())
            
            logger.debug(f"Agent {self.agent_id} completed processing message {message_id}")
            
        except Exception as e:
            message_id = message.get('id', 'unknown')
            logger.error(f"Error processing message in agent {self.agent_id}: {e}")
            
            # エラーが発生した場合も、応答が必要なメッセージには応答する
            if message.get("requires_response", False):
                from_agent = message.get("from_agent")
                if from_agent:
                    error_result = {
                        "error": str(e), 
                        "message_id": message_id,
                        "status": "error"
                    }
                    self.send_response(
                        recipient_id=from_agent,
                        in_response_to=message_id,
                        message_type=MessageType.ERROR,
                        content=error_result
                    )
    
    async def check_idle_timeout(self) -> bool:
        """
        アイドルタイムアウトをチェック
        
        Returns:
            タイムアウトした場合はTrue
        """
        if not self.state.is_autonomous:
            return False
            
        idle_timeout = self.state.autonomous_mode_config.get("idle_timeout", 300)
        
        # 最後のアクティビティからの経過時間を計算
        elapsed = (datetime.now() - self.state.last_activity_time).total_seconds()
        
        if elapsed > idle_timeout:
            logger.info(f"Agent {self.agent_id} idle timeout after {elapsed}s")
            return True
            
        return False
        
    # 自律的な判断関連のメソッド
    
    async def make_autonomous_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        自律的な判断を行う
        各エージェントはこのメソッドをオーバーライドして特定の判断ロジックを実装
        
        Args:
            context: 判断に必要なコンテキスト
            
        Returns:
            判断結果
        """
        # 自律モードのポリシーを確認
        policy = self.state.autonomous_mode_config.get("policy", {})
        
        # 判断の信頼度閾値を取得
        confidence_threshold = policy.get("confidence_threshold", 0.8)
        
        # 判断の優先度を取得
        priority_level = policy.get("priority_level", "normal")
        
        # 判断のタイムアウトを取得
        decision_timeout = policy.get("decision_timeout", 30.0)
        
        try:
            # 判断の実行（タイムアウト付き）
            async with asyncio.timeout(decision_timeout):
                decision = await self._execute_decision_logic(context)
                
                # 判断の信頼度を評価
                if decision.get("confidence", 0) >= confidence_threshold:
                    return {
                        "decision": decision.get("action", "no_action"),
                        "confidence": decision.get("confidence", 0),
                        "priority": priority_level,
                        "reasoning": decision.get("reasoning", "自動判断による決定"),
                        "status": "accepted"
                    }
                else:
                    return {
                        "decision": "human_review",
                        "confidence": decision.get("confidence", 0),
                        "priority": "high",
                        "reasoning": "信頼度が閾値を下回ったため人間の確認が必要",
                        "status": "pending"
                    }
                    
        except asyncio.TimeoutError:
            return {
                "decision": "timeout",
                "confidence": 0,
                "priority": "high",
                "reasoning": "判断がタイムアウトしました",
                "status": "error"
            }
        except Exception as e:
            logger.error(f"自律的な判断中にエラーが発生: {e}")
            return {
                "decision": "error",
                "confidence": 0,
                "priority": "high",
                "reasoning": f"エラーが発生: {str(e)}",
                "status": "error"
            }
            
    async def _execute_decision_logic(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        実際の判断ロジックを実行
        サブクラスでオーバーライドして具体的な判断ロジックを実装
        
        Args:
            context: 判断コンテキスト
            
        Returns:
            判断結果
        """
        # デフォルトの実装
        return {
            "action": "no_action",
            "confidence": 0.5,
            "reasoning": "デフォルトの判断ロジック"
        } 