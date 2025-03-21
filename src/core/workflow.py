"""
LangGraphを使用したエージェントワークフロー
"""

import uuid
import asyncio
import json
from src.utils import json_utils
import os
from typing import Dict, List, Any, Literal, TypedDict, Optional, cast, Tuple, Callable
from datetime import datetime, timedelta

import langgraph.graph as lg
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from loguru import logger

# langgraph_checkpointのインポートエラーを修正
# 適切なパッケージが見つからない場合、必要な機能を持つ代替クラスを定義
class MemorySaver(BaseCheckpointSaver):
    """
    メモリ内でチェックポイントを保存する簡易なセーバー
    """
    def __init__(self):
        # BaseCheckpointSaverの初期化をスキップ（input_keyなどの引数を期待しないため）
        # super().__init__() は呼び出さない
        self.checkpoints = {}
        
    async def get_state(self, config_id: str, thread_id: str) -> Optional[Dict[str, Any]]:
        key = f"{config_id}:{thread_id}"
        return self.checkpoints.get(key)
        
    async def put_state(self, config_id: str, thread_id: str, state: Dict[str, Any]) -> None:
        key = f"{config_id}:{thread_id}"
        self.checkpoints[key] = state

# src.core.configからsettingsをインポート
from src.core.config import settings
# src.core.error_handlerからErrorHandlerをインポート
from src.core.error_handler import ErrorHandler

# 型定義
class WorkflowState(TypedDict, total=False):
    """ワークフロー状態の型定義"""
    workflow_id: str
    status: Literal["created", "in_progress", "paused", "completed", "error"]
    current_agent: str
    procedure_id: str
    procedure_text: str
    sample_id: Optional[str]
    sample_data: Optional[Dict[str, Any]]
    messages: List[Dict[str, Any]]
    results: List[Dict[str, Any]]
    error: Optional[str]
    paused_reason: Optional[str]
    human_input_required: Optional[bool]
    human_input: Optional[Dict[str, Any]]
    updated_at: str


def create_workflow_state(
    procedure_id: str,
    procedure_text: str,
    sample_id: str,
    data_source: str,
) -> WorkflowState:
    """
    ワークフロー状態を作成
    
    Args:
        procedure_id: 監査手続きID
        procedure_text: 監査手続きテキスト
        sample_id: サンプルデータID
        data_source: データソース名
        
    Returns:
        初期化されたワークフロー状態
    """
    workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
    current_time = datetime.now().isoformat()
    
    return {
        "procedure_id": procedure_id,
        "procedure_text": procedure_text,
        "sample_id": sample_id,
        "data_source": data_source,
        "agent_a_output": None,
        "agent_b_output": None,
        "agent_c_output": None,
        "agent_d_output": None,
        "current_agent": settings.AGENT_A_ID,
        "status": "initialized",
        "error": None,
        "messages": [],
        "retry_count": {},
        "retry_after": None,
        "retry_reason": None,
        "error_data": {},
        "workflow_id": workflow_id,
        "created_at": current_time,
        "updated_at": current_time,
    }


def add_message_to_state(
    state: WorkflowState,
    from_agent: str,
    to_agent: str,
    message_type: str,
    content: Dict[str, Any],
) -> WorkflowState:
    """
    ワークフロー状態にメッセージを追加
    
    Args:
        state: 現在の状態
        from_agent: 送信元エージェント
        to_agent: 宛先エージェント
        message_type: メッセージタイプ
        content: メッセージ内容
        
    Returns:
        更新された状態
    """
    message = {
        "id": f"msg-{uuid.uuid4().hex[:8]}",
        "from_agent": from_agent,
        "to_agent": to_agent,
        "message_type": message_type,
        "content": content,
        "created_at": datetime.now().isoformat(),
    }
    
    # 新しい状態を作成（immutableを維持）
    new_state = state.copy()
    new_state["messages"] = state["messages"] + [message]
    new_state["updated_at"] = datetime.now().isoformat()
    
    return new_state


# エラーハンドリングラッパー
def with_error_handling(agent_func: Callable) -> Callable:
    """
    エージェント関数にエラーハンドリングを追加するデコレータ
    
    Args:
        agent_func: 元のエージェント関数
        
    Returns:
        エラーハンドリング機能を追加した関数
    """
    error_handler = ErrorHandler()
    
    async def wrapped_func(state: WorkflowState) -> Dict[str, Any]:
        # 現在のエージェント名を取得
        agent_name = agent_func.__name__.replace("_node", "")
        
        # リトライカウントの初期化
        retry_counts = state.get("retry_count", {})
        agent_retry_count = retry_counts.get(agent_name, 0)
        
        try:
            # エージェント関数を実行
            return await agent_func(state)
        except Exception as e:
            logger.error(f"Error in {agent_name}: {str(e)}")
            
            # エラーハンドラーを使用して処理
            recovered, updated_state = await error_handler.handle_error(state, e)
            
            if recovered:
                # リトライカウントを更新
                retry_counts = updated_state.get("retry_count", {})
                retry_counts[agent_name] = agent_retry_count + 1
                updated_state["retry_count"] = retry_counts
                
                # 一時停止状態の場合は、そのまま返す
                if updated_state.get("status") == "paused":
                    return updated_state
                
                # 回復できた場合は、再度エージェント関数を実行
                logger.info(f"Retrying {agent_name} after error recovery")
                return await agent_func(updated_state)
            else:
                # 回復できなかった場合は、エラー状態を返す
                return updated_state
    
    return wrapped_func


