#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
エージェント間コンテキスト共有APIエンドポイント

このモジュールでは、エージェント間コンテキスト共有機能にアクセスするための
APIエンドポイントを定義しています。これにより、監査コンテキストの作成、
エージェントワークフローの開始、イベント処理、状態取得などが可能になります。
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Body, Query, Path, Depends
from pydantic import BaseModel, Field

from loguru import logger
from src.core.agent_context_manager import get_context_manager


# APIルーターの作成
router = APIRouter(prefix="/agent-context", tags=["エージェントコンテキスト"])


# モデル定義
class AuditContextCreate(BaseModel):
    """監査コンテキスト作成リクエスト"""
    audit_id: str = Field(..., description="監査ID")
    title: str = Field(..., description="監査タイトル")
    description: str = Field("", description="監査の説明")


class AgentWorkflowStart(BaseModel):
    """エージェントワークフロー開始リクエスト"""
    agent_id: str = Field(..., description="エージェントID")
    initial_state: Dict[str, Any] = Field(default_factory=dict, description="初期状態")


class AgentEvent(BaseModel):
    """エージェントイベント"""
    agent_id: str = Field(..., description="エージェントID")
    event_type: str = Field(..., description="イベントタイプ")
    data: Dict[str, Any] = Field(default_factory=dict, description="イベントデータ")


# エンドポイント定義
@router.post("/contexts", response_model=Dict[str, Any])
async def create_audit_context(context: AuditContextCreate):
    """
    新しい監査コンテキストを作成
    
    監査コンテキストは複数のエージェント間で情報を共有するための基盤となります。
    
    Returns:
        作成されたコンテキスト情報
    """
    try:
        context_manager = get_context_manager()
        context_id = await context_manager.create_audit_context(
            context.audit_id, context.title, context.description
        )
        
        context_info = await context_manager.get_audit_context(context_id)
        return context_info
    except Exception as e:
        logger.error(f"監査コンテキスト作成エラー: {e}")
        raise HTTPException(status_code=500, detail=f"監査コンテキスト作成エラー: {str(e)}")


@router.get("/contexts/{context_id}", response_model=Dict[str, Any])
async def get_audit_context(context_id: str = Path(..., description="監査コンテキストID")):
    """
    監査コンテキスト情報を取得
    
    指定されたIDに対応する監査コンテキストの詳細情報を取得します。
    
    Args:
        context_id: 監査コンテキストID
        
    Returns:
        監査コンテキスト情報
    """
    try:
        context_manager = get_context_manager()
        context_info = await context_manager.get_audit_context(context_id)
        
        if not context_info:
            raise HTTPException(status_code=404, detail=f"監査コンテキスト {context_id} が見つかりません")
            
        return context_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"監査コンテキスト取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"監査コンテキスト取得エラー: {str(e)}")


@router.post("/contexts/{context_id}/agents", response_model=Dict[str, Any])
async def start_agent_workflow(
    workflow: AgentWorkflowStart,
    context_id: str = Path(..., description="監査コンテキストID")
):
    """
    エージェントのワークフローを開始
    
    指定された監査コンテキスト内で新しいエージェントワークフローを開始します。
    
    Args:
        context_id: 監査コンテキストID
        workflow: エージェント情報と初期状態
        
    Returns:
        作成されたワークフロー情報
    """
    try:
        context_manager = get_context_manager()
        
        # コンテキストの存在確認
        context_info = await context_manager.get_audit_context(context_id)
        if not context_info:
            raise HTTPException(status_code=404, detail=f"監査コンテキスト {context_id} が見つかりません")
        
        # ワークフロー開始
        workflow_id = await context_manager.start_agent_workflow(
            workflow.agent_id, context_id, workflow.initial_state
        )
        
        # 現在の状態を取得
        state = await context_manager.get_agent_state(workflow.agent_id, context_id)
        
        return {
            "workflow_id": workflow_id,
            "agent_id": workflow.agent_id,
            "context_id": context_id,
            "state": state
        }
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"ワークフロー開始エラー (パラメーター不正): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"ワークフロー開始エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ワークフロー開始エラー: {str(e)}")


@router.post("/contexts/{context_id}/events", response_model=Dict[str, Any])
async def process_agent_event(
    event: AgentEvent,
    context_id: str = Path(..., description="監査コンテキストID")
):
    """
    エージェントイベントを処理
    
    指定された監査コンテキスト内のエージェントにイベントを送信し、処理させます。
    
    Args:
        context_id: 監査コンテキストID
        event: 処理するイベント情報
        
    Returns:
        イベント処理結果
    """
    try:
        context_manager = get_context_manager()
        
        # コンテキストの存在確認
        context_info = await context_manager.get_audit_context(context_id)
        if not context_info:
            raise HTTPException(status_code=404, detail=f"監査コンテキスト {context_id} が見つかりません")
        
        # イベントデータを準備
        event_data = {
            "type": event.event_type,
            **event.data
        }
        
        # イベント処理
        result = await context_manager.process_agent_event(
            event.agent_id, context_id, event_data
        )
        
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"イベント処理エラー (パラメーター不正): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"イベント処理エラー: {e}")
        raise HTTPException(status_code=500, detail=f"イベント処理エラー: {str(e)}")


