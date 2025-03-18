#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
エージェントAのLangGraphベース状態遷移グラフ

このモジュールでは、エージェントAの監査手続き理解・設計プロセスを
LangGraphの状態遷移グラフとして実装しています。
このグラフは以下のノードで構成されています：
- 監査手続き理解：監査手続きのテキストを分析し構造化された理解を生成
- サンプルデータ分析：監査対象のサンプルデータを分析
- テスト計画生成：手続き理解とサンプル分析に基づいてテスト計画を生成
- テスト計画評価：生成されたテスト計画の品質と網羅性を評価

また、情報が不足している場合はチェックポイントを作成し、
追加情報が提供された後に処理を再開する機能も含まれています。
"""

import asyncio
import uuid
import json
from src.utils import json_utils
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional, TypedDict, Union, cast, Callable
from pydantic import BaseModel, Field

from loguru import logger
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver

# 基本的なエージェント機能をインポート
from src.core.agent_base import AgentState
from src.utils.llm_utils import LLMFactory, PromptManager


class AgentAGraphState(TypedDict, total=False):
    """エージェントA状態遷移グラフの状態型定義"""
    # 基本情報
    workflow_id: str
    procedure_id: str
    procedure_text: str
    sample_id: Optional[str]
    
    # 状態管理
    status: str  # in_progress, waiting_for_info, error, completed
    current_step: str  # 現在のステップ（ノード）
    
    # 監査手続き関連
    procedure_understanding: Optional[Dict[str, Any]]  # 手続きの構造化理解
    required_info: List[str]  # 必要な情報のリスト
    
    # サンプルデータ関連
    sample_analysis: Optional[Dict[str, Any]]  # サンプルデータの分析結果
    
    # 出力関連
    test_plan: Optional[Dict[str, Any]]  # 生成されたテスト計画
    test_plan_evaluation: Optional[Dict[str, Any]]  # テスト計画の評価結果
    
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
async def procedure_understanding_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    監査手続き理解ノード: 監査手続きのテキストを分析し構造化された理解を生成する
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state.get('workflow_id', 'unknown')}] 監査手続き理解ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["current_step"] = "procedure_understanding"
    new_state["updated_at"] = datetime.now().isoformat()
    
    # 手続きテキストの検証
    procedure_text = state.get("procedure_text")
    if not procedure_text:
        logger.warning(f"[{state.get('workflow_id', 'unknown')}] 監査手続きテキストがありません")
        new_state["status"] = "error"
        new_state["error"] = "監査手続きテキストが不足しています"
        return new_state
    
    # LLMを使用して手続きを理解
    try:
        llm = LLMFactory.create_llm()
        
        # 監査手続き理解プロンプトの作成
        prompt_template = PromptManager.get_prompt("audit_procedure_understanding")
        prompt = prompt_template.format(procedure_text=procedure_text)
        
        # LLM呼び出し
        response = await llm.apredict(prompt)
        
        # レスポンスをパース
        try:
            understanding = json_utils.json_deserialize(response)
        except json.JSONDecodeError:
            logger.warning("JSON解析エラー、フォールバックとして単純な構造を使用")
            understanding = {
                "objectives": [{"description": "目的を特定できませんでした"}],
                "risks": [{"description": "リスクを特定できませんでした"}],
                "requirements": [{"description": "要件を特定できませんでした"}],
                "data_needs": []
            }
        
        # 構造化
        structured_understanding = {
            "objectives": understanding.get("objectives", []),
            "risks": understanding.get("risks", []),
            "requirements": understanding.get("requirements", []),
            "data_needs": understanding.get("data_needs", [])
        }
        
        # 必要なデータ項目の抽出
        required_info = ["audit_procedure"]
        for data_need in structured_understanding.get("data_needs", []):
            if data_need.get("data_type") and data_need.get("importance", "").lower() == "high":
                required_info.append(data_need.get("data_type"))
        
        # 結果を状態に反映
        new_state["procedure_understanding"] = structured_understanding
        new_state["required_info"] = required_info
        new_state["current_step"] = "sample_analysis"
        
        logger.info(f"[{state.get('workflow_id', 'unknown')}] 監査手続き理解完了")
        return new_state
        
    except Exception as e:
        logger.error(f"手続き理解中にエラー: {e}")
        new_state["status"] = "error"
        new_state["error"] = f"手続き理解エラー: {str(e)}"
        return new_state


@with_error_handling
async def sample_analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    サンプルデータ分析ノード: 監査対象のサンプルデータを分析する
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state.get('workflow_id', 'unknown')}] サンプルデータ分析ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["current_step"] = "sample_analysis"
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
    
    # サンプルIDの検証
    sample_id = state.get("sample_id")
    if not sample_id:
        # サンプル情報が必要ない場合は次のステップへ
        if "sample_data" not in required_info:
            logger.info("サンプルデータは必要ありません、テスト計画生成へスキップ")
            new_state["sample_analysis"] = {"status": "skipped", "reason": "サンプルデータ不要"}
            new_state["current_step"] = "test_plan_generation"
            return new_state
        else:
            logger.warning(f"[{state.get('workflow_id', 'unknown')}] サンプルIDがありません")
            new_state["status"] = "waiting_for_info"
            new_state["missing_info"] = ["sample_id"]
            new_state["redirect_to"] = "handle_insufficient_info"
            return new_state
    
    # サンプルデータ分析実行（ここでは簡易版を実装）
    # 実際の実装では、サンプルデータをロードして詳細な分析を行う
    sample_analysis = {
        "total_records": 100,  # サンプル値
        "columns": [
            {"name": "取引ID", "type": "string", "unique": True},
            {"name": "日付", "type": "date", "null_ratio": 0.0},
            {"name": "金額", "type": "numeric", "min": 1000, "max": 50000},
            {"name": "取引種別", "type": "category", "categories": ["入金", "出金", "振替"]}
        ],
        "data_quality": {
            "completeness": 0.98,
            "consistency": 0.95,
            "issues": []
        },
        "statistics": {
            "数値データ": {"平均": 25000, "中央値": 22000, "標準偏差": 8000},
            "カテゴリデータ": {"最頻値": "入金", "カテゴリ数": 3}
        }
    }
    
    # コレクション情報からサンプル分析情報があれば使用
    if "sample_analysis" in collected_info:
        sample_analysis = collected_info["sample_analysis"].get("data", sample_analysis)
    
    # 結果を状態に反映
    new_state["sample_analysis"] = sample_analysis
    new_state["current_step"] = "test_plan_generation"
    
    logger.info(f"[{state.get('workflow_id', 'unknown')}] サンプルデータ分析完了")
    return new_state


@with_error_handling
async def test_plan_generation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    テスト計画生成ノード: 手続き理解とサンプル分析に基づいてテスト計画を生成する
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state.get('workflow_id', 'unknown')}] テスト計画生成ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["current_step"] = "test_plan_generation"
    new_state["updated_at"] = datetime.now().isoformat()
    
    # 必要な情報が揃っているか確認
    procedure_understanding = state.get("procedure_understanding")
    
    if not procedure_understanding:
        logger.warning(f"[{state.get('workflow_id', 'unknown')}] 手続き理解情報がありません")
        new_state["status"] = "error"
        new_state["error"] = "手続き理解情報が不足しています"
        return new_state
    
    # サンプル分析情報を取得（オプション）
    sample_analysis = state.get("sample_analysis", {})
    
    # LLMを使用してテスト計画を生成
    try:
        llm = LLMFactory.create_llm()
        
        # テスト計画生成プロンプトの作成
        prompt_template = PromptManager.get_prompt("test_plan_generation")
        prompt = prompt_template.format(
            procedure_understanding=json_utils.json_serialize(procedure_understanding),
            sample_analysis=json_utils.json_serialize(sample_analysis)
        )
        
        # LLM呼び出し
        response = await llm.apredict(prompt)
        
        # レスポンスをパース
        try:
            test_plan = json_utils.json_deserialize(response)
        except json.JSONDecodeError:
            logger.warning("JSON解析エラー、フォールバックとして単純な構造を使用")
            test_plan = {
                "test_items": [
                    {
                        "id": f"test-{uuid.uuid4().hex[:8]}",
                        "name": "基本的な検証",
                        "description": "基本的なデータ検証を実施",
                        "expected_results": "データが基準を満たしていること",
                        "risk_addressed": "データ不整合リスク"
                    }
                ]
            }
        
        # 結果を状態に反映
        new_state["test_plan"] = test_plan
        new_state["current_step"] = "test_plan_evaluation"
        
        logger.info(f"[{state.get('workflow_id', 'unknown')}] テスト計画生成完了")
        return new_state
        
    except Exception as e:
        logger.error(f"テスト計画生成中にエラー: {e}")
        new_state["status"] = "error"
        new_state["error"] = f"テスト計画生成エラー: {str(e)}"
        return new_state


@with_error_handling
async def test_plan_evaluation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    テスト計画評価ノード: 生成されたテスト計画の品質と網羅性を評価する
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state.get('workflow_id', 'unknown')}] テスト計画評価ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["current_step"] = "test_plan_evaluation"
    new_state["updated_at"] = datetime.now().isoformat()
    
    # テスト計画が存在するか確認
    test_plan = state.get("test_plan")
    if not test_plan:
        logger.warning(f"[{state.get('workflow_id', 'unknown')}] テスト計画がありません")
        new_state["status"] = "error"
        new_state["error"] = "テスト計画が不足しています"
        return new_state
    
    # 手続き理解情報を取得
    procedure_understanding = state.get("procedure_understanding", {})
    
    # LLMを使用してテスト計画を評価
    try:
        llm = LLMFactory.create_llm()
        
        # テスト計画評価プロンプトの作成
        prompt_template = PromptManager.get_prompt("test_plan_evaluation")
        prompt = prompt_template.format(
            procedure_understanding=json_utils.json_serialize(procedure_understanding),
            test_plan=json_utils.json_serialize(test_plan)
        )
        
        # LLM呼び出し
        response = await llm.apredict(prompt)
        
        # レスポンスをパース
        try:
            evaluation = json_utils.json_deserialize(response)
        except json.JSONDecodeError:
            logger.warning("JSON解析エラー、フォールバックとして単純な構造を使用")
            evaluation = {
                "quality_score": 0.7,
                "coverage_score": 0.7,
                "gaps": ["いくつかのリスク領域がカバーされていない可能性があります"],
                "improvements": ["追加のテスト項目を検討してください"],
                "overall_assessment": "良好"
            }
        
        # テスト計画の合格判定
        quality_score = evaluation.get("quality_score", 0)
        coverage_score = evaluation.get("coverage_score", 0)
        
        if quality_score >= 0.7 and coverage_score >= 0.7:
            # 評価が良好な場合は完了
            new_state["test_plan_evaluation"] = evaluation
            new_state["status"] = "completed"
            new_state["current_step"] = "completed"
        else:
            # 評価が不十分な場合は、改善点を記録して再生成を提案
            new_state["test_plan_evaluation"] = evaluation
            new_state["status"] = "needs_improvement"
            # 実際の実装では、ここでユーザーに承認を求めるか、
            # 自動的に再生成するかの判断ロジックを追加
        
        logger.info(f"[{state.get('workflow_id', 'unknown')}] テスト計画評価完了: {evaluation.get('overall_assessment')}")
        return new_state
        
    except Exception as e:
        logger.error(f"テスト計画評価中にエラー: {e}")
        new_state["status"] = "error"
        new_state["error"] = f"テスト計画評価エラー: {str(e)}"
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
        new_state["current_step"] = state.get("current_step", "procedure_understanding")
        return new_state
    
    # チェックポイントを作成
    checkpoint_id = f"cp-{uuid.uuid4().hex[:8]}"
    checkpoint = {
        "id": checkpoint_id,
        "step": state.get("current_step", "unknown"),
        "timestamp": datetime.now().isoformat(),
        "missing_info": missing_info,
        "return_to": state.get("redirect_to", state.get("current_step", "procedure_understanding"))
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
    return_to = checkpoint.get("return_to", "procedure_understanding")
    
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
    current_step = state.get("current_step", "procedure_understanding")
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
    
    # 状態改善が必要な場合（テスト計画の品質が不十分）
    if status == "needs_improvement" and current_step == "test_plan_evaluation":
        return "test_plan_generation"  # テスト計画を再生成
    
    # 待機状態の場合
    if status == "waiting_for_info":
        return END  # 情報待ちの場合は終了
    
    # 通常の状態遷移
    if current_step == "procedure_understanding":
        return "sample_analysis"
    elif current_step == "sample_analysis":
        return "test_plan_generation"
    elif current_step == "test_plan_generation":
        return "test_plan_evaluation"
    
    # デフォルトは手続き理解から開始
    return "procedure_understanding"


def create_agent_a_graph() -> StateGraph:
    """
    エージェントAの状態遷移グラフを作成する
    
    Returns:
        構成されたStateGraph
    """
    logger.info("エージェントA状態遷移グラフを作成中...")
    
    try:
        # StateGraphの作成
        workflow = StateGraph(AgentAGraphState)
        
        # 各ノードの追加
        workflow.add_node("procedure_understanding", procedure_understanding_node)
        workflow.add_node("sample_analysis", sample_analysis_node)
        workflow.add_node("test_plan_generation", test_plan_generation_node)
        workflow.add_node("test_plan_evaluation", test_plan_evaluation_node)
        workflow.add_node("handle_insufficient_info", handle_insufficient_info_node)
        workflow.add_node("resume_from_checkpoint", resume_from_checkpoint_node)
        
        # エントリーポイントの設定
        workflow.set_entry_point("procedure_understanding")
        
        # 各ノードからの条件付き遷移の設定
        workflow.add_edge("procedure_understanding", route_to_next_step)
        workflow.add_edge("sample_analysis", route_to_next_step)
        workflow.add_edge("test_plan_generation", route_to_next_step)
        workflow.add_edge("test_plan_evaluation", route_to_next_step)
        workflow.add_edge("handle_insufficient_info", route_to_next_step)
        workflow.add_edge("resume_from_checkpoint", route_to_next_step)
        
        # グラフをコンパイル
        compiled_workflow = workflow.compile()
        
        logger.info("エージェントA状態遷移グラフの作成完了")
        return compiled_workflow
        
    except Exception as e:
        logger.error(f"エージェントA状態遷移グラフの作成エラー: {e}")
        # 基本的なグラフを作成してエラー時のフォールバックとする
        basic_workflow = StateGraph(AgentAGraphState)
        basic_workflow.add_node("procedure_understanding", procedure_understanding_node)
        basic_workflow.add_edge("procedure_understanding", END)
        basic_workflow.set_entry_point("procedure_understanding")
        
        logger.warning("エラーによりフォールバックグラフを作成")
        return basic_workflow.compile()


# シングルトンインスタンスを提供する関数
_agent_a_graph_instance = None

def get_agent_a_graph() -> StateGraph:
    """エージェントA状態遷移グラフのシングルトンインスタンスを取得"""
    global _agent_a_graph_instance
    if _agent_a_graph_instance is None:
        _agent_a_graph_instance = create_agent_a_graph()
    return _agent_a_graph_instance 