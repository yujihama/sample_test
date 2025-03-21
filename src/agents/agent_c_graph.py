#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
エージェントCのLangGraphベース状態遷移グラフ

このモジュールでは、エージェントCの監査結果評価・要約プロセスを
LangGraphの状態遷移グラフとして実装しています。
このグラフは以下のノードで構成されています：
- テスト結果分析：実行されたテストの結果を分析
- 遵守評価：テスト結果に基づいて規制遵守状況を評価
- 問題分類：特定された問題を分類し重要度を判定
- 結果要約：全体の結果を要約し報告書に含める推奨事項を提案

また、情報が不足している場合はチェックポイントを作成し、
追加情報が提供された後に処理を再開する機能も含まれています。
"""

import asyncio
import uuid
import json
import sys
from src.utils import json_utils
from datetime import datetime
from typing import Dict, Any, List, Optional, TypedDict, Union, cast, Callable
from pydantic import BaseModel, Field

from loguru import logger
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver

# 基本的なエージェント機能をインポート
from src.core.agent_base import AgentState
from src.utils.llm_utils import LLMFactory, PromptManager


class AgentCGraphState(TypedDict, total=False):
    """エージェントC状態遷移グラフの状態型定義"""
    # 基本情報
    workflow_id: str
    test_results_id: str
    procedure_id: Optional[str]
    
    # 状態管理
    status: str  # in_progress, waiting_for_info, error, completed
    current_step: str  # 現在のステップ（ノード）
    
    # テスト結果関連
    test_results: Optional[Dict[str, Any]]  # 実行されたテスト結果
    result_analysis: Optional[Dict[str, Any]]  # テスト結果の分析
    required_info: List[str]  # 必要な情報のリスト
    
    # 評価関連
    compliance_evaluation: Optional[Dict[str, Any]]  # 規制遵守の評価
    issue_classification: Optional[Dict[str, Any]]  # 問題の分類と重要度
    
    # 出力関連
    summary: Optional[Dict[str, Any]]  # 結果の要約
    
    # チェックポイント管理
    checkpoints: List[Dict[str, Any]]  # チェックポイントのリスト
    
    # 時間情報
    created_at: str
    updated_at: str
    
    # 収集済み情報
    collected_info: Dict[str, Any]  # 収集された情報
    
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
async def test_results_analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    テスト結果分析ノード: 実行されたテスト結果を分析する
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state.get('workflow_id', 'unknown')}] テスト結果分析ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["current_step"] = "test_results_analysis"
    new_state["updated_at"] = datetime.now().isoformat()
    
    # テスト結果の検証
    test_results = state.get("test_results")
    if not test_results:
        logger.warning(f"[{state.get('workflow_id', 'unknown')}] テスト結果がありません")
        new_state["status"] = "error"
        new_state["error"] = "テスト結果が不足しています"
        return new_state
    
    # LLMを使用してテスト結果を分析
    try:
        llm = LLMFactory.create_llm()
        
        # テスト結果分析プロンプトの作成
        prompt_template = PromptManager.get_prompt("test_results_analysis")
        prompt = prompt_template.format(test_results=json_utils.json_serialize(test_results))
        
        # LLM呼び出し
        response = await llm.apredict(prompt)
        
        # レスポンスをパース
        try:
            analysis = json_utils.json_deserialize(response)
        except json.JSONDecodeError:
            logger.warning("JSON解析エラー、フォールバックとして単純な構造を使用")
            analysis = {
                "total_tests": len(test_results.get("tests", [])),
                "passed_tests": sum(1 for test in test_results.get("tests", []) if test.get("status") == "passed"),
                "failed_tests": sum(1 for test in test_results.get("tests", []) if test.get("status") == "failed"),
                "key_findings": ["結果を正しく分析できませんでした"],
                "data_quality_issues": []
            }
        
        # 結果を状態に反映
        new_state["result_analysis"] = analysis
        
        # 規制遵守評価に必要な追加情報の特定
        required_info = ["test_results"]
        if analysis.get("requires_regulation_details", False):
            required_info.append("regulation_details")
        
        new_state["required_info"] = required_info
        new_state["current_step"] = "compliance_evaluation"
        
        logger.info(f"[{state.get('workflow_id', 'unknown')}] テスト結果分析完了")
        return new_state
        
    except Exception as e:
        logger.error(f"テスト結果分析中にエラー: {e}")
        new_state["status"] = "error"
        new_state["error"] = f"テスト結果分析エラー: {str(e)}"
        return new_state


@with_error_handling
async def compliance_evaluation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    遵守評価ノード: テスト結果に基づいて規制遵守状況を評価する
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state.get('workflow_id', 'unknown')}] 遵守評価ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["current_step"] = "compliance_evaluation"
    new_state["updated_at"] = datetime.now().isoformat()
    
    # 情報が不足しているかをチェック
    required_info = state.get("required_info", [])
    collected_info = state.get("collected_info", {})
    
    # 不足している情報を特定
    missing_info = [info for info in required_info if info not in collected_info]
    
    # 情報が不足している場合は情報不足ノードへリダイレクト
    if missing_info and new_state.get("status") != "resumed_from_checkpoint":
        logger.warning(f"[{state.get('workflow_id', 'unknown')}] 情報不足を検出: {missing_info}")
        new_state["missing_info"] = missing_info
        new_state["redirect_to"] = "handle_insufficient_info"
        return new_state
    
    # テスト結果分析の検証
    result_analysis = state.get("result_analysis")
    if not result_analysis:
        logger.warning(f"[{state.get('workflow_id', 'unknown')}] テスト結果分析がありません")
        new_state["status"] = "error"
        new_state["error"] = "テスト結果分析が不足しています"
        return new_state
    
    # LLMを使用して遵守評価を実施
    try:
        llm = LLMFactory.create_llm()
        
        # 規制詳細情報の取得（オプション）
        regulation_details = {}
        if "regulation_details" in collected_info:
            regulation_details = collected_info["regulation_details"]
        
        # 遵守評価プロンプトの作成
        prompt_template = PromptManager.get_prompt("compliance_evaluation")
        prompt = prompt_template.format(
            result_analysis=json_utils.json_serialize(result_analysis),
            regulation_details=json_utils.json_serialize(regulation_details)
        )
        
        # LLM呼び出し
        response = await llm.apredict(prompt)
        
        # レスポンスをパース
        try:
            compliance_evaluation = json_utils.json_deserialize(response)
        except json.JSONDecodeError:
            logger.warning("JSON解析エラー、フォールバックとして単純な構造を使用")
            compliance_evaluation = {
                "overall_compliance": "不明",
                "compliance_score": 0.5,
                "regulation_areas": [
                    {
                        "name": "遵守状況を評価できませんでした",
                        "status": "不明",
                        "details": "データ不足のため正確な評価ができません"
                    }
                ]
            }
        
        # 結果を状態に反映
        new_state["compliance_evaluation"] = compliance_evaluation
        new_state["current_step"] = "issue_classification"
        
        logger.info(f"[{state.get('workflow_id', 'unknown')}] 遵守評価完了: {compliance_evaluation.get('overall_compliance')}")
        return new_state
        
    except Exception as e:
        logger.error(f"遵守評価中にエラー: {e}")
        new_state["status"] = "error"
        new_state["error"] = f"遵守評価エラー: {str(e)}"
        return new_state


@with_error_handling
async def issue_classification_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    問題分類ノード: 特定された問題を分類し重要度を判定する
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state.get('workflow_id', 'unknown')}] 問題分類ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["current_step"] = "issue_classification"
    new_state["updated_at"] = datetime.now().isoformat()
    
    # 結果分析の検証
    result_analysis = state.get("result_analysis")
    compliance_evaluation = state.get("compliance_evaluation")
    
    if not result_analysis or not compliance_evaluation:
        logger.warning(f"[{state.get('workflow_id', 'unknown')}] 分析結果または遵守評価がありません")
        new_state["status"] = "error"
        new_state["error"] = "分析結果または遵守評価が不足しています"
        return new_state
    
    # LLMを使用して問題分類を実施
    try:
        llm = LLMFactory.create_llm()
        
        # 問題分類プロンプトの作成
        prompt_template = PromptManager.get_prompt("issue_classification")
        prompt = prompt_template.format(
            result_analysis=json_utils.json_serialize(result_analysis),
            compliance_evaluation=json_utils.json_serialize(compliance_evaluation)
        )
        
        # LLM呼び出し
        response = await llm.apredict(prompt)
        
        # レスポンスをパース
        try:
            issue_classification = json_utils.json_deserialize(response)
        except json.JSONDecodeError:
            logger.warning("JSON解析エラー、フォールバックとして単純な構造を使用")
            issue_classification = {
                "issues": [
                    {
                        "id": f"issue-{uuid.uuid4().hex[:8]}",
                        "description": "問題が特定されていますが、分類できませんでした",
                        "severity": "中",
                        "category": "その他",
                        "impact": "不明"
                    }
                ],
                "risk_levels": {
                    "high": 0,
                    "medium": 1,
                    "low": 0
                }
            }
        
        # 結果を状態に反映
        new_state["issue_classification"] = issue_classification
        new_state["current_step"] = "results_summary"
        
        logger.info(f"[{state.get('workflow_id', 'unknown')}] 問題分類完了: 問題数 {len(issue_classification.get('issues', []))}")
        return new_state
        
    except Exception as e:
        logger.error(f"問題分類中にエラー: {e}")
        new_state["status"] = "error"
        new_state["error"] = f"問題分類エラー: {str(e)}"
        return new_state


@with_error_handling
async def results_summary_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    結果要約ノード: 全体の結果を要約し報告書に含める推奨事項を提案する
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state.get('workflow_id', 'unknown')}] 結果要約ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["current_step"] = "results_summary"
    new_state["updated_at"] = datetime.now().isoformat()
    
    # 必要な情報の検証
    result_analysis = state.get("result_analysis")
    compliance_evaluation = state.get("compliance_evaluation")
    issue_classification = state.get("issue_classification")
    
    if not result_analysis or not compliance_evaluation or not issue_classification:
        logger.warning(f"[{state.get('workflow_id', 'unknown')}] 必要な分析情報が不足しています")
        new_state["status"] = "error"
        new_state["error"] = "結果要約に必要な分析情報が不足しています"
        return new_state
    
    # LLMを使用して結果要約を実施
    try:
        llm = LLMFactory.create_llm()
        
        # 結果要約プロンプトの作成
        prompt_template = PromptManager.get_prompt("results_summary")
        prompt = prompt_template.format(
            result_analysis=json_utils.json_serialize(result_analysis),
            compliance_evaluation=json_utils.json_serialize(compliance_evaluation),
            issue_classification=json_utils.json_serialize(issue_classification)
        )
        
        # LLM呼び出し
        response = await llm.apredict(prompt)
        
        # レスポンスをパース
        try:
            summary = json_utils.json_deserialize(response)
        except json.JSONDecodeError:
            logger.warning("JSON解析エラー、フォールバックとして単純な構造を使用")
            summary = {
                "executive_summary": "十分なデータ分析ができませんでした。",
                "key_findings": ["主要な発見事項を特定できませんでした"],
                "recommendations": ["具体的な推奨事項を提案できません"],
                "next_steps": ["詳細な分析のためにより多くのデータを収集してください"],
                "overall_risk_assessment": "不明"
            }
        
        # 結果を状態に反映
        new_state["summary"] = summary
        new_state["status"] = "completed"
        new_state["current_step"] = "completed"
        
        logger.info(f"[{state.get('workflow_id', 'unknown')}] 結果要約完了: {summary.get('overall_risk_assessment')}")
        return new_state
        
    except Exception as e:
        logger.error(f"結果要約中にエラー: {e}")
        new_state["status"] = "error"
        new_state["error"] = f"結果要約エラー: {str(e)}"
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
    logger.info(f"[{state.get('workflow_id', 'unknown')}] 情報不足処理ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["updated_at"] = datetime.now().isoformat()
    
    # 不足している情報を取得
    missing_info = state.get("missing_info", [])
    if not missing_info:
        # 不足情報が指定されていない場合は元のステップに戻る
        logger.warning(f"[{state.get('workflow_id', 'unknown')}] 不足情報が指定されていません")
        new_state["current_step"] = state.get("current_step", "test_results_analysis")
        return new_state
    
    # チェックポイントを作成
    checkpoint_id = f"cp-{uuid.uuid4().hex[:8]}"
    checkpoint = {
        "id": checkpoint_id,
        "step": state.get("current_step", "unknown"),
        "timestamp": datetime.now().isoformat(),
        "missing_info": missing_info,
        "return_to": state.get("redirect_to", state.get("current_step", "test_results_analysis"))
    }
    
    # チェックポイントを状態に追加
    if "checkpoints" not in new_state:
        new_state["checkpoints"] = []
    new_state["checkpoints"].append(checkpoint)
    
    # 待機状態に設定
    new_state["status"] = "waiting_for_info"
    new_state["current_checkpoint_id"] = checkpoint_id
    
    logger.info(f"[{state.get('workflow_id', 'unknown')}] 情報不足処理完了: チェックポイント作成 {checkpoint_id}")
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
    logger.info(f"[{state.get('workflow_id', 'unknown')}] チェックポイント復元ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["updated_at"] = datetime.now().isoformat()
    
    # チェックポイントIDを取得
    checkpoint_id = state.get("restore_checkpoint_id")
    if not checkpoint_id:
        logger.warning(f"[{state.get('workflow_id', 'unknown')}] 復元するチェックポイントIDが指定されていません")
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
        logger.warning(f"[{state.get('workflow_id', 'unknown')}] チェックポイント {checkpoint_id} が見つかりません")
        new_state["status"] = "error"
        new_state["error"] = f"チェックポイント {checkpoint_id} が見つかりません"
        return new_state
    
    # 復元するステップを取得
    return_to = checkpoint.get("return_to", "test_results_analysis")
    
    # 状態を更新
    new_state["status"] = "resumed_from_checkpoint"
    new_state["current_step"] = return_to
    new_state["restored_from_checkpoint"] = checkpoint_id
    
    logger.info(f"[{state.get('workflow_id', 'unknown')}] チェックポイント {checkpoint_id} から復元、ステップ {return_to} へ")
    return new_state


def route_to_next_step(state: Dict[str, Any]) -> str:
    """
    次のステップを決定するルーター関数
    
    Args:
        state: 現在の状態
        
    Returns:
        次のステップ名
    """
    # リダイレクト先が指定されている場合はそこへ
    if "redirect_to" in state:
        return state["redirect_to"]
    
    # 状態に基づいて次のステップを決定
    current_step = state.get("current_step", "test_results_analysis")
    status = state.get("status", "in_progress")
    
    # エラー状態の場合
    if status == "error":
        return END
    
    # 完了状態の場合
    if status == "completed" or current_step == "completed":
        return END
    
    # チェックポイントからの復元が指定されている場合
    if "restore_checkpoint_id" in state:
        return "resume_from_checkpoint"
    
    # 待機状態の場合
    if status == "waiting_for_info":
        return END  # 情報待ちの場合は終了
    
    # 通常の状態遷移
    if current_step == "test_results_analysis":
        return "compliance_evaluation"
    elif current_step == "compliance_evaluation":
        return "issue_classification"
    elif current_step == "issue_classification":
        return "results_summary"
    
    # デフォルトはテスト結果分析から開始
    return "test_results_analysis"


def create_agent_c_graph() -> StateGraph:
    """
    エージェントCの状態遷移グラフを作成する
    
    Returns:
        構成されたStateGraph
    """
    logger.info("エージェントC状態遷移グラフを作成中...")
    
    try:
        # StateGraphの作成
        workflow = StateGraph(AgentCGraphState)
        
        # 各ノードの追加
        workflow.add_node("test_results_analysis", test_results_analysis_node)
        workflow.add_node("compliance_evaluation", compliance_evaluation_node)
        workflow.add_node("issue_classification", issue_classification_node)
        workflow.add_node("results_summary", results_summary_node)
        workflow.add_node("handle_insufficient_info", handle_insufficient_info_node)
        workflow.add_node("resume_from_checkpoint", resume_from_checkpoint_node)
        
        # エントリーポイントの設定
        workflow.set_entry_point("test_results_analysis")
        
        # 各ノードからの条件付き遷移の設定
        workflow.add_edge("test_results_analysis", route_to_next_step)
        workflow.add_edge("compliance_evaluation", route_to_next_step)
        workflow.add_edge("issue_classification", route_to_next_step)
        workflow.add_edge("results_summary", route_to_next_step)
        workflow.add_edge("handle_insufficient_info", route_to_next_step)
        workflow.add_edge("resume_from_checkpoint", route_to_next_step)
        
        # グラフをコンパイル
        compiled_workflow = workflow.compile()
        
        logger.info("エージェントC状態遷移グラフの作成完了")
        return compiled_workflow
        
    except Exception as e:
        logger.error(f"エージェントC状態遷移グラフの作成エラー: {e}")
        try:
            # 基本的なグラフを作成してエラー時のフォールバックとする
            basic_workflow = StateGraph(AgentCGraphState)
            basic_workflow.add_node("fallback_node", lambda x: x)
            basic_workflow.add_edge("fallback_node", END)
            basic_workflow.set_entry_point("fallback_node")
            
            logger.warning("エラーによりフォールバックグラフを作成")
            compiled_basic = basic_workflow.compile()
            return compiled_basic
        except Exception as fallback_error:
            logger.error(f"フォールバックグラフの作成も失敗: {fallback_error}")
            return None


# シングルトンインスタンスを提供する関数
_agent_c_graph_instance = None

def get_agent_c_graph() -> StateGraph:
    """エージェントC状態遷移グラフのシングルトンインスタンスを取得"""
    global _agent_c_graph_instance
    # テスト環境では常に新しいインスタンスを作成する
    if "pytest" in sys.modules:
        return create_agent_c_graph()
    # 通常の実行では、シングルトンパターンを使用
    if _agent_c_graph_instance is None:
        _agent_c_graph_instance = create_agent_c_graph()
    return _agent_c_graph_instance 