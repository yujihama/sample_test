"""
ファイル管理用のルーター
"""

import os
import uuid
import logging
import shutil
import base64
import math
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Body, status
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
import aiofiles
import mimetypes
from io import BytesIO
import json
from datetime import datetime
from fastapi.security import SecurityScopes
import sqlite3

from src.models.repositories import FileRepository
from src.utils.db_manager import get_db_context
from src.core.config import settings
from src.api.dependencies import get_current_user
from src.api.services.file_service import FileService

# FileDetailsクラスを定義（辞書型として使用）
FileDetails = Dict[str, Any]

# ロガーの設定
logger = logging.getLogger(__name__)

# 重要: APIのルート構造とプレフィックスを明確に
# ファイル管理機能用ルーター - プレフィックスなし（main.pyで/api/filesが付与される）
file_router = APIRouter(
    tags=["files"],
    responses={404: {"description": "Not found"}},
)

# アップロード用の補助ルーター - プレフィックスなし（main.pyで/apiが付与される）
upload_router = APIRouter(
    tags=["file-upload"],
    responses={404: {"description": "Not found"}},
)

# ユーティリティ関数: SQLiteに直接接続してファイル情報を保存
def _save_file_to_db(file_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """直接SQLiteを使用してファイル情報を保存する（トランザクション問題を回避）"""
    try:
        # 必須フィールドの確認
        if not file_metadata.get("id") or not file_metadata.get("file_path"):
            raise ValueError("ファイルIDとファイルパスは必須です")
            
        # データベースファイルのパスを取得
        db_url = settings.DATABASE_URL
        if db_url.startswith("sqlite:///"):
            db_path = db_url.replace("sqlite:///", "")
            if not os.path.isabs(db_path):
                db_path = os.path.abspath(db_path)
        else:
            raise ValueError(f"サポートされていないデータベースURL: {db_url}")
            
        # 現在時刻を追加
        if "created_at" not in file_metadata:
            file_metadata["created_at"] = datetime.now().isoformat()
        
        # 完全に独立したデータベース接続を作成
        conn = None
        try:
            conn = sqlite3.connect(db_path, isolation_level=None)  # autocommitモード
            cursor = conn.cursor()
            
            # SQL文を作成
            fields = ', '.join(file_metadata.keys())
            placeholders = ', '.join(['?'] * len(file_metadata.keys()))
            sql = f"INSERT INTO files ({fields}) VALUES ({placeholders})"
            
            # 値のリストを作成
            values = list(file_metadata.values())
            
            # SQLを実行
            cursor.execute(sql, values)
            logger.info(f"ファイルメタデータをDBに保存しました: id={file_metadata.get('id')}")
            
            return file_metadata
        finally:
            if conn:
                try:
                    conn.close()
                    logger.debug("SQLite接続を閉じました")
                except:
                    pass
                    
    except Exception as e:
        logger.error(f"ファイル情報のDB保存に失敗: {str(e)}")
        # エラーを上位に伝播
        raise

# ファイル一覧取得 (メインエンドポイント)
@file_router.get("/", summary="ファイル一覧を取得")
async def get_files():
    """
    すべてのファイル一覧を取得します
    """
    try:
        logger.info("ファイル一覧の取得リクエストを受信")
        file_service = FileService()
        files = file_service.get_all_files()
        
        logger.info(f"ファイル一覧を返却: {len(files)}件")
        return files
        
    except Exception as e:
        logger.error(f"ファイル一覧の取得中にエラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ファイル一覧の取得に失敗: {str(e)}"
        )

# 後方互換性のためのエンドポイント
@file_router.get("/files", summary="ファイル一覧を取得（旧エンドポイント）")
async def get_files_old():
    """
    すべてのファイル一覧を取得します（後方互換性用）
    """
    return await get_files()

# ファイル詳細取得
@file_router.get("/{file_id}", summary="ファイル詳細を取得")
async def get_file_details(file_id: str):
    """
    特定のファイルの詳細情報を取得します
    """
    try:
        logger.info(f"ファイル詳細の取得リクエスト: id={file_id}")
        file_service = FileService()
        file_info = file_service.get_file_info(file_id)
        
        logger.info(f"ファイル詳細を返却: id={file_id}")
        return file_info
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ファイル詳細の取得中にエラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ファイル詳細の取得に失敗: {str(e)}"
        )