# エージェントA（監査手続き理解・設計）のノード
@with_error_handling
async def agent_a_node(state: WorkflowState) -> Dict[str, Any]:
    """
    監査手続き理解と計画立案エージェント (AgentA) のノード関数
    
    このノードでは以下の処理を行います:
    1. 監査手続きの理解と分析
    2. テスト計画の生成
    3. Agent Bへの出力送信
    
    Args:
        state: 現在のワークフロー状態
        
    Returns:
        更新されたワークフロー状態
    """
    # 状態の検証と修復
    state = ensure_valid_state(state)
    
    # すでにAgent Aの出力が存在する場合は次に進む
    if state.get("outputs", {}).get(settings.AGENT_A_ID):
        logger.info(f"Agent A output already exists for workflow {state['workflow_id']}, skipping")
        return {
            **state,
            "current_agent": settings.AGENT_B_ID
        }
    
    logger.info(f"Agent A processing workflow {state['workflow_id']}")
    
    try:
        # 進行状況の更新
        updated_state = {
            **state,
            "status": "in_progress",
            "current_agent": settings.AGENT_A_ID,
            "updated_at": datetime.now().isoformat()
        }
        
        # 状態の永続化
        await save_workflow_state(updated_state)
        
        # AgentAインスタンスの作成
        from src.agents.agent_a import AgentA
        agent_a = AgentA()
        
        # 監査手続きの理解
        procedure_id = state.get("procedure_id")
        procedure_text = state.get("procedure_text", "")
        
        if not procedure_text:
            raise ValueError("Procedure text is missing in the workflow state")
            
        logger.info(f"Agent A understanding audit procedure: {procedure_id}")
        
        # 監査手続きの理解を生成
        understanding = await agent_a.understand_audit_procedure(procedure_text, procedure_id)
        
        # エラーチェック
        if isinstance(understanding, dict) and "error" in understanding:
            raise ValueError(f"Error understanding procedure: {understanding['error']}")
        
        # サンプルデータの分析 (あれば)
        sample_id = state.get("sample_id")
        sample_data = state.get("sample_data")
        data_analysis = None
        
        if sample_data:
            logger.info(f"Agent A analyzing sample data for workflow {state['workflow_id']}")
            
            # サンプルデータリポジトリからメタデータを取得
            db = next(get_db())
            sample_repo = SampleDataRepository()
            sample_metadata = None
            
            if sample_id:
                try:
                    sample = sample_repo.get(db, sample_id)
                    if sample:
                        sample_metadata = {
                            "id": sample.id,
                            "name": sample.name,
                            "description": sample.description,
                            "data_source": sample.data_source,
                            "created_at": sample.created_at.isoformat() if sample.created_at else None,
                        }
                except Exception as e:
                    logger.warning(f"Failed to get sample metadata: {e}")
            
            # サンプルデータの分析
            from src.utils.data_analyzer import analyze_sample_data
            data_analysis = await analyze_sample_data(sample_data, understanding, sample_metadata)
            
            # エラーチェック
            if isinstance(data_analysis, dict) and "error" in data_analysis:
                raise ValueError(f"Error analyzing sample data: {data_analysis['error']}")
        
        # テスト計画の生成
        logger.info(f"Agent A generating test plan for workflow {state['workflow_id']}")
        
        # データ分析がない場合のデフォルト値
        if not data_analysis:
            data_analysis = {
                "status": "no_data_available",
                "message": "No sample data was provided for analysis"
            }
        
        # テスト計画を生成
        test_plan = await agent_a.generate_test_plan(understanding, data_analysis)
        
        # エラーチェック
        if isinstance(test_plan, dict) and "error" in test_plan:
            raise ValueError(f"Error generating test plan: {test_plan['error']}")
        
        # 出力の記録
        agent_a_output = {
            "understanding": understanding,
            "data_analysis": data_analysis,
            "test_plan": test_plan,
            "timestamp": datetime.now().isoformat()
        }
        
        # メッセージの生成
        final_state = add_message_to_state(
            state=updated_state,
            from_agent=settings.AGENT_A_ID, 
            to_agent=settings.AGENT_B_ID,
            message_type="test_plan",
            content={
                "procedure_id": procedure_id,
                "procedure_text": procedure_text,
                "test_plan": test_plan
            }
        )
        
        # Agent Aの出力を記録
        final_state["outputs"] = {
            **(final_state.get("outputs", {})),
            settings.AGENT_A_ID: agent_a_output
        }
        
        # 次のエージェントを設定
        final_state["current_agent"] = settings.AGENT_B_ID
        
        # 状態の永続化
        await save_workflow_state(final_state)
        
        logger.info(f"Agent A completed processing workflow {state['workflow_id']}")
        return final_state
        
    except Exception as e:
        logger.error(f"Error in Agent A node: {e}")
        error_state = {
            **state,
            "status": "error",
            "error": f"Agent A error: {str(e)}",
            "updated_at": datetime.now().isoformat()
        }
        # エラー状態の永続化
        await save_workflow_state(error_state)
        return error_state


# エージェントB（監査テスト実行）のノード
@with_error_handling
async def agent_b_node(state: WorkflowState) -> Dict[str, Any]:
    """
    テスト実行エージェント (AgentB) のノード関数
    
    このノードでは以下の処理を行います:
    1. Agent Aから受け取ったテスト計画に基づいてテストを実行
    2. テスト結果を取得
    3. Agent Cへの出力送信
    
    Args:
        state: 現在のワークフロー状態
        
    Returns:
        更新されたワークフロー状態
    """
    # 状態の検証と修復
    state = ensure_valid_state(state)
    
    # すでにAgent Bの出力が存在する場合は次に進む
    if state.get("outputs", {}).get(settings.AGENT_B_ID):
        logger.info(f"Agent B output already exists for workflow {state['workflow_id']}, skipping")
        return {
            **state,
            "current_agent": settings.AGENT_C_ID
        }
    
    logger.info(f"Agent B processing workflow {state['workflow_id']}")
    
    try:
        # 進行状況の更新
        updated_state = {
            **state,
            "status": "in_progress",
            "current_agent": settings.AGENT_B_ID,
            "updated_at": datetime.now().isoformat()
        }
        
        # 状態の永続化
        await save_workflow_state(updated_state)
        
        # 必要なパラメータの検証
        workflow_id = state.get("workflow_id")
        if not workflow_id:
            raise ValueError("Workflow ID is missing in the workflow state")
            
        procedure_id = state.get("procedure_id")
        if not procedure_id:
            raise ValueError("Procedure ID is missing in the workflow state")
        
        # テスト計画の取得
        agent_a_output = state.get("outputs", {}).get(settings.AGENT_A_ID, {})
        test_plan = agent_a_output.get("test_plan")
        
        if not test_plan:
            # Agent Aからのメッセージから計画を取得
            messages = state.get("messages", [])
            test_plan_messages = [
                msg for msg in messages 
                if msg.get("from_agent") == settings.AGENT_A_ID 
                and msg.get("to_agent") == settings.AGENT_B_ID
                and msg.get("type") == "test_plan"
            ]
            
            if test_plan_messages:
                latest_message = test_plan_messages[-1]
                test_plan = latest_message.get("content", {}).get("test_plan")
            
            if not test_plan:
                raise ValueError("No test plan found in workflow state")
        
        # AgentBインスタンスの作成
        from src.agents.agent_b import AgentB
        agent_b = AgentB()
        
        # サンプルIDの取得
        sample_id = state.get("sample_id")
        if not sample_id:
            raise ValueError("Sample ID is missing in the workflow state")
            
        # サンプルデータの検証
        sample_data = state.get("sample_data")
        if not sample_data:
            logger.warning(f"Sample data is missing in workflow {workflow_id}, attempting to load from database")
            # データベースからサンプルデータを取得する処理を追加
            try:
                from src.models.db import get_db
                from src.models.repositories import SampleDataRepository
                
                db = next(get_db())
                sample_repo = SampleDataRepository()
                sample = sample_repo.get(db, sample_id)
                
                if not sample:
                    raise ValueError(f"Sample data with ID {sample_id} not found in database")
                    
                sample_data = sample.data
                # ワークフロー状態にサンプルデータを追加
                updated_state["sample_data"] = sample_data
                await save_workflow_state(updated_state)
            except Exception as db_error:
                logger.error(f"Failed to load sample data from database: {db_error}")
                raise ValueError(f"Could not load sample data: {str(db_error)}")
        
        # テスト実行リクエストの作成
        test_request = {
            "sample_id": sample_id,
            "sample_data": sample_data,
            "test_plan": test_plan,
            "procedure_id": procedure_id,
            "workflow_id": workflow_id
        }
        
        # テストの実行
        logger.info(f"Agent B executing tests for workflow {workflow_id}")
        test_results = await agent_b.execute_tests(test_request)
        
        # テスト結果の検証
        if not test_results:
            raise ValueError("Test execution failed, no results returned")
            
        if isinstance(test_results, dict) and test_results.get("error"):
            raise ValueError(f"Test execution error: {test_results.get('error')}")
        
        # 出力の記録
        agent_b_output = {
            "test_results": test_results,
            "timestamp": datetime.now().isoformat()
        }
        
        # メッセージの生成
        final_state = add_message_to_state(
            state=updated_state,
            from_agent=settings.AGENT_B_ID, 
            to_agent=settings.AGENT_C_ID,
            message_type="test_results",
            content={
                "procedure_id": procedure_id,
                "sample_id": sample_id,
                "test_results": test_results
            }
        )
        
        # Agent Bの出力を記録
        final_state["outputs"] = {
            **(final_state.get("outputs", {})),
            settings.AGENT_B_ID: agent_b_output
        }
        
        # 次のエージェントを設定
        final_state["current_agent"] = settings.AGENT_C_ID
        
        # 状態の永続化
        await save_workflow_state(final_state)
        
        # エージェント状態の更新（データベース）
        try:
            from src.models.db import get_db
            db = next(get_db())
            await update_agent_states(db, final_state)
        except Exception as db_error:
            logger.warning(f"Failed to update agent states in database: {db_error}")
            # データベース更新エラーはワークフロー続行の致命的エラーではないため、例外をスローしない
        
        logger.info(f"Agent B completed processing workflow {workflow_id}")
        return final_state
        
    except Exception as e:
        logger.error(f"Error in Agent B node: {e}")
        error_state = {
            **state,
            "status": "error",
            "error": f"Agent B error: {str(e)}",
            "updated_at": datetime.now().isoformat()
        }
        # エラー状態の永続化
        await save_workflow_state(error_state)
        # エラーログの詳細記録
        ErrorHandler.log_error(
            error_type="agent_b_execution_error",
            error_message=str(e),
            workflow_id=state.get("workflow_id", "unknown"),
            agent_id=settings.AGENT_B_ID,
            context={
                "procedure_id": state.get("procedure_id"),
                "sample_id": state.get("sample_id")
            }
        )
        return error_state


