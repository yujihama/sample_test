"""
規程情報管理用LangGraphノード

このモジュールでは、規程情報を検索・参照するためのLangGraphノードを定義します。
エージェントの状態遷移グラフに組み込んで使用します。
"""

from typing import Dict, List, Any, Optional, Tuple, Callable, TypedDict, cast
import json
import logging
from datetime import datetime
from langchain_core.pydantic_v1 import BaseModel, Field
import httpx

from src.utils.logger import get_logger
from src.utils.error_handler import with_error_handling
from src.models.schema import RegulationSearchQuery, RegulationDecisionReferenceCreate

logger = get_logger(__name__)

# 検索API呼び出し用のベースURL
API_BASE_URL = "http://localhost:8000"  # 環境に応じて変更


class RegulationLookupInput(TypedDict, total=False):
    """規程検索入力モデル"""
    query: Optional[str]
    category: Optional[str]
    keywords: Optional[List[str]]
    workflow_id: Optional[str]
    context: Optional[Dict[str, Any]]


class RegulationLookupOutput(TypedDict, total=False):
    """規程検索出力モデル"""
    success: bool
    total_results: int
    regulations: List[Dict[str, Any]]
    error: Optional[str]
    matched_sections: Optional[List[Dict[str, Any]]]


class RegulationDecisionInput(TypedDict, total=False):
    """規程判断記録入力モデル"""
    regulation_id: str
    workflow_id: str
    agent_id: str
    decision_context: Dict[str, Any]
    applied_section: Optional[str]
    decision_details: Dict[str, Any]


class RegulationDecisionOutput(TypedDict, total=False):
    """規程判断記録出力モデル"""
    success: bool
    reference_id: Optional[str]
    regulation_code: Optional[str]
    regulation_title: Optional[str]
    error: Optional[str]


