"""
サンプルバッチ管理API

サンプルバッチの作成、取得、更新、削除およびサンプル管理のためのエンドポイント。
"""

import os
import json
import uuid
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path as PathLib
from fastapi import Path as FastAPIPath
import aiofiles

from src.models.schema import (
    SampleBatchCreate, SampleBatchResponse, SampleCreate, SampleResponse, 
    SampleResultResponse, BatchUploadJobResponse, SampleListResponse, BatchListResponse
)
from src.models.repositories import (
    SampleBatchRepository, SampleRepository, SampleResultRepository, BatchUploadJobRepository,
    WorkflowRepository, FileRepository
)
from src.utils.db_manager import get_db, get_db_context
from src.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/sample-batches",
    tags=["sample_batches"],
    responses={404: {"description": "Not found"}}
)

@router.post("", response_model=SampleBatchResponse)
async def create_batch(
    batch_data: SampleBatchCreate,
    db: Session = Depends(get_db)
):
    """新しいサンプルバッチを作成する"""
    try:
        repo = SampleBatchRepository(db)
        batch = repo.create(
            name=batch_data.name,
            description=batch_data.description,
            metadata=batch_data.metadata
        )
        
        return SampleBatchResponse(
            id=batch.id,
            name=batch.name,
            description=batch.description,
            status=batch.status,
            sample_count=batch.sample_count,
            created_at=batch.created_at,
            updated_at=batch.updated_at,
            metadata=batch.meta_data
        )
    except Exception as e:
        logger.error(f"バッチ作成エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"バッチの作成に失敗しました: {str(e)}")


@router.get("", response_model=BatchListResponse)
async def list_batches(
    page: int = Query(1, ge=1, description="ページ番号"),
    page_size: int = Query(20, ge=1, le=100, description="1ページあたりの件数"),
    status: Optional[str] = Query(None, description="ステータスでフィルタリング"),
    sort_by: str = Query("created_at", description="ソート項目"),
    sort_order: str = Query("desc", description="ソート順序 (asc, desc)"),
    db: Session = Depends(get_db)
):
    """サンプルバッチの一覧を取得する"""
    try:
        repo = SampleBatchRepository(db)
        batches, total = repo.get_all(
            page=page,
            per_page=page_size,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return BatchListResponse(
            batches=[
                SampleBatchResponse(
                    id=batch.id,
                    name=batch.name,
                    description=batch.description,
                    status=batch.status,
                    sample_count=batch.sample_count,
                    created_at=batch.created_at,
                    updated_at=batch.updated_at,
                    metadata=batch.meta_data
                ) for batch in batches
            ],
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"バッチ一覧取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"バッチ一覧の取得に失敗しました: {str(e)}")


@router.get("/{batch_id}", response_model=SampleBatchResponse)
async def get_batch(
    batch_id: str = FastAPIPath(..., description="バッチID"),
    db: Session = Depends(get_db)
):
    """指定されたIDのサンプルバッチを取得する"""
    try:
        repo = SampleBatchRepository(db)
        batch = repo.get_by_id(batch_id)
        
        if not batch:
            raise HTTPException(status_code=404, detail=f"バッチID {batch_id} が見つかりません")
        
        return SampleBatchResponse(
            id=batch.id,
            name=batch.name,
            description=batch.description,
            status=batch.status,
            sample_count=batch.sample_count,
            created_at=batch.created_at,
            updated_at=batch.updated_at,
            metadata=batch.meta_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"バッチ取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"バッチの取得に失敗しました: {str(e)}")


@router.put("/{batch_id}", response_model=SampleBatchResponse)
async def update_batch(
    batch_data: SampleBatchCreate,
    batch_id: str = FastAPIPath(..., description="バッチID"),
    db: Session = Depends(get_db)
):
    """サンプルバッチ情報を更新する"""
    try:
        repo = SampleBatchRepository(db)
        batch = repo.get_by_id(batch_id)
        
        if not batch:
            raise HTTPException(status_code=404, detail=f"バッチID {batch_id} が見つかりません")
        
        updated_batch = repo.update(
            batch_id=batch_id,
            name=batch_data.name,
            description=batch_data.description,
            metadata=batch_data.metadata
        )
        
        return SampleBatchResponse(
            id=updated_batch.id,
            name=updated_batch.name,
            description=updated_batch.description,
            status=updated_batch.status,
            sample_count=updated_batch.sample_count,
            created_at=updated_batch.created_at,
            updated_at=updated_batch.updated_at,
            metadata=updated_batch.meta_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"バッチ更新エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"バッチの更新に失敗しました: {str(e)}")


@router.get("/{batch_id}/samples", response_model=SampleListResponse)
async def list_samples(
    batch_id: str = FastAPIPath(..., description="バッチID"),
    page: int = Query(1, ge=1, description="ページ番号"),
    page_size: int = Query(20, ge=1, le=100, description="1ページあたりの件数"),
    status: Optional[str] = Query(None, description="ステータスでフィルタリング"),
    sort_by: str = Query("created_at", description="ソート項目"),
    sort_order: str = Query("desc", description="ソート順序 (asc, desc)"),
    db: Session = Depends(get_db)
):
    """バッチ内のサンプル一覧を取得する"""
    try:
        # バッチの存在確認
        batch_repo = SampleBatchRepository(db)
        batch = batch_repo.get_by_id(batch_id)
        
        if not batch:
            raise HTTPException(status_code=404, detail=f"バッチID {batch_id} が見つかりません")
        
        # サンプル一覧取得
        sample_repo = SampleRepository(db)
        samples, total = sample_repo.get_by_batch_id(
            batch_id=batch_id,
            page=page,
            per_page=page_size,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return SampleListResponse(
            samples=[
                SampleResponse(
                    id=sample.id,
                    batch_id=sample.batch_id,
                    name=sample.name,
                    description=sample.description,
                    status=sample.status,
                    file_count=sample.file_count,
                    created_at=sample.created_at,
                    updated_at=sample.updated_at,
                    metadata=sample.meta_data
                ) for sample in samples
            ],
            total=total,
            page=page,
            page_size=page_size
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"サンプル一覧取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"サンプル一覧の取得に失敗しました: {str(e)}")


@router.post("/{batch_id}/samples", response_model=SampleResponse)
async def create_sample(
    sample_data: SampleCreate,
    batch_id: str = FastAPIPath(..., description="バッチID"),
    db: Session = Depends(get_db)
):
    """バッチに新しいサンプルを作成する"""
    try:
        # バッチの存在確認
        batch_repo = SampleBatchRepository(db)
        batch = batch_repo.get_by_id(batch_id)
        
        if not batch:
            raise HTTPException(status_code=404, detail=f"バッチID {batch_id} が見つかりません")
        
        # サンプル作成
        sample_repo = SampleRepository(db)
        sample = sample_repo.create(
            batch_id=batch_id,
            name=sample_data.name,
            description=sample_data.description,
            metadata=sample_data.metadata
        )
        
        return SampleResponse(
            id=sample.id,
            batch_id=sample.batch_id,
            name=sample.name,
            description=sample.description,
            status=sample.status,
            file_count=sample.file_count,
            created_at=sample.created_at,
            updated_at=sample.updated_at,
            metadata=sample.meta_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"サンプル作成エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"サンプルの作成に失敗しました: {str(e)}")


@router.get("/{batch_id}/samples/{sample_id}", response_model=SampleResponse)
async def get_sample(
    batch_id: str = FastAPIPath(..., description="バッチID"),
    sample_id: str = FastAPIPath(..., description="サンプルID"),
    db: Session = Depends(get_db)
):
    """指定されたサンプルの詳細を取得する"""
    try:
        # サンプル取得
        sample_repo = SampleRepository(db)
        sample = sample_repo.get_by_id(sample_id)
        
        if not sample:
            raise HTTPException(status_code=404, detail=f"サンプルID {sample_id} が見つかりません")
        
        # バッチIDの整合性確認
        if sample.batch_id != batch_id:
            raise HTTPException(status_code=400, detail=f"サンプル {sample_id} はバッチ {batch_id} に属していません")
        
        return SampleResponse(
            id=sample.id,
            batch_id=sample.batch_id,
            name=sample.name,
            description=sample.description,
            status=sample.status,
            file_count=sample.file_count,
            created_at=sample.created_at,
            updated_at=sample.updated_at,
            metadata=sample.meta_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"サンプル取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"サンプルの取得に失敗しました: {str(e)}")


@router.put("/{batch_id}/samples/{sample_id}", response_model=SampleResponse)
async def update_sample(
    sample_data: SampleCreate,
    batch_id: str = FastAPIPath(..., description="バッチID"),
    sample_id: str = FastAPIPath(..., description="サンプルID"),
    db: Session = Depends(get_db)
):
    """サンプル情報を更新する"""
    try:
        # サンプル取得
        sample_repo = SampleRepository(db)
        sample = sample_repo.get_by_id(sample_id)
        
        if not sample:
            raise HTTPException(status_code=404, detail=f"サンプルID {sample_id} が見つかりません")
        
        # バッチIDの整合性確認
        if sample.batch_id != batch_id:
            raise HTTPException(status_code=400, detail=f"サンプル {sample_id} はバッチ {batch_id} に属していません")
        
        # サンプル更新
        updated_sample = sample_repo.update(
            sample_id=sample_id,
            name=sample_data.name,
            description=sample_data.description,
            metadata=sample_data.metadata
        )
        
        return SampleResponse(
            id=updated_sample.id,
            batch_id=updated_sample.batch_id,
            name=updated_sample.name,
            description=updated_sample.description,
            status=updated_sample.status,
            file_count=updated_sample.file_count,
            created_at=updated_sample.created_at,
            updated_at=updated_sample.updated_at,
            metadata=updated_sample.meta_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"サンプル更新エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"サンプルの更新に失敗しました: {str(e)}")


@router.delete("/{batch_id}/samples/{sample_id}", response_model=SampleResponse)
async def delete_sample(
    batch_id: str = FastAPIPath(..., description="バッチID"),
    sample_id: str = FastAPIPath(..., description="サンプルID"),
    db: Session = Depends(get_db)
):
    """指定されたサンプルを削除する"""
    try:
        # サンプル取得
        sample_repo = SampleRepository(db)
        sample = sample_repo.get_by_id(sample_id)
        
        if not sample:
            raise HTTPException(status_code=404, detail=f"サンプルID {sample_id} が見つかりません")
        
        # バッチIDの整合性確認
        if sample.batch_id != batch_id:
            raise HTTPException(status_code=400, detail=f"サンプル {sample_id} はバッチ {batch_id} に属していません")
        
        # サンプル削除
        deleted = sample_repo.delete(sample_id)
        
        if not deleted:
            raise HTTPException(status_code=500, detail="サンプルの削除に失敗しました")
            
        return SampleResponse(
            id=sample.id,
            batch_id=sample.batch_id,
            name=sample.name,
            description=sample.description,
            status=sample.status,
            file_count=sample.file_count,
            created_at=sample.created_at,
            updated_at=sample.updated_at,
            metadata=sample.meta_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"サンプル削除エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"サンプルの削除に失敗しました: {str(e)}")


@router.get("/upload-status/{job_id}", response_model=BatchUploadJobResponse)
async def get_upload_status(
    job_id: str = FastAPIPath(..., description="アップロードジョブID"),
    db: Session = Depends(get_db)
):
    """フォルダアップロードの進捗状況を取得する"""
    try:
        job_repo = BatchUploadJobRepository(db)
        job = job_repo.get_by_id(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"アップロードジョブID {job_id} が見つかりません")
        
        return BatchUploadJobResponse(
            id=job.id,
            batch_id=job.batch_id,
            status=job.status,
            total_folders=job.total_folders,
            processed_folders=job.processed_folders,
            total_files=job.total_files,
            processed_files=job.processed_files,
            failed_files=job.failed_files,
            errors=job.errors if job.errors else [],
            started_at=job.started_at,
            updated_at=job.updated_at,
            estimated_completion=job.estimated_completion
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"アップロード状態取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"アップロード状態の取得に失敗しました: {str(e)}")


@router.post("/upload-folder", response_model=BatchUploadJobResponse)
async def upload_folder(
    batch_id: str = Form(..., description="バッチID"),
    folder_upload: UploadFile = File(..., description="アップロードするZIPファイル（フォルダ構造を含む）"),
    folder_structure: Optional[str] = Form(None, description="フォルダ構造の説明（JSON形式）"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    既存のバッチにフォルダをアップロードする
    
    ZIPファイル内の各トップレベルフォルダはサンプルとして処理されます。
    フォルダ内のファイルは対応するサンプルに追加されます。
    """
    try:
        # バッチの存在確認
        batch_repo = SampleBatchRepository(db)
        batch = batch_repo.get_by_id(batch_id)
        
        if not batch:
            raise HTTPException(status_code=404, detail=f"バッチID {batch_id} が見つかりません")
        
        # フォルダ構造のJSONを解析（提供されている場合）
        metadata_dict = {}
        if folder_structure:
            try:
                metadata_dict = json.loads(folder_structure)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="フォルダ構造のJSONが無効です")
        
        # 一時ディレクトリを作成
        job_id = f"upload-{uuid.uuid4()}"
        temp_dir = os.path.join(settings.UPLOAD_DIR, "temp", job_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        # ZIPファイルを一時ディレクトリに保存
        zip_path = os.path.join(temp_dir, "upload.zip")
        with open(zip_path, "wb") as f:
            content = await folder_upload.read()
            f.write(content)
        
        # アップロードジョブをデータベースに記録
        job_repo = BatchUploadJobRepository(db)
        job = job_repo.create(
            batch_id=batch_id,
            status="pending",
            total_folders=0,  # 後で更新
            processed_folders=0,
            total_files=0,  # 後で更新
            processed_files=0,
            failed_files=0
        )
        
        # バックグラウンドタスクでフォルダ処理を実行
        background_tasks.add_task(
            process_uploaded_folder,
            job_id=job.id,
            batch_id=batch_id,
            zip_path=zip_path,
            temp_dir=temp_dir
        )
        
        return BatchUploadJobResponse(
            id=job.id,
            batch_id=batch_id,
            status="pending",
            total_folders=0,
            processed_folders=0,
            total_files=0,
            processed_files=0,
            failed_files=0,
            errors=[],
            started_at=job.started_at,
            updated_at=job.updated_at,
            estimated_completion=None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"フォルダアップロードエラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"フォルダのアップロードに失敗しました: {str(e)}")


@router.post("/create-with-folders", response_model=BatchUploadJobResponse)
async def create_batch_with_folders(
    batch_name: str = Form(..., description="バッチ名"),
    batch_description: Optional[str] = Form(None, description="バッチの説明"),
    folder_upload: UploadFile = File(..., description="アップロードするZIPファイル（フォルダ構造を含む）"),
    metadata: Optional[str] = Form(None, description="バッチのメタデータ（JSON形式）"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    新しいバッチを作成し、フォルダをアップロードする
    
    ZIPファイル内の各トップレベルフォルダはサンプルとして処理されます。
    フォルダ内のファイルは対応するサンプルに追加されます。
    """
    try:
        # メタデータのJSONを解析（提供されている場合）
        metadata_dict = {}
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="メタデータのJSONが無効です")
        
        # 新しいバッチを作成
        batch_repo = SampleBatchRepository(db)
        batch = batch_repo.create(
            name=batch_name,
            description=batch_description,
            metadata=metadata_dict
        )
        
        # アップロードジョブを作成
        job_id = f"upload-{uuid.uuid4()}"
        
        # 一時ディレクトリを作成
        temp_dir = os.path.join(settings.UPLOAD_DIR, "temp", job_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        # ZIPファイルを一時ディレクトリに保存
        zip_path = os.path.join(temp_dir, "upload.zip")
        with open(zip_path, "wb") as f:
            content = await folder_upload.read()
            f.write(content)
        
        # アップロードジョブをデータベースに記録
        job_repo = BatchUploadJobRepository(db)
        job = job_repo.create(
            batch_id=batch.id,
            status="pending",
            total_folders=0,  # 後で更新
            processed_folders=0,
            total_files=0,  # 後で更新
            processed_files=0,
            failed_files=0
        )
        
        # バックグラウンドタスクでフォルダ処理を実行
        background_tasks.add_task(
            process_uploaded_folder,
            job_id=job.id,
            batch_id=batch.id,
            zip_path=zip_path,
            temp_dir=temp_dir
        )
        
        return BatchUploadJobResponse(
            id=job.id,
            batch_id=batch.id,
            status="pending",
            total_folders=0,
            processed_folders=0,
            total_files=0,
            processed_files=0,
            failed_files=0,
            errors=[],
            started_at=job.started_at,
            updated_at=job.updated_at,
            estimated_completion=None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"バッチ作成とフォルダアップロードエラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"バッチの作成とフォルダのアップロードに失敗しました: {str(e)}")


async def process_uploaded_folder(job_id: str, batch_id: str, zip_path: str, temp_dir: str):
    """
    アップロードされたZIPファイルを処理し、サンプルとファイルを作成する
    
    この関数はバックグラウンドタスクとして実行される
    """
    import zipfile
    import shutil
    from datetime import datetime, timedelta
    
    try:
        # データベース接続
        with get_db() as db:
            job_repo = BatchUploadJobRepository(db)
            sample_repo = SampleRepository(db)
            
            # ジョブのステータスを更新
            job = job_repo.update(
                job_id=job_id,
                status="processing"
            )
            
            # ZIPファイルを解凍
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # フォルダを検索（第一階層のディレクトリのみ）
            folders = [f for f in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, f))]
            
            # 総フォルダ数を更新
            total_folders = len(folders)
            job = job_repo.update(
                job_id=job_id,
                total_folders=total_folders
            )
            
            # 全ファイル数を計算
            total_files = 0
            for folder in folders:
                folder_path = os.path.join(extract_dir, folder)
                for root, _, files in os.walk(folder_path):
                    total_files += len(files)
            
            # 総ファイル数を更新
            job = job_repo.update(
                job_id=job_id,
                total_files=total_files
            )
            
            # 各フォルダをサンプルとして処理
            processed_folders = 0
            processed_files = 0
            failed_files = 0
            errors = []
            
            for folder in folders:
                folder_path = os.path.join(extract_dir, folder)
                
                try:
                    # サンプルを作成
                    sample = sample_repo.create(
                        batch_id=batch_id,
                        name=folder,
                        description=f"フォルダ '{folder}' から自動生成されたサンプル",
                        metadata={"source_folder": folder}
                    )
                    
                    # フォルダ内のファイルを処理
                    for root, _, files in os.walk(folder_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            relative_path = os.path.relpath(file_path, folder_path)
                            
                            try:
                                # ファイルをアップロードディレクトリにコピー
                                file_id = f"file-{uuid.uuid4()}"
                                dest_path = os.path.join(settings.UPLOAD_DIR, "files", file_id)
                                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                                shutil.copy2(file_path, dest_path)
                                
                                # ファイルメタデータを取得
                                file_size = os.path.getsize(dest_path)
                                file_type = os.path.splitext(file)[1].lstrip(".").lower()
                                
                                # ファイルをデータベースに登録
                                # ここでは実際のファイル登録ロジックを呼び出す必要がある
                                # （例えば、FileRepositoryを使用）
                                
                                processed_files += 1
                            except Exception as e:
                                failed_files += 1
                                errors.append(f"ファイル '{relative_path}' の処理エラー: {str(e)}")
                    
                    processed_folders += 1
                    
                    # 進捗を更新
                    job = job_repo.update(
                        job_id=job_id,
                        processed_folders=processed_folders,
                        processed_files=processed_files,
                        failed_files=failed_files,
                        errors=errors,
                        estimated_completion=(
                            datetime.now() + timedelta(seconds=(
                                (total_folders - processed_folders) *
                                (datetime.now() - job.started_at).total_seconds() / max(processed_folders, 1)
                            ))
                        ) if processed_folders > 0 else None
                    )
                except Exception as e:
                    errors.append(f"フォルダ '{folder}' の処理エラー: {str(e)}")
            
            # 処理完了
            final_status = "completed" if failed_files == 0 else "completed_with_errors"
            job = job_repo.update(
                job_id=job_id,
                status=final_status,
                processed_folders=processed_folders,
                processed_files=processed_files,
                failed_files=failed_files,
                errors=errors
            )
            
            # 一時ディレクトリの削除
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except Exception as e:
        logger.error(f"フォルダ処理エラー: {str(e)}", exc_info=True)
        
        # エラー状態を記録
        try:
            with get_db() as db:
                job_repo = BatchUploadJobRepository(db)
                job_repo.update(
                    job_id=job_id,
                    status="failed",
                    errors=[f"処理エラー: {str(e)}"]
                )
        except Exception as update_error:
            logger.error(f"エラー状態の更新に失敗: {str(update_error)}")
        
        # 一時ディレクトリの削除を試みる
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

# ファイル管理関連APIエンドポイント（互換性維持用）
@router.get("/{batch_id}/files", response_model=List[Dict[str, Any]])
async def get_batch_files(
    batch_id: str = FastAPIPath(..., description="バッチID"),
    db: Session = Depends(get_db)
):
    """互換性維持のためのエンドポイント：バッチ内のすべてのファイルを取得する"""
    try:
        # バッチの存在確認
        batch_repo = SampleBatchRepository(db)
        batch = batch_repo.get_by_id(batch_id)
        
        if not batch:
            raise HTTPException(status_code=404, detail=f"バッチID {batch_id} が見つかりません")
        
        # サンプル一覧取得
        sample_repo = SampleRepository(db)
        all_samples = sample_repo.get_all_by_batch_id(batch_id)
        
        # 各サンプルからファイルを取得して結合
        file_repo = FileRepository(db)
        all_files = []
        
        for sample in all_samples:
            sample_files = file_repo.get_all_by_sample_id(sample.id)
            all_files.extend(sample_files)
        
        # 非推奨通知ヘッダー追加（実装時に有効化）
        # response.headers["X-API-Deprecated"] = "true"
        # response.headers["X-API-Deprecation-Date"] = "2025-06-30"
        # response.headers["X-API-Alternative"] = "/api/sample-batches/{batchId}/samples and /api/sample-batches/{batchId}/samples/{sampleId}/files"
        
        # ファイル情報を整形して返却
        return [
            {
                "id": f.id,
                "filename": f.filename,
                "file_type": f.file_type,
                "file_size": f.file_size,
                "batch_id": batch_id,  # 互換性のために明示的に設定
                "sample_id": f.sample_id,
                "created_at": f.created_at if f.created_at else None,
                "metadata": f.meta_data
            }
            for f in all_files
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"バッチファイル一覧取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"バッチファイル一覧の取得に失敗しました: {str(e)}")

# バッチクローンAPI
@router.post("/{source_batch_id}/clone", response_model=Dict[str, Any])
async def clone_batch(
    source_batch_id: str = FastAPIPath(..., description="複製元バッチID"),
    clone_config: Dict[str, Any] = Body(..., description="クローン設定"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    既存バッチを複製して新しいバッチを作成します。
    サンプルとファイルも必要に応じて複製します。
    """
    try:
        logger.info(f"バッチクローン開始: source_batch_id={source_batch_id}")
        
        # 必要なパラメータの取得
        new_name = clone_config.get("new_name")
        if not new_name:
            new_name = f"コピー - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
        include_files = clone_config.get("include_files", True)
        metadata_overrides = clone_config.get("metadata_overrides", {})
        
        # 元バッチの存在確認
        batch_repo = SampleBatchRepository(db)
        source_batch = batch_repo.get_by_id(source_batch_id)
        
        if not source_batch:
            raise HTTPException(status_code=404, detail=f"バッチID {source_batch_id} が見つかりません")
        
        # 新しいバッチの作成
        # 元のメタデータをコピーし、上書き情報があれば適用
        metadata = source_batch.meta_data or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
                
        # メタデータの上書き
        metadata.update(metadata_overrides)
        
        new_batch = batch_repo.create(
            name=new_name, 
            description=f"{source_batch.description or ''} (複製元: {source_batch_id})",
            metadata=metadata
        )
        
        # ファイル複製の処理をバックグラウンドで実行
        if include_files:
            background_tasks.add_task(
                clone_batch_samples_and_files,
                source_batch_id=source_batch_id,
                target_batch_id=new_batch.id
            )
            clone_status = "進行中（バックグラウンドでファイル複製中）"
        else:
            clone_status = "完了（ファイル複製なし）"
        
        logger.info(f"バッチクローン成功: source_batch_id={source_batch_id}, new_batch_id={new_batch.id}")
        
        return {
            "source_batch_id": source_batch_id,
            "new_batch_id": new_batch.id,
            "name": new_batch.name,
            "clone_status": clone_status,
            "created_at": new_batch.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"バッチクローン中にエラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"バッチのクローン作成に失敗しました: {str(e)}"
        )

async def clone_batch_samples_and_files(source_batch_id: str, target_batch_id: str):
    """
    バッチのサンプルとファイルを複製するバックグラウンドタスク
    """
    try:
        logger.info(f"サンプルとファイルの複製を開始: source_batch_id={source_batch_id}, target_batch_id={target_batch_id}")
        
        # データベース接続
        with get_db() as db:
            # リポジトリの初期化
            sample_repo = SampleRepository(db)
            file_repo = FileRepository(db)
            batch_repo = SampleBatchRepository(db)
            
            # 元バッチのサンプル一覧を取得
            source_samples = sample_repo.get_all_by_batch_id(source_batch_id)
            
            # サンプル数をカウント
            total_samples = len(source_samples)
            processed_samples = 0
            total_files = 0
            processed_files = 0
            
            # サンプルごとに処理
            for source_sample in source_samples:
                try:
                    # 新しいサンプルを作成
                    new_sample = sample_repo.create(
                        batch_id=target_batch_id,
                        name=source_sample.name,
                        description=source_sample.description,
                        metadata=source_sample.meta_data
                    )
                    
                    # サンプルに属するファイル一覧を取得
                    sample_files = file_repo.get_all_by_sample_id(source_sample.id)
                    total_files += len(sample_files)
                    
                    # ファイルごとに処理
                    for source_file in sample_files:
                        try:
                            # ファイルの実体をコピー
                            source_path = source_file.file_path
                            if source_path and os.path.exists(source_path):
                                # 新しいファイルIDの生成
                                new_file_id = f"file-{uuid.uuid4()}"
                                
                                # 保存先パスの作成
                                dest_path = os.path.join(settings.UPLOAD_DIR, "files", new_file_id)
                                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                                
                                # ファイルのコピー
                                shutil.copy2(source_path, dest_path)
                                
                                # ファイルメタデータを登録
                                new_file = file_repo.create(
                                    {
                                        "id": new_file_id,
                                        "filename": source_file.filename,
                                        "file_path": dest_path,
                                        "file_size": source_file.file_size,
                                        "file_type": source_file.file_type,
                                        "sample_id": new_sample.id,
                                        "file_metadata": source_file.meta_data
                                    }
                                )
                                
                            processed_files += 1
                        except Exception as file_error:
                            logger.error(f"ファイル複製中にエラー: file_id={source_file.id}, error={str(file_error)}")
                    
                    processed_samples += 1
                    
                    # 進捗状況の更新（20%ごと）
                    if processed_samples % max(1, total_samples // 5) == 0:
                        logger.info(f"バッチクローン進捗: {processed_samples}/{total_samples} サンプル, {processed_files}/{total_files} ファイル")
                        
                except Exception as sample_error:
                    logger.error(f"サンプル複製中にエラー: sample_id={source_sample.id}, error={str(sample_error)}")
            
            # バッチのサンプル数を更新
            batch_repo.update_sample_count(target_batch_id)
            
            logger.info(f"バッチクローン完了: {processed_samples}/{total_samples} サンプル, {processed_files}/{total_files} ファイル")
            
    except Exception as e:
        logger.error(f"バッチクローン処理中にエラー: {str(e)}") 

@router.get("/{batch_id}/samples/{sample_id}/files", summary="サンプルのファイル一覧を取得")
def get_sample_files(
    batch_id: str = FastAPIPath(..., description="バッチID"),
    sample_id: str = FastAPIPath(..., description="サンプルID"),
    skip: int = Query(0, description="スキップするレコード数"),
    limit: int = Query(100, description="取得するレコード数の上限")
):
    """特定のサンプルに関連付けられているファイルの一覧を取得します"""
    try:
        logger.info(f"サンプルファイル一覧取得リクエスト: batch_id={batch_id}, sample_id={sample_id}")
        
        # バッチの存在確認
        db = next(get_db())
        batch_repo = SampleBatchRepository(db)
        batch = batch_repo.get_by_id(batch_id)
        
        if not batch:
            raise HTTPException(status_code=404, detail=f"バッチID {batch_id} が見つかりません")
        
        # サンプルの存在確認
        sample_repo = SampleRepository(db)
        sample = sample_repo.get_by_id(sample_id)
        
        if not sample:
            raise HTTPException(status_code=404, detail=f"サンプルID {sample_id} が見つかりません")
            
        if sample.batch_id != batch_id:
            raise HTTPException(status_code=400, detail=f"サンプルID {sample_id} はバッチID {batch_id} に属していません")
        
        # データベース接続
        with get_db_context() as db:
            # ファイル一覧を取得
            sql = text("""
                SELECT id, filename, file_size, file_type, created_at, updated_at, file_metadata
                FROM files
                WHERE sample_id = :sample_id
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :skip
            """)
            
            # カウントクエリ
            count_sql = text("""
                SELECT COUNT(*) as total
                FROM files
                WHERE sample_id = :sample_id
            """)
            
            # クエリ実行
            files = db.execute(
                sql,
                {"sample_id": sample_id, "limit": limit, "skip": skip}
            ).fetchall()
            
            count_result = db.execute(
                count_sql,
                {"sample_id": sample_id}
            ).fetchone()
            
            total_count = count_result.total if count_result else 0
            
            # 結果を整形
            file_list = []
            for file in files:
                file_dict = {
                    "id": file.id,
                    "filename": file.filename,
                    "file_size": file.file_size,
                    "file_type": file.file_type,
                    "created_at": file.created_at if file.created_at else None,
                    "updated_at": file.updated_at if file.updated_at else None,
                    "metadata": file.file_metadata
                }
                file_list.append(file_dict)
            
            logger.info(f"サンプルファイル一覧取得完了: total={total_count}")
            
            return {
                "files": file_list,
                "total": total_count,
                "skip": skip,
                "limit": limit
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"サンプルファイル一覧の取得に失敗: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"サンプルファイル一覧の取得に失敗: {str(e)}"
        )

@router.post("/{batch_id}/samples/{sample_id}/files", summary="サンプルにファイルを追加")
def add_file_to_sample(
    batch_id: str = FastAPIPath(..., description="バッチID"),
    sample_id: str = FastAPIPath(..., description="サンプルID"),
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None)
):
    """特定のサンプルにファイルを追加します"""
    try:
        logger.info(f"サンプルへのファイル追加リクエスト: batch_id={batch_id}, sample_id={sample_id}")
        
        # バッチの存在確認
        db = next(get_db())
        batch_repo = SampleBatchRepository(db)
        batch = batch_repo.get_by_id(batch_id)
        
        if not batch:
            raise HTTPException(status_code=404, detail=f"バッチID {batch_id} が見つかりません")
        
        # サンプルの存在確認
        sample_repo = SampleRepository(db)
        sample = sample_repo.get_by_id(sample_id)
        
        if not sample:
            raise HTTPException(status_code=404, detail=f"サンプルID {sample_id} が見つかりません")
            
        if sample.batch_id != batch_id:
            raise HTTPException(status_code=400, detail=f"サンプルID {sample_id} はバッチID {batch_id} に属していません")
        
        # メタデータのJSONパース
        meta_data = {}
        if metadata:
            try:
                meta_data = json.loads(metadata)
            except:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="無効なメタデータJSONフォーマット"
                )
        
        # ファイルIDの生成
        file_id = f"file-{uuid.uuid4()}"
        
        # ファイルの保存先ディレクトリを作成
        upload_dir = PathLib(settings.UPLOAD_DIR) / batch_id / sample_id
        os.makedirs(upload_dir, exist_ok=True)
        
        # ファイルパスを生成
        file_path = upload_dir / file_id
        
        # ファイルの保存
        with open(file_path, "wb") as f:
            f.write(file.file.read())
        
        # ファイルサイズを取得
        file_size = os.path.getsize(file_path)
        
        # ファイルタイプの推定
        file_type = file.content_type or "application/octet-stream"
        
        # データベースにファイル情報を保存
        with get_db_context() as db:
            file_repo = FileRepository(db)
            
            # ファイル情報をデータベースに保存
            file_obj = file_repo.create(
                {
                    "id": file_id,
                    "filename": file.filename,
                    "file_path": str(file_path),
                    "file_size": file_size,
                    "file_type": file_type,
                    "sample_id": sample_id,
                    "file_metadata": meta_data
                }
            )
            
            # サンプルのファイル数を更新
            sample_repo.increment_file_count(sample_id)
        
        logger.info(f"ファイルが正常に追加されました: file_id={file_id}")
        
        return {
            "id": file_id,
            "filename": file.filename,
            "file_size": file_size,
            "file_type": file_type,
            "sample_id": sample_id,
            "created_at": datetime.now().isoformat(),
            "metadata": meta_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ファイル追加中にエラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ファイルの追加に失敗: {str(e)}"
        )

@router.delete("/{batch_id}/samples/{sample_id}/files", summary="サンプルからファイルを削除")
def remove_files_from_sample(
    batch_id: str = FastAPIPath(..., description="バッチID"),
    sample_id: str = FastAPIPath(..., description="サンプルID"),
    file_ids: List[str] = Body(..., embed=True)
):
    """特定のサンプルから指定されたファイルを削除します"""
    try:
        logger.info(f"サンプルからのファイル削除リクエスト: batch_id={batch_id}, sample_id={sample_id}, file_ids={file_ids}")
        
        if not file_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="削除するファイルIDが指定されていません"
            )
        
        # バッチとサンプルの存在確認は同じDBセッションを使用
        with get_db_context() as db:
            # バッチの存在確認
            batch_repo = SampleBatchRepository(db)
            batch = batch_repo.get_by_id(batch_id)
            
            if not batch:
                raise HTTPException(status_code=404, detail=f"バッチID {batch_id} が見つかりません")
            
            # サンプルの存在確認
            sample_repo = SampleRepository(db)
            sample = sample_repo.get_by_id(sample_id)
            
            if not sample:
                raise HTTPException(status_code=404, detail=f"サンプルID {sample_id} が見つかりません")
                
            if sample.batch_id != batch_id:
                raise HTTPException(status_code=400, detail=f"サンプルID {sample_id} はバッチID {batch_id} に属していません")
            
            results = []
            delete_count = 0
            file_repo = FileRepository(db)
            
            for file_id in file_ids:
                try:
                    # ファイルの存在確認と取得
                    file_obj = file_repo.get_by_id(file_id)
                    
                    if not file_obj:
                        results.append({
                            "file_id": file_id,
                            "success": False,
                            "message": "ファイルが見つかりません"
                        })
                        continue
                    
                    # ファイルが指定されたサンプルに属しているか確認
                    if file_obj.sample_id != sample_id:
                        results.append({
                            "file_id": file_id,
                            "success": False,
                            "message": f"ファイルはサンプルID {sample_id} に属していません"
                        })
                        continue
                    
                    # ファイルシステム上のファイルを削除
                    if os.path.exists(file_obj.file_path):
                        os.remove(file_obj.file_path)
                    
                    # データベースからファイル情報を削除
                    file_repo.delete(file_id)
                    delete_count += 1
                    
                    results.append({
                        "file_id": file_id,
                        "success": True,
                        "message": "削除に成功しました"
                    })
                    
                except Exception as e:
                    logger.error(f"ファイル {file_id} の削除中にエラー: {str(e)}")
                    results.append({
                        "file_id": file_id,
                        "success": False,
                        "message": f"削除中にエラー: {str(e)}"
                    })
            
            # サンプルのファイル数を更新 - 同じセッション内で行う
            if delete_count > 0:
                sample_repo.decrement_file_count(sample_id, delete_count)
        
        logger.info(f"ファイル削除処理完了: 成功={delete_count}/{len(file_ids)}件")
        
        return {
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ファイル削除処理中にエラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ファイルの削除に失敗: {str(e)}"
        ) 