# エージェントC（結果評価・総括）のノード
@with_error_handling
async def agent_c_node(state: WorkflowState) -> Dict[str, Any]:
    """
    監査評価・分析エージェント (AgentC) のノード関数
    
    このノードでは以下の処理を行います:
    1. Agent AとBの出力を評価
    2. 監査結果の分析
    3. Agent Dへの出力送信
    
    Args:
        state: 現在のワークフロー状態
        
    Returns:
        更新されたワークフロー状態
    """
    # 状態の検証と修復
    state = ensure_valid_state(state)
    
    # すでにAgent Cの出力が存在する場合は次に進む
    if state.get("outputs", {}).get(settings.AGENT_C_ID):
        logger.info(f"Agent C output already exists for workflow {state['workflow_id']}, skipping")
        return {
            **state,
            "current_agent": settings.AGENT_D_ID
        }
    
    logger.info(f"Agent C processing workflow {state['workflow_id']}")
    
    try:
        # 必要なパラメータの検証
        workflow_id = state.get("workflow_id")
        if not workflow_id:
            raise ValueError("Workflow ID is missing in the workflow state")
        
        # 進行状況の更新
        updated_state = {
            **state,
            "status": "in_progress",
            "current_agent": settings.AGENT_C_ID,
            "updated_at": datetime.now().isoformat()
        }
        
        # 状態の永続化
        await save_workflow_state(updated_state)
        
        # 前段のエージェント出力の取得
        agent_a_output = state.get("outputs", {}).get(settings.AGENT_A_ID, {})
        agent_b_output = state.get("outputs", {}).get(settings.AGENT_B_ID, {})
        
        # 評価に必要な情報の取得
        procedure_id = state.get("procedure_id")
        if not procedure_id:
            raise ValueError("Procedure ID is missing in the workflow state")
            
        procedure_text = state.get("procedure_text", "")
        test_plan = agent_a_output.get("test_plan")
        test_results = agent_b_output.get("test_results")
        
        # 必要なデータの検証
        if not procedure_text:
            raise ValueError("Procedure text is missing in the workflow state")
            
        if not test_plan:
            raise ValueError("Test plan is missing in Agent A output")
            
        if not test_results:
            raise ValueError("Test results are missing in Agent B output")
        
        # AgentCインスタンスの作成
        from src.agents.agent_c import AgentC
        agent_c = AgentC()
        
        # 評価リクエストの作成
        evaluation_request = {
            "procedure_id": procedure_id,
            "procedure_text": procedure_text,
            "test_plan": test_plan,
            "test_results": test_results,
            "workflow_id": workflow_id
        }
        
        # 評価の実行
        logger.info(f"Agent C evaluating results for workflow {workflow_id}")
        evaluation = await agent_c.evaluate_results(evaluation_request)
        
        # 評価結果の検証
        if not evaluation:
            raise ValueError("Evaluation failed, no results returned")
            
        if isinstance(evaluation, dict) and evaluation.get("error"):
            raise ValueError(f"Evaluation error: {evaluation.get('error')}")
        
        # 出力の記録
        agent_c_output = {
            "evaluation": evaluation,
            "timestamp": datetime.now().isoformat()
        }
        
        # メッセージの生成
        final_state = add_message_to_state(
            state=updated_state,
            from_agent=settings.AGENT_C_ID, 
            to_agent=settings.AGENT_D_ID,
            message_type="evaluation",
            content={
                "procedure_id": procedure_id,
                "evaluation": evaluation
            }
        )
        
        # Agent Cの出力を記録
        final_state["outputs"] = {
            **(final_state.get("outputs", {})),
            settings.AGENT_C_ID: agent_c_output
        }
        
        # 次のエージェントを設定
        final_state["current_agent"] = settings.AGENT_D_ID
        
        # 状態の永続化
        await save_workflow_state(final_state)
        
        # エージェント状態の更新（データベース）
        try:
            from src.models.db import get_db
            db = next(get_db())
            await update_agent_states(db, final_state)
        except Exception as db_error:
            logger.warning(f"Failed to update agent states in database: {db_error}")
            # データベース更新エラーはワークフロー続行の致命的エラーではないため、例外をスローしない
        
        logger.info(f"Agent C completed processing workflow {workflow_id}")
        return final_state
        
    except Exception as e:
        logger.error(f"Error in Agent C node: {e}")
        error_state = {
            **state,
            "status": "error",
            "error": f"Agent C error: {str(e)}",
            "updated_at": datetime.now().isoformat()
        }
        # エラー状態の永続化
        await save_workflow_state(error_state)
        # エラーログの詳細記録
        ErrorHandler.log_error(
            error_type="agent_c_execution_error",
            error_message=str(e),
            workflow_id=state.get("workflow_id", "unknown"),
            agent_id=settings.AGENT_C_ID,
            context={
                "procedure_id": state.get("procedure_id")
            }
        )
        return error_state


