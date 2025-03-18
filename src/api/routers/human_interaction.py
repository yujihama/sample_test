"""
ヒューマンインタラクションAPI

このモジュールは、ヒューマンインタラクションに関するAPIエンドポイントを提供します。
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import uuid

from src.utils.db_manager import get_db
from src.core.workflow import get_workflow_status, execute_workflow
from src.models.schema import MessageType, MessagePriority
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/human",
    tags=["human"],
    responses={404: {"description": "Not found"}}
)

# モデル定義
class HumanQuery(BaseModel):
    """ヒューマンクエリ"""
    query_text: str = Field(..., description="クエリテキスト")
    context: Optional[Dict[str, Any]] = Field(None, description="クエリコンテキスト")
    workflow_id: Optional[str] = Field(None, description="関連ワークフローID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query_text": "この予算変更は規程に準拠していますか？",
                "context": {
                    "department": "営業部",
                    "current_budget": 1000000,
                    "requested_budget": 1200000,
                    "reason": "新規プロジェクト対応"
                },
                "workflow_id": None
            }
        }
    )

class HumanResponse(BaseModel):
    """ヒューマン応答"""
    query_id: str = Field(..., description="クエリID")
    response_text: str = Field(..., description="応答テキスト")
    additional_data: Optional[Dict[str, Any]] = Field(None, description="追加データ")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query_id": "12345678-1234-5678-1234-567812345678",
                "response_text": "はい、規程に準拠しています。",
                "additional_data": {
                    "details": "予算変更額が20%以内であり、部長権限で承認可能です。",
                    "approved": True
                }
            }
        }
    )

# エンドポイント定義
@router.post("/query")
async def submit_query(
    query: HumanQuery,
    db: Session = Depends(get_db)
):
    """ヒューマンクエリを送信する"""
    try:
        query_id = str(uuid.uuid4())
        
        # クエリをデータベースに保存
        # TODO: 実際のクエリ保存処理を実装
        
        return {
            "query_id": query_id,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"クエリ送信エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/response")
async def submit_response(
    response: HumanResponse,
    db: Session = Depends(get_db)
):
    """ヒューマン応答を送信する"""
    try:
        # 応答をデータベースに保存
        # TODO: 実際の応答保存処理を実装
        
        return {
            "status": "completed",
            "updated_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"応答送信エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))