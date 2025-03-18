"""
ワークフロー管理サービスモジュール（改善版）

このモジュールは、エージェント間のワークフロー管理と実行のための統合サービスを提供します。
異なるタイプのワークフロー作成と実行を一元化し、ワークフロー関連機能の重複を解消します。

改善点: 
- 単一責任の原則の適用
- 依存性逆転の原則の適用
- 統一されたデータモデルの使用
"""

import uuid
import time
import asyncio
import threading
from typing import Dict, List, Any, Optional, Tuple, Callable, Union, Protocol, TypeVar
from datetime import datetime
from loguru import logger

# エージェント管理サービスを使用
from src.core.agent_management_service import get_agent_management_service
from src.core.config import settings
from src.models.schema import MessageType
# 共有されたクライアントのみインポート
from src.core.conversation_context import ContextClient
# リポジトリへの直接依存を避ける
from src.repositories.workflow_repository import WorkflowRepository

# 型定義
T = TypeVar('T')

# ワークフローの状態を表す基本クラス
class WorkflowState:
    """
    ワークフロー状態の基本クラス
    
    すべてのワークフロー状態オブジェクトが共通して持つプロパティを定義します。
    """
    workflow_id: str
    context_id: Optional[str] = None
    current_agent_id: Optional[str] = None
    status: str = "in_progress"  # in_progress, completed, failed, paused
    next_agent_ids: List[str] = []
    previous_agent_id: Optional[str] = None
    start_time: datetime = datetime.now()
    end_time: Optional[datetime] = None
    is_human_intervention_required: bool = False
    human_query: Optional[Dict[str, Any]] = None
    human_response: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}
    messages: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    results: Dict[str, Any] = {}


# グラフビルダープロトコル
class GraphBuilder(Protocol):
    """ワークフローグラフを構築するためのプロトコル"""
    
    def add_node(self, name: str, function: Callable) -> None:
        """ノードを追加する"""
        ...
    
    def add_edge(self, start: str, end: str) -> None:
        """エッジを追加する"""
        ...
    
    def add_conditional_edge(self, start: str, condition: Callable, destinations: Dict[str, str]) -> None:
        """条件付きエッジを追加する"""
        ...
    
    def set_entry_point(self, node_name: str) -> None:
        """エントリーポイントを設定する"""
        ...
    
    def compile(self) -> Any:
        """グラフをコンパイルする"""
        ...


