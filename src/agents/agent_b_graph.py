#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
エージェントBのLangGraphベース状態遷移グラフ

このモジュールでは、エージェントBの問題解決プロセスを
LangGraphの状態遷移グラフとして実装しています。
このグラフは以下のノードで構成されています：
- 問題分類：監査の問題タイプを特定し必要な情報を決定
- 情報収集：必要な情報を集め、適切なツールを選択
- 解決策生成：収集した情報に基づいて解決策を生成
- 解決策評価：生成された解決策の品質を評価

また、情報が不足している場合はチェックポイントを作成し、
追加情報が提供された後に処理を再開する機能も含まれています。
"""

import asyncio
import uuid
import json
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, TypedDict, Union, cast, Callable
from pydantic import BaseModel, Field

from loguru import logger
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver

# 既存のツールレジストリをインポート
from src.tools.tool_registry import registry as tool_registry
# 基本的なエージェント機能をインポート
from src.core.agent_base import AgentState


class AgentBGraphState(TypedDict, total=False):
    """エージェントB状態遷移グラフの状態型定義"""
    # 基本情報
    workflow_id: str
    procedure_id: str
    sample_id: str
    sample_path: Optional[str]
    
    # 状態管理
    status: str  # in_progress, waiting_for_info, error, completed
    current_step: str  # 現在のステップ（ノード）
    
    # 問題解決プロセス関連
    problem_type: Optional[str]  # 問題の種類
    required_info: List[str]  # 必要な情報のリスト
    collected_info: Dict[str, Any]  # 収集された情報
    
    # ツール関連
    selected_tools: List[str]  # 選択されたツール
    tool_results: List[Dict[str, Any]]  # ツール実行結果
    
    # 解決策関連
    solution: Optional[Dict[str, Any]]  # 生成された解決策
    evaluation: Optional[Dict[str, Any]]  # 解決策の評価
    
    # チェックポイント管理
    checkpoints: List[Dict[str, Any]]  # チェックポイントのリスト
    
    # 時間情報
    created_at: str
    updated_at: str
    
    # エラー情報
    error: Optional[str]


def with_error_handling(func: Callable):
    """
    ノード関数のエラーハンドリングを行うデコレータ
    
    Args:
        func: 元のノード関数
        
    Returns:
        エラーハンドリングを追加した関数
    """
    async def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return await func(state)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            new_state = state.copy()
            new_state["status"] = "error"
            new_state["error"] = f"{func.__name__} error: {str(e)}"
            new_state["updated_at"] = datetime.now().isoformat()
            return new_state
    
    return wrapper


@with_error_handling
async def problem_classification_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    問題分類ノード: 監査の問題タイプを特定し、必要な情報を決定する
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state['workflow_id']}] 問題分類ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["current_step"] = "problem_classification"
    new_state["updated_at"] = datetime.now().isoformat()
    
    # 監査手続きと既存データの分析
    procedure_id = state.get("procedure_id")
    procedure_text = state.get("procedure_text", "")
    test_plan = state.get("test_plan", {})
    
    if not procedure_id or not test_plan:
        logger.warning(f"[{state['workflow_id']}] 監査手続きまたはテスト計画がありません")
        new_state["status"] = "error"
        new_state["error"] = "監査手続きまたはテスト計画が不足しています"
        return new_state
    
    # テスト項目から問題タイプを特定
    # 実際の実装ではLLMを使用して問題タイプを特定
    test_items = test_plan.get("test_items", [])
    risk_types = [item.get("risk_addressed", "") for item in test_items if "risk_addressed" in item]
    
    # 問題タイプの決定（実際のLLM呼び出しをシミュレート）
    problem_type = "data_consistency_check"  # デフォルト設定
    if any("不一致" in risk for risk in risk_types):
        problem_type = "data_inconsistency"
    elif any("未承認" in risk for risk in risk_types):
        problem_type = "approval_verification"
    elif any("上限" in risk for risk in risk_types):
        problem_type = "threshold_validation"
    
    # 必要な情報を特定
    required_info = ["base_data"]
    if problem_type == "data_inconsistency":
        required_info.extend(["comparison_data", "reconciliation_rules"])
    elif problem_type == "approval_verification":
        required_info.extend(["approval_history", "authorization_matrix"])
    elif problem_type == "threshold_validation":
        required_info.extend(["threshold_limits", "transaction_history"])
    
    # 結果を状態に反映
    new_state["problem_type"] = problem_type
    new_state["required_info"] = required_info
    new_state["current_step"] = "information_gathering"
    
    logger.info(f"[{state['workflow_id']}] 問題分類完了: {problem_type}")
    return new_state


@with_error_handling
async def information_gathering_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    情報収集ノード: 必要な情報を集め、適切なツールを選択する
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state['workflow_id']}] 情報収集ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["current_step"] = "information_gathering"
    new_state["updated_at"] = datetime.now().isoformat()
    
    # 情報が不足しているかをチェック
    required_info = state.get("required_info", [])
    collected_info = state.get("collected_info", {})
    
    # 不足している情報を特定
    missing_info = [info for info in required_info if info not in collected_info]
    
    # 情報が不足している場合は情報不足ノードへリダイレクト
    if missing_info and new_state.get("status") != "resumed_from_checkpoint":
        logger.warning(f"[{state['workflow_id']}] 情報不足を検出: {missing_info}")
        new_state["missing_info"] = missing_info
        new_state["redirect_to"] = "handle_insufficient_info"
        return new_state
    
    # 問題タイプに基づいて適切なツールを選択
    problem_type = state.get("problem_type", "")
    selected_tools = []
    
    if problem_type == "data_inconsistency":
        selected_tools.append("data_comparison_tool")
    elif problem_type == "approval_verification":
        selected_tools.append("document_analyzer")
    elif problem_type == "threshold_validation":
        selected_tools.append("data_validation_tool")
    
    # 基本的なデータ分析ツールは常に含める
    if "excel_analyzer" not in selected_tools:
        selected_tools.append("excel_analyzer")
    
    # 利用可能なツールをチェック
    available_tools = tool_registry.list_available_tools()
    selected_tools = [tool for tool in selected_tools if tool in available_tools]
    
    # 結果を状態に反映
    new_state["selected_tools"] = selected_tools
    if "collected_info" not in new_state:
        new_state["collected_info"] = {}
    
    # 基本データを取得（実際の実装ではサンプルデータから取得）
    if "base_data" not in new_state["collected_info"]:
        new_state["collected_info"]["base_data"] = {
            "status": "collected",
            "data": {"sample_data": f"Sample data for {new_state.get('sample_id', 'unknown')}"}
        }
    
    # 次のステップへ進む
    new_state["current_step"] = "solution_generation"
    
    logger.info(f"[{state['workflow_id']}] 情報収集完了: ツール={selected_tools}")
    return new_state


@with_error_handling
async def solution_generation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    解決策生成ノード: 収集した情報に基づいて解決策を生成する
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state['workflow_id']}] 解決策生成ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["current_step"] = "solution_generation"
    new_state["updated_at"] = datetime.now().isoformat()
    
    # 必要な情報が揃っているか確認
    required_info = state.get("required_info", [])
    collected_info = state.get("collected_info", {})
    
    if not all(info in collected_info for info in required_info):
        missing = [info for info in required_info if info not in collected_info]
        logger.warning(f"[{state['workflow_id']}] 解決策生成に必要な情報が不足: {missing}")
        new_state["missing_info"] = missing
        new_state["redirect_to"] = "handle_insufficient_info"
        return new_state
    
    # テスト計画から解決策のテンプレートを取得
    test_plan = state.get("test_plan", {})
    test_items = test_plan.get("test_items", [])
    
    # 問題タイプに基づいて解決策を生成
    problem_type = state.get("problem_type", "")
    solution = {
        "description": f"{problem_type}に対する監査テストを実施",
        "actions": [],
        "findings": [],
        "recommendations": [],
        "confidence": 0.8,
        "timestamp": datetime.now().isoformat()
    }
    
    # テスト項目から解決策のアクションを生成
    for item in test_items:
        solution["actions"].append({
            "test_id": item.get("id", str(uuid.uuid4())),
            "name": item.get("name", "未定義テスト"),
            "description": item.get("description", ""),
            "expected_results": item.get("expected_results", ""),
        })
    
    # 結果を状態に反映
    new_state["solution"] = solution
    new_state["current_step"] = "solution_evaluation"
    
    logger.info(f"[{state['workflow_id']}] 解決策生成完了")
    return new_state


@with_error_handling
async def solution_evaluation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    解決策評価ノード: 生成された解決策の品質を評価する
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state['workflow_id']}] 解決策評価ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["current_step"] = "solution_evaluation"
    new_state["updated_at"] = datetime.now().isoformat()
    
    # 解決策が存在するか確認
    solution = state.get("solution")
    if not solution:
        logger.warning(f"[{state['workflow_id']}] 評価する解決策がありません")
        new_state["status"] = "error"
        new_state["error"] = "評価する解決策がありません"
        return new_state
    
    # 解決策を評価（実際の実装ではLLMを使用）
    confidence = solution.get("confidence", 0.0)
    actions_count = len(solution.get("actions", []))
    
    # 評価結果を生成
    evaluation = {
        "quality": "high" if confidence > 0.7 else "medium" if confidence > 0.5 else "low",
        "coverage": min(1.0, actions_count / max(1, len(state.get("test_plan", {}).get("test_items", [])) * 0.8)),
        "risks": [],
        "recommendation": "実施を推奨" if confidence > 0.6 else "追加検証が必要",
        "timestamp": datetime.now().isoformat()
    }
    
    # テスト項目のカバレッジが低い場合はリスクを追加
    if evaluation["coverage"] < 0.8:
        evaluation["risks"].append("一部のテスト項目がカバーされていません")
    
    # 結果を状態に反映
    new_state["evaluation"] = evaluation
    new_state["status"] = "completed"
    new_state["current_step"] = "completed"
    
    logger.info(f"[{state['workflow_id']}] 解決策評価完了: 品質={evaluation['quality']}")
    return new_state


@with_error_handling
async def handle_insufficient_info_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    情報不足処理ノード: 情報が不足している場合にチェックポイントを作成し、情報要求を行う
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state['workflow_id']}] 情報不足処理ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["updated_at"] = datetime.now().isoformat()
    
    # 不足している情報を取得
    missing_info = state.get("missing_info", [])
    if not missing_info:
        # 不足情報が指定されていない場合は元のステップに戻る
        logger.warning(f"[{state['workflow_id']}] 不足情報が指定されていません")
        new_state["current_step"] = state.get("current_step", "problem_classification")
        return new_state
    
    # チェックポイントを作成
    checkpoint_id = f"cp-{uuid.uuid4().hex[:8]}"
    checkpoint = {
        "id": checkpoint_id,
        "step": state.get("current_step", "unknown"),
        "timestamp": datetime.now().isoformat(),
        "missing_info": missing_info,
        "return_to": state.get("redirect_to", state.get("current_step", "problem_classification"))
    }
    
    # チェックポイントを状態に追加
    if "checkpoints" not in new_state:
        new_state["checkpoints"] = []
    new_state["checkpoints"].append(checkpoint)
    
    # 待機状態に設定
    new_state["status"] = "waiting_for_info"
    new_state["current_checkpoint_id"] = checkpoint_id
    
    logger.info(f"[{state['workflow_id']}] 情報不足処理完了: チェックポイント作成 {checkpoint_id}")
    return new_state


@with_error_handling
async def resume_from_checkpoint_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    チェックポイント復元ノード: チェックポイントから処理を再開する
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state['workflow_id']}] チェックポイント復元ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["updated_at"] = datetime.now().isoformat()
    
    # チェックポイントIDを取得
    checkpoint_id = state.get("restore_checkpoint_id")
    if not checkpoint_id:
        logger.warning(f"[{state['workflow_id']}] 復元するチェックポイントIDが指定されていません")
        new_state["status"] = "error"
        new_state["error"] = "復元するチェックポイントIDが指定されていません"
        return new_state
    
    # チェックポイントを検索
    checkpoints = state.get("checkpoints", [])
    checkpoint = None
    for cp in checkpoints:
        if cp.get("id") == checkpoint_id:
            checkpoint = cp
            break
    
    if not checkpoint:
        logger.warning(f"[{state['workflow_id']}] チェックポイント {checkpoint_id} が見つかりません")
        new_state["status"] = "error"
        new_state["error"] = f"チェックポイント {checkpoint_id} が見つかりません"
        return new_state
    
    # 復元するステップを取得
    return_to = checkpoint.get("return_to", "problem_classification")
    
    # 状態を更新
    new_state["status"] = "resumed_from_checkpoint"
    new_state["current_step"] = return_to
    new_state["restored_from_checkpoint"] = checkpoint_id
    
    logger.info(f"[{state['workflow_id']}] チェックポイント {checkpoint_id} から復元、ステップ {return_to} へ")
    return new_state


def create_agent_b_graph() -> StateGraph:
    """
    エージェントBの状態遷移グラフを作成
    
    Returns:
        StateGraph: 状態遷移グラフ
    """
    logger.info("エージェントB状態遷移グラフを作成中...")
    
    # 初期状態の作成
    def create_initial_state() -> Dict[str, Any]:
        return {
            "workflow_id": str(uuid.uuid4()),
            "status": "in_progress",
            "current_step": "problem_classification",
            "required_info": [],
            "collected_info": {},
            "selected_tools": [],
            "tool_results": [],
            "checkpoints": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    
    try:
        # グラフの作成
        workflow = StateGraph(AgentBGraphState)
        
        # ノードの追加
        workflow.add_node("problem_classification", problem_classification_node)
        workflow.add_node("information_gathering", information_gathering_node)
        workflow.add_node("solution_generation", solution_generation_node)
        workflow.add_node("solution_evaluation", solution_evaluation_node)
        workflow.add_node("handle_insufficient_info", handle_insufficient_info_node)
        workflow.add_node("resume_from_checkpoint", resume_from_checkpoint_node)
        
        # 初期状態を問題分類ノードに設定
        workflow.set_entry_point("problem_classification")
        
        # エッジの追加 - 各ノードから次のノードへの条件付き遷移を設定
        workflow.add_edge("problem_classification", "information_gathering")
        workflow.add_edge("problem_classification", "handle_insufficient_info")
        workflow.add_edge("information_gathering", "solution_generation")
        workflow.add_edge("information_gathering", "handle_insufficient_info")
        workflow.add_edge("solution_generation", "solution_evaluation")
        workflow.add_edge("solution_generation", "handle_insufficient_info")
        workflow.add_edge("solution_evaluation", END)
        workflow.add_edge("handle_insufficient_info", END)
        workflow.add_edge("resume_from_checkpoint", "problem_classification")
        workflow.add_edge("resume_from_checkpoint", "information_gathering")
        workflow.add_edge("resume_from_checkpoint", "solution_generation")
        
        # 条件付きルーターを設定
        workflow.set_next("problem_classification", lambda x: "handle_insufficient_info" if x.get("missing_info") else "information_gathering")
        workflow.set_next("information_gathering", lambda x: "handle_insufficient_info" if x.get("missing_info") else "solution_generation")
        workflow.set_next("solution_generation", lambda x: "handle_insufficient_info" if x.get("missing_info") else "solution_evaluation")
        workflow.set_next("resume_from_checkpoint", lambda x: x.get("current_step", "problem_classification"))
        
        # グラフをコンパイル
        compiled_workflow = workflow.compile()
        logger.info("エージェントB状態遷移グラフが正常に作成されました")
        return compiled_workflow
        
    except Exception as e:
        logger.error(f"エージェントB状態遷移グラフの作成エラー: {e}")
        try:
            # シンプルなフォールバックグラフを作成
            fallback = StateGraph(AgentBGraphState)
            
            # フォールバックノードを追加
            fallback.add_node("fallback_node", async_to_sync(fallback_node))
            
            # 初期状態をフォールバックノードに設定
            fallback.set_entry_point("fallback_node")
            
            # フォールバックからENDへのエッジ
            fallback.add_edge("fallback_node", END)
            
            # コンパイル
            compiled_fallback = fallback.compile()
            return compiled_fallback
            
        except Exception as fallback_error:
            logger.critical(f"フォールバックグラフの作成も失敗: {fallback_error}")
            try:
                # 最後の手段：完全に空のグラフを作成
                empty = StateGraph(dict)  # 汎用dictタイプを使用
                empty.add_node("empty_node", lambda x: x)
                empty.set_entry_point("empty_node")
                empty.add_edge("empty_node", END)
                compiled_empty = empty.compile()
                return compiled_empty
            except Exception as empty_error:
                logger.critical(f"空のグラフの作成も失敗: {empty_error}")
                # どうしても失敗する場合はNoneを返す
                return None

# フォールバック用のノード
async def fallback_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """フォールバック用の単純なノード"""
    new_state = state.copy() if state else {}
    new_state["status"] = "completed"
    new_state["error"] = "フォールバックモードで実行されました"
    new_state["solution"] = {
        "summary": "エラーが発生したため、詳細な分析はできませんでした。",
        "recommendation": "管理者に連絡してください。"
    }
    new_state["updated_at"] = datetime.now().isoformat()
    return new_state

def async_to_sync(async_func):
    """非同期関数を同期関数に変換するヘルパー関数"""
    def wrapper(state):
        try:
            return asyncio.run(async_func(state))
        except Exception as e:
            logger.error(f"Async-to-sync error: {e}")
            return fallback_sync_node(state)
    return wrapper

def fallback_sync_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """同期的なフォールバックノード"""
    new_state = state.copy() if state else {}
    new_state["status"] = "error"
    new_state["error"] = "非同期実行中にエラーが発生しました"
    return new_state

# グローバル変数として保持するためのインスタンス
_agent_b_graph = None

def get_agent_b_graph() -> Optional[StateGraph]:
    """
    エージェントBのグラフインスタンスを取得（シングルトンパターン）
    
    Returns:
        StateGraph: エージェントBの状態遷移グラフ、作成失敗時はNone
    """
    global _agent_b_graph
    # テスト環境では常に新しいインスタンスを作成する
    if "pytest" in sys.modules:
        return create_agent_b_graph()
    # 通常の実行では、シングルトンパターンを使用
    if _agent_b_graph is None:
        _agent_b_graph = create_agent_b_graph()
    return _agent_b_graph 