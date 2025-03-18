"""
エラー管理用のAPIエンドポイント
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any
from datetime import datetime, UTC
from src.api.dependencies import get_current_user

router = APIRouter(
    prefix="/errors",
    tags=["error_management"],
    responses={404: {"description": "Not found"}},
)

@router.post("/report")
async def report_error(
    error_data: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """エラーレポートを送信するエンドポイント"""
    try:
        # モックレスポンスを返す
        error_id = "ERR_" + datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return {
            "error_id": error_id,
            "status": "received",
            "task_id": error_data.get("task_id"),
            "error_type": error_data.get("error_type"),
            "description": error_data.get("description"),
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/{error_id}")
async def get_error_status(
    error_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """エラー状態を確認するエンドポイント"""
    try:
        # モックレスポンスを返す
        return {
            "error_id": error_id,
            "status": "reported",
            "task_id": "integration_002",
            "error_type": "validation_error",
            "description": "不正なタスクデータ形式",
            "resolution": "エラーが報告され、対応待ちです",
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 