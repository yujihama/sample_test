#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
エージェントDのLangGraphベース状態遷移グラフ

このモジュールでは、エージェントDの監査レポート生成プロセスを
LangGraphの状態遷移グラフとして実装しています。
このグラフは以下のノードで構成されています：
- 監査情報分析：監査結果と要約を分析
- レポート構造設計：レポートの構造と章立てを設計
- セクション生成：各セクションの詳細内容を生成
- レポート編集：全体のレポートを調整し最終化

また、情報が不足している場合はチェックポイントを作成し、
追加情報が提供された後に処理を再開する機能も含まれています。
"""

import asyncio
import uuid
import json
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


class AgentDGraphState(TypedDict, total=False):
    """エージェントD状態遷移グラフの状態型定義"""
    # 基本情報
    workflow_id: str
    summary_id: str
    procedure_id: Optional[str]
    
    # 状態管理
    status: str  # in_progress, waiting_for_info, error, completed
    current_step: str  # 現在のステップ（ノード）
    
    # 監査情報関連
    audit_summary: Optional[Dict[str, Any]]  # 監査結果の要約
    procedure_text: Optional[str]  # 監査手続きテキスト
    audit_info_analysis: Optional[Dict[str, Any]]  # 監査情報の分析結果
    required_info: List[str]  # 必要な情報のリスト
    
    # レポート関連
    report_structure: Optional[Dict[str, Any]]  # レポートの構造設計
    report_sections: Dict[str, Any]  # 生成されたレポートセクション
    report: Optional[str]  # 最終的なレポート文書
    
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
async def audit_info_analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    監査情報分析ノード: 監査結果と要約を分析する
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state.get('workflow_id', 'unknown')}] 監査情報分析ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["current_step"] = "audit_info_analysis"
    new_state["updated_at"] = datetime.now().isoformat()
    
    # 監査要約の検証
    audit_summary = state.get("audit_summary")
    if not audit_summary:
        logger.warning(f"[{state.get('workflow_id', 'unknown')}] 監査要約がありません")
        new_state["status"] = "error"
        new_state["error"] = "監査要約が不足しています"
        return new_state
    
    # LLMを使用して監査情報を分析
    try:
        llm = LLMFactory.create_llm()
        
        # 監査手続きテキスト（オプション）
        procedure_text = state.get("procedure_text", "監査手続き情報が提供されていません")
        
        # 監査情報分析プロンプトの作成
        prompt_template = PromptManager.get_prompt("audit_info_analysis")
        prompt = prompt_template.format(
            audit_summary=json_utils.json_serialize(audit_summary),
            procedure_text=procedure_text
        )
        
        # LLM呼び出し
        response = await llm.apredict(prompt)
        
        # レスポンスをパース
        try:
            analysis = json_utils.json_deserialize(response)
        except json.JSONDecodeError:
            logger.warning("JSON解析エラー、フォールバックとして単純な構造を使用")
            analysis = {
                "audience": "監査委員会",
                "key_elements": [
                    {"name": "主要な監査結果", "importance": "高"},
                    {"name": "推奨される改善策", "importance": "高"},
                    {"name": "リスク評価", "importance": "中"}
                ],
                "required_info": ["監査要約", "手続きテキスト"]
            }
        
        # 結果を状態に反映
        new_state["audit_info_analysis"] = analysis
        
        # レポート作成に必要な追加情報の特定
        required_info = ["audit_summary"]
        for item in analysis.get("key_elements", []):
            if item.get("missing_info") and item.get("importance") == "高":
                required_info.append(item.get("missing_info"))
        
        new_state["required_info"] = required_info
        new_state["current_step"] = "report_structure_design"
        
        logger.info(f"[{state.get('workflow_id', 'unknown')}] 監査情報分析完了")
        return new_state
        
    except Exception as e:
        logger.error(f"監査情報分析中にエラー: {e}")
        new_state["status"] = "error"
        new_state["error"] = f"監査情報分析エラー: {str(e)}"
        return new_state


@with_error_handling
async def report_structure_design_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    レポート構造設計ノード: レポートの構造と章立てを設計する
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state.get('workflow_id', 'unknown')}] レポート構造設計ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["current_step"] = "report_structure_design"
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
    
    # 監査情報分析の検証
    audit_info_analysis = state.get("audit_info_analysis")
    if not audit_info_analysis:
        logger.warning(f"[{state.get('workflow_id', 'unknown')}] 監査情報分析がありません")
        new_state["status"] = "error"
        new_state["error"] = "監査情報分析が不足しています"
        return new_state
    
    # LLMを使用してレポート構造を設計
    try:
        llm = LLMFactory.create_llm()
        
        # 監査要約を取得
        audit_summary = state.get("audit_summary", {})
        
        # レポート構造設計プロンプトの作成
        prompt_template = PromptManager.get_prompt("report_structure_design")
        prompt = prompt_template.format(
            audit_info_analysis=json_utils.json_serialize(audit_info_analysis),
            audit_summary=json_utils.json_serialize(audit_summary)
        )
        
        # LLM呼び出し
        response = await llm.apredict(prompt)
        
        # レスポンスをパース
        try:
            structure = json_utils.json_deserialize(response)
        except json.JSONDecodeError:
            logger.warning("JSON解析エラー、フォールバックとして単純な構造を使用")
            structure = {
                "title": "監査結果報告書",
                "sections": [
                    {"id": "executive_summary", "title": "エグゼクティブサマリー", "order": 1},
                    {"id": "findings", "title": "主要な発見事項", "order": 2},
                    {"id": "recommendations", "title": "推奨事項", "order": 3},
                    {"id": "conclusion", "title": "結論", "order": 4}
                ],
                "metadata": {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "version": "1.0",
                    "confidentiality": "社内限り"
                }
            }
        
        # 結果を状態に反映
        new_state["report_structure"] = structure
        new_state["report_sections"] = {}  # 初期化
        new_state["current_step"] = "section_generation"
        
        logger.info(f"[{state.get('workflow_id', 'unknown')}] レポート構造設計完了: {len(structure.get('sections', []))}セクション")
        return new_state
        
    except Exception as e:
        logger.error(f"レポート構造設計中にエラー: {e}")
        new_state["status"] = "error"
        new_state["error"] = f"レポート構造設計エラー: {str(e)}"
        return new_state


@with_error_handling
async def section_generation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    セクション生成ノード: 各セクションの詳細内容を生成する
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state.get('workflow_id', 'unknown')}] セクション生成ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["current_step"] = "section_generation"
    new_state["updated_at"] = datetime.now().isoformat()
    
    # レポート構造の検証
    report_structure = state.get("report_structure")
    if not report_structure:
        logger.warning(f"[{state.get('workflow_id', 'unknown')}] レポート構造がありません")
        new_state["status"] = "error"
        new_state["error"] = "レポート構造が不足しています"
        return new_state
    
    # 監査要約の取得
    audit_summary = state.get("audit_summary", {})
    
    # 生成済みセクションの取得
    report_sections = state.get("report_sections", {})
    
    # すべてのセクションが生成済みかをチェック
    sections = report_structure.get("sections", [])
    remaining_sections = [s for s in sections if s.get("id") not in report_sections]
    
    # すべてのセクションが生成済みの場合は次のステップへ
    if not remaining_sections:
        logger.info(f"[{state.get('workflow_id', 'unknown')}] すべてのセクションが生成済み")
        new_state["current_step"] = "report_editing"
        return new_state
    
    # 次に生成するセクションを選択（順序に従って）
    current_section = sorted(remaining_sections, key=lambda x: x.get("order", 999))[0]
    section_id = current_section.get("id")
    section_title = current_section.get("title")
    
    logger.info(f"[{state.get('workflow_id', 'unknown')}] セクション生成中: {section_title} (ID: {section_id})")
    
    # LLMを使用してセクションを生成
    try:
        llm = LLMFactory.create_llm()
        
        # セクション生成プロンプトの作成
        prompt_template = PromptManager.get_prompt("report_section_generation")
        prompt = prompt_template.format(
            section_id=section_id,
            section_title=section_title,
            report_structure=json_utils.json_serialize(report_structure),
            audit_summary=json_utils.json_serialize(audit_summary)
        )
        
        # LLM呼び出し
        response = await llm.apredict(prompt)
        
        # レスポンスを整形
        section_content = {
            "id": section_id,
            "title": section_title,
            "content": response,
            "generated_at": datetime.now().isoformat()
        }
        
        # 結果を状態に反映
        new_state["report_sections"][section_id] = section_content
        
        # まだセクションが残っている場合は再度このノードを実行
        if len(new_state["report_sections"]) < len(sections):
            new_state["current_step"] = "section_generation"
        else:
            # すべてのセクションが生成されたら次のステップへ
            new_state["current_step"] = "report_editing"
        
        logger.info(f"[{state.get('workflow_id', 'unknown')}] セクション生成完了: {section_title} (残り: {len(sections) - len(new_state['report_sections'])})")
        return new_state
        
    except Exception as e:
        logger.error(f"セクション生成中にエラー: {e}")
        new_state["status"] = "error"
        new_state["error"] = f"セクション生成エラー: {str(e)}"
        return new_state


@with_error_handling
async def report_editing_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    レポート編集ノード: 全体のレポートを調整し最終化する
    
    Args:
        state: 現在の状態
        
    Returns:
        更新された状態
    """
    logger.info(f"[{state.get('workflow_id', 'unknown')}] レポート編集ノードを実行中...")
    
    # 現在の状態をコピー
    new_state = state.copy()
    new_state["current_step"] = "report_editing"
    new_state["updated_at"] = datetime.now().isoformat()
    
    # レポート構造とセクションの検証
    report_structure = state.get("report_structure")
    report_sections = state.get("report_sections", {})
    
    if not report_structure or not report_sections:
        logger.warning(f"[{state.get('workflow_id', 'unknown')}] レポート構造またはセクションがありません")
        new_state["status"] = "error"
        new_state["error"] = "レポート編集に必要な情報が不足しています"
        return new_state
    
    # すべてのセクションが揃っているかを確認
    sections = report_structure.get("sections", [])
    if len(report_sections) < len(sections):
        missing = [s.get("id") for s in sections if s.get("id") not in report_sections]
        logger.warning(f"[{state.get('workflow_id', 'unknown')}] 不足しているセクション: {missing}")
        new_state["status"] = "error"
        new_state["error"] = f"セクションが不足しています: {missing}"
        return new_state
    
    # LLMを使用してレポートを最終調整
    try:
        llm = LLMFactory.create_llm()
        
        # レポートのメタデータを取得
        metadata = report_structure.get("metadata", {})
        title = report_structure.get("title", "監査レポート")
        
        # セクションの内容を順序に従って結合
        ordered_sections = sorted(sections, key=lambda x: x.get("order", 999))
        report_content = []
        
        # タイトルとメタデータの追加
        report_content.append(f"# {title}")
        report_content.append(f"作成日: {metadata.get('date', datetime.now().strftime('%Y-%m-%d'))}")
        report_content.append(f"文書バージョン: {metadata.get('version', '1.0')}")
        report_content.append(f"機密区分: {metadata.get('confidentiality', '社内限り')}")
        report_content.append("\n---\n")
        
        # 各セクションの追加
        for section in ordered_sections:
            section_id = section.get("id")
            section_title = section.get("title")
            section_content = report_sections.get(section_id, {}).get("content", "内容がありません")
            
            report_content.append(f"## {section_title}")
            report_content.append(section_content)
            report_content.append("\n")
        
        # レポートコンテンツを結合
        full_report = "\n".join(report_content)
        
        # レポート編集プロンプトの作成
        prompt_template = PromptManager.get_prompt("report_editing")
        prompt = prompt_template.format(
            draft_report=full_report,
            report_structure=json_utils.json_serialize(report_structure)
        )
        
        # LLM呼び出し
        response = await llm.apredict(prompt)
        
        # 結果を状態に反映
        new_state["report"] = response
        new_state["status"] = "completed"
        new_state["current_step"] = "completed"
        
        logger.info(f"[{state.get('workflow_id', 'unknown')}] レポート編集完了: 文字数 {len(response)}")
        return new_state
        
    except Exception as e:
        logger.error(f"レポート編集中にエラー: {e}")
        new_state["status"] = "error"
        new_state["error"] = f"レポート編集エラー: {str(e)}"
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
        new_state["current_step"] = state.get("current_step", "audit_info_analysis")
        return new_state
    
    # チェックポイントを作成
    checkpoint_id = f"cp-{uuid.uuid4().hex[:8]}"
    checkpoint = {
        "id": checkpoint_id,
        "step": state.get("current_step", "unknown"),
        "timestamp": datetime.now().isoformat(),
        "missing_info": missing_info,
        "return_to": state.get("redirect_to", state.get("current_step", "audit_info_analysis"))
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
    return_to = checkpoint.get("return_to", "audit_info_analysis")
    
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
    current_step = state.get("current_step", "audit_info_analysis")
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
    if current_step == "audit_info_analysis":
        return "report_structure_design"
    elif current_step == "report_structure_design":
        return "section_generation"
    elif current_step == "section_generation":
        # セクション生成ノードで判断
        if state.get("report_structure", {}).get("sections", []) and len(state.get("report_sections", {})) < len(state.get("report_structure", {}).get("sections", [])):
            return "section_generation"  # まだ生成すべきセクションがある
        else:
            return "report_editing"
    elif current_step == "report_editing":
        return END
    
    # デフォルトは監査情報分析から開始
    return "audit_info_analysis"


def create_agent_d_graph() -> StateGraph:
    """
    エージェントDの状態遷移グラフを作成する
    
    Returns:
        構成されたStateGraph
    """
    logger.info("エージェントD状態遷移グラフを作成中...")
    
    try:
        # StateGraphの作成
        workflow = StateGraph(AgentDGraphState)
        
        # 各ノードの追加
        workflow.add_node("audit_info_analysis", audit_info_analysis_node)
        workflow.add_node("report_structure_design", report_structure_design_node)
        workflow.add_node("section_generation", section_generation_node)
        workflow.add_node("report_editing", report_editing_node)
        workflow.add_node("handle_insufficient_info", handle_insufficient_info_node)
        workflow.add_node("resume_from_checkpoint", resume_from_checkpoint_node)
        
        # エントリーポイントの設定
        workflow.set_entry_point("audit_info_analysis")
        
        # 各ノードからの条件付き遷移の設定
        workflow.add_edge("audit_info_analysis", route_to_next_step)
        workflow.add_edge("report_structure_design", route_to_next_step)
        workflow.add_edge("section_generation", route_to_next_step)
        workflow.add_edge("report_editing", route_to_next_step)
        workflow.add_edge("handle_insufficient_info", route_to_next_step)
        workflow.add_edge("resume_from_checkpoint", route_to_next_step)
        
        # グラフをコンパイル
        compiled_workflow = workflow.compile()
        
        logger.info("エージェントD状態遷移グラフの作成完了")
        return compiled_workflow
        
    except Exception as e:
        logger.error(f"エージェントD状態遷移グラフの作成エラー: {e}")
        # 基本的なグラフを作成してエラー時のフォールバックとする
        basic_workflow = StateGraph(AgentDGraphState)
        basic_workflow.add_node("audit_info_analysis", audit_info_analysis_node)
        basic_workflow.add_edge("audit_info_analysis", END)
        basic_workflow.set_entry_point("audit_info_analysis")
        
        logger.warning("エラーによりフォールバックグラフを作成")
        return basic_workflow.compile()


# シングルトンインスタンスを提供する関数
_agent_d_graph_instance = None

def get_agent_d_graph() -> StateGraph:
    """エージェントD状態遷移グラフのシングルトンインスタンスを取得"""
    global _agent_d_graph_instance
    if _agent_d_graph_instance is None:
        _agent_d_graph_instance = create_agent_d_graph()
    return _agent_d_graph_instance 