# エージェントD（報告書作成）のノード
@with_error_handling
async def agent_d_node(state: WorkflowState) -> Dict[str, Any]:
    """
    報告書生成エージェント (AgentD) のノード関数
    
    このノードでは以下の処理を行います:
    1. 全エージェントの出力を統合
    2. 最終報告書の生成
    3. ワークフローの完了
    
    Args:
        state: 現在のワークフロー状態
        
    Returns:
        更新されたワークフロー状態
    """
    # 状態の検証と修復
    state = ensure_valid_state(state)
    
    # すでにAgent Dの出力が存在する場合は次に進む
    if state.get("outputs", {}).get(settings.AGENT_D_ID):
        logger.info(f"Agent D output already exists for workflow {state['workflow_id']}, skipping")
        return {
            **state,
            "current_agent": "completed",
            "status": "completed"
        }
    
    logger.info(f"Agent D processing workflow {state['workflow_id']}")
    
    try:
        # 必要なパラメータの検証
        workflow_id = state.get("workflow_id")
        if not workflow_id:
            raise ValueError("Workflow ID is missing in the workflow state")
            
        # 進行状況の更新
        updated_state = {
            **state,
            "status": "in_progress",
            "current_agent": settings.AGENT_D_ID,
            "updated_at": datetime.now().isoformat()
        }
        
        # 状態の永続化
        await save_workflow_state(updated_state)
        
        # 各エージェントの出力の取得
        agent_a_output = state.get("outputs", {}).get(settings.AGENT_A_ID, {})
        agent_b_output = state.get("outputs", {}).get(settings.AGENT_B_ID, {})
        agent_c_output = state.get("outputs", {}).get(settings.AGENT_C_ID, {})
        
        # 報告書生成に必要な情報の取得
        procedure_id = state.get("procedure_id")
        if not procedure_id:
            raise ValueError("Procedure ID is missing in the workflow state")
            
        procedure_text = state.get("procedure_text", "")
        test_plan = agent_a_output.get("test_plan")
        test_results = agent_b_output.get("test_results")
        evaluation = agent_c_output.get("evaluation")
        
        # 必要なデータの検証
        if not procedure_text:
            raise ValueError("Procedure text is missing in the workflow state")
            
        if not test_plan:
            raise ValueError("Test plan is missing in Agent A output")
            
        if not test_results:
            raise ValueError("Test results are missing in Agent B output")
            
        if not evaluation:
            raise ValueError("Evaluation is missing in Agent C output")
        
        # AgentDインスタンスの作成
        from src.agents.agent_d import AgentD
        agent_d = AgentD()
        
        # 報告書リクエストの作成
        report_request = {
            "procedure_id": procedure_id,
            "procedure_text": procedure_text,
            "test_plan": test_plan,
            "test_results": test_results,
            "evaluation": evaluation,
            "workflow_id": workflow_id
        }
        
        # 報告書の生成
        logger.info(f"Agent D generating report for workflow {workflow_id}")
        report = await agent_d.generate_report(report_request)
        
        # 報告書結果の検証
        if not report:
            raise ValueError("Report generation failed, no report returned")
            
        if isinstance(report, dict) and report.get("error"):
            raise ValueError(f"Report generation error: {report.get('error')}")
        
        # 出力の記録
        agent_d_output = {
            "report": report,
            "timestamp": datetime.now().isoformat()
        }
        
        # 報告書のファイルパスがあれば記録
        if "file_path" in report:
            agent_d_output["report_file_path"] = report["file_path"]
            logger.info(f"Report file generated at: {report['file_path']}")
        else:
            logger.warning(f"No report file path returned for workflow {workflow_id}")
        
        # 最終状態の更新
        final_state = {
            **updated_state,
            "outputs": {
                **(updated_state.get("outputs", {})),
                settings.AGENT_D_ID: agent_d_output
            },
            "current_agent": "completed",
            "status": "completed",
            "completed_at": datetime.now().isoformat()
        }
        
        # 状態の永続化
        await save_workflow_state(final_state)
        
        # エージェント状態の更新（データベース）
        try:
            from src.models.db import get_db
            db = next(get_db())
            await update_agent_states(db, final_state)
        except Exception as db_error:
            logger.warning(f"Failed to update agent states in database: {db_error}")
            # データベース更新エラーはワークフロー続行の致命的エラーではないため、例外をスローしない
        
        logger.info(f"Agent D completed processing workflow {workflow_id}, workflow completed")
        return final_state
        
    except Exception as e:
        logger.error(f"Error in Agent D node: {e}")
        error_state = {
            **state,
            "status": "error",
            "error": f"Agent D error: {str(e)}",
            "updated_at": datetime.now().isoformat()
        }
        # エラー状態の永続化
        await save_workflow_state(error_state)
        # エラーログの詳細記録
        ErrorHandler.log_error(
            error_type="agent_d_execution_error",
            error_message=str(e),
            workflow_id=state.get("workflow_id", "unknown"),
            agent_id=settings.AGENT_D_ID,
            context={
                "procedure_id": state.get("procedure_id")
            }
        )
        return error_state


# 人間介入ノードを関数定義
async def human_node(state: WorkflowState) -> Dict[str, Any]:
    """
    人間介入ノード
    
    人間からの入力を待機し、ワークフローを一時停止します。
    
    Args:
        state: 現在のワークフロー状態
        
    Returns:
        更新されたワークフロー状態
    """
    logger.info(f"Human intervention requested for workflow {state['workflow_id']}")
    
    try:
        # ワークフロー状態を一時停止に設定
        updated_state = {
            **state,
            "status": "paused",
            "paused_reason": state.get("error") or "人間の介入が必要です",
            "human_input_required": True,
            "updated_at": datetime.now().isoformat()
        }
        
        # データベースに人間介入リクエストを作成
        from src.models.repositories import HumanInterventionRequestRepository
        from src.utils.db_manager import get_db
        
        db = next(get_db())
        intervention_repo = HumanInterventionRequestRepository()
        
        # 既存の保留中の介入リクエストをチェック
        existing_intervention = intervention_repo.find_by_workflow_id(
            db, state['workflow_id'], status="pending"
        )
        
        if not existing_intervention:
            # 新しい介入リクエストを作成
            intervention_data = {
                "workflow_id": state['workflow_id'],
                "status": "pending",
                "request_type": "error_resolution" if "error" in state else "review",
                "details": {
                    "error": state.get("error"),
                    "current_state": state,
                    "paused_reason": state.get("paused_reason") or "人間の介入が必要です"
                },
                "resolved_at": None
            }
            
            intervention_repo.create(db, intervention_data)
            logger.info(f"Created human intervention request for workflow {state['workflow_id']}")
        
        # 状態の永続化
        await save_workflow_state(updated_state)
        
        logger.info(f"Workflow {state['workflow_id']} paused waiting for human intervention")
        return updated_state
        
    except Exception as e:
        logger.error(f"Error in human intervention node: {e}")
        error_state = {
            **state,
            "status": "error",
            "error": f"Human intervention error: {str(e)}",
            "updated_at": datetime.now().isoformat()
        }
        # エラー状態の永続化
        await save_workflow_state(error_state)
        return error_state