@router.get("/contexts/{context_id}/agents/{agent_id}/state", response_model=Dict[str, Any])
async def get_agent_state(
    context_id: str = Path(..., description="監査コンテキストID"),
    agent_id: str = Path(..., description="エージェントID")
):
    """
    エージェントの状態を取得
    
    指定された監査コンテキスト内のエージェントの現在の状態を取得します。
    
    Args:
        context_id: 監査コンテキストID
        agent_id: エージェントID
        
    Returns:
        エージェントの現在の状態
    """
    try:
        context_manager = get_context_manager()
        
        # 状態取得
        state = await context_manager.get_agent_state(agent_id, context_id)
        
        if not state:
            raise HTTPException(status_code=404, detail=f"エージェント {agent_id} の状態が見つかりません")
            
        return state
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"状態取得エラー (パラメーター不正): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"状態取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"状態取得エラー: {str(e)}")


@router.get("/contexts/{context_id}/agents/{agent_id}/checkpoints", response_model=List[Dict[str, Any]])
async def get_agent_checkpoints(
    context_id: str = Path(..., description="監査コンテキストID"),
    agent_id: str = Path(..., description="エージェントID")
):
    """
    エージェントのチェックポイント一覧を取得
    
    指定された監査コンテキスト内のエージェントのチェックポイント一覧を取得します。
    
    Args:
        context_id: 監査コンテキストID
        agent_id: エージェントID
        
    Returns:
        チェックポイントのリスト
    """
    try:
        context_manager = get_context_manager()
        
        # チェックポイント一覧取得
        checkpoints = await context_manager.get_agent_checkpoints(agent_id, context_id)
        return checkpoints
    except ValueError as e:
        logger.error(f"チェックポイント一覧取得エラー (パラメーター不正): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"チェックポイント一覧取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"チェックポイント一覧取得エラー: {str(e)}")


@router.post("/contexts/{context_id}/agents/{agent_id}/checkpoints/{checkpoint_id}/restore", response_model=Dict[str, Any])
async def restore_agent_checkpoint(
    context_id: str = Path(..., description="監査コンテキストID"),
    agent_id: str = Path(..., description="エージェントID"),
    checkpoint_id: str = Path(..., description="チェックポイントID")
):
    """
    エージェントのチェックポイントから復元
    
    指定された監査コンテキスト内のエージェントの状態をチェックポイントから復元します。
    
    Args:
        context_id: 監査コンテキストID
        agent_id: エージェントID
        checkpoint_id: チェックポイントID
        
    Returns:
        復元された状態
    """
    try:
        context_manager = get_context_manager()
        
        # チェックポイント復元
        restored_state = await context_manager.restore_agent_checkpoint(
            agent_id, context_id, checkpoint_id
        )
        
        if not restored_state:
            raise HTTPException(status_code=404, detail=f"チェックポイント {checkpoint_id} が見つかりません")
            
        return restored_state
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"チェックポイント復元エラー (パラメーター不正): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"チェックポイント復元エラー: {e}")
        raise HTTPException(status_code=500, detail=f"チェックポイント復元エラー: {str(e)}")


@router.get("/contexts/{context_id}/status", response_model=Dict[str, Any])
async def get_audit_status(
    context_id: str = Path(..., description="監査コンテキストID")
):
    """
    監査の全体状況を取得
    
    指定された監査コンテキストの全体的な状況を取得します。
    すべてのエージェントの状態を含みます。
    
    Args:
        context_id: 監査コンテキストID
        
    Returns:
        監査の状況情報
    """
    try:
        context_manager = get_context_manager()
        
        # 監査状況取得
        status = await context_manager.get_audit_status(context_id)
        return status
    except ValueError as e:
        logger.error(f"監査状況取得エラー (パラメーター不正): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"監査状況取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"監査状況取得エラー: {str(e)}")


@router.get("/contexts/{context_id}/sharing-history", response_model=List[Dict[str, Any]])
async def get_context_sharing_history(
    context_id: str = Path(..., description="監査コンテキストID"),
    from_agent: Optional[str] = Query(None, description="送信元エージェント（フィルター用）"),
    to_agent: Optional[str] = Query(None, description="送信先エージェント（フィルター用）")
):
    """
    コンテキスト共有の履歴を取得
    
    指定された監査コンテキスト内でのエージェント間コンテキスト共有の履歴を取得します。
    
    Args:
        context_id: 監査コンテキストID
        from_agent: 送信元エージェント（フィルタリング用、オプション）
        to_agent: 送信先エージェント（フィルタリング用、オプション）
        
    Returns:
        共有履歴のリスト
    """
    try:
        context_manager = get_context_manager()
        
        # 共有履歴取得
        history = await context_manager.get_context_sharing_history(
            context_id, from_agent, to_agent
        )
        return history
    except ValueError as e:
        logger.error(f"共有履歴取得エラー (パラメーター不正): {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"共有履歴取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"共有履歴取得エラー: {str(e)}") 