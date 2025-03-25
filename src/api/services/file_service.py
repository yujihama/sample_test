import os
import uuid
import json
import shutil
from typing import Any, Dict, List, Optional, Union, BinaryIO
from fastapi import UploadFile, HTTPException
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text, Column, String, Integer, DateTime, create_engine
from datetime import datetime, UTC
import sqlite3
import aiofiles

from src.utils.db_manager import get_db_context
from src.models.repositories import FileRepository
from src.core.config import settings

logger = logging.getLogger(__name__)

class FileService:
    """ファイル管理サービス"""
    
    def __init__(self):
        """ファイルサービスを初期化"""
        self.settings = settings
        
        # アップロードディレクトリの作成
        os.makedirs(self.settings.UPLOAD_DIR, exist_ok=True)
        
        # テーブルの存在確認と作成
        self._ensure_table_exists()
        
    def _ensure_table_exists(self):
        """filesテーブルが存在することを確認し、なければ作成する"""
        try:
            # 直接SQLiteを使用して確認と作成
            db_path = self._get_db_path()
            
            # データベースに接続
            conn = None
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # テーブルの存在確認
                cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='files'")
                exists = cursor.fetchone()[0] > 0
                
                if not exists:
                    logger.info("filesテーブルが存在しないため、作成します")
                    # テーブルの作成
                    create_table_sql = """
                    CREATE TABLE files (
                        id VARCHAR(255) PRIMARY KEY,
                        filename VARCHAR(255) NOT NULL,
                        content_type VARCHAR(255),
                        file_path VARCHAR(500) NOT NULL,
                        file_type VARCHAR(100),
                        file_size INTEGER,
                        description TEXT,
                        related_id VARCHAR(255),
                        sample_id VARCHAR(50),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP
                    )
                    """
                    cursor.execute(create_table_sql)
                    conn.commit()
                    logger.info("filesテーブルを作成しました")
                else:
                    # テーブルは存在するが、sample_idカラムが存在するか確認
                    cursor.execute("PRAGMA table_info(files)")
                    columns = [column[1] for column in cursor.fetchall()]
                    
                    # sample_idカラムが存在しない場合は追加
                    if "sample_id" not in columns:
                        logger.info("filesテーブルにsample_idカラムを追加します")
                        alter_table_sql = "ALTER TABLE files ADD COLUMN sample_id VARCHAR(50)"
                        cursor.execute(alter_table_sql)
                        conn.commit()
                        logger.info("sample_idカラムを追加しました")
            finally:
                # 接続を閉じる
                if conn:
                    conn.close()
            
        except Exception as e:
            logger.error(f"テーブル作成中にエラーが発生: {str(e)}")
            # エラーをスローせず、続行する
        
    def _get_db_path(self):
        """データベースファイルのパスを取得"""
        db_url = self.settings.DATABASE_URL
        if db_url.startswith("sqlite:///"):
            db_path = db_url.replace("sqlite:///", "")
            
            # 相対パスを絶対パスに変換
            if not os.path.isabs(db_path):
                db_path = os.path.abspath(db_path)
            
            return db_path
        else:
            raise ValueError(f"サポートされていないデータベースURL: {db_url}")
        
    async def save_file(self, file: UploadFile, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        ファイルを保存し、メタデータをDBに記録
        
        Args:
            file: アップロードされたファイル
            metadata: ファイルに関連する追加情報
            
        Returns:
            保存したファイルの情報
        """
        file_path = None
        try:
            # ファイルIDを生成
            file_id = str(uuid.uuid4())
            
            # ファイルの保存先パスを作成
            file_path = os.path.join(self.settings.UPLOAD_DIR, file_id)
            
            # ファイルを保存
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            logger.info(f"ファイルを保存しました: {file_path}")
            
            # ファイル情報を作成
            file_info = {
                "id": file_id,
                "filename": file.filename,
                "content_type": file.content_type,
                "file_path": file_path,
                "file_type": "document",
                "file_size": os.path.getsize(file_path),
                "description": "APIでアップロードされたファイル"
            }
            
            # メタデータをデータベースに保存 - SQLiteを直接使用
            try:
                # データベースファイルのパスを取得
                db_path = self._get_db_path()
                
                # データベースに接続
                conn = None
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # ファイルメタデータの作成
                    file_metadata = file_info.copy()
                    file_metadata["created_at"] = datetime.now().isoformat()
                    
                    # SQL文を作成
                    fields = ', '.join(file_metadata.keys())
                    placeholders = ', '.join(['?'] * len(file_metadata.keys()))
                    sql = f"INSERT INTO files ({fields}) VALUES ({placeholders})"
                    
                    # 値のリストを作成
                    values = list(file_metadata.values())
                    
                    # SQLを実行
                    cursor.execute(sql, values)
                    conn.commit()
                    
                    logger.info(f"ファイルメタデータをDBに保存しました: id={file_id}")
                finally:
                    # 接続を閉じる
                    if conn:
                        conn.close()
                    
            except Exception as db_error:
                logger.error(f"データベース保存エラー: {db_error}")
                # DBエラーでもファイル情報は返す
            
            # メタデータを追加して返す
            file_info["metadata"] = metadata or {}
            return file_info
                
        except Exception as e:
            # エラー発生時はファイルがあれば削除
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"エラーによりファイルを削除しました: {file_path}")
                except:
                    pass
            
            logger.error(f"ファイル保存中にエラーが発生: {str(e)}")
            raise HTTPException(status_code=500, detail=f"ファイルの保存に失敗しました: {str(e)}")
            
    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """
        ファイル情報を取得
        
        Args:
            file_id: ファイルID
            
        Returns:
            ファイル情報
        """
        try:
            # 特殊ケース：filesはファイル一覧を表す
            if file_id.lower() == "files":
                return self.get_all_files()
        
            # 直接SQLiteを使用
            db_path = self._get_db_path()
            conn = None
            try:
                conn = sqlite3.connect(db_path)
                # カラム名を取得するための設定
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # ファイル情報を取得
                cursor.execute("SELECT * FROM files WHERE id = ?", (file_id,))
                row = cursor.fetchone()
                
                if row:
                    # 辞書に変換
                    result = dict(row)
                    
                    # メタデータがなければ追加
                    if "metadata" not in result:
                        result["metadata"] = {}
                    
                    return result
                else:
                    # ファイルシステムでの確認を試みる
                    file_path = os.path.join(self.settings.UPLOAD_DIR, file_id)
                    if os.path.exists(file_path):
                        return {
                            "id": file_id,
                            "filename": file_id,  # 実際のファイル名は不明
                            "content_type": "application/octet-stream",
                            "file_size": os.path.getsize(file_path),
                            "metadata": {}
                        }
                    else:
                        raise HTTPException(status_code=404, detail=f"ファイルが見つかりません: {file_id}")
            finally:
                # 接続を閉じる
                if conn:
                    conn.close()
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"ファイル情報の取得中にエラーが発生: {str(e)}")
            raise HTTPException(status_code=500, detail=f"ファイル情報の取得に失敗しました: {str(e)}")
    
    def get_all_files(self) -> List[Dict[str, Any]]:
        """
        すべてのファイル情報を取得
        
        Returns:
            ファイル情報のリスト
        """
        try:
            # 直接SQLiteを使用
            db_path = self._get_db_path()
            conn = None
            try:
                conn = sqlite3.connect(db_path)
                # カラム名を取得するための設定
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # すべてのファイル情報を取得
                cursor.execute("SELECT * FROM files ORDER BY created_at DESC")
                rows = cursor.fetchall()
                
                # 結果を変換
                result = []
                for row in rows:
                    # 辞書に変換
                    file_dict = dict(row)
                    
                    # メタデータがなければ追加
                    if "metadata" not in file_dict:
                        file_dict["metadata"] = {}
                    
                    result.append(file_dict)
                
                return result
            finally:
                # 接続を閉じる
                if conn:
                    conn.close()
            
        except Exception as e:
            logger.error(f"ファイル一覧の取得中にエラーが発生: {str(e)}")
            return []  # エラー時は空のリストを返す
    
    def get_file_content(self, file_id: str) -> Union[bytes, BinaryIO]:
        """
        ファイルの内容を取得
        
        Args:
            file_id: ファイルID
            
        Returns:
            ファイルの内容
        """
        try:
            # ファイルパスを取得
            file_path = os.path.join(self.settings.UPLOAD_DIR, file_id)
            
            # ファイルの存在確認
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"ファイルが見つかりません: {file_id}")
                
            # ファイルの内容を読み込む
            with open(file_path, "rb") as f:
                content = f.read()
            
            logger.info(f"ファイル内容を読み込みました: {file_path}")
            return content
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"ファイル内容の取得中にエラーが発生: {str(e)}")
            raise HTTPException(status_code=500, detail=f"ファイル内容の取得に失敗しました: {str(e)}")
    
    def get_file_stream(self, file_id: str) -> BinaryIO:
        """
        ファイルストリームを取得
        
        Args:
            file_id: ファイルID
            
        Returns:
            ファイルストリーム
        """
        try:
            # ファイルパスを取得
            file_path = os.path.join(self.settings.UPLOAD_DIR, file_id)
            
            # ファイルの存在確認
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"ファイルが見つかりません: {file_id}")
            
            # ファイルを開いてストリームとして返す
            from io import BytesIO
            with open(file_path, "rb") as f:
                content = f.read()
            
            return BytesIO(content)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"ファイルストリームの取得中にエラーが発生: {str(e)}")
            raise HTTPException(status_code=500, detail=f"ファイルストリームの取得に失敗しました: {str(e)}")
            
    def delete_file(self, file_id: str) -> bool:
        """
        ファイルを削除
        
        Args:
            file_id: ファイルID
            
        Returns:
            削除が成功したかどうか
        """
        try:
            # ファイルパスを取得
            file_path = os.path.join(self.settings.UPLOAD_DIR, file_id)
            
            # ファイルの存在確認
            if not os.path.exists(file_path):
                logger.warning(f"削除対象のファイルが見つかりません: {file_path}")
                # ファイルが存在しなくても、メタデータの削除を試みる
            
            # ファイルを削除
            else:
                os.remove(file_path)
                logger.info(f"ファイルを削除しました: {file_path}")
            
            # メタデータを削除
            try:
                # 直接SQLiteを使用
                db_path = self._get_db_path()
                conn = None
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # ファイルを削除
                    cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
                    conn.commit()
                    
                    # 影響を受けた行数を確認
                    deleted = cursor.rowcount > 0
                    
                    if deleted:
                        logger.info(f"ファイルメタデータを削除しました: id={file_id}")
                    else:
                        logger.warning(f"ファイルメタデータの削除に失敗: id={file_id} (レコードが見つかりません)")
                finally:
                    # 接続を閉じる
                    if conn:
                        conn.close()
                
            except Exception as db_error:
                logger.error(f"メタデータ削除中にエラーが発生: {db_error}")
                # ファイル自体の削除は成功しているので、部分的に成功とみなす
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"ファイル削除中にエラーが発生: {str(e)}")
            raise HTTPException(status_code=500, detail=f"ファイルの削除に失敗しました: {str(e)}")
            
    def update_file_metadata(self, file_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        ファイルのメタデータを更新
        
        Args:
            file_id: ファイルID
            metadata: 更新するメタデータ
            
        Returns:
            更新後のファイル情報
        """
        try:
            # ファイルの存在確認
            file_path = os.path.join(self.settings.UPLOAD_DIR, file_id)
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"ファイルが見つかりません: {file_id}")
            
            # ファイル情報を取得
            current_info = self.get_file_info(file_id)
            
            # 更新後のファイル情報
            updated_info = current_info.copy()
            updated_info["metadata"] = metadata
            
            # データベースの更新は行わない（metadataカラムがないため）
            
            return updated_info
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"メタデータ更新中にエラーが発生: {str(e)}")
            raise HTTPException(status_code=500, detail=f"メタデータの更新に失敗しました: {str(e)}")
    
    def create_file_record(self, file_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        ファイル情報をデータベースに保存する（SQLiteを直接使用）
        
        Args:
            file_metadata: 保存するファイルのメタデータ
            
        Returns:
            保存したファイル情報
        """
        try:
            # 必須フィールドの確認
            if not file_metadata.get("id") or not file_metadata.get("file_path"):
                raise ValueError("ファイルIDとファイルパスは必須です")
                
            # データベースファイルのパスを取得
            db_path = self._get_db_path()
            
            # 現在時刻を追加
            if "created_at" not in file_metadata:
                file_metadata["created_at"] = datetime.now().isoformat()
            
            # トランザクションを使わず、直接データベースへの新規接続を作成して書き込み
            try:
                # 単一のデータベース接続を作成
                conn = sqlite3.connect(db_path, isolation_level=None)  # autocommitモード
                cursor = conn.cursor()
                
                # SQL文を作成
                fields = ', '.join(file_metadata.keys())
                placeholders = ', '.join(['?'] * len(file_metadata.keys()))
                sql = f"INSERT INTO files ({fields}) VALUES ({placeholders})"
                
                # 値のリストを作成
                values = list(file_metadata.values())
                
                # SQLを実行（autocommitモードなのでcommit不要）
                cursor.execute(sql, values)
                
                logger.info(f"ファイルメタデータをDBに保存しました: id={file_metadata.get('id')}")
                
                # 接続を閉じる
                cursor.close()
                conn.close()
                
                # 追加したレコードを返す
                return file_metadata
                
            except sqlite3.Error as sql_e:
                logger.error(f"SQLiteエラー: {sql_e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"データベース操作エラー: {str(sql_e)}"
                )
                    
        except Exception as e:
            logger.error(f"ファイルレコード作成中にエラーが発生: {str(e)}")
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=500, 
                detail=f"ファイルレコード作成に失敗しました: {str(e)}"
            ) 