# ファイルダウンロード
@file_router.get("/{file_id}/download", summary="ファイルをダウンロード")
async def download_file(file_id: str):
    """
    ファイルをダウンロードします
    """
    try:
        logger.info(f"ファイルダウンロードリクエスト: id={file_id}")
        file_service = FileService()
        
        # ファイル情報の取得
        file_info = file_service.get_file_info(file_id)
        if not file_info:
            logger.warning(f"ファイルが見つかりません: id={file_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたファイルが見つかりません"
            )
            
        # ファイルストリームの取得
        file_stream = file_service.get_file_stream(file_id)
        
        # レスポンスヘッダーを設定
        filename = file_info.get("filename", f"file_{file_id}")
        content_type = file_info.get("content_type", "application/octet-stream")
        
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
        
        logger.info(f"ファイルをダウンロードします: id={file_id}, filename={filename}")
        return StreamingResponse(
            file_stream,
            media_type=content_type,
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ファイルダウンロード中にエラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ファイルダウンロードに失敗: {str(e)}"
        )

# ファイル削除
@file_router.delete("/{file_id}", summary="ファイルを削除")
async def delete_file(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    特定のファイルを削除します
    """
    # 管理者権限の確認
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この操作には管理者権限が必要です"
        )
            
    try:
        logger.info(f"ファイル削除リクエスト: id={file_id}")
        file_service = FileService()
        
        # ファイルの削除
        result = file_service.delete_file(file_id)
        
        logger.info(f"ファイルが正常に削除されました: id={file_id}")
        return {"message": f"ファイルID {file_id} が正常に削除されました"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ファイル削除中にエラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ファイル削除に失敗: {str(e)}"
        )

# メタデータ更新
@file_router.put("/{file_id}/metadata", summary="ファイルメタデータを更新")
async def update_file_metadata(
    file_id: str,
    metadata: dict,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    ファイルのメタデータを更新します
    """
    try:
        logger.info(f"メタデータ更新リクエスト: id={file_id}, metadata={metadata}")
        file_service = FileService()
        
        # メタデータの更新
        updated_file = file_service.update_file_metadata(file_id, metadata)
        
        logger.info(f"メタデータが正常に更新されました: id={file_id}")
        return updated_file
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"メタデータ更新中にエラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"メタデータ更新に失敗: {str(e)}"
        )

