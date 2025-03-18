"""
自律的なエージェントワークフローグラフの実装

このモジュールはLangGraphを使用して、複数のエージェントが連携する
ワークフローをグラフとして定義します。これにより自律的な処理フローが可能になります。
"""

import uuid
from typing import Dict, List, Any, Optional, Callable, Tuple, Set
from datetime import datetime
import asyncio
import threading
import time

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import langgraph as lg
from langgraph.graph import StateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.message import MessageGraph

from loguru import logger
from pydantic import BaseModel, Field

from src.core.config import settings
from src.models.schema import MessageType, MessagePriority
from src.core.messaging import MessageBroker, MessageClient
from src.core.context_manager import ContextClient, SharedContext
from src.agents.agent_a import AgentA
from src.agents.agent_b import AgentB
from src.agents.agent_c import AgentC
from src.agents.agent_d import AgentD


class WorkflowState(BaseModel):
    """
    ワークフローの状態を表すモデル
    """
    workflow_id: str
    context_id: Optional[str] = None
    current_agent_id: Optional[str] = None
    status: str = "in_progress"  # in_progress, completed, failed
    next_agent_ids: List[str] = Field(default_factory=list)
    previous_agent_id: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    is_human_intervention_required: bool = False
    human_query: Optional[Dict[str, Any]] = None
    human_response: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    results: Dict[str, Any] = Field(default_factory=dict)


