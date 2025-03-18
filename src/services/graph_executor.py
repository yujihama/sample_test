"""
グラフ実行サービス層

このモジュールは、LangGraphの実行を管理するサービス層を提供します。
以下の機能を含みます：
- ワークフローグラフの作成と初期化
- イベントによるグラフの進行
- 状態管理とチェックポイント機能
- 監査証跡とログ機能
"""

import asyncio
import uuid
import copy
import json
from src.utils import json_utils
import difflib
from datetime import datetime
from typing import Dict, Any, List, Optional, TypedDict, Tuple, Union

import langchain
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.utils import Input, Output
from loguru import logger
from sqlalchemy.orm import Session

# 監査証跡と状態履歴用のインポート
from src.utils.db_manager import get_db_session
from src.models.repositories import (
    get_graph_state_history_repository,
    get_checkpoint_record_repository
)

# 注: 既存機能に応じて必要なインポートは調整してください
# from src.core.workflow import create_audit_workflow
# from src.utils.db_manager import get_db_session
# from src.repositories.workflow_repository import WorkflowRepository


class WorkflowState(TypedDict, total=False):
    """ワークフローの状態を表すデータ型"""
    workflow_id: str
    procedure_id: str
    procedure_text: str
    sample_id: Optional[str]
    status: str
    current_agent: str
    messages: List[Dict[str, Any]]
    created_at: str
    updated_at: str
    error: Optional[str]


class Checkpoint(TypedDict, total=False):
    """チェックポイントを表すデータ型"""
    checkpoint_id: str
    workflow_id: str
    timestamp: str
    node_id: str
    state: WorkflowState


