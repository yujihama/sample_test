"""
監査手続き管理用のルーター
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from src.models.repositories import AuditProcedureRepository
from src.utils.db_manager import get_db_context

router = APIRouter(
    prefix="/procedures",
    tags=["procedures"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)

@router.post("")
async def create_procedure(
    procedure_data: Dict[str, Any]
) -> Dict[str, Any]:
    """監査手続きを作成する"""
    with get_db_context() as db:
        try:
            repo = AuditProcedureRepository(db)
            procedure = repo.create(procedure_data)
            return {"id": procedure.id, "status": "created"}
        except Exception as e:
            db.rollback()
            logger.error(f"監査手続きの作成中にエラーが発生しました: {str(e)}")
            logger.exception(e)
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/{procedure_id}")
async def get_procedure(
    procedure_id: str
) -> Dict[str, Any]:
    """監査手続きを取得する"""
    with get_db_context() as db:
        try:
            repo = AuditProcedureRepository(db)
            procedure = repo.get_by_id(db, procedure_id)
            if not procedure:
                raise HTTPException(status_code=404, detail="Procedure not found")
            return {
                "id": procedure.id,
                "title": procedure.title,
                "description": procedure.description,
                "risk_areas": procedure.risk_areas,
                "required_data_fields": procedure.required_data_fields,
                "created_at": procedure.created_at,
                "updated_at": procedure.updated_at
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) 