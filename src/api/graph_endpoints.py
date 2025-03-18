"""
グラフAPIエンドポイント

このモジュールでは、LangGraphに基づいたワークフローの管理と実行のためのAPIエンドポイントを提供します。
以下の機能を含みます：
- ワークフローグラフの作成
- イベント処理によるグラフの進行
- 状態取得
- チェックポイントの管理と復元
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Body, Query
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import json
import uuid
from datetime import datetime

from loguru import logger
from src.services.graph_executor import GraphExecutor, get_graph_executor


# モデル定義
class WorkflowCreateRequest(BaseModel):
    """ワークフローグラフ作成リクエスト"""
    workflow_id: Optional[str] = Field(None, description="カスタムワークフローID（省略可）")
    procedure_id: str = Field(..., description="監査手続きID")
    procedure_text: str = Field(..., description="監査手続き内容")
    sample_id: Optional[str] = Field(None, description="サンプルデータID")
    initial_state: Optional[Dict[str, Any]] = Field(None, description="初期状態データ")


class EventRequest(BaseModel):
    """グラフイベントリクエスト"""
    event_type: str = Field(..., description="イベントタイプ")
    payload: Dict[str, Any] = Field(..., description="イベントデータ")


class WorkflowResponse(BaseModel):
    """ワークフロー操作レスポンス"""
    workflow_id: str
    status: str
    message: str


class EventResponse(BaseModel):
    """イベント処理レスポンス"""
    event_id: str
    status: str
    message: str


# ルーター定義
router = APIRouter(prefix="/graph", tags=["graph"])


# エンドポイント
@router.post("/workflows", response_model=WorkflowResponse, status_code=201)
async def create_workflow_graph(
    request: WorkflowCreateRequest,
    background_tasks: BackgroundTasks,
    executor: GraphExecutor = Depends(get_graph_executor)
):
    """
    新しいワークフローグラフを作成する
    
    監査手続きとオプションのサンプルデータに基づいて、
    新しいワークフローグラフを作成します。
    """
    try:
        # 初期状態の構築
        initial_state = request.initial_state or {}
        initial_state.update({
            "workflow_id": request.workflow_id,
            "procedure_id": request.procedure_id,
            "procedure_text": request.procedure_text,
            "sample_id": request.sample_id
        })
        
        # バックグラウンドでグラフ作成（非同期）
        state = await executor.create_workflow(initial_state)
        
        return {
            "workflow_id": state["workflow_id"],
            "status": "created",
            "message": "ワークフローグラフが作成されました"
        }
    except Exception as e:
        logger.error(f"ワークフローグラフの作成に失敗しました: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ワークフローグラフの作成に失敗しました: {str(e)}")


@router.post("/{workflow_id}/events", response_model=EventResponse, status_code=202)
async def process_graph_event(
    workflow_id: str,
    event: EventRequest,
    background_tasks: BackgroundTasks,
    executor: GraphExecutor = Depends(get_graph_executor)
):
    """
    ワークフローグラフにイベントを送信する
    
    指定されたワークフローグラフに対してイベントを処理し、
    グラフの進行や状態の更新を行います。
    """
    try:
        # イベントデータの準備
        event_id = f"evt-{uuid.uuid4().hex[:8]}"
        event_data = {
            "event_id": event_id,
            "event_type": event.event_type,
            "payload": event.payload,
            "timestamp": datetime.now().isoformat()
        }
        
        # バックグラウンドでイベント処理（非同期）
        background_tasks.add_task(
            executor.process_event,
            workflow_id,
            event_data
        )
        
        return {
            "event_id": event_id,
            "status": "accepted",
            "message": "イベントが受け付けられました"
        }
    except ValueError as e:
        logger.error(f"ワークフローが見つかりません: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"イベント処理に失敗しました: {str(e)}")
        raise HTTPException(status_code=500, detail=f"イベント処理に失敗しました: {str(e)}")


@router.get("/{workflow_id}/state", response_model=Dict[str, Any])
async def get_workflow_state(
    workflow_id: str,
    executor: GraphExecutor = Depends(get_graph_executor)
):
    """
    ワークフローグラフの現在の状態を取得する
    
    指定されたワークフローグラフの最新の状態を取得します。
    """
    try:
        state = await executor.get_state(workflow_id)
        if not state:
            raise HTTPException(status_code=404, detail=f"ワークフロー {workflow_id} が見つかりません")
        return state
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"状態取得に失敗しました: {str(e)}")
        raise HTTPException(status_code=500, detail=f"状態取得に失敗しました: {str(e)}")


@router.get("/{workflow_id}/checkpoints", response_model=List[Dict[str, Any]])
async def list_checkpoints(
    workflow_id: str,
    executor: GraphExecutor = Depends(get_graph_executor)
):
    """
    ワークフローグラフのチェックポイント一覧を取得する
    
    指定されたワークフローグラフの保存されたチェックポイント一覧を取得します。
    """
    try:
        checkpoints = await executor.list_checkpoints(workflow_id)
        return checkpoints
    except Exception as e:
        logger.error(f"チェックポイント一覧取得に失敗しました: {str(e)}")
        raise HTTPException(status_code=500, detail=f"チェックポイント一覧取得に失敗しました: {str(e)}")


@router.get("/{workflow_id}/checkpoints/{checkpoint_id}", response_model=Dict[str, Any])
async def get_checkpoint(
    workflow_id: str,
    checkpoint_id: str,
    executor: GraphExecutor = Depends(get_graph_executor)
):
    """
    特定のチェックポイントを取得する
    
    指定されたワークフローグラフの特定のチェックポイントを取得します。
    """
    try:
        checkpoint = await executor.get_checkpoint(workflow_id, checkpoint_id)
        if not checkpoint:
            raise HTTPException(status_code=404, detail=f"チェックポイント {checkpoint_id} が見つかりません")
        return checkpoint
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"チェックポイント取得に失敗しました: {str(e)}")
        raise HTTPException(status_code=500, detail=f"チェックポイント取得に失敗しました: {str(e)}")


@router.post("/{workflow_id}/restore/{checkpoint_id}", response_model=Dict[str, Any])
async def restore_from_checkpoint(
    workflow_id: str,
    checkpoint_id: str,
    executor: GraphExecutor = Depends(get_graph_executor)
):
    """
    チェックポイントから状態を復元する
    
    指定されたチェックポイントの状態にワークフローを復元します。
    """
    try:
        state = await executor.restore_checkpoint(workflow_id, checkpoint_id)
        if not state:
            raise HTTPException(status_code=404, detail=f"チェックポイント {checkpoint_id} が見つかりません")
        return {
            "workflow_id": workflow_id,
            "checkpoint_id": checkpoint_id,
            "status": "restored",
            "message": "チェックポイントから状態を復元しました",
            "state": state
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"チェックポイントからの復元に失敗しました: {str(e)}")
        raise HTTPException(status_code=500, detail=f"チェックポイントからの復元に失敗しました: {str(e)}") 