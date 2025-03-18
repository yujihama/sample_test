"""
統合されたワークフロー管理API

このモジュールは、監査ワークフローの管理に関する統合されたAPIエンドポイントを提供します。
"""

import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Path, Depends
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy.orm import Session

from src.utils.db_manager import get_db_context
from src.core.workflow import (
    create_audit_workflow,
    get_workflow_status,
    list_workflows,
    reset_workflow,
    clean_workflow,
    audit_workflow,
    ensure_valid_state
)
from src.models.schema import WorkflowStatus
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
    responses={404: {"description": "Not found"}}
)

# モデル定義
class WorkflowRequest(BaseModel):
    """ワークフロー作成リクエスト"""
    audit_procedure_id: str = Field(..., description="監査手続きID")
    sample_data_id: str = Field(..., description="サンプルデータID")
    procedure_text: Optional[str] = Field(None, description="監査手続きの内容テキスト")
    initial_state: str = Field("created", description="初期状態")
    config: Optional[Dict[str, Any]] = Field(None, description="追加設定")

class WorkflowResponse(BaseModel):
    """ワークフロー応答"""
    workflow_id: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime]
    audit_procedure_id: str
    sample_data_id: str
    message: Optional[str]

# エンドポイント定義
@router.post("", response_model=WorkflowResponse)
async def create_workflow(
    workflow_request: WorkflowRequest,
    background_tasks: BackgroundTasks
):
    """新しいワークフローを作成する"""
    with get_db_context() as db:
        try:
            workflow_id = str(uuid.uuid4())
            initial_state = {
                "workflow_id": workflow_id,
                "status": workflow_request.initial_state,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "audit_procedure_id": workflow_request.audit_procedure_id,
                "sample_data_id": workflow_request.sample_data_id
            }
            
            initial_state = ensure_valid_state(initial_state)
            workflow = await create_audit_workflow(
                initial_state=initial_state,
                audit_procedure_id=workflow_request.audit_procedure_id,
                procedure_text=workflow_request.procedure_text,
                sample_data_id=workflow_request.sample_data_id
            )
            
            return WorkflowResponse(
                workflow_id=workflow_id,
                status=workflow_request.initial_state,
                created_at=datetime.fromisoformat(initial_state["created_at"]),
                updated_at=datetime.fromisoformat(initial_state["updated_at"]),
                audit_procedure_id=workflow_request.audit_procedure_id,
                sample_data_id=workflow_request.sample_data_id,
                message="ワークフローが正常に作成されました"
            )
        except Exception as e:
            logger.error(f"ワークフロー作成エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=List[WorkflowResponse])
async def list_all_workflows(
    status: Optional[str] = Query(None, description="フィルタするステータス"),
    limit: int = Query(10, description="取得する最大件数", ge=1, le=100),
    offset: int = Query(0, description="スキップする件数", ge=0)
):
    """ワークフロー一覧を取得する"""
    with get_db_context() as db:
        try:
            workflows = await list_workflows(db, status=status, limit=limit, offset=offset)
            return [
                WorkflowResponse(
                    workflow_id=w.id,
                    status=w.status,
                    created_at=w.created_at,
                    updated_at=w.updated_at,
                    audit_procedure_id=w.audit_procedure_id,
                    sample_data_id=w.sample_data_id,
                    message=None
                )
                for w in workflows
            ]
        except Exception as e:
            logger.error(f"ワークフロー一覧取得エラー: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str = Path(..., description="ワークフローID"),
    db: Session = Depends(get_db_context)
):
    """特定のワークフローを取得する"""
    try:
        workflow = await get_workflow_status(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"ワークフロー {workflow_id} が見つかりません")
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            status=workflow["status"],
            created_at=workflow["created_at"],
            updated_at=workflow.get("updated_at"),
            audit_procedure_id=workflow["procedure_id"],
            sample_data_id=workflow["sample_data_id"],
            message=None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ワークフロー取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{workflow_id}/actions/start")
async def start_workflow(
    workflow_id: str = Path(..., description="ワークフローID"),
    db: Session = Depends(get_db_context)
):
    """ワークフローを開始する"""
    try:
        workflow = await get_workflow_status(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"ワークフロー {workflow_id} が見つかりません")
        
        if workflow["status"] != "created":
            raise HTTPException(status_code=400, detail=f"ワークフロー {workflow_id} は既に開始されているか、完了しています")
        
        # ワークフローの状態を更新
        workflow["status"] = "in_progress"
        workflow["updated_at"] = datetime.now()
        
        # 状態を保存
        with get_db_context() as db:
            await audit_workflow(workflow_id, workflow)
        
        return {
            "message": f"ワークフロー {workflow_id} を開始しました",
            "status": "started", 
            "workflow_id": workflow_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ワークフロー開始エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{workflow_id}/actions/pause")
async def pause_workflow(
    workflow_id: str = Path(..., description="ワークフローID"),
    db: Session = Depends(get_db_context)
):
    """ワークフローを一時停止する"""
    try:
        workflow = await get_workflow_status(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"ワークフロー {workflow_id} が見つかりません")
        
        if workflow["status"] != "in_progress":
            raise HTTPException(status_code=400, detail="実行中のワークフローのみ一時停止できます")
        
        # 一時停止処理
        # TODO: 一時停止の実装
        return {"status": "paused", "workflow_id": workflow_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ワークフロー一時停止エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{workflow_id}/actions/resume")
async def resume_workflow(
    workflow_id: str = Path(..., description="ワークフローID"),
    db: Session = Depends(get_db_context)
):
    """一時停止したワークフローを再開する"""
    try:
        workflow = await get_workflow_status(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"ワークフロー {workflow_id} が見つかりません")
        
        if workflow["status"] != "paused":
            raise HTTPException(status_code=400, detail="一時停止中のワークフローのみ再開できます")
        
        # 再開処理
        # TODO: 再開の実装
        return {"status": "running", "workflow_id": workflow_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ワークフロー再開エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str = Path(..., description="ワークフローID"),
    db: Session = Depends(get_db_context)
):
    """ワークフローを削除する"""
    try:
        workflow = await get_workflow_status(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"ワークフロー {workflow_id} が見つかりません")
        
        # 削除処理
        await clean_workflow(workflow_id)
        return {"status": "deleted", "workflow_id": workflow_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ワークフロー削除エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 