# ファイルアップロード
@file_router.post("/upload", summary="ファイルをアップロード")
async def upload_file(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    ファイルをアップロードします
    """
    try:
        logger.info(f"ファイルアップロードリクエスト: {file.filename}")
        
        # メタデータの処理
        metadata_dict = {}
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
                logger.info(f"メタデータを解析: {metadata_dict}")
            except json.JSONDecodeError as e:
                logger.error(f"メタデータのJSONデコードに失敗: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="不正なメタデータ形式です。有効なJSONを指定してください。"
                )
        
        # ファイルサービスの初期化とファイルの保存
        file_service = FileService()
        file_info = await file_service.save_file(file, metadata_dict)
        
        logger.info(f"ファイルが正常にアップロードされました: {file_info}")
        return file_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ファイルアップロード中にエラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ファイルアップロードに失敗: {str(e)}"
        )

# レポート取得
@file_router.get("/reports/{workflow_id}", summary="監査レポートを取得")
async def get_report(workflow_id: str) -> FileResponse:
    """
    特定のワークフローの監査レポートを取得します
    """
    logger.info(f"レポート取得リクエスト: ワークフローID {workflow_id}")
    try:
        # TODO: ワークフローに関連するレポートファイルを取得する実装を追加
        # 現在はモックレスポンスを返す
        report_path = os.path.join(settings.REPORT_DIR, f"report_{workflow_id}.pdf")
        
        if not os.path.exists(report_path):
            logger.warning(f"レポートが見つかりません: {workflow_id}")
            raise HTTPException(status_code=404, detail="Report not found")
        
        logger.info(f"レポートを取得しました: ワークフローID {workflow_id}")
        return FileResponse(
            path=report_path,
            filename=f"audit_report_{workflow_id}.pdf",
            media_type="application/pdf"
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"レポートの取得中にエラー: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# シンプルアップロード（直接SQLiteを使用）
@upload_router.post("/upload-simple", summary="シンプルなファイルアップロード")
async def upload_file_simple(
    file: UploadFile = File(...),
    file_type: str = Form("document"),
    description: Optional[str] = Form(None)
):
    """
    シンプルなファイルアップロード（トランザクション制御なし）
    """
    logger.info(f"シンプルアップロードリクエスト: {file.filename}, タイプ: {file_type}")
    try:
        # ファイルIDを生成
        file_id = f"file-{uuid.uuid4()}"
        
        # アップロードディレクトリ
        upload_subdir = file_type
        upload_dir = os.path.join(settings.UPLOAD_DIR, upload_subdir)
        os.makedirs(upload_dir, exist_ok=True)
        
        # ファイル名の組み立て
        file_name = os.path.basename(file.filename)
        base_name, extension = os.path.splitext(file_name)
        file_path = os.path.join(upload_dir, f"{base_name}_{file_id}{extension}")
        
        # ファイルを保存
        content = None
        async with aiofiles.open(file_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
        
        if not content:
            raise ValueError("ファイル内容の読み込みに失敗しました")
        
        # メタデータ準備
        file_metadata = {
            "id": file_id,
            "filename": file.filename,
            "file_path": file_path,
            "file_type": file_type,
            "file_size": len(content),
            "content_type": file.content_type,
            "related_id": None,
            "description": description
        }
        
        # 独立したデータベース操作
        try:
            _save_file_to_db(file_metadata)
        except Exception as db_e:
            logger.error(f"データベース保存エラー: {str(db_e)}")
            # データベース保存エラーでもファイルアップロードは成功とする
        
        logger.info(f"ファイルアップロード成功: {file_id}, パス: {file_path}")
        return {
            "file_id": file_id,
            "filename": file.filename,
            "file_size": len(content),
            "file_type": file_type,
            "content_type": file.content_type,
            "status": "uploaded",
            "file_path": file_path
        }
    
    except Exception as e:
        logger.error(f"ファイルアップロード中にエラー: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# 互換性のための古いエンドポイント
@upload_router.post("/upload", summary="ファイルアップロード (レガシーAPI)")
async def upload_file_endpoint(
    file: UploadFile = File(...),
    file_type: str = Form("document"),
    related_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """
    ファイルアップロード (後方互換性用)
    """
    logger.info(f"レガシーAPIでファイルアップロードリクエスト: {file.filename}")
    try:
        # ファイルIDを生成
        file_id = f"file-{uuid.uuid4()}"
        
        # アップロードディレクトリ
        upload_subdir = file_type
        upload_dir = os.path.join(settings.UPLOAD_DIR, upload_subdir)
        os.makedirs(upload_dir, exist_ok=True)
        
        # ファイル名の組み立て
        file_name = os.path.basename(file.filename)
        base_name, extension = os.path.splitext(file_name)
        file_path = os.path.join(upload_dir, f"{base_name}_{file_id}{extension}")
        
        # ファイルを保存
        async with aiofiles.open(file_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
        
        # メタデータをデータベースに保存
        file_metadata = {
            "id": file_id,
            "filename": file.filename,
            "file_path": file_path,
            "file_type": file_type,
            "file_size": len(content),
            "content_type": file.content_type,
            "related_id": related_id,
            "description": description
        }
        
        # SQLiteを直接使用してデータベースに保存
        try:
            _save_file_to_db(file_metadata)
        except Exception as db_e:
            logger.error(f"データベース保存エラー: {str(db_e)}")
            # データベース保存エラーでもファイルアップロードは成功とする
        
        logger.info(f"ファイルアップロード成功: {file_id}, パス: {file_path}")
        return {
            "file_id": file_id,
            "filename": file.filename,
            "file_size": len(content),
            "file_type": file_type,
            "content_type": file.content_type,
            "status": "uploaded"
        }
        
    except Exception as e:
        logger.error(f"ファイルアップロード中にエラー: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# サンプルファイル管理用のエンドポイント
@file_router.get("/sample-batches/{batch_id}/samples/{sample_id}/files", summary="サンプル内のファイル一覧を取得")
async def get_sample_files(
    batch_id: str,
    sample_id: str,
    page: int = Query(1, ge=1, description="ページ番号"),
    page_size: int = Query(20, ge=1, le=100, description="1ページあたりの件数"),
    sort_by: str = Query("created_at", description="ソート項目"),
    sort_order: str = Query("desc", description="ソート順序 (asc, desc)")
):
    """
    特定のサンプルに含まれるファイル一覧を取得します
    """
    try:
        logger.info(f"サンプルファイル一覧の取得リクエスト: batch_id={batch_id}, sample_id={sample_id}")
        
        # データベース接続
        async with get_db_context() as db:
            # ファイルリポジトリのインスタンス作成
            file_repo = FileRepository(db)
            
            # サンプルに含まれるファイル一覧を取得
            files, total = file_repo.get_files_by_sample_id(
                sample_id=sample_id,
                page=page,
                per_page=page_size,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            # ファイル情報を整形
            file_list = [
                {
                    "id": f.id,
                    "filename": f.filename,
                    "file_size": f.file_size,
                    "file_type": f.file_type,
                    "created_at": f.created_at,
                    "updated_at": f.updated_at,
                    "sample_id": f.sample_id,
                    "metadata": f.meta_data
                }
                for f in files
            ]
            
        logger.info(f"サンプルファイル一覧を返却: {len(file_list)}件")
        return {
            "files": file_list,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"サンプルファイル一覧の取得中にエラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"サンプルファイル一覧の取得に失敗: {str(e)}"
        )

@file_router.post("/sample-batches/{batch_id}/samples/{sample_id}/files", summary="サンプルにファイルを追加")
async def add_file_to_sample(
    batch_id: str,
    sample_id: str,
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None)
):
    """
    特定のサンプルにファイルを追加します
    """
    try:
        logger.info(f"サンプルへのファイル追加リクエスト: batch_id={batch_id}, sample_id={sample_id}")
        
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
        
        # アップロードディレクトリの作成
        upload_dir = Path(settings.UPLOAD_DIR) / "files"
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / file_id
        
        # ファイルの保存
        content = await file.read()
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)
        
        # ファイル情報の作成
        file_size = len(content)
        file_type = os.path.splitext(file.filename)[1].lstrip('.').lower()
        
        # ファイルメタデータをデータベースに保存
        file_metadata = {
            "id": file_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "file_size": file_size,
            "file_type": file_type,
            "sample_id": sample_id,
            "meta_data": json.dumps(meta_data) if meta_data else None,
            "created_at": datetime.now().isoformat()
        }
        
        # データベースに保存
        async with get_db_context() as db:
            file_repo = FileRepository(db)
            # 辞書形式でデータを渡す
            file_data = {
                "id": file_id,
                "filename": file.filename,
                "file_path": str(file_path),
                "file_size": file_size,
                "file_type": file_type,
                "sample_id": sample_id,
                "meta_data": json.dumps(meta_data) if meta_data else None
            }
            saved_file = file_repo.create(file_data)
        
        logger.info(f"ファイルをサンプルに追加しました: file_id={file_id}, sample_id={sample_id}")
        return {
            "id": saved_file.id,
            "filename": saved_file.filename,
            "file_size": saved_file.file_size,
            "file_type": saved_file.file_type,
            "sample_id": saved_file.sample_id,
            "created_at": saved_file.created_at,
            "metadata": saved_file.meta_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"サンプルへのファイル追加中にエラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"サンプルへのファイル追加に失敗: {str(e)}"
        )

@file_router.delete("/sample-batches/{batch_id}/samples/{sample_id}/files", summary="サンプルからファイルを削除")
async def remove_files_from_sample(
    batch_id: str,
    sample_id: str,
    file_ids: List[str] = Body(..., embed=True)
):
    """
    特定のサンプルから複数のファイルを削除します
    """
    try:
        logger.info(f"サンプルからのファイル削除リクエスト: batch_id={batch_id}, sample_id={sample_id}, file_ids={file_ids}")
        
        # データベース接続
        async with get_db_context() as db:
            file_repo = FileRepository(db)
            
            # 削除結果を記録
            results = []
            
            # 各ファイルを削除
            for file_id in file_ids:
                try:
                    # ファイル情報を取得
                    file_info = file_repo.get_by_id(file_id)
                    
                    if not file_info:
                        results.append({
                            "file_id": file_id,
                            "success": False,
                            "message": "ファイルが存在しません"
                        })
                        continue
                    
                    # サンプルIDの確認
                    if file_info.sample_id != sample_id:
                        results.append({
                            "file_id": file_id,
                            "success": False,
                            "message": "指定されたサンプルに属していないファイルです"
                        })
                        continue
                    
                    # ファイルをデータベースから削除
                    file_repo.delete(file_id)
                    
                    # 実ファイルを削除
                    if file_info.file_path and os.path.exists(file_info.file_path):
                        os.remove(file_info.file_path)
                    
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
                        "message": f"削除中にエラーが発生しました: {str(e)}"
                    })
            
        logger.info(f"サンプルからのファイル削除結果: {results}")
        return {"results": results}
        
    except Exception as e:
        logger.error(f"サンプルからのファイル削除中にエラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"サンプルからのファイル削除に失敗: {str(e)}"
        ) 