class GraphExecutor:
    """LangGraphの実行を管理するサービス"""
    
    def __init__(self, graph=None, checkpoint_saver=None):
        """GraphExecutorの初期化"""
        # 注: 実際の実装では既存のworkflow作成関数を使用
        # self.graph = create_audit_workflow()
        
        # グラフインスタンス（引数から取得）
        self.graph = graph
        
        # アクティブなワークフロー
        self.active_workflows = {}
        
        # チェックポイント用メモリストア（ディクショナリ）
        self.checkpoints = {}
        
        # チェックポイントセーバー
        self.checkpoint_saver = checkpoint_saver
        
        # 最後の状態を保持するディクショナリ（差分計算用）
        self.last_states = {}
        
        # ワークフローリポジトリの初期化
        # self.workflow_repository = WorkflowRepository(get_db_session())
        
        logger.info("GraphExecutorが初期化されました")
    
    async def create_workflow(self, initial_state: Dict[str, Any]) -> WorkflowState:
        """
        新しいワークフローグラフを作成
        
        Args:
            initial_state: 初期状態の情報
            
        Returns:
            作成されたワークフローの状態
        """
        # ワークフローIDの生成（または既存のものを使用）
        workflow_id = initial_state.get("workflow_id", f"wf-{uuid.uuid4().hex[:8]}")
        
        # 初期状態の構築
        state: WorkflowState = {
            "workflow_id": workflow_id,
            "procedure_id": initial_state.get("procedure_id", ""),
            "procedure_text": initial_state.get("procedure_text", ""),
            "sample_id": initial_state.get("sample_id"),
            "status": "created",
            "current_agent": "agent_a",  # 初期エージェント
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # その他のカスタムフィールドがあれば追加
        for key, value in initial_state.items():
            if key not in state:
                state[key] = value
        
        # 最終状態の記録（差分計算用）
        self.last_states[workflow_id] = copy.deepcopy(state)
        
        # 状態の永続化
        await self._save_workflow_state(state)
        
        # アクティブワークフローに追加
        self.active_workflows[workflow_id] = state
        
        # 監査証跡への記録
        await self._record_state_history(
            workflow_id=workflow_id, 
            agent_id=state["current_agent"],
            transition_to="created", 
            state_snapshot=state,
            state_diff=None,
            event_type="create_workflow", 
            event_data=initial_state,
            context_id=initial_state.get("context_id")
        )
        
        logger.info(f"新しいワークフローを作成しました: {workflow_id}")
        return state
    
    async def process_event(self, workflow_id: str, event: Dict[str, Any]) -> WorkflowState:
        """
        イベントを処理してグラフを進める
        
        Args:
            workflow_id: ワークフローID
            event: 処理するイベント
            
        Returns:
            更新された状態
        
        Raises:
            ValueError: ワークフローが見つからない場合
        """
        # 現在の状態をロード
        state = await self._load_workflow_state(workflow_id)
        if not state:
            logger.error(f"ワークフロー状態が見つかりません: {workflow_id}")
            raise ValueError(f"ワークフロー {workflow_id} が見つかりません")
        
        # 処理前の状態をコピー（監査証跡用）
        prev_state = copy.deepcopy(state)
        prev_status = state.get("status", "")
        
        # イベントタイプに基づいて状態を更新
        if event.get("event_type") == "message":
            # メッセージイベントの処理
            payload = event.get("payload", {})
            
            # メッセージ履歴に追加
            if "messages" not in state:
                state["messages"] = []
            
            message_id = f"msg-{uuid.uuid4().hex[:8]}"
            state["messages"].append({
                "id": message_id,
                "from_agent": payload.get("from_agent"),
                "to_agent": payload.get("to_agent"),
                "content": payload.get("content"),
                "timestamp": datetime.now().isoformat()
            })
            
            # 現在のエージェントを更新
            state["current_agent"] = payload.get("to_agent")
            state["status"] = "in_progress"
        
        # その他のイベントタイプに対する処理...
        
        # グラフ進行のための設定
        config_id = f"workflow_{workflow_id}"
        thread_id = workflow_id
        
        # チェックポイントの自動作成（ノード開始前）
        checkpoint_id = await self._create_checkpoint(state, f"pre_event_{event.get('event_type')}")
        
        try:
            # 実際のグラフにイベントを適用
            # 注: 実際のLangGraphオブジェクトが必要
            if self.graph:
                # 実際のLangGraph実行
                new_state = await self.graph.ainvoke(
                    state,
                    config=RunnableConfig(
                        configurable={"thread_id": thread_id, "config_id": config_id}
                    )
                )
            else:
                # ダミー実装（グラフなしの場合）
                new_state = state.copy()
                new_state["updated_at"] = datetime.now().isoformat()
            
            # 状態更新のチェックポイント作成（ノード完了後）
            checkpoint_id = await self._create_checkpoint(new_state, f"post_event_{event.get('event_type')}")
            
            # 状態の変化を分析
            transition_from = prev_status
            transition_to = new_state.get("status", "")
            
            # 監査証跡への記録
            await self._record_state_history(
                workflow_id=workflow_id,
                agent_id=new_state.get("current_agent", "unknown"),
                node_id=f"event_{event.get('event_type')}",
                transition_from=transition_from,
                transition_to=transition_to,
                state_snapshot=new_state,
                state_diff=self._calculate_state_diff(workflow_id, new_state),
                event_type=event.get("event_type"),
                event_data=event,
                context_id=new_state.get("context_id"),
                checkpoint_id=checkpoint_id
            )
            
            # 最終状態の更新（差分計算用）
            self.last_states[workflow_id] = copy.deepcopy(new_state)
            
            # 状態の永続化
            await self._save_workflow_state(new_state)
            
            # アクティブワークフローを更新
            self.active_workflows[workflow_id] = new_state
            
            logger.info(f"イベント処理が完了しました: {workflow_id} - {event.get('event_type')}")
            return new_state
            
        except Exception as e:
            logger.error(f"グラフ実行中にエラー: {e}")
            state["status"] = "error"
            state["error"] = str(e)
            
            # エラー状態チェックポイントの作成
            error_checkpoint_id = await self._create_checkpoint(state, "error")
            
            # 監査証跡への記録
            await self._record_state_history(
                workflow_id=workflow_id,
                agent_id=state.get("current_agent", "unknown"),
                node_id="error",
                transition_from=prev_status,
                transition_to="error",
                state_snapshot=state,
                state_diff=self._calculate_state_diff(workflow_id, state),
                event_type="error",
                event_data={"error": str(e), "original_event": event},
                context_id=state.get("context_id"),
                checkpoint_id=error_checkpoint_id
            )
            
            # 最終状態の更新（差分計算用）
            self.last_states[workflow_id] = copy.deepcopy(state)
            
            # エラー状態の永続化
            await self._save_workflow_state(state)
            
            # アクティブワークフローを更新
            self.active_workflows[workflow_id] = state
            
            return state
    
    async def get_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """
        現在のワークフロー状態を取得
        
        Args:
            workflow_id: ワークフローID
            
        Returns:
            ワークフロー状態（存在しない場合はNone）
        """
        return await self._load_workflow_state(workflow_id)
    
    async def get_checkpoint(self, workflow_id: str, checkpoint_id: Optional[str] = None) -> Optional[Checkpoint]:
        """
        特定のチェックポイントを取得
        
        Args:
            workflow_id: ワークフローID
            checkpoint_id: チェックポイントID（省略時は最新の状態）
            
        Returns:
            チェックポイント情報（存在しない場合はNone）
        """
        # チェックポイントIDが指定されていない場合は最新の状態を返す
        if not checkpoint_id:
            state = await self.get_state(workflow_id)
            if not state:
                return None
                
            return {
                "checkpoint_id": "latest",
                "workflow_id": workflow_id,
                "timestamp": datetime.now().isoformat(),
                "node_id": "current",
                "state": state
            }
        
        # チェックポイントの取得（メモリストアから）
        try:
            # チェックポイントの検索ロジック
            checkpoint_key = f"workflow_{workflow_id}_{checkpoint_id}"
            
            # ディクショナリからチェックポイントを取得
            if checkpoint_key in self.checkpoints:
                return self.checkpoints[checkpoint_key]
            
            # チェックポイントが見つからない場合
            logger.warning(f"チェックポイントが見つかりません: {checkpoint_id}")
            return None
        except Exception as e:
            logger.error(f"チェックポイント取得エラー: {e}")
            return None
    
    async def list_checkpoints(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        ワークフローのチェックポイント一覧を取得
        
        Args:
            workflow_id: ワークフローID
            
        Returns:
            チェックポイントのリスト
        """
        # ワークフロー毎のチェックポイントリストを取得
        workflow_checkpoints_key = f"workflow_{workflow_id}_checkpoints"
        if workflow_checkpoints_key in self.checkpoints:
            return self.checkpoints[workflow_checkpoints_key]
        
        # チェックポイントが見つからない場合は空リスト
        return []
    
    async def restore_checkpoint(self, workflow_id: str, checkpoint_id: str) -> Optional[WorkflowState]:
        """
        チェックポイントから状態を復元
        
        Args:
            workflow_id: ワークフローID
            checkpoint_id: 復元するチェックポイントID
            
        Returns:
            復元された状態（失敗時はNone）
        """
        checkpoint = await self.get_checkpoint(workflow_id, checkpoint_id)
        if not checkpoint or "state" not in checkpoint:
            logger.error(f"復元するチェックポイントが見つかりません: {checkpoint_id}")
            return None
        
        # 状態の復元と永続化
        state = checkpoint["state"]
        state["updated_at"] = datetime.now().isoformat()
        state["status"] = "restored"
        
        # 監査証跡への記録
        await self._record_state_history(
            workflow_id=workflow_id,
            agent_id=state.get("current_agent", "unknown"),
            node_id=f"restore_{checkpoint_id}",
            transition_from="unknown",
            transition_to="restored",
            state_snapshot=state,
            state_diff=self._calculate_state_diff(workflow_id, state),
            event_type="restore_checkpoint",
            event_data={"checkpoint_id": checkpoint_id},
            context_id=state.get("context_id")
        )
        
        # 最終状態の更新（差分計算用）
        self.last_states[workflow_id] = copy.deepcopy(state)
        
        # チェックポイントを復元済みとしてマーク
        try:
            db = next(get_db_session())
            cp_repo = get_checkpoint_record_repository(db)
            cp_repo.mark_as_restored(checkpoint_id)
            db.close()
        except Exception as e:
            logger.warning(f"チェックポイント復元マーク中にエラー: {e}")
        
        await self._save_workflow_state(state)
        
        # アクティブワークフローを更新
        self.active_workflows[workflow_id] = state
        
        logger.info(f"チェックポイントから状態を復元しました: {workflow_id} - {checkpoint_id}")
        return state
    
    async def get_state_history(self, workflow_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        ワークフローの状態履歴を取得
        
        Args:
            workflow_id: ワークフローID
            limit: 取得する履歴の最大数
            offset: 取得開始位置
            
        Returns:
            状態履歴のリスト
        """
        try:
            db = next(get_db_session())
            history_repo = get_graph_state_history_repository(db)
            
            histories = history_repo.search(
                workflow_id=workflow_id,
                limit=limit,
                offset=offset
            )
            
            # レスポンス用にフォーマット
            result = []
            for history in histories:
                history_dict = {
                    "id": history.id,
                    "workflow_id": history.workflow_id,
                    "agent_id": history.agent_id,
                    "node_id": history.node_id,
                    "transition_from": history.transition_from,
                    "transition_to": history.transition_to,
                    "event_type": history.event_type,
                    "created_at": history.created_at.isoformat() if history.created_at else None,
                    "checkpoint_id": history.checkpoint_id
                }
                
                # 状態スナップショットとイベントデータがあれば解析してJSONに変換
                if history.state_snapshot:
                    try:
                        history_dict["state_snapshot"] = json_utils.json_deserialize(history.state_snapshot)
                    except:
                        history_dict["state_snapshot"] = None
                
                if history.state_diff:
                    try:
                        history_dict["state_diff"] = json_utils.json_deserialize(history.state_diff)
                    except:
                        history_dict["state_diff"] = None
                
                if history.event_data:
                    try:
                        history_dict["event_data"] = json_utils.json_deserialize(history.event_data)
                    except:
                        history_dict["event_data"] = None
                
                result.append(history_dict)
            
            db.close()
            return result
            
        except Exception as e:
            logger.error(f"状態履歴の取得中にエラー: {e}")
            return []
    
    async def get_state_transitions(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        ワークフローの状態遷移履歴を取得
        
        Args:
            workflow_id: ワークフローID
            
        Returns:
            状態遷移のリスト
        """
        try:
            db = next(get_db_session())
            history_repo = get_graph_state_history_repository(db)
            
            # 遷移情報のみを持つ履歴を取得
            histories = history_repo.search(workflow_id=workflow_id)
            
            # 遷移情報のみを抽出
            transitions = []
            for history in histories:
                if history.transition_from or history.transition_to:
                    transitions.append({
                        "id": history.id,
                        "from_state": history.transition_from,
                        "to_state": history.transition_to,
                        "agent_id": history.agent_id,
                        "node_id": history.node_id,
                        "event_type": history.event_type,
                        "timestamp": history.created_at.isoformat() if history.created_at else None
                    })
            
            db.close()
            return transitions
            
        except Exception as e:
            logger.error(f"状態遷移履歴の取得中にエラー: {e}")
            return []
    
    async def _create_checkpoint(self, state: WorkflowState, node_id: str) -> str:
        """
        状態のチェックポイントを作成
        
        Args:
            state: 保存する状態
            node_id: チェックポイントのノードID
            
        Returns:
            作成されたチェックポイントID
        """
        workflow_id = state["workflow_id"]
        checkpoint_id = f"cp-{uuid.uuid4().hex[:8]}"
        
        # チェックポイントの作成
        checkpoint: Checkpoint = {
            "checkpoint_id": checkpoint_id,
            "workflow_id": workflow_id,
            "timestamp": datetime.now().isoformat(),
            "node_id": node_id,
            "state": state
        }
        
        # チェックポイントをディクショナリに保存
        checkpoint_key = f"workflow_{workflow_id}_{checkpoint_id}"
        self.checkpoints[checkpoint_key] = checkpoint
        
        # ワークフロー毎のチェックポイントリストも更新
        workflow_checkpoints_key = f"workflow_{workflow_id}_checkpoints"
        if workflow_checkpoints_key not in self.checkpoints:
            self.checkpoints[workflow_checkpoints_key] = []
        self.checkpoints[workflow_checkpoints_key].append({
            "checkpoint_id": checkpoint_id,
            "workflow_id": workflow_id,
            "timestamp": checkpoint["timestamp"],
            "node_id": node_id
        })
        
        # DBにチェックポイントを記録
        try:
            db = next(get_db_session())
            cp_repo = get_checkpoint_record_repository(db)
            
            # チェックポイントタイプの決定
            if "error" in node_id:
                checkpoint_type = "error"
            elif "restore" in node_id:
                checkpoint_type = "restore"
            elif "pre_event" in node_id:
                checkpoint_type = "pre_event"
            elif "post_event" in node_id:
                checkpoint_type = "post_event"
            else:
                checkpoint_type = "auto"
            
            # チェックポイントをDBに記録
            cp_repo.create(
                workflow_id=workflow_id,
                agent_id=state.get("current_agent", "unknown"),
                checkpoint_type=checkpoint_type,
                node_id=node_id,
                state_reference={"checkpoint_id": checkpoint_id},
                metadata={"node_id": node_id, "status": state.get("status")},
                context_id=state.get("context_id")
            )
            
            db.close()
        except Exception as e:
            logger.warning(f"チェックポイントのDB記録中にエラー: {e}")
        
        # 外部チェックポイントセーバーを使用（存在する場合）
        if self.checkpoint_saver:
            try:
                await self.checkpoint_saver.save(workflow_id, checkpoint_id, state)
            except Exception as e:
                logger.warning(f"外部チェックポイントセーバーでのチェックポイント保存中にエラー: {e}")
        
        logger.info(f"チェックポイントを作成しました: {workflow_id} - {checkpoint_id} ({node_id})")
        return checkpoint_id
    
    async def _load_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """
        ワークフロー状態をロード
        
        Args:
            workflow_id: ワークフローID
            
        Returns:
            ワークフロー状態（存在しない場合はNone）
        """
        # メモリキャッシュからのロード
        if workflow_id in self.active_workflows:
            return self.active_workflows[workflow_id]
        
        # 実際のデータベースからのロード
        # 注: 実際の永続化ロジックは調整が必要
        # state = await self.workflow_repository.get_workflow_by_id(workflow_id)
        # return state
        
        # ダミー実装
        return None
    
    async def _save_workflow_state(self, state: WorkflowState) -> None:
        """
        ワークフロー状態を保存
        
        Args:
            state: 保存する状態
        """
        workflow_id = state["workflow_id"]
        
        # 永続化処理
        # 注: 実際の永続化ロジックは調整が必要
        # await self.workflow_repository.save_workflow(state)
        
        # アクティブワークフローを更新
        self.active_workflows[workflow_id] = state
        
        logger.debug(f"ワークフロー状態を保存しました: {workflow_id}")
    
    def _calculate_state_diff(self, workflow_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        前回の状態との差分を計算
        
        Args:
            workflow_id: ワークフローID
            state: 現在の状態
            
        Returns:
            差分情報
        """
        if workflow_id not in self.last_states:
            # 前回の状態が保存されていない場合は差分なし
            return {"is_first_state": True}
        
        prev_state = self.last_states[workflow_id]
        diff = {}
        
        # 各フィールドの差分をチェック
        for key, value in state.items():
            if key not in prev_state:
                # 新しく追加されたフィールド
                diff[key] = {"added": value}
            elif prev_state[key] != value:
                # 値が変更されたフィールド
                if isinstance(value, (str, int, float, bool)) and isinstance(prev_state[key], (str, int, float, bool)):
                    # プリミティブ型の場合は前後の値を記録
                    diff[key] = {"from": prev_state[key], "to": value}
                elif isinstance(value, (list, dict)) and isinstance(prev_state[key], (list, dict)):
                    # リストや辞書の場合は変更された部分のみを記録
                    prev_json = json_utils.json_serialize(prev_state[key])
                    curr_json = json_utils.json_serialize(value)
                    
                    if prev_json != curr_json:
                        # JSON文字列での差分
                        if len(prev_json) < 1000 and len(curr_json) < 1000:
                            # 小さいJSONの場合は文字列の差分を取得
                            diff_lines = list(difflib.unified_diff(
                                prev_json.splitlines(),
                                curr_json.splitlines(),
                                lineterm='',
                                n=0
                            ))
                            diff[key] = {"diff": diff_lines}
                        else:
                            # 大きいJSONの場合は変更があったことだけを記録
                            diff[key] = {"changed": True}
                else:
                    # その他の型の場合は変更があったことだけを記録
                    diff[key] = {"changed": True}
        
        # 削除されたフィールドをチェック
        for key in prev_state:
            if key not in state:
                diff[key] = {"removed": prev_state[key]}
        
        return diff
    
    async def _record_state_history(
        self,
        workflow_id: str,
        agent_id: str,
        node_id: Optional[str] = None,
        transition_from: Optional[str] = None,
        transition_to: Optional[str] = None,
        state_snapshot: Optional[Dict[str, Any]] = None,
        state_diff: Optional[Dict[str, Any]] = None,
        event_type: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        context_id: Optional[str] = None,
        checkpoint_id: Optional[str] = None
    ) -> None:
        """
        状態履歴をDBに記録
        
        Args:
            workflow_id: ワークフローID
            agent_id: エージェントID
            node_id: ノードID
            transition_from: 遷移元状態
            transition_to: 遷移先状態
            state_snapshot: 状態のスナップショット
            state_diff: 状態の差分
            event_type: イベントタイプ
            event_data: イベントデータ
            context_id: コンテキストID
            checkpoint_id: チェックポイントID
        """
        try:
            # DBセッションとリポジトリの取得
            db = next(get_db_session())
            history_repo = get_graph_state_history_repository(db)
            
            # 状態履歴の記録
            history_repo.create(
                workflow_id=workflow_id,
                agent_id=agent_id,
                node_id=node_id,
                transition_from=transition_from,
                transition_to=transition_to,
                state_snapshot=state_snapshot,
                state_diff=state_diff,
                event_type=event_type,
                event_data=event_data,
                context_id=context_id,
                checkpoint_id=checkpoint_id
            )
            
            db.close()
            logger.debug(f"状態履歴を記録しました: {workflow_id}")
        except Exception as e:
            logger.warning(f"状態履歴の記録中にエラー: {e}")


# シングルトンインスタンスを提供する関数
_graph_executor_instance = None

def get_graph_executor() -> GraphExecutor:
    """GraphExecutorのシングルトンインスタンスを取得"""
    global _graph_executor_instance
    if _graph_executor_instance is None:
        _graph_executor_instance = GraphExecutor()
    return _graph_executor_instance 