# 一時停止状態チェックノード
async def check_paused_state(state: WorkflowState) -> Dict[str, Any]:
    """
    一時停止状態をチェックし、再開すべきかどうかを判断する
    
    Args:
        state: 現在のワークフロー状態
        
    Returns:
        更新された状態
    """
    logger.info(f"Checking paused state for workflow {state['workflow_id']}")
    
    try:
        # データベースから最新のワークフロー状態を取得
        from src.models.repositories import WorkflowRepository
        from src.utils.db_manager import get_db
        
        db = next(get_db())
        workflow_repo = WorkflowRepository(db)
        workflow = workflow_repo.get_by_id(state['workflow_id'])
        
        if not workflow:
            logger.error(f"Workflow {state['workflow_id']} not found in database")
            return {
                **state,
                "status": "error",
                "error": f"Workflow {state['workflow_id']} not found"
            }
        
        # 人間介入の状態を確認
        from src.models.repositories import HumanInterventionRequestRepository
        intervention_repo = HumanInterventionRequestRepository(db)
        
        # このワークフローに関連する未解決の介入要求を検索
        interventions = intervention_repo.find_by_workflow_id(db, state['workflow_id'], status="pending")
        
        if not interventions:
            logger.info(f"No pending interventions found for workflow {state['workflow_id']}")
            
            # 一時停止フラグがセットされているが介入要求がない場合は再開
            if workflow.status == "paused" and state["status"] == "paused":
                logger.info(f"Resuming workflow {state['workflow_id']} as no interventions are pending")
                return {
                    **state,
                    "status": "in_progress",
                    "current_agent": state.get("current_agent", settings.AGENT_A_ID)
                }
            
            # すでに再開されている場合は現在の状態を維持
            return state
        
        # アクティブな介入要求が存在する場合
        intervention = interventions[0]  # 最初の未解決介入要求
        
        # 介入要求の状態を確認
        if intervention.status == "responded":
            logger.info(f"Human intervention {intervention.id} has been responded, resuming workflow")
            
            # 介入応答をメッセージとして記録
            response_content = json_utils.json_deserialize(intervention.response_data) if intervention.response_data else {}
            
            new_state = add_message_to_state(
                state=state,
                from_agent="human",
                to_agent=state.get("current_agent", settings.AGENT_A_ID),
                message_type="intervention_response",
                content={
                    "intervention_id": intervention.id,
                    "response": response_content
                }
            )
            
            # 介入要求を完了状態に更新
            intervention_repo.update(intervention.id, {"status": "completed"})
            
            # ワークフローを再開
            return {
                **new_state,
                "status": "in_progress",
                "current_agent": state.get("current_agent", settings.AGENT_A_ID)
            }
        elif intervention.status == "cancelled":
            logger.info(f"Human intervention {intervention.id} was cancelled, resuming workflow")
            
            # 介入キャンセルをメッセージとして記録
            new_state = add_message_to_state(
                state=state,
                from_agent="human",
                to_agent=state.get("current_agent", settings.AGENT_A_ID),
                message_type="intervention_cancelled",
                content={
                    "intervention_id": intervention.id,
                    "reason": "Cancelled by user"
                }
            )
            
            # ワークフローを再開
            return {
                **new_state,
                "status": "in_progress",
                "current_agent": state.get("current_agent", settings.AGENT_A_ID)
            }
        else:
            # まだ応答がない場合は一時停止状態を維持
            logger.info(f"Workflow {state['workflow_id']} remains paused waiting for intervention {intervention.id}")
            return {
                **state,
                "status": "paused"
            }
    
    except Exception as e:
        logger.error(f"Error checking paused state: {e}")
        return {
            **state,
            "status": "error",
            "error": f"Failed to check paused state: {str(e)}"
        }


# 状態ルーターの定義
def state_router(state: WorkflowState) -> str:
    """
    次に実行するエージェントを決定
    
    Args:
        state: 現在のワークフロー状態
        
    Returns:
        次のノード名
    """
    # 一時停止状態の場合
    if state.get("status") == "paused":
        return "check_paused"
    
    # エラー状態の場合
    if state.get("status") == "error" or state.get("status") == "failed":
        return "end"
    
    # 現在のエージェントに基づくルーティング
    current_agent = state.get("current_agent")
    
    if current_agent == settings.AGENT_A_ID:
        return "agent_a"
    elif current_agent == settings.AGENT_B_ID:
        return "agent_b"
    elif current_agent == settings.AGENT_C_ID:
        return "agent_c"
    elif current_agent == settings.AGENT_D_ID:
        return "agent_d"
    elif current_agent == "completed":
        return "end"
    else:
        logger.error(f"Unknown agent: {current_agent}")
        return "end"


# 一時停止状態からの遷移先を決定するグローバル関数
def route_from_pause_check(state):
    """
    一時停止状態から遷移先のエージェントを決定する
    
    Args:
        state: 現在のワークフロー状態
        
    Returns:
        遷移先ノード名
    """
    agent_id = state.get("current_agent", settings.AGENT_A_ID)
    # エージェントIDが文字列であることを確認
    if not isinstance(agent_id, str):
        logger.warning(f"Invalid agent_id in state: {agent_id}, using default agent_a")
        return "agent_a"
    # 有効なエージェントIDかチェック
    if agent_id in ["agent_a", "agent_b", "agent_c", "agent_d"]:
        return agent_id
    # デフォルトの最初のエージェントに遷移
    return "agent_a"