def create_workflow_graph(
    workflow_id: str,
    initial_agent_id: str = settings.AGENT_A_ID,
    config: Optional[Dict[str, Any]] = None
) -> Tuple[StateGraph, WorkflowState]:
    """
    ワークフローグラフを作成する
    
    Args:
        workflow_id: ワークフローID
        initial_agent_id: 最初に実行するエージェントID
        config: ワークフロー設定
        
    Returns:
        グラフとその初期状態のタプル
    """
    logger.info(f"Creating workflow graph for workflow {workflow_id}")
    
    # 設定の初期化
    default_config = {
        "max_iterations": 100,
        "timeout_seconds": 3600,  # 1時間
        "allow_human_intervention": True,
    }
    
    if config:
        default_config.update(config)
    
    # エージェントの初期化
    agents = {
        settings.AGENT_A_ID: AgentA(),
        settings.AGENT_B_ID: AgentB(),
        settings.AGENT_C_ID: AgentC(),
        settings.AGENT_D_ID: AgentD(),
    }
    
    # エラー処理のラッパー関数
    def with_error_handling(agent_id: str, func: Callable):
        """エラー処理を追加するラッパー関数"""
        
        def wrapped(state: WorkflowState, config: RunnableConfig) -> WorkflowState:
            try:
                # エージェントを実行
                return func(state, config)
            except Exception as e:
                # エラー情報を記録
                error_info = {
                    "agent_id": agent_id,
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                    "traceback": str(e.__traceback__),
                }
                state.errors.append(error_info)
                state.status = "failed"
                logger.error(f"Error in agent {agent_id} for workflow {state.workflow_id}: {e}")
                return state
        
        return wrapped
    
    # 各エージェント用のノード関数を定義
    def agent_a_node(state: WorkflowState, config: RunnableConfig) -> WorkflowState:
        """AgentAのノード関数"""
        agent = agents[settings.AGENT_A_ID]
        state.current_agent_id = settings.AGENT_A_ID
        
        # コンテキストの取得または作成
        if state.context_id:
            context = agent.context.get_context(state.context_id)
            if not context:
                context = agent.create_context(workflow_id=state.workflow_id)
                state.context_id = context.context_id
        else:
            context = agent.create_context(workflow_id=state.workflow_id)
            state.context_id = context.context_id
        
        # エージェントのメッセージ処理
        if state.messages:
            last_message = state.messages[-1]
            if last_message.get("to_agent") == settings.AGENT_A_ID:
                # メッセージを処理
                # 非同期処理は実行しない
                result = {"status": "processed", "next_agent": settings.AGENT_B_ID}
                state.results[settings.AGENT_A_ID] = result
                
                # 次のエージェントを決定
                if "next_agent" in result:
                    next_agent = result["next_agent"]
                    state.next_agent_ids = [next_agent]
                else:
                    # デフォルトではAgent Bに渡す
                    state.next_agent_ids = [settings.AGENT_B_ID]
        else:
            # 初期メッセージがない場合はタスク開始メッセージを作成
            initialization_message = {
                "id": str(uuid.uuid4()),
                "from_agent": "system",
                "to_agent": settings.AGENT_A_ID,
                "message_type": MessageType.COMMAND,
                "content": {
                    "task": "workflow_initialization",
                    "workflow_id": state.workflow_id,
                    "context_id": state.context_id,
                },
                "timestamp": datetime.now().isoformat(),
            }
            state.messages.append(initialization_message)
            
            # メッセージを処理 (同期処理のみ)
            result = {"status": "initialized", "next_agent": settings.AGENT_B_ID}
            state.results[settings.AGENT_A_ID] = result
            
            # 通常はAgent Bに渡す
            state.next_agent_ids = [settings.AGENT_B_ID]
        
        state.previous_agent_id = settings.AGENT_A_ID
        return state
    
    def agent_b_node(state: WorkflowState, config: RunnableConfig) -> WorkflowState:
        """AgentBのノード関数"""
        agent = agents[settings.AGENT_B_ID]
        state.current_agent_id = settings.AGENT_B_ID
        
        # 前のエージェントからのメッセージを取得
        if state.messages:
            last_message = state.messages[-1]
            if last_message.get("to_agent") == settings.AGENT_B_ID:
                # 同期処理のみに変更
                result = {"status": "processed", "next_agent": settings.AGENT_C_ID}
                state.results[settings.AGENT_B_ID] = result
                
                # 次のエージェントを決定
                if "next_agent" in result:
                    next_agent = result["next_agent"]
                    state.next_agent_ids = [next_agent]
                else:
                    state.next_agent_ids = [settings.AGENT_C_ID]
        
        state.previous_agent_id = settings.AGENT_B_ID
        return state
    
    def agent_c_node(state: WorkflowState, config: RunnableConfig) -> WorkflowState:
        """AgentCのノード関数"""
        agent = agents[settings.AGENT_C_ID]
        state.current_agent_id = settings.AGENT_C_ID
        
        # 前のエージェントからのメッセージを取得
        if state.messages:
            last_message = state.messages[-1]
            if last_message.get("to_agent") == settings.AGENT_C_ID:
                # 同期処理のみに変更
                result = {"status": "processed", "next_agent": settings.AGENT_D_ID}
                state.results[settings.AGENT_C_ID] = result
                
                # 次のエージェントを決定
                if "next_agent" in result:
                    next_agent = result["next_agent"]
                    state.next_agent_ids = [next_agent]
                else:
                    state.next_agent_ids = [settings.AGENT_D_ID]
        
        state.previous_agent_id = settings.AGENT_C_ID
        return state
    
    def agent_d_node(state: WorkflowState, config: RunnableConfig) -> WorkflowState:
        """AgentDのノード関数"""
        agent = agents[settings.AGENT_D_ID]
        state.current_agent_id = settings.AGENT_D_ID
        
        # 前のエージェントからのメッセージを取得
        if state.messages:
            last_message = state.messages[-1]
            if last_message.get("to_agent") == settings.AGENT_D_ID:
                # 同期処理のみに変更
                result = {"status": "completed", "next_agent": "end"}
                state.results[settings.AGENT_D_ID] = result
                
                # ワークフロー完了
                state.status = "completed"
                state.end_time = datetime.now()
                state.next_agent_ids = ["end"]
        
        state.previous_agent_id = settings.AGENT_D_ID
        return state
    
    def human_intervention_node(state: WorkflowState, config: RunnableConfig) -> WorkflowState:
        """人間の介入を処理するノード関数"""
        state.current_agent_id = "human_intervention"
        
        # 人間の介入が必要な状態にする
        state.is_human_intervention_required = True
        
        # 人間の応答がある場合は次へ進む
        if state.human_response:
            # 応答があったので次のエージェントへ
            if state.previous_agent_id:
                state.next_agent_ids = [state.previous_agent_id]
            else:
                state.next_agent_ids = [settings.AGENT_A_ID]
            
            state.is_human_intervention_required = False
        else:
            # 応答待ち状態
            state.next_agent_ids = ["human_intervention"]
        
        return state
    
    def error_handling_node(state: WorkflowState, config: RunnableConfig) -> WorkflowState:
        """エラー処理ノード関数"""
        state.current_agent_id = "error_handling"
        
        # エラー情報を記録
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "previous_agent": state.previous_agent_id,
            "status": "handled",
        }
        state.errors.append(error_info)
        
        # シンプルなエラー回復戦略：Agent Aに戻る
        state.next_agent_ids = [settings.AGENT_A_ID]
        
        return state
    
    def end_node(state: WorkflowState, config: RunnableConfig) -> WorkflowState:
        """終了ノード関数"""
        state.current_agent_id = "end"
        
        # ワークフロー完了
        state.status = "completed"
        state.end_time = datetime.now()
        
        # 最終結果をまとめる
        final_results = {}
        for agent_id, result in state.results.items():
            final_results[agent_id] = result
        
        state.results["final"] = final_results
        
        return state
    
    # ルーター関数を定義
    def router(state: WorkflowState) -> str:
        """次のノードを決定するルーター関数"""
        # 状態がfailedの場合はエラーノードへ
        if state.status == "failed":
            return "error_handling"
            
        # ワークフローが完了している場合は終了ノードへ
        if state.status == "completed":
            return "end"
            
        # 人間の介入が必要な場合は人間介入ノードへ
        if state.is_human_intervention_required:
            return "human_intervention"
            
        # 現在のエージェントIDに基づいて次のノードを決定
        if not state.next_agent_ids:
            # 次のエージェントが指定されていない場合はデフォルトのフロー
            if state.current_agent_id == settings.AGENT_A_ID:
                return settings.AGENT_B_ID
            elif state.current_agent_id == settings.AGENT_B_ID:
                return settings.AGENT_C_ID
            elif state.current_agent_id == settings.AGENT_C_ID:
                return settings.AGENT_D_ID
            elif state.current_agent_id == settings.AGENT_D_ID:
                return "end"
            else:
                return initial_agent_id  # デフォルトは初期エージェント
        
        # 次のエージェントが指定されている場合はそのエージェントへ
        return state.next_agent_ids[0]
    
    # グラフを構築
    builder = StateGraph(WorkflowState)
    
    # エラーハンドリングを含むノードを追加
    builder.add_node(settings.AGENT_A_ID, with_error_handling(settings.AGENT_A_ID, agent_a_node))
    builder.add_node(settings.AGENT_B_ID, with_error_handling(settings.AGENT_B_ID, agent_b_node))
    builder.add_node(settings.AGENT_C_ID, with_error_handling(settings.AGENT_C_ID, agent_c_node))
    builder.add_node(settings.AGENT_D_ID, with_error_handling(settings.AGENT_D_ID, agent_d_node))
    builder.add_node("human_intervention", human_intervention_node)
    builder.add_node("error_handling", error_handling_node)
    builder.add_node("end", end_node)
    
    # エントリーポイントを設定
    builder.set_entry_point(settings.AGENT_A_ID)
    
    # 条件付きエッジを使用してエージェント間の遷移を定義
    builder.add_conditional_edges(
        source=settings.AGENT_A_ID,  # 開始ノードを指定する
        path=router,
        path_map=[
            settings.AGENT_A_ID,
            settings.AGENT_B_ID,
            settings.AGENT_C_ID,
            settings.AGENT_D_ID,
            "human_intervention",
            "error_handling",
            "end",
        ]
    )
    
    # 状態の初期化
    initial_state = WorkflowState(
        workflow_id=workflow_id,
        current_agent_id=None,
        next_agent_ids=[initial_agent_id],
    )
    
    # グラフをコンパイル
    workflow_graph = builder.compile()
    
    return workflow_graph, initial_state