@with_error_handling
async def regulation_lookup_node(
    state: Dict[str, Any],
    search_input: Optional[RegulationLookupInput] = None
) -> Dict[str, Any]:
    """
    規程情報検索ノード
    
    監査状態や入力に基づいて関連する規程情報を検索します。
    
    Args:
        state (Dict[str, Any]): グラフの状態
        search_input (Optional[RegulationLookupInput], optional): 検索条件
        
    Returns:
        Dict[str, Any]: 更新された状態
    """
    logger.info("規程情報検索ノードを実行中...")
    
    # 検索条件の準備
    input_data = search_input or {}
    
    # 状態から検索クエリを抽出または生成（入力が指定されていない場合）
    if not input_data.get("query") and state.get("current_issue"):
        # 例: 現在の課題から検索クエリを生成
        issue = state.get("current_issue", {})
        issue_type = issue.get("type", "")
        issue_description = issue.get("description", "")
        
        # 課題タイプに応じてカテゴリを設定
        category = None
        if "予算" in issue_type or "金額" in issue_type:
            category = "予算承認規程"
        elif "出張" in issue_type:
            category = "出張規程"
        elif "購買" in issue_type or "調達" in issue_type:
            category = "購買規程"
        
        # 検索クエリの作成
        input_data["query"] = issue_description
        if category:
            input_data["category"] = category
            
    # ワークフローIDの設定
    workflow_id = input_data.get("workflow_id") or state.get("workflow_id")
    
    # コンテキスト情報を追加
    context = input_data.get("context") or {}
    if not context and state.get("context"):
        context = state.get("context")
    
    # 検索クエリの構築
    search_query = RegulationSearchQuery(
        query=input_data.get("query"),
        category=input_data.get("category"),
        keywords=input_data.get("keywords"),
        effective_date=datetime.now(),
        context=context
    )
    
    # API呼び出し
    try:
        # アクター（エージェント）情報
        actor = state.get("agent_id", "unknown_agent")
        
        # HTTPリクエスト
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/regulations/search",
                json=search_query.dict(exclude_none=True),
                params={"actor": actor, "workflow_id": workflow_id} if workflow_id else {"actor": actor}
            )
            
            # レスポンス処理
            if response.status_code == 200:
                result = response.json()
                
                # 検索結果を状態に追加
                new_state = state.copy()
                new_state["regulation_lookup_result"] = {
                    "success": True,
                    "total_results": result.get("total", 0),
                    "regulations": result.get("regulations", []),
                    "matched_sections": result.get("matches", []),
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"規程検索結果: {result.get('total', 0)}件の規程が見つかりました")
                return new_state
            else:
                error_msg = f"規程検索API呼び出しエラー: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                # エラー情報を状態に追加
                new_state = state.copy()
                new_state["regulation_lookup_result"] = {
                    "success": False,
                    "error": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
                return new_state
    
    except Exception as e:
        error_msg = f"規程検索中に例外が発生: {str(e)}"
        logger.error(error_msg)
        
        # エラー情報を状態に追加
        new_state = state.copy()
        new_state["regulation_lookup_result"] = {
            "success": False,
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }
        return new_state


@with_error_handling
async def regulation_decision_reference_node(
    state: Dict[str, Any],
    decision_input: Optional[RegulationDecisionInput] = None
) -> Dict[str, Any]:
    """
    規程判断参照ノード
    
    エージェントの判断を規程に基づいて記録します。
    
    Args:
        state (Dict[str, Any]): グラフの状態
        decision_input (Optional[RegulationDecisionInput], optional): 判断参照データ
        
    Returns:
        Dict[str, Any]: 更新された状態
    """
    logger.info("規程判断参照ノードを実行中...")
    
    # 入力データの準備
    input_data = decision_input or {}
    
    # 必須パラメータの確認
    if not input_data.get("regulation_id"):
        if state.get("regulation_lookup_result", {}).get("regulations"):
            # 最も関連性の高い規程を選択
            regulations = state.get("regulation_lookup_result", {}).get("regulations", [])
            if regulations:
                input_data["regulation_id"] = regulations[0].get("id")
        
        if not input_data.get("regulation_id"):
            error_msg = "規程IDが指定されておらず、検索結果からも取得できません"
            logger.error(error_msg)
            
            # エラー情報を状態に追加
            new_state = state.copy()
            new_state["regulation_decision_result"] = {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
            return new_state
    
    # ワークフローIDとエージェントIDの設定
    input_data["workflow_id"] = input_data.get("workflow_id") or state.get("workflow_id")
    input_data["agent_id"] = input_data.get("agent_id") or state.get("agent_id")
    
    if not input_data.get("workflow_id") or not input_data.get("agent_id"):
        error_msg = "ワークフローIDまたはエージェントIDが不足しています"
        logger.error(error_msg)
        
        # エラー情報を状態に追加
        new_state = state.copy()
        new_state["regulation_decision_result"] = {
            "success": False,
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }
        return new_state
    
    # 判断コンテキストの設定
    if not input_data.get("decision_context"):
        input_data["decision_context"] = {
            "current_issue": state.get("current_issue", {}),
            "context": state.get("context", {})
        }
    
    # API呼び出し
    try:
        # 判断参照データの構築
        reference_data = RegulationDecisionReferenceCreate(
            regulation_id=input_data["regulation_id"],
            workflow_id=input_data["workflow_id"],
            agent_id=input_data["agent_id"],
            decision_context=input_data["decision_context"],
            decision_details=input_data.get("decision_details", {}),
            applied_section=input_data.get("applied_section")
        )
        
        # アクター（エージェント）情報
        actor = state.get("agent_id", "unknown_agent")
        
        # HTTPリクエスト
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/regulations/decision-references",
                json=reference_data.dict(exclude_none=True),
                params={"actor": actor}
            )
            
            # レスポンス処理
            if response.status_code == 200:
                result = response.json()
                
                # 結果を状態に追加
                new_state = state.copy()
                new_state["regulation_decision_result"] = {
                    "success": True,
                    "reference_id": result.get("reference_id"),
                    "regulation_code": result.get("regulation_code"),
                    "regulation_title": result.get("regulation_title"),
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"規程判断参照を作成しました: {result.get('regulation_code')} - {result.get('reference_id')}")
                return new_state
            else:
                error_msg = f"規程判断参照API呼び出しエラー: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                # エラー情報を状態に追加
                new_state = state.copy()
                new_state["regulation_decision_result"] = {
                    "success": False,
                    "error": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
                return new_state
    
    except Exception as e:
        error_msg = f"規程判断参照中に例外が発生: {str(e)}"
        logger.error(error_msg)
        
        # エラー情報を状態に追加
        new_state = state.copy()
        new_state["regulation_decision_result"] = {
            "success": False,
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }
        return new_state


async def get_regulation_references_node(
    state: Dict[str, Any]
) -> Dict[str, Any]:
    """
    規程参照一覧取得ノード
    
    ワークフローに関連する規程判断参照一覧を取得します。
    
    Args:
        state (Dict[str, Any]): グラフの状態
        
    Returns:
        Dict[str, Any]: 更新された状態
    """
    logger.info("規程参照一覧取得ノードを実行中...")
    
    # ワークフローIDの確認
    workflow_id = state.get("workflow_id")
    if not workflow_id:
        error_msg = "ワークフローIDが指定されていません"
        logger.error(error_msg)
        
        # エラー情報を状態に追加
        new_state = state.copy()
        new_state["regulation_references_result"] = {
            "success": False,
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }
        return new_state
    
    # API呼び出し
    try:
        # HTTPリクエスト
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_BASE_URL}/regulations/workflow/{workflow_id}/decision-references"
            )
            
            # レスポンス処理
            if response.status_code == 200:
                result = response.json()
                
                # 結果を状態に追加
                new_state = state.copy()
                new_state["regulation_references_result"] = {
                    "success": True,
                    "references": result,
                    "total": len(result),
                    "timestamp": datetime.now().isoformat()
                }
                
                logger.info(f"規程参照一覧を取得しました: {len(result)}件")
                return new_state
            else:
                error_msg = f"規程参照一覧API呼び出しエラー: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                # エラー情報を状態に追加
                new_state = state.copy()
                new_state["regulation_references_result"] = {
                    "success": False,
                    "error": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
                return new_state
    
    except Exception as e:
        error_msg = f"規程参照一覧取得中に例外が発生: {str(e)}"
        logger.error(error_msg)
        
        # エラー情報を状態に追加
        new_state = state.copy()
        new_state["regulation_references_result"] = {
            "success": False,
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }
        return new_state 