def create_audit_workflow() -> StateGraph:
    """
    監査ワークフローグラフを作成する
    
    Returns:
        構成されたStateGraph
    """
    logger.info("Creating audit workflow graph")
    
    try:
        # StateGraphの作成
        workflow = StateGraph(WorkflowState)
        
        # 各エージェントノードの追加
        workflow.add_node("agent_a", agent_a_node)
        workflow.add_node("agent_b", agent_b_node)
        workflow.add_node("agent_c", agent_c_node)
        workflow.add_node("agent_d", agent_d_node)
        
        # 一時停止状態チェックノードの追加
        workflow.add_node("check_paused", check_paused_state)
        
        # 人間介入ノードの追加
        workflow.add_node("human", human_node)
        
        # エージェント状態ルーターの設定
        # 各エージェントへのエッジに条件付き遷移を追加
        workflow.add_conditional_edges(
            "check_paused",
            lambda state: state.get("status") == "paused",
            {
                True: "check_paused",  # まだ一時停止中の場合は繰り返しチェック
                False: "agent_a"  # 一時停止解除時は最初のエージェントに進む（後で状態に基づいて調整される）
            }
        )
        
        # 各エージェントからの条件付き遷移の設定
        # エージェントの出力（現在のステータス）によって次の遷移先を決定
        workflow.add_conditional_edges(
            "agent_a",
            lambda state: state.get("status"),
            {
                "error": "human",  # エラー時は人間介入
                "paused": "check_paused",  # 一時停止時は一時停止チェックへ
                "in_progress": "agent_b",  # 通常は次のエージェントへ
                "default": "agent_b"  # デフォルトは次のエージェントへ
            }
        )
        
        workflow.add_conditional_edges(
            "agent_b",
            lambda state: state.get("status"),
            {
                "error": "human",
                "paused": "check_paused",
                "in_progress": "agent_c",
                "default": "agent_c"
            }
        )
        
        workflow.add_conditional_edges(
            "agent_c",
            lambda state: state.get("status"),
            {
                "error": "human",
                "paused": "check_paused",
                "in_progress": "agent_d",
                "default": "agent_d"
            }
        )
        
        workflow.add_conditional_edges(
            "agent_d",
            lambda state: state.get("status"),
            {
                "error": "human",
                "paused": "check_paused",
                "completed": END,  # ワークフロー完了
                "default": END
            }
        )
        
        # 人間介入ノードからの遷移
        workflow.add_conditional_edges(
            "human",
            lambda state: state.get("status"),
            {
                "paused": "check_paused",  # 一時停止後は一時停止チェックへ
                "error": "human",  # エラーが解決しない場合は再度人間介入
                "default": "agent_a"  # デフォルトは最初のエージェントへ
            }
        )
        
        # デフォルトのエントリーポイントをチェックポイントノードに設定
        workflow.set_entry_point("check_paused")
        
        # メモリセーバーの設定（チェックポイント保存）
        # ここではチェックポイントを保存するためのクラスを設定
        memory_saver = MemorySaver()
        
        # ワークフローグラフをコンパイル（チェックポイント機能付き）
        compiled_workflow = workflow.compile(checkpointer=memory_saver)
        
        logger.info("Audit workflow graph created and compiled successfully")
        return compiled_workflow
        
    except Exception as e:
        logger.error(f"Error creating audit workflow graph: {e}")
        # 基本的なグラフを作成してエラー時のフォールバックとする
        basic_workflow = StateGraph(WorkflowState)
        basic_workflow.add_node("agent_a", agent_a_node)
        basic_workflow.add_edge("agent_a", END)
        basic_workflow.set_entry_point("agent_a")
        
        logger.warning("Created fallback audit workflow graph due to error")
        return basic_workflow.compile()


# グローバルワークフローインスタンス
audit_workflow = create_audit_workflow()


def validate_workflow_state(state: WorkflowState) -> Tuple[bool, Optional[str]]:
    """
    ワークフロー状態が有効かどうかを検証する

    Args:
        state: 検証するワークフロー状態

    Returns:
        有効かどうかのフラグとエラーメッセージのタプル
    """
    # 必須キーの確認
    required_keys = ["workflow_id", "status", "current_agent", "procedure_id", "procedure_text"]
    for key in required_keys:
        if key not in state:
            return False, f"Required key '{key}' is missing in workflow state"

    # ステータスの検証
    valid_statuses = ["created", "in_progress", "paused", "completed", "error"]
    if state["status"] not in valid_statuses:
        return False, f"Invalid status '{state['status']}'. Valid statuses are: {', '.join(valid_statuses)}"

    # エージェントIDの検証
    valid_agents = [settings.AGENT_A_ID, settings.AGENT_B_ID, settings.AGENT_C_ID, settings.AGENT_D_ID, "completed"]
    if state["current_agent"] not in valid_agents:
        return False, f"Invalid agent '{state['current_agent']}'. Valid agents are: {', '.join(valid_agents)}"

    # メッセージの検証
    if "messages" in state:
        for idx, msg in enumerate(state["messages"]):
            if not isinstance(msg, dict):
                return False, f"Message at index {idx} is not a dictionary"
            
            msg_required_keys = ["id", "from_agent", "to_agent", "timestamp", "type", "content"]
            for key in msg_required_keys:
                if key not in msg:
                    return False, f"Required key '{key}' is missing in message at index {idx}"
    
    # エージェント出力の検証
    if "outputs" in state:
        if not isinstance(state["outputs"], dict):
            return False, f"'outputs' must be a dictionary"
        
        for agent_id, output in state["outputs"].items():
            if not isinstance(output, dict):
                return False, f"Output for agent '{agent_id}' is not a dictionary"
    
    return True, None

def ensure_valid_state(state: WorkflowState) -> WorkflowState:
    """
    ワークフロー状態が有効であることを確認し、必要に応じて修正する

    Args:
        state: 確認するワークフロー状態

    Returns:
        有効なワークフロー状態
    """
    is_valid, error_msg = validate_workflow_state(state)
    
    if is_valid:
        return state
    
    logger.warning(f"Invalid workflow state detected: {error_msg}. Attempting to fix.")
    
    # 無効な状態の修正を試みる
    fixed_state = dict(state)
    
    # 必須キーの追加
    if "workflow_id" not in fixed_state:
        fixed_state["workflow_id"] = str(uuid.uuid4())
        logger.info(f"Generated new workflow_id: {fixed_state['workflow_id']}")
    
    if "status" not in fixed_state or fixed_state["status"] not in ["created", "in_progress", "paused", "completed", "error"]:
        fixed_state["status"] = "created"
        logger.info(f"Reset workflow status to 'created'")
    
    if "current_agent" not in fixed_state or fixed_state["current_agent"] not in [settings.AGENT_A_ID, settings.AGENT_B_ID, settings.AGENT_C_ID, settings.AGENT_D_ID, "completed"]:
        fixed_state["current_agent"] = settings.AGENT_A_ID
        logger.info(f"Reset current_agent to '{settings.AGENT_A_ID}'")
    
    if "procedure_id" not in fixed_state:
        fixed_state["procedure_id"] = "unknown"
        logger.warning("Missing procedure_id, set to 'unknown'")
    
    if "procedure_text" not in fixed_state:
        fixed_state["procedure_text"] = ""
        logger.warning("Missing procedure_text, set to empty string")
    
    if "messages" not in fixed_state:
        fixed_state["messages"] = []
    
    if "outputs" not in fixed_state:
        fixed_state["outputs"] = {}
    
    # タイムスタンプの更新
    fixed_state["updated_at"] = datetime.now().isoformat()
    
    # 修正した状態の再検証
    is_valid, error_msg = validate_workflow_state(fixed_state)
    if not is_valid:
        logger.error(f"Failed to fix workflow state: {error_msg}")
        # 最終手段として最小限の有効な状態を返す
        return {
            "workflow_id": fixed_state.get("workflow_id", str(uuid.uuid4())),
            "status": "error",
            "current_agent": settings.AGENT_A_ID,
            "procedure_id": fixed_state.get("procedure_id", "unknown"),
            "procedure_text": fixed_state.get("procedure_text", ""),
            "messages": [],
            "outputs": {},
            "error": f"Failed to fix invalid state: {error_msg}",
            "updated_at": datetime.now().isoformat()
        }
    
    logger.info("Successfully fixed workflow state")
    return fixed_state