class WorkflowService:
    """
    ワークフロー管理サービス（改善版）
    
    このサービスクラスは以下の役割を持ちます：
    1. 各種ワークフローグラフの作成を一元化
    2. ワークフロー実行機能の提供
    3. ワークフロー状態の管理
    
    改善点:
    - 機能重複の解消
    - 単一責任の原則の適用
    - 依存性逆転の原則の適用
    - 統一されたデータモデルの使用
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """シングルトンパターンの実装"""
        if cls._instance is None:
            cls._instance = super(WorkflowService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """サービスの初期化（シングルトンなので1回だけ実行）"""
        if self._initialized:
            return
            
        self._initialized = True
        
        # 内部コンポーネントの初期化
        # エージェント管理サービスの使用
        self.agent_service = get_agent_management_service()
        self.context_client = ContextClient("workflow_service")
        self.workflow_repository = WorkflowRepository()
        
        # アクティブなワークフローの追跡
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
    
    def create_workflow_graph(
        self,
        workflow_type: str = "agent",
        config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        ワークフロータイプに基づいたワークフローグラフを作成する
        
        Args:
            workflow_type: ワークフロータイプ（"agent"または"audit"）
            config: ワークフロー設定（オプション）
            
        Returns:
            ワークフローグラフオブジェクト
            
        Raises:
            ValueError: サポートされていないワークフロータイプ
        """
        config = config or {}
        
        try:
            # ワークフロータイプに基づいたファクトリーメソッド
            if workflow_type == "agent":
                return self._create_agent_workflow_graph(config)
            elif workflow_type == "audit":
                return self._create_audit_workflow_graph(config)
            else:
                raise ValueError(f"サポートされていないワークフロータイプ: {workflow_type}")
        
        except Exception as e:
            logger.error(f"ワークフローグラフの作成中にエラーが発生: {e}")
            raise
    
    def _create_agent_workflow_graph(self, config: Dict[str, Any]) -> Any:
        """
        エージェントワークフローグラフを作成する
        
        Args:
            config: ワークフロー設定
            
        Returns:
            エージェントワークフローグラフ
        """
        try:
            # ConfigからGraphBuilderをインポート
            # 依存性を最小限に抑えるため、ここでインポート
            from src.utils.graph import GraphBuilder
            
            # グラフビルダーの初期化
            builder = GraphBuilder()
            
            # 基本エージェントをノードとして追加
            builder.add_node("agent_a", self._create_agent_node(settings.AGENT_A_ID))
            builder.add_node("agent_b", self._create_agent_node(settings.AGENT_B_ID))
            
            # 人間介入ノードを追加
            builder.add_node("human_intervention", self._create_human_intervention_node())
            
            # エンドノード（終了処理）を追加
            builder.add_node("end", self._create_end_node())
            
            # エラー処理ノード
            builder.add_node("error_handling", self._create_error_handling_node())
            
            # 基本エッジ（エージェントA -> エージェントB）
            builder.add_edge("agent_a", "agent_b")
            
            # エージェントB -> エンド
            builder.add_edge("agent_b", "end")
            
            # 人間の介入が必要な場合の条件付きエッジ
            builder.add_conditional_edge(
                "agent_a",
                self._human_response_condition,
                {
                    "needs_human": "human_intervention",
                    "default": "agent_b"
                }
            )
            
            # 人間介入 -> エージェントA（結果を戻す）
            builder.add_edge("human_intervention", "agent_a")
            
            # エラー処理
            builder.add_edge("error_handling", "agent_a")
            
            # エントリーポイントの設定
            builder.set_entry_point("agent_a")
            
            # グラフをコンパイル
            workflow_graph = builder.compile()
            
            logger.info("エージェントワークフローグラフの作成完了")
            return workflow_graph
        
        except Exception as e:
            logger.error(f"ワークフローグラフの作成中にエラーが発生: {e}")
            raise
    
    def _create_audit_workflow_graph(self, config: Dict[str, Any]) -> Any:
        """
        監査ワークフローグラフを作成する
        
        Args:
            config: ワークフロー設定
            
        Returns:
            監査ワークフローグラフ
        """
        from src.utils.graph import GraphBuilder
        
        # グラフビルダーの初期化
        builder = GraphBuilder()
        
        # 監査固有のノードとエッジを追加
        # ここでは実装を省略（実際の監査ワークフローに応じて実装）
        
        return builder.compile()
    
    def _create_agent_node(self, agent_id: str) -> Callable:
        """
        エージェントノード処理関数を作成する
        
        Args:
            agent_id: エージェントID
            
        Returns:
            ノード処理関数
        """
        
        def agent_node(state: WorkflowState, config: Dict[str, Any]) -> WorkflowState:
            # エージェントノードの実行
            state.current_agent_id = agent_id
            
            # エージェント情報を取得
            agent_info = self.agent_service.get_agent_status(agent_id)
            
            # 前のエージェントからのメッセージがあれば処理
            if state.messages and len(state.messages) > 0:
                latest_message = state.messages[-1]
                # メッセージをエージェントに送信
                # （実際の実装はここでは省略）
            
            # 結果の格納
            result_key = f"agent_{agent_id}_result"
            state.results[result_key] = {
                "timestamp": datetime.now().isoformat(),
                "status": "completed"
            }
            
            return state
        
        return agent_node
    
    def _create_human_intervention_node(self) -> Callable:
        """
        人間介入ノード処理関数を作成する
        
        Returns:
            ノード処理関数
        """
        
        def human_intervention_node(state: WorkflowState, config: Dict[str, Any]) -> WorkflowState:
            # 人間への問い合わせが必要なことをマーク
            state.is_human_intervention_required = True
            
            # 既に回答があれば、フラグをリセット
            if state.human_response:
                state.is_human_intervention_required = False
            
            return state
        
        return human_intervention_node
    
    def _create_error_handling_node(self) -> Callable:
        """
        エラー処理ノード関数を作成する
        
        Returns:
            ノード処理関数
        """
        
        def error_handling_node(state: WorkflowState, config: Dict[str, Any]) -> WorkflowState:
            # エラー処理ロジック
            if state.errors and len(state.errors) > 0:
                # エラーを処理し、可能であれば修正
                # （実際の実装はここでは省略）
                pass
            
            # 処理結果を記録
            state.results["error_handling"] = {
                "timestamp": datetime.now().isoformat(),
                "errors_processed": len(state.errors)
            }
            
            return state
        
        return error_handling_node
    
    def _create_end_node(self) -> Callable:
        """
        終了ノード処理関数を作成する
        
        Returns:
            ノード処理関数
        """
        
        def end_node(state: WorkflowState, config: Dict[str, Any]) -> WorkflowState:
            # ワークフロー終了処理
            state.status = "completed"
            state.end_time = datetime.now()
            
            # 結果の集約
            state.results["workflow_summary"] = {
                "start_time": state.start_time.isoformat(),
                "end_time": state.end_time.isoformat(),
                "duration_seconds": (state.end_time - state.start_time).total_seconds()
            }
            
            return state
        
        return end_node
    
    def _human_response_condition(self, state: WorkflowState) -> str:
        """
        人間の回答が必要かどうかを判断する条件関数
        
        Args:
            state: ワークフロー状態
            
        Returns:
            "needs_human"または"default"
        """
        # ここで人間の介入が必要かどうかのロジックを実装
        # 例: 特定の条件に基づいて判断
        return "needs_human" if state.is_human_intervention_required else "default"
    
    async def run_workflow(
        self,
        workflow_id: str,
        workflow_type: str = "agent",
        initial_data: Optional[Dict[str, Any]] = None,
        initial_agent_id: str = settings.AGENT_A_ID,
        config: Optional[Dict[str, Any]] = None,
        human_interaction_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        ワークフローを実行する
        
        Args:
            workflow_id: ワークフローID
            workflow_type: ワークフロータイプ
            initial_data: 初期データ
            initial_agent_id: 開始エージェントID
            config: 実行設定
            human_interaction_callback: 人間の介入が必要な場合のコールバック関数
            
        Returns:
            ワークフロー実行結果
        """
        try:
            # 実行設定の準備
            execution_config = config or {}
            initial_data = initial_data or {}
            
            # ワークフローグラフの生成
            workflow_graph = self.create_workflow_graph(workflow_type, execution_config)
            
            # 初期ワークフロー状態の作成
            initial_state = WorkflowState()
            initial_state.workflow_id = workflow_id
            initial_state.context_id = f"workflow_{workflow_id}"
            initial_state.current_agent_id = initial_agent_id
            initial_state.start_time = datetime.now()
            
            # 初期データを適用
            for key, value in initial_data.items():
                if hasattr(initial_state, key):
                    setattr(initial_state, key, value)
            
            # ワークフローの実行状態を追跡
            self.active_workflows[workflow_id] = {
                "id": workflow_id,
                "type": workflow_type,
                "status": "started",
                "start_time": initial_state.start_time.isoformat(),
                "current_agent": initial_agent_id,
            }
            
            # 人間の介入が必要な場合の処理
            if human_interaction_callback:
                async def _handle_human_interaction(state: WorkflowState) -> WorkflowState:
                    if state.is_human_intervention_required and state.human_query:
                        try:
                            human_response = await human_interaction_callback(state.human_query)
                            state.human_response = human_response
                        except Exception as e:
                            logger.error(f"人間の介入コールバックでエラーが発生: {e}")
                            state.errors.append({
                                "source": "human_interaction",
                                "timestamp": datetime.now().isoformat(),
                                "error": str(e),
                            })
                    return state
            
                # 人間の介入ハンドラを登録
                execution_config["callbacks"] = [_handle_human_interaction]
            
            # ステータス更新
            await self.workflow_repository.update_workflow_status(
                workflow_id, 
                {
                    "status": "running",
                    "started_at": datetime.now().isoformat()
                }
            )
            
            # ワークフローエンジンの実行
            # （実際のワークフロー実行ロジックはここに実装）
            # 例: final_state = await workflow_engine.execute(workflow_graph, initial_state, execution_config)
            
            # 簡易的な実装（実際にはワークフローエンジンを使用）
            final_state = initial_state
            final_state.status = "completed"
            final_state.end_time = datetime.now()
            
            # 実行結果を保存
            result = {
                "workflow_id": workflow_id,
                "status": final_state.status,
                "start_time": final_state.start_time.isoformat(),
                "end_time": final_state.end_time.isoformat() if final_state.end_time else None,
                "results": final_state.results
            }
            
            # 実行状態を更新
            self.active_workflows[workflow_id]["status"] = final_state.status
            self.active_workflows[workflow_id]["end_time"] = final_state.end_time.isoformat() if final_state.end_time else None
            
            # 結果をデータベースに保存
            await self.workflow_repository.update_workflow_state(workflow_id, final_state.__dict__)
            
            return result
            
        except Exception as e:
            logger.error(f"ワークフローの実行中にエラーが発生: {e}")
            
            # エラー状態を記録
            self.active_workflows[workflow_id]["status"] = "failed"
            self.active_workflows[workflow_id]["error"] = str(e)
            
            # エラー情報をデータベースに保存
            await self.workflow_repository.update_workflow_status(
                workflow_id,
                {
                    "status": "failed",
                    "error": str(e),
                    "ended_at": datetime.now().isoformat()
                }
            )
            
            # エラー情報を返す
            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": str(e)
            }
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        ワークフローの状態を取得する
        
        Args:
            workflow_id: ワークフローID
            
        Returns:
            ワークフローの状態情報、存在しない場合はNone
        """
        # アクティブワークフローから状態を取得
        if workflow_id in self.active_workflows:
            return self.active_workflows[workflow_id]
        
        # データベースからワークフロー状態を取得
        try:
            # リポジトリから状態を取得
            workflow_state = asyncio.run(self.workflow_repository.get_workflow_state(workflow_id))
            
            if workflow_state:
                return {
                    "id": workflow_id,
                    "status": workflow_state.get("status", "unknown"),
                    "start_time": workflow_state.get("start_time") or workflow_state.get("created_at"),
                    "end_time": workflow_state.get("end_time"),
                    "type": workflow_state.get("type", "unknown"),
                    "is_archived": True
                }
        except Exception as e:
            logger.error(f"ワークフロー状態の取得中にエラーが発生: {e}")
        
            return None
    
    def get_all_workflows(
        self,
        status: Optional[str] = None,
        workflow_type: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        すべてのワークフローを取得する
        
        Args:
            status: 状態でフィルタリング
            workflow_type: タイプでフィルタリング
            limit: 結果の最大数
            offset: 結果のオフセット
            
        Returns:
            ワークフローのリスト
        """
        try:
            # アクティブなワークフローを取得
            active_workflows = list(self.active_workflows.values())
            
            # フィルタリング
            if status:
                active_workflows = [w for w in active_workflows if w.get("status") == status]
            
            if workflow_type:
                active_workflows = [w for w in active_workflows if w.get("type") == workflow_type]
            
            # データベースからアーカイブされたワークフローを取得
            archived_workflows = asyncio.run(
                self.workflow_repository.get_workflows(
                    status=status,
                    workflow_type=workflow_type,
                    limit=limit,
                    offset=offset
                )
            )
            
            # アーカイブフラグを追加
            for workflow in archived_workflows:
                workflow["is_archived"] = True
            
            # アクティブなものに優先度を持たせるため、先にリストに追加
            combined_workflows = active_workflows + archived_workflows
            
            # 結果の制限を適用
            return combined_workflows[offset:offset+limit]
            
        except Exception as e:
            logger.error(f"ワークフローの取得中にエラーが発生: {e}")
            return []
    
    def pause_workflow(self, workflow_id: str, reason: str = "manually_paused") -> bool:
        """
        ワークフローを一時停止する
        
        Args:
            workflow_id: ワークフローID
            reason: 一時停止の理由
            
        Returns:
            一時停止に成功したかどうか
        """
        try:
            # アクティブなワークフローかどうかを確認
            if workflow_id not in self.active_workflows:
                logger.warning(f"一時停止できるアクティブなワークフローが見つかりません: {workflow_id}")
                return False
            
            # ワークフローの状態を確認
            if self.active_workflows[workflow_id]["status"] != "running":
                logger.warning(f"実行中でないワークフローは一時停止できません: {workflow_id}")
                return False
            
            # ワークフローを一時停止
            self.active_workflows[workflow_id]["status"] = "paused"
            self.active_workflows[workflow_id]["paused_at"] = datetime.now().isoformat()
            self.active_workflows[workflow_id]["pause_reason"] = reason
            
            # データベースにも状態を保存
            asyncio.run(
                self.workflow_repository.update_workflow_status(
                    workflow_id,
                    {
                        "status": "paused",
                        "paused_at": datetime.now().isoformat(),
                        "pause_reason": reason
                    }
                )
            )
            
            return True
            
        except Exception as e:
            logger.error(f"ワークフロー一時停止中にエラーが発生: {e}")
            return False
    
    def resume_workflow(self, workflow_id: str) -> bool:
        """
        一時停止されたワークフローを再開する
        
        Args:
            workflow_id: ワークフローID
            
        Returns:
            再開に成功したかどうか
        """
        try:
            # アクティブなワークフローかどうかを確認
            if workflow_id not in self.active_workflows:
                logger.warning(f"再開できるアクティブなワークフローが見つかりません: {workflow_id}")
                return False
            
            # ワークフローの状態を確認
            if self.active_workflows[workflow_id]["status"] != "paused":
                logger.warning(f"一時停止されていないワークフローは再開できません: {workflow_id}")
                return False
            
            # ワークフローを再開
            self.active_workflows[workflow_id]["status"] = "running"
            self.active_workflows[workflow_id]["resumed_at"] = datetime.now().isoformat()
            
            # データベースにも状態を保存
            asyncio.run(
                self.workflow_repository.update_workflow_status(
                    workflow_id,
                    {
                        "status": "running",
                        "resumed_at": datetime.now().isoformat()
                    }
                )
            )
            
            # ワークフローの実行を再開
            # （実際のワークフロー再開ロジックはここに実装）
            
            return True
            
        except Exception as e:
            logger.error(f"ワークフロー再開中にエラーが発生: {e}")
            return False


# サービスのシングルトンインスタンスを取得する関数
def get_workflow_service() -> WorkflowService:
    """
    ワークフローサービスのシングルトンインスタンスを取得する
    
    Returns:
        WorkflowServiceのシングルトンインスタンス
    """
    return WorkflowService()


# FastAPI用の依存関係注入関数
def get_workflow_service_dependency() -> WorkflowService:
    """
    FastAPI用の依存関係注入関数
    
    Returns:
        WorkflowServiceのインスタンス
    """
    return get_workflow_service()


# 後方互換性のためのラッパー関数（非推奨）
async def run_workflow(workflow_id: str, workflow_state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    旧APIとの後方互換性のためのラッパー関数（非推奨）
    
    Args:
        workflow_id: ワークフローID
        workflow_state: ワークフロー状態
        **kwargs: その他のパラメータ
        
    Returns:
        ワークフロー実行結果
        
    Note:
        この関数は非推奨です。
        代わりに WorkflowService.run_workflow() を使用してください。
    """
    import warnings
    warnings.warn(
        "run_workflow関数は非推奨です。代わりにget_workflow_service().run_workflow()を使用してください。",
        DeprecationWarning,
        stacklevel=2
    )
    
    service = get_workflow_service()
    
    result = await service.run_workflow(
        workflow_id=workflow_id,
        workflow_type="audit",
        initial_data=workflow_state,
        **kwargs
    )
    
    return result


# 後方互換性のためのラッパー関数（非推奨）
def get_workflow_status(workflow_id: str) -> Optional[Dict[str, Any]]:
    """
    旧APIとの後方互換性のためのラッパー関数（非推奨）
    
    Args:
        workflow_id: ワークフローID
        
    Returns:
        ワークフロー状態
        
    Note:
        この関数は非推奨です。
        代わりに WorkflowService.get_workflow_status() を使用してください。
    """
    import warnings
    warnings.warn(
        "get_workflow_status関数は非推奨です。代わりにget_workflow_service().get_workflow_status()を使用してください。",
        DeprecationWarning,
        stacklevel=2
    )
    
    service = get_workflow_service()
    return service.get_workflow_status(workflow_id)
