"""
サンプルデータアップロード用のルーター
"""

import os
import uuid
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import pandas as pd

from src.models.repositories import SampleDataRepository
from src.utils.db_manager import get_db_context
from src.utils.data_utils import load_sample_data
from src.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["samples"])

@router.post("/upload-sample")
async def upload_sample(
    file: UploadFile = File(...),
    procedure_id: str = Query(..., description="関連する監査手続きID")
) -> Dict[str, Any]:
    """
    サンプルデータファイルをアップロードする
    
    Args:
        file: アップロードするファイル
        procedure_id: 関連する監査手続きID
        
    Returns:
        Dict[str, Any]: アップロード結果（サンプルID等）
    """
    logger.info(f"サンプルアップロードリクエスト: {file.filename}, 監査手続きID: {procedure_id}")
    try:
        # サンプルIDを生成
        sample_id = f"sample-{uuid.uuid4()}"
        
        # アップロードディレクトリ内のサブディレクトリを決定
        upload_dir = os.path.join(settings.UPLOAD_DIR, "samples")
        os.makedirs(upload_dir, exist_ok=True)
        
        # ファイル名の組み立て (同名ファイルの上書きを防ぐため)
        file_name = os.path.basename(file.filename)
        base_name, extension = os.path.splitext(file_name)
        file_path = os.path.join(upload_dir, f"{base_name}_{sample_id}{extension}")
        
        # ファイルを保存
        with open(file_path, "wb") as out_file:
            content = await file.read()
            out_file.write(content)
        
        # ファイルの基本情報を取得
        file_size = len(content)
        file_type = extension.lstrip('.')
        
        # データファイル分析 (CSVやExcelの場合)
        row_count = 0
        column_count = 0
        columns = []
        
        try:
            if file_type.lower() in ['csv', 'xlsx', 'xls']:
                # CSVまたはExcelファイルの場合はデータフレームとして読み込む
                df, metadata = load_sample_data(file_path)
                row_count = len(df)
                column_count = len(df.columns)
                columns = df.columns.tolist()
        except Exception as e:
            logger.warning(f"サンプルデータの分析中にエラーが発生しました: {e}")
            # 分析エラーはアップロード自体を失敗させない
        
        # メタデータをデータベースに保存
        sample_metadata = {
            "id": sample_id,
            "procedure_id": procedure_id,
            "filename": file.filename,
            "file_path": file_path,
            "file_size": file_size,
            "file_type": file_type,
            "row_count": row_count,
            "column_count": column_count,
            "columns": columns,
            "file_metadata": {
                "content_type": file.content_type
            }
        }
        
        with get_db_context() as db:
            repo = SampleDataRepository(db)
            sample_record = repo.create(sample_metadata)
        
        logger.info(f"サンプルデータをアップロードしました: {sample_id}, 保存先: {file_path}")
        return {
            "status": "success",
            "message": f"ファイル '{file.filename}' が正常にアップロードされました",
            "sample_id": sample_id,
            "procedure_id": procedure_id,
            "file_info": {
                "filename": file.filename,
                "file_size": file_size,
                "file_type": file_type,
                "row_count": row_count,
                "column_count": column_count
            }
        }
        
    except Exception as e:
        logger.error(f"サンプルアップロード中にエラーが発生しました: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 