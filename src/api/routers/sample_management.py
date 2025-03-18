"""
サンプルデータ管理用のルーター
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from src.models.repositories import SampleDataRepository
from src.utils.db_manager import get_db_context

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/samples",
    tags=["samples"],
    responses={404: {"description": "Not found"}},
)

@router.post("")
async def create_sample(
    sample_data: Dict[str, Any]
) -> Dict[str, Any]:
    """サンプルデータを作成する"""
    logger.info(f"サンプルデータ作成リクエスト: {sample_data}")
    with get_db_context() as db:
        try:
            repo = SampleDataRepository(db)
            sample = repo.create(sample_data)
            logger.info(f"サンプルデータを作成しました: {sample.id}")
            return {"id": sample.id, "status": "created"}
        except Exception as e:
            logger.error(f"サンプルデータの作成中にエラーが発生しました: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/{sample_id}")
async def get_sample(
    sample_id: str
) -> Dict[str, Any]:
    """サンプルデータを取得する"""
    logger.info(f"サンプルデータ取得リクエスト: {sample_id}")
    with get_db_context() as db:
        try:
            repo = SampleDataRepository(db)
            sample = repo.get_by_id(sample_id)
            if not sample:
                logger.warning(f"サンプルデータが見つかりません: {sample_id}")
                raise HTTPException(status_code=404, detail="Sample not found")
            logger.info(f"サンプルデータを取得しました: {sample_id}")
            return {
                "id": sample.id,
                "filename": sample.filename,
                "file_path": sample.file_path,
                "file_size": sample.file_size,
                "file_type": sample.file_type,
                "row_count": sample.row_count,
                "column_count": sample.column_count,
                "columns": sample.columns,
                "procedure_id": sample.procedure_id,
                "file_metadata": sample.file_metadata
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"サンプルデータの取得中にエラーが発生しました: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e)) 