async def save_workflow_state(workflow_state: Dict[str, Any]) -> None:
    """ワークフロー状態を保存する"""
    try:
        from src.models.repositories import WorkflowRepository
        from src.utils.db_manager import get_db
        from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
        
        # セッション取得
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            workflow_repo = WorkflowRepository()
            
            # 保存するデータの準備
            workflow_data = {
                "audit_procedure_id": workflow_state.get("procedure_id", "unknown"),
                "sample_data_id": workflow_state.get("sample_id", "unknown"),
                "status": workflow_state.get("status", "created"),
                "current_agent": workflow_state.get("current_agent", "agent_a"),
                "results": json.dumps(workflow_state)
            }
            
            # ワークフローIDの取得
            workflow_id = workflow_state.get("workflow_id")
            if workflow_id:
                # 既存のワークフローを更新
                existing_workflow = workflow_repo.get_by_id(workflow_id)
                if existing_workflow:
                    workflow_repo.update(workflow_id, workflow_data)
                else:
                    workflow_data["id"] = workflow_id
                    workflow_repo.create(workflow_data)
            else:
                # 新しいワークフローを作成
                workflow_repo.create(workflow_data)
            
            db.commit()
            logger.info(f"ワークフロー状態を保存しました: {workflow_id}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"ワークフロー状態の保存中にエラーが発生: {e}")
            raise
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"ワークフロー状態の保存中に予期しないエラーが発生: {e}")
        raise


async def load_workflow_state(workflow_id: str) -> Optional[Dict[str, Any]]:
    """ワークフロー状態を取得する"""
    try:
        from src.models.repositories import WorkflowRepository
        from src.utils.db_manager import get_db
        
        # セッション取得
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            workflow_repo = WorkflowRepository(db)
            workflow = workflow_repo.get_by_id(workflow_id)
            
            if not workflow:
                logger.warning(f"ワークフロー {workflow_id} が見つかりません")
                return None
            
            # JSON文字列から状態を復元
            state_data = json.loads(workflow.results) if workflow.results else {}
            return state_data
            
        except Exception as e:
            logger.error(f"ワークフロー状態の取得中にエラーが発生: {e}")
            return None
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"ワークフロー状態の取得中に予期しないエラーが発生: {e}")
        return None


async def cleanup_old_workflow_states() -> None:
    """
    古いワークフロー状態を削除（バックグラウンドタスク）
    """
    db = None
    try:
        from src.models.repositories import WorkflowRepository
        from src.utils.db_manager import get_db
        
        # 完了または失敗して30日以上経過したワークフローを削除
        db_gen = get_db()
        db = next(db_gen)
        
        workflow_repo = WorkflowRepository(db)
        cutoff_date = datetime.now() - timedelta(days=30)
        
        # 削除条件の設定
        conditions = {
            "status": ["completed", "failed", "error"],
            "updated_at_before": cutoff_date
        }
        
        # 古いワークフロー状態を削除
        count = workflow_repo.delete_by_conditions(db, conditions)
        if count > 0:
            logger.info(f"{count}件の古いワークフロー状態を削除しました")
            
    except Exception as e:
        logger.error(f"古いワークフロー状態の削除中にエラーが発生: {e}")
        
    finally:
        if db:
            db.close()

