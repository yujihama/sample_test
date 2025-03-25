"""
ファイル管理APIのテスト用スクリプト
"""

import os
import sys
import json
import argparse
import uuid
import time
import asyncio
import aiohttp
import mimetypes
from pathlib import Path
from typing import Dict, Any, List, Optional

# ログ設定
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("file_test.log")
    ]
)
logger = logging.getLogger(__name__)

# デフォルト設定
DEFAULT_API_BASE_URL = "http://localhost:7000/api"
DEFAULT_TEST_DATA_DIR = "./test_data"
DEFAULT_OUTPUT_DIR = "./test_output"

class FileAPITester:
    """ファイル管理API用テストクラス"""
    
    def __init__(self, api_base_url: str, test_data_dir: str, output_dir: str):
        """
        初期化
        
        Args:
            api_base_url: APIのベースURL
            test_data_dir: テスト用ファイルディレクトリ
            output_dir: 出力ディレクトリ
        """
        self.api_base_url = api_base_url  # http://localhost:8000/api
        self.test_data_dir = test_data_dir
        self.output_dir = output_dir
        
        # 統計情報
        self.stats = {
            "upload_success": 0,
            "upload_failed": 0,
            "download_success": 0,
            "download_failed": 0,
            "preview_success": 0,
            "preview_failed": 0,
            "chunk_upload_success": 0,
            "chunk_upload_failed": 0,
            "chunk_download_success": 0,
            "chunk_download_failed": 0,
            "total_time": 0
        }
        
        # テスト結果
        self.test_results = []
        
        # アップロードされたファイルIDの記録
        self.uploaded_file_ids = []
        
        # テストデータの準備
        os.makedirs(test_data_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
    
    async def run_all_tests(self):
        """すべてのテストを実行する"""
        start_time = time.time()
        
        logger.info("==== ファイル管理APIテスト開始 ====")
        logger.info(f"API URL: {self.api_base_url}")
        logger.info(f"テストデータディレクトリ: {self.test_data_dir}")
        logger.info(f"出力ディレクトリ: {self.output_dir}")
        
        # テスト用のファイルを取得
        test_files = self.get_test_files()
        if not test_files:
            self.generate_test_files()
            test_files = self.get_test_files()
            
        logger.info(f"テストファイル数: {len(test_files)}")
        
        # HTTPセッションを作成
        async with aiohttp.ClientSession() as session:
            # 通常アップロードのテスト
            for file_path in test_files:
                if os.path.getsize(file_path) < 5 * 1024 * 1024:  # 5MB未満の場合は通常アップロード
                    file_id = await self.test_upload(session, file_path)
                    if file_id:
                        self.uploaded_file_ids.append(file_id)
                        
                        # メタデータ取得のテスト
                        await self.test_get_metadata(session, file_id)
                        
                        # プレビュー取得のテスト
                        await self.test_get_preview(session, file_id)
                        
                        # ダウンロードのテスト
                        await self.test_download(session, file_id)
            
            # チャンクアップロードのテスト
            for file_path in test_files:
                if os.path.getsize(file_path) > 1024 * 1024:  # 1MB以上の場合はチャンクアップロード
                    file_id = await self.test_chunk_upload(session, file_path)
                    if file_id:
                        self.uploaded_file_ids.append(file_id)
                        
                        # チャンクダウンロードのテスト
                        await self.test_chunk_download(session, file_id)
            
            # 削除テスト
            for file_id in self.uploaded_file_ids:
                await self.test_delete(session, file_id)
        
        # テスト時間の計測
        end_time = time.time()
        self.stats["total_time"] = end_time - start_time
        
        # 結果の表示
        self.print_results()
        
        logger.info("==== ファイル管理APIテスト終了 ====")
        
        return self.stats
    
    def get_test_files(self) -> List[str]:
        """テスト用ファイルのリストを取得する"""
        return [
            os.path.join(self.test_data_dir, f) 
            for f in os.listdir(self.test_data_dir) 
            if os.path.isfile(os.path.join(self.test_data_dir, f))
        ]
    
    def generate_test_files(self):
        """テスト用ファイルを生成する"""
        logger.info("テスト用ファイルの生成を開始します")
        
        # テキストファイル
        with open(os.path.join(self.test_data_dir, "test_text.txt"), "w") as f:
            f.write("This is a test file.\n" * 100)
        
        # JSONファイル
        with open(os.path.join(self.test_data_dir, "test_json.json"), "w") as f:
            json.dump({
                "name": "Test Data",
                "description": "This is a test JSON file",
                "items": [{"id": i, "value": f"value_{i}"} for i in range(100)]
            }, f, indent=2)
        
        # 大きなテキストファイル (約2MB)
        with open(os.path.join(self.test_data_dir, "test_large.txt"), "w") as f:
            f.write("This is a large test file.\n" * 100000)
        
        logger.info("テスト用ファイルの生成が完了しました")
    
    async def test_upload(self, session: aiohttp.ClientSession, file_path: str) -> Optional[str]:
        """通常のファイルアップロードをテストする"""
        filename = os.path.basename(file_path)
        logger.info(f"ファイルアップロードテスト: {filename}")
        
        try:
            # フォームデータを作成
            with open(file_path, "rb") as f:
                form_data = aiohttp.FormData()
                form_data.add_field(
                    "file",
                    f,
                    filename=filename,
                    content_type=mimetypes.guess_type(file_path)[0] or "application/octet-stream"
                )
                form_data.add_field("file_type", "document")
                form_data.add_field("description", f"Test file {filename}")
                
                # 本来のエンドポイント: /api/files/upload
                # シンプル版を試す: /api/files/upload-simple
                # 新しいルートエンドポイント: /api/upload-simple
                async with session.post(
                    f"{self.api_base_url}/upload-simple",
                    data=form_data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"アップロード成功: {filename}, ファイルID: {result.get('file_id')}")
                        self.stats["upload_success"] += 1
                        self.test_results.append({
                            "test": "upload",
                            "file": filename,
                            "status": "success",
                            "result": result
                        })
                        return result.get("file_id")
                    else:
                        error_text = await response.text()
                        logger.error(f"アップロード失敗: {filename}, ステータス: {response.status}, エラー: {error_text}")
                        self.stats["upload_failed"] += 1
                        self.test_results.append({
                            "test": "upload",
                            "file": filename,
                            "status": "error",
                            "error": error_text,
                            "status_code": response.status
                        })
                        return None
        except Exception as e:
            logger.error(f"アップロードエラー: {filename}, 例外: {str(e)}")
            self.stats["upload_failed"] += 1
            self.test_results.append({
                "test": "upload",
                "file": filename,
                "status": "error",
                "error": str(e)
            })
            return None
    
    async def test_get_metadata(self, session: aiohttp.ClientSession, file_id: str) -> bool:
        """
        ファイルメタデータ取得のテスト
        
        Args:
            session: HTTPセッション
            file_id: ファイルID
            
        Returns:
            bool: 成功したかどうか
        """
        logger.info(f"メタデータ取得テスト: {file_id}")
        
        try:
            start_time = time.time()
            async with session.get(
                f"{self.api_base_url}/files/{file_id}/metadata"
            ) as response:
                elapsed_time = time.time() - start_time
                
                if response.status == 200:
                    metadata = await response.json()
                    
                    logger.info(f"メタデータ取得成功: {file_id}, ファイル名: {metadata.get('filename')} ({elapsed_time:.2f}秒)")
                    self.test_results.append({
                        "test": "get_metadata",
                        "file_id": file_id,
                        "status": "success",
                        "metadata": metadata,
                        "elapsed_time": elapsed_time
                    })
                    
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"メタデータ取得失敗: {file_id}, ステータス: {response.status}, エラー: {error_text}")
                    self.test_results.append({
                        "test": "get_metadata",
                        "file_id": file_id,
                        "status": "failed",
                        "status_code": response.status,
                        "error": error_text,
                        "elapsed_time": elapsed_time
                    })
                    
                    return False
                
        except Exception as e:
            logger.error(f"メタデータ取得エラー: {file_id}, 例外: {str(e)}")
            self.test_results.append({
                "test": "get_metadata",
                "file_id": file_id,
                "status": "error",
                "error": str(e)
            })
            
            return False
    
    async def test_get_preview(self, session: aiohttp.ClientSession, file_id: str) -> bool:
        """
        ファイルプレビュー取得のテスト
        
        Args:
            session: HTTPセッション
            file_id: ファイルID
            
        Returns:
            bool: 成功したかどうか
        """
        logger.info(f"プレビュー取得テスト: {file_id}")
        
        try:
            start_time = time.time()
            async with session.get(
                f"{self.api_base_url}/files/{file_id}/preview"
            ) as response:
                elapsed_time = time.time() - start_time
                
                if response.status == 200:
                    preview = await response.json()
                    
                    logger.info(f"プレビュー取得成功: {file_id}, タイプ: {preview.get('preview_type')} ({elapsed_time:.2f}秒)")
                    self.stats["preview_success"] += 1
                    self.test_results.append({
                        "test": "get_preview",
                        "file_id": file_id,
                        "status": "success",
                        "preview_type": preview.get("preview_type"),
                        "elapsed_time": elapsed_time
                    })
                    
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"プレビュー取得失敗: {file_id}, ステータス: {response.status}, エラー: {error_text}")
                    self.stats["preview_failed"] += 1
                    self.test_results.append({
                        "test": "get_preview",
                        "file_id": file_id,
                        "status": "failed",
                        "status_code": response.status,
                        "error": error_text,
                        "elapsed_time": elapsed_time
                    })
                    
                    return False
                
        except Exception as e:
            logger.error(f"プレビュー取得エラー: {file_id}, 例外: {str(e)}")
            self.stats["preview_failed"] += 1
            self.test_results.append({
                "test": "get_preview",
                "file_id": file_id,
                "status": "error",
                "error": str(e)
            })
            
            return False
    
    async def test_download(self, session: aiohttp.ClientSession, file_id: str) -> bool:
        """
        ファイルダウンロードのテスト
        
        Args:
            session: HTTPセッション
            file_id: ファイルID
            
        Returns:
            bool: 成功したかどうか
        """
        logger.info(f"ダウンロードテスト: {file_id}")
        
        try:
            # まずメタデータを取得してファイル名を取得
            async with session.get(
                f"{self.api_base_url}/files/{file_id}/metadata"
            ) as metadata_response:
                if metadata_response.status != 200:
                    logger.error(f"メタデータ取得失敗: {file_id}, ステータス: {metadata_response.status}")
                    return False
                
                metadata = await metadata_response.json()
                filename = metadata.get("filename", f"downloaded_{file_id}")
            
            # ダウンロード
            start_time = time.time()
            async with session.get(
                f"{self.api_base_url}/files/{file_id}"
            ) as response:
                elapsed_time = time.time() - start_time
                
                if response.status == 200:
                    # ダウンロードしたファイルを保存
                    content = await response.read()
                    output_path = os.path.join(self.output_dir, f"downloaded_{os.path.basename(filename)}")
                    
                    with open(output_path, "wb") as f:
                        f.write(content)
                    
                    file_size = len(content)
                    logger.info(f"ダウンロード成功: {file_id} -> {output_path}, サイズ: {file_size} バイト ({elapsed_time:.2f}秒)")
                    self.stats["download_success"] += 1
                    self.test_results.append({
                        "test": "download",
                        "file_id": file_id,
                        "status": "success",
                        "output_path": output_path,
                        "file_size": file_size,
                        "elapsed_time": elapsed_time
                    })
                    
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"ダウンロード失敗: {file_id}, ステータス: {response.status}, エラー: {error_text}")
                    self.stats["download_failed"] += 1
                    self.test_results.append({
                        "test": "download",
                        "file_id": file_id,
                        "status": "failed",
                        "status_code": response.status,
                        "error": error_text,
                        "elapsed_time": elapsed_time
                    })
                    
                    return False
                
        except Exception as e:
            logger.error(f"ダウンロードエラー: {file_id}, 例外: {str(e)}")
            self.stats["download_failed"] += 1
            self.test_results.append({
                "test": "download",
                "file_id": file_id,
                "status": "error",
                "error": str(e)
            })
            
            return False
    
    async def test_chunk_upload(self, session: aiohttp.ClientSession, file_path: str) -> Optional[str]:
        """
        チャンクアップロードのテスト
        
        Args:
            session: HTTPセッション
            file_path: アップロードするファイルのパス
            
        Returns:
            file_id: アップロードされたファイルのID（失敗時はNone）
        """
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        chunk_size = 1024 * 1024  # 1MBチャンク
        total_chunks = (file_size + chunk_size - 1) // chunk_size  # 切り上げ
        
        logger.info(f"チャンクアップロードテスト: {file_name}, サイズ: {file_size} バイト, チャンク数: {total_chunks}")
        
        try:
            # コンテンツタイプの推測
            content_type, _ = mimetypes.guess_type(file_path)
            file_type = "document"
            if content_type:
                if content_type.startswith("image/"):
                    file_type = "image"
                elif content_type.startswith("text/"):
                    file_type = "text"
            
            # チャンクアップロードの初期化
            form_data = aiohttp.FormData()
            form_data.add_field("filename", file_name)
            form_data.add_field("file_type", file_type)
            form_data.add_field("total_size", str(file_size))
            form_data.add_field("total_chunks", str(total_chunks))
            form_data.add_field("content_type", content_type or "application/octet-stream")
            form_data.add_field("description", f"Chunk test upload of {file_name}")
            
            start_time = time.time()
            async with session.post(
                f"{self.api_base_url}/files/chunk-upload/init",
                data=form_data
            ) as init_response:
                if init_response.status != 200:
                    error_text = await init_response.text()
                    logger.error(f"チャンクアップロード初期化失敗: {file_name}, ステータス: {init_response.status}, エラー: {error_text}")
                    self.stats["chunk_upload_failed"] += 1
                    return None
                
                init_data = await init_response.json()
                file_id = init_data.get("file_id")
                logger.info(f"チャンクアップロード初期化成功: {file_name} -> {file_id}")
                
                # 各チャンクのアップロード
                with open(file_path, "rb") as f:
                    for chunk_index in range(total_chunks):
                        chunk_data = f.read(chunk_size)
                        
                        # チャンクデータのアップロード
                        chunk_form = aiohttp.FormData()
                        chunk_form.add_field("chunk_index", str(chunk_index))
                        chunk_form.add_field(
                            name="chunk_data",
                            value=chunk_data,
                            filename=f"chunk_{chunk_index}",
                            content_type="application/octet-stream"
                        )
                        
                        async with session.post(
                            f"{self.api_base_url}/files/chunk-upload/{file_id}",
                            data=chunk_form
                        ) as chunk_response:
                            if chunk_response.status != 200:
                                error_text = await chunk_response.text()
                                logger.error(f"チャンクアップロード失敗: {file_id}, チャンク: {chunk_index}, ステータス: {chunk_response.status}, エラー: {error_text}")
                                return None
                            
                            chunk_result = await chunk_response.json()
                            logger.info(f"チャンクアップロード進捗: {file_id}, チャンク: {chunk_index}/{total_chunks-1}, ステータス: {chunk_result.get('status')}")
                
                elapsed_time = time.time() - start_time
                logger.info(f"チャンクアップロード完了: {file_id}, 経過時間: {elapsed_time:.2f}秒")
                self.stats["chunk_upload_success"] += 1
                self.test_results.append({
                    "test": "chunk_upload",
                    "filename": file_name,
                    "status": "success",
                    "file_id": file_id,
                    "file_size": file_size,
                    "total_chunks": total_chunks,
                    "elapsed_time": elapsed_time
                })
                
                return file_id
                
        except Exception as e:
            logger.error(f"チャンクアップロードエラー: {file_name}, 例外: {str(e)}")
            self.stats["chunk_upload_failed"] += 1
            self.test_results.append({
                "test": "chunk_upload",
                "filename": file_name,
                "status": "error",
                "error": str(e)
            })
            
            return None
    
    async def test_chunk_download(self, session: aiohttp.ClientSession, file_id: str) -> bool:
        """
        チャンクダウンロードのテスト
        
        Args:
            session: HTTPセッション
            file_id: ファイルID
            
        Returns:
            bool: 成功したかどうか
        """
        logger.info(f"チャンクダウンロードテスト: {file_id}")
        
        try:
            # まずメタデータを取得してファイル名を取得
            async with session.get(
                f"{self.api_base_url}/files/{file_id}/metadata"
            ) as metadata_response:
                if metadata_response.status != 200:
                    logger.error(f"メタデータ取得失敗: {file_id}, ステータス: {metadata_response.status}")
                    return False
                
                metadata = await metadata_response.json()
                filename = metadata.get("filename", f"chunk_downloaded_{file_id}")
                file_size = metadata.get("file_size", 0)
            
            # ダウンロード先の準備
            output_path = os.path.join(self.output_dir, f"chunk_downloaded_{os.path.basename(filename)}")
            
            # チャンクサイズの設定
            chunk_size = 1024 * 1024  # 1MB
            
            # 最初のチャンクをダウンロードして合計チャンク数を取得
            start_time = time.time()
            async with session.get(
                f"{self.api_base_url}/files/{file_id}/chunk-download?chunk_index=0&chunk_size={chunk_size}"
            ) as first_response:
                if first_response.status != 200:
                    error_text = await first_response.text()
                    logger.error(f"チャンクダウンロード失敗: {file_id}, チャンク: 0, ステータス: {first_response.status}, エラー: {error_text}")
                    self.stats["chunk_download_failed"] += 1
                    return False
                
                total_chunks = int(first_response.headers.get("X-Total-Chunks", "1"))
                
                # ファイルを書き込み開始
                with open(output_path, "wb") as f:
                    # 最初のチャンクを書き込み
                    first_chunk = await first_response.read()
                    f.write(first_chunk)
                    
                    # 残りのチャンクをダウンロード
                    for chunk_index in range(1, total_chunks):
                        async with session.get(
                            f"{self.api_base_url}/files/{file_id}/chunk-download?chunk_index={chunk_index}&chunk_size={chunk_size}"
                        ) as chunk_response:
                            if chunk_response.status != 200:
                                error_text = await chunk_response.text()
                                logger.error(f"チャンクダウンロード失敗: {file_id}, チャンク: {chunk_index}, ステータス: {chunk_response.status}, エラー: {error_text}")
                                return False
                            
                            chunk_data = await chunk_response.read()
                            f.write(chunk_data)
                            
                            logger.info(f"チャンクダウンロード進捗: {file_id}, チャンク: {chunk_index}/{total_chunks-1}")
            
            elapsed_time = time.time() - start_time
            downloaded_size = os.path.getsize(output_path)
            
            logger.info(f"チャンクダウンロード完了: {file_id} -> {output_path}, サイズ: {downloaded_size} バイト ({elapsed_time:.2f}秒)")
            self.stats["chunk_download_success"] += 1
            self.test_results.append({
                "test": "chunk_download",
                "file_id": file_id,
                "status": "success",
                "output_path": output_path,
                "file_size": downloaded_size,
                "expected_size": file_size,
                "total_chunks": total_chunks,
                "elapsed_time": elapsed_time
            })
            
            return True
                
        except Exception as e:
            logger.error(f"チャンクダウンロードエラー: {file_id}, 例外: {str(e)}")
            self.stats["chunk_download_failed"] += 1
            self.test_results.append({
                "test": "chunk_download",
                "file_id": file_id,
                "status": "error",
                "error": str(e)
            })
            
            return False
    
    async def test_delete(self, session: aiohttp.ClientSession, file_id: str) -> bool:
        """
        ファイル削除のテスト
        
        Args:
            session: HTTPセッション
            file_id: ファイルID
            
        Returns:
            bool: 成功したかどうか
        """
        logger.info(f"削除テスト: {file_id}")
        
        try:
            start_time = time.time()
            async with session.delete(
                f"{self.api_base_url}/files/{file_id}"
            ) as response:
                elapsed_time = time.time() - start_time
                
                if response.status == 200:
                    result = await response.json()
                    
                    logger.info(f"削除成功: {file_id}, ステータス: {result.get('status')} ({elapsed_time:.2f}秒)")
                    self.test_results.append({
                        "test": "delete",
                        "file_id": file_id,
                        "status": "success",
                        "result": result,
                        "elapsed_time": elapsed_time
                    })
                    
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"削除失敗: {file_id}, ステータス: {response.status}, エラー: {error_text}")
                    self.test_results.append({
                        "test": "delete",
                        "file_id": file_id,
                        "status": "failed",
                        "status_code": response.status,
                        "error": error_text,
                        "elapsed_time": elapsed_time
                    })
                    
                    return False
                
        except Exception as e:
            logger.error(f"削除エラー: {file_id}, 例外: {str(e)}")
            self.test_results.append({
                "test": "delete",
                "file_id": file_id,
                "status": "error",
                "error": str(e)
            })
            
            return False
    
    def print_results(self):
        """テスト結果を表示する"""
        logger.info("==== テスト結果 ====")
        logger.info(f"実行時間: {self.stats['total_time']:.2f}秒")
        logger.info(f"アップロード:         成功: {self.stats['upload_success']}, 失敗: {self.stats['upload_failed']}")
        logger.info(f"ダウンロード:         成功: {self.stats['download_success']}, 失敗: {self.stats['download_failed']}")
        logger.info(f"プレビュー:           成功: {self.stats['preview_success']}, 失敗: {self.stats['preview_failed']}")
        logger.info(f"チャンクアップロード: 成功: {self.stats['chunk_upload_success']}, 失敗: {self.stats['chunk_upload_failed']}")
        logger.info(f"チャンクダウンロード: 成功: {self.stats['chunk_download_success']}, 失敗: {self.stats['chunk_download_failed']}")
        
        # 詳細なテスト結果をファイルに出力
        result_file = os.path.join(self.output_dir, "test_results.json")
        with open(result_file, "w") as f:
            json.dump({
                "stats": self.stats,
                "results": self.test_results
            }, f, indent=2)
        
        logger.info(f"詳細な結果は {result_file} に保存されました")


async def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="ファイル管理APIテスト")
    parser.add_argument("--api-url", type=str, default=DEFAULT_API_BASE_URL, help="APIのベースURL")
    parser.add_argument("--test-data", type=str, default=DEFAULT_TEST_DATA_DIR, help="テスト用ファイルディレクトリ")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_DIR, help="出力ディレクトリ")
    
    args = parser.parse_args()
    
    tester = FileAPITester(
        api_base_url=args.api_url,
        test_data_dir=args.test_data,
        output_dir=args.output
    )
    
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main()) 