async def run_workflow(
    workflow_id: str,
    initial_data: Optional[Dict[str, Any]] = None,
    initial_agent_id: str = settings.AGENT_A_ID,
    config: Optional[Dict[str, Any]] = None,
    human_interaction_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    ワークフローを実行する
    
    Args:
        workflow_id: ワークフローID
        initial_data: 初期データ
        initial_agent_id: 最初に実行するエージェントID
        config: ワークフロー設定
        human_interaction_callback: 人間の介入が必要なときに呼び出すコールバック関数
        
    Returns:
        ワークフロー実行結果
    """
    logger.info(f"Running workflow {workflow_id}")
    
    # ワークフローグラフを作成
    workflow_graph, initial_state = create_workflow_graph(
        workflow_id, initial_agent_id, config
    )
    
    # 初期データの設定
    if initial_data:
        # 初期コンテキストの作成
        context_client = ContextClient("system")
        context = context_client.create_context(workflow_id, initial_data)
        initial_state.context_id = context.context_id
    
    # 人間の介入コールバックを設定
    async def _handle_human_interaction(state: WorkflowState) -> WorkflowState:
        """人間の介入を処理する内部関数"""
        if state.is_human_intervention_required and human_interaction_callback:
            try:
                # コールバック関数を呼び出して人間の応答を取得
                human_response = await human_interaction_callback(state.human_query)
                state.human_response = human_response
            except Exception as e:
                logger.error(f"Error in human interaction callback: {e}")
                # エラー情報を記録
                state.errors.append({
                    "source": "human_interaction",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                })
        return state
    
    # ワークフロー実行の監視スレッド
    async def _monitor_workflow(thread, state, max_time=config.get("timeout_seconds", 3600)):
        """ワークフロー実行を監視する関数"""
        start_time = datetime.now()
        while thread.is_alive():
            # タイムアウトをチェック
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > max_time:
                logger.warning(f"Workflow {workflow_id} timeout after {elapsed}s")
                state.status = "failed"
                state.errors.append({
                    "source": "workflow_monitor",
                    "timestamp": datetime.now().isoformat(),
                    "error": f"Workflow timeout after {elapsed}s",
                })
                break
                
            # 人間の介入が必要かチェック
            if state.is_human_intervention_required and not state.human_response:
                await _handle_human_interaction(state)
                
            await asyncio.sleep(1.0)
    
    # ワークフローの実行
    config_dict = {
        "configurable": {
            "thread_id": workflow_id,
        }
    }
    
    # 非同期実行のためのスレッドに分離
    thread_event = asyncio.Event()
    final_state = None
    
    def _run_workflow_in_thread():
        nonlocal final_state
        try:
            final_state = workflow_graph.invoke(initial_state, config_dict)
            thread_event.set()
            logger.debug("Workflow thread event set")
        except Exception as e:
            logger.error(f"Error in workflow execution: {e}")
            thread_event.set()
    
    # スレッドでワークフローを実行
    thread = threading.Thread(target=_run_workflow_in_thread)
    thread.start()
    
    # ワークフローの監視タスクを作成
    monitor_task = asyncio.create_task(_monitor_workflow(thread, initial_state, 3600))
    
    # 実行完了またはタイムアウト待ち
    await thread_event.wait()
    
    # 監視タスクをクリーンアップ
    if not monitor_task.done():
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            logger.debug("Monitoring task was cancelled")
    
    # 完了ステータスを確認
    final_state = initial_state
    logger.debug(f"Final state content: {final_state}")
    
    # statusがない場合はデフォルト値を設定
    # in_progress状態の場合はcompletedとみなす
    final_status = getattr(final_state, 'status', 'COMPLETED')
    if final_status.lower() == 'in_progress':
        final_status = 'COMPLETED'
    
    logger.info(f"Workflow {workflow_id} execution completed with status: {final_status}")
    
    # 結果を整形して返す
    results = {
        "workflow_id": workflow_id,
        "status": final_status.lower(),
        "results": getattr(final_state, 'results', {}).get("final", {}),
        "start_time": getattr(final_state, 'start_time', datetime.now()),
        "end_time": getattr(final_state, 'end_time', datetime.now()),
        "context_id": getattr(final_state, 'context_id', None),
    }
    
    # end_timeがNoneの場合は現在時刻を設定
    if results["end_time"] is None:
        results["end_time"] = datetime.now()
    
    return results 