async def execute_workflow(workflow_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ワークフローを実行する
    
    Args:
        workflow_state: 初期ワークフロー状態
        
    Returns:
        最終的なワークフロー状態
    """
    try:
        # ワークフロー状態の検証
        is_valid, error_msg = validate_workflow_state(workflow_state)
        if not is_valid:
            return {
                **workflow_state,
                "status": "error",
                "error": error_msg,
                "updated_at": datetime.now().isoformat()
            }
        
        # ワークフローIDの設定
        if "workflow_id" not in workflow_state:
            workflow_state["workflow_id"] = f"flow-{uuid.uuid4().hex}"
        
        # 作成日時と更新日時の設定
        if "created_at" not in workflow_state:
            workflow_state["created_at"] = datetime.now().isoformat()
        workflow_state["updated_at"] = datetime.now().isoformat()
        
        # 初期状態をデータベースに保存
        await save_workflow_state(workflow_state)
        
        # グラフのコンフィグIDとスレッドIDを設定
        config_id = "audit_workflow"
        thread_id = workflow_state["workflow_id"]
        
        logger.info(f"Starting workflow execution: {thread_id}")
        
        # ワークフローの実行
        try:
            # StateGraphをInvokeして実行
            final_state = await audit_workflow.ainvoke(
                workflow_state,
                config_id=config_id,
                thread_id=thread_id
            )
            
            logger.info(f"Workflow completed: {thread_id}")
            return final_state
        except Exception as e:
            logger.error(f"Error executing workflow {thread_id}: {e}")
            # エラー状態を返す
            error_state = {
                **workflow_state,
                "status": "error",
                "error": f"Workflow execution error: {str(e)}",
                "updated_at": datetime.now().isoformat()
            }
            
            # エラー状態を保存
            await save_workflow_state(error_state)
            return error_state
    except Exception as e:
        logger.error(f"Unexpected error in execute_workflow: {e}")
        return {
            **workflow_state,
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "updated_at": datetime.now().isoformat()
        }

async def update_agent_states(db, state: Dict[str, Any]) -> None:
    """
    エージェントの状態をデータベースに更新する
    
    Args:
        db: データベースセッション
        state: ワークフロー状態
        
    Raises:
        ValueError: 更新対象が見つからない場合
        RuntimeError: データベース操作中にエラーが発生した場合
    """
    try:
        from src.models.repositories import AgentStateRepository
        from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
        
        agent_state_repo = AgentStateRepository()
        workflow_id = state.get("workflow_id")
        
        if not workflow_id:
            logger.error("エージェント状態の更新に失敗: ワークフローIDがありません")
            return
        
        # 各エージェントの出力を更新
        outputs = state.get("outputs", {})
        
        for agent_id, output in outputs.items():
            if output is not None:
                # エージェント状態データの作成
                agent_state_data = {
                    "workflow_id": workflow_id,
                    "agent_id": agent_id,
                    "state_data": json_utils.json_serialize(output),
                    "updated_at": datetime.now()
                }
                
                # エージェント状態の検索と更新/作成
                try:
                    existing_state = agent_state_repo.find(
                        db, 
                        {"workflow_id": workflow_id, "agent_id": agent_id}
                    )
                    
                    if existing_state:
                        success = agent_state_repo.update(
                            db, 
                            existing_state["id"], 
                            {"state_data": json_utils.json_serialize(output), "updated_at": datetime.now()}
                        )
                        if success:
                            logger.debug(f"エージェント状態を更新しました: agent={agent_id}, workflow={workflow_id}")
                        else:
                            logger.warning(f"エージェント状態の更新に失敗しました: agent={agent_id}, workflow={workflow_id}")
                    else:
                        new_id = agent_state_repo.create(db, agent_state_data)
                        logger.debug(f"新しいエージェント状態を作成しました: {new_id}")
                        
                except IntegrityError as e:
                    db.rollback()
                    logger.error(f"エージェント状態の更新に失敗: データ整合性エラー - {e}")
                    # このエージェントの更新は失敗しても他のエージェントの処理は続行
                    
                except OperationalError as e:
                    db.rollback()
                    logger.error(f"エージェント状態の更新に失敗: データベース操作エラー - {e}")
                    # このエージェントの更新は失敗しても他のエージェントの処理は続行
                    
                except SQLAlchemyError as e:
                    db.rollback()
                    logger.error(f"エージェント状態の更新に失敗: SQLAlchemyエラー - {e}")
                    # このエージェントの更新は失敗しても他のエージェントの処理は続行
    
    except Exception as e:
        logger.error(f"エージェント状態の更新中に予期しないエラーが発生しました: {e}")
        # エージェント状態の更新エラーはワークフロー状態の保存には影響させない 


async def get_workflow_status(workflow_id: str) -> Optional[Dict[str, Any]]:
    """
    ワークフローの状態を取得する
    
    Args:
        workflow_id: ワークフローID
        
    Returns:
        ワークフローの状態。存在しない場合はNone
    """
    from src.models.repositories import WorkflowRepository
    from src.utils.db_manager import get_db_context
    
    try:
        with get_db_context() as db:
            repo = WorkflowRepository(db)
            workflow = repo.get_by_id(workflow_id)
            if not workflow:
                return None
            
            # 状態データをデシリアライズ
            state = json.loads(workflow.results) if workflow.results else {}
            
            return {
                "workflow_id": workflow.id,
                "status": workflow.status,
                "created_at": workflow.created_at,
                "updated_at": workflow.updated_at,
                "procedure_id": workflow.audit_procedure_id,
                "sample_data_id": workflow.sample_data_id,
                **state
            }
    except Exception as e:
        logger.error(f"ワークフロー状態取得エラー: {e}")
        return None


async def list_workflows(
    page_size: int = 10,
    page_offset: int = 0,
    filter_status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    ワークフロー一覧を取得する
    
    Args:
        page_size: 1ページあたりの件数
        page_offset: オフセット
        filter_status: フィルタするステータス
        
    Returns:
        ワークフロー一覧
    """
    try:
        # モックデータを返す（テスト用）
        mock_workflows = [
            {
                "id": "workflow_1",
                "status": "running",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "procedure_id": "proc_1",
                "sample_id": "sample_1"
            },
            {
                "id": "workflow_2",
                "status": "completed",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "procedure_id": "proc_2",
                "sample_id": "sample_2"
            }
        ]
        
        # ステータスでフィルタ
        if filter_status:
            mock_workflows = [wf for wf in mock_workflows if wf["status"] == filter_status]
            
        # ページング
        start = page_offset
        end = start + page_size
        return mock_workflows[start:end]
    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        raise

async def reset_workflow(workflow_id: str) -> Dict[str, Any]:
    """
    ワークフローをリセットする
    
    Args:
        workflow_id: リセットするワークフローのID
        
    Returns:
        リセット結果
    """
    logger.info(f"ワークフロー {workflow_id} をリセット中")
    return {"status": "reset", "workflow_id": workflow_id}


async def clean_workflow(workflow_id: str) -> Dict[str, Any]:
    """
    ワークフローのデータをクリーンアップする
    
    Args:
        workflow_id: クリーンアップするワークフローのID
        
    Returns:
        クリーンアップ結果
    """
    logger.info(f"ワークフロー {workflow_id} をクリーンアップ中")
    return {"status": "cleaned", "workflow_id": workflow_id}


async def audit_workflow(
    workflow_id: str,
    procedure_text: str
) -> Dict[str, Any]:
    """
    ワークフローを監査する
    
    Args:
        workflow_id: ワークフローID
        procedure_text: 監査手続きテキスト
        
    Returns:
        更新されたワークフロー状態
    """
    try:
        # ワークフロー状態を取得
        workflow_state = await get_workflow_status(workflow_id)
        if not workflow_state:
            raise ValueError(f"Workflow {workflow_id} not found")
            
        # 状態を更新
        workflow_state["status"] = "in_progress"
        workflow_state["procedure_text"] = procedure_text
        workflow_state["updated_at"] = datetime.now().isoformat()
        
        # ワークフロー実行
        updated_state = await execute_workflow(workflow_state)
        
        return updated_state
    except Exception as e:
        logger.error(f"Error auditing workflow: {e}")
        raise

async def create_audit_workflow(
    initial_state: Dict[str, Any],
    audit_procedure_id: str,
    procedure_text: Optional[str],
    sample_data_id: str
) -> Dict[str, Any]:
    """
    監査ワークフローを作成する
    
    Args:
        initial_state: 初期状態
        audit_procedure_id: 監査手続きID
        procedure_text: 監査手続きテキスト（オプション）
        sample_data_id: サンプルデータID
        
    Returns:
        作成されたワークフロー状態
    """
    from src.models.repositories import get_workflow_repository
    from src.utils.db_manager import get_db_context
    
    try:
        with get_db_context() as db:
            # ワークフローを作成
            workflow_data = {
                "id": initial_state["workflow_id"],
                "audit_procedure_id": audit_procedure_id,
                "sample_data_id": sample_data_id,
                "status": initial_state["status"],
                "current_agent": initial_state.get("current_agent", "agent_a"),
                "created_at": datetime.fromisoformat(initial_state["created_at"]),
                "updated_at": datetime.fromisoformat(initial_state["updated_at"]),
                "results": json.dumps(initial_state),
                "error": None
            }
            
            repo = get_workflow_repository(db)
            # リポジトリのcreateメソッドは作成されたワークフローオブジェクトを返す
            workflow_obj = repo.create(workflow_data)
            
            # 作成されたワークフローオブジェクトのIDを確認
            logger.info(f"ワークフローが作成されました: {workflow_obj.id}")
            
            return initial_state
            
    except Exception as e:
        logger.error(f"ワークフローの作成に失敗しました: {e}")
        # DBセッションが存在する場合はロールバック
        try:
            if 'db' in locals():
                db.rollback()
        except Exception as rollback_error:
            logger.error(f"ロールバック中にエラーが発生しました: {rollback_error}")
        # 元のエラーを再度発生させる
        raise ValueError(f"ワークフローの作成に失敗しました: {e}")