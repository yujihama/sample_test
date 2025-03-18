"""
データベースおよびファイルのバックアップ管理ユーティリティ

このモジュールは、データベースファイルや重要なデータファイルのバックアップを
作成・管理するための機能を提供します。
"""

import os
import sys
import shutil
import datetime
import zipfile
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from loguru import logger

# ルートディレクトリをパスに追加して他のモジュールをインポートできるようにする
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(root_dir)

from src.core.config import settings

# バックアップの保存場所
DEFAULT_BACKUP_DIR = os.path.join(root_dir, "backups")
os.makedirs(DEFAULT_BACKUP_DIR, exist_ok=True)

def backup_database(
    db_path: Optional[str] = None, 
    backup_path: Optional[str] = None,
    add_timestamp: bool = False
) -> Dict[str, Any]:
    """
    データベースのバックアップを作成
    
    Args:
        db_path: バックアップするデータベースのパス（省略時はsettingsから取得）
        backup_path: バックアップの保存先パス（省略時はデフォルト生成）
        add_timestamp: ファイル名にタイムスタンプを追加するかどうか
    
    Returns:
        バックアップ結果の情報を含む辞書
    """
    # データベースパスの取得
    if db_path is None:
        db_path = settings.DB_PATH
    
    # バックアップパスの生成
    if backup_path is None:
        db_filename = os.path.basename(db_path)
        if add_timestamp:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{os.path.splitext(db_filename)[0]}_{timestamp}.backup"
        else:
            backup_filename = f"{db_filename}.backup"
        backup_path = os.path.join(DEFAULT_BACKUP_DIR, backup_filename)
    
    logger.info(f"データベースをバックアップしています: {db_path} -> {backup_path}")
    
    result = {
        "success": False,
        "source": db_path,
        "destination": backup_path,
        "timestamp": datetime.datetime.now().isoformat(),
        "error": None
    }
    
    try:
        # データベースファイルが存在する場合のみバックアップを作成
        if os.path.exists(db_path):
            # ディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            # コピー実行
            shutil.copy2(db_path, backup_path)
            logger.info(f"バックアップが正常に作成されました: {backup_path}")
            result["success"] = True
        else:
            error_msg = "データベースファイルが存在しないため、バックアップは作成されませんでした"
            logger.warning(error_msg)
            result["error"] = error_msg
    except Exception as e:
        error_msg = f"バックアップの作成中にエラーが発生しました: {e}"
        logger.error(error_msg)
        result["error"] = str(e)
    
    return result

def restore_database_from_backup(
    backup_path: str,
    target_path: Optional[str] = None,
    create_backup: bool = True
) -> Dict[str, Any]:
    """
    バックアップからデータベースを復元
    
    Args:
        backup_path: 復元元のバックアップパス
        target_path: 復元先のパス（省略時はsettingsから取得）
        create_backup: 復元前に現在のDBをバックアップするかどうか
    
    Returns:
        復元結果の情報を含む辞書
    """
    # 復元先パスの取得
    if target_path is None:
        target_path = settings.DB_PATH
    
    result = {
        "success": False,
        "source": backup_path,
        "destination": target_path,
        "timestamp": datetime.datetime.now().isoformat(),
        "backup_created": None,
        "error": None
    }
    
    # バックアップファイルの存在確認
    if not os.path.exists(backup_path):
        error_msg = f"指定されたバックアップファイルが存在しません: {backup_path}"
        logger.error(error_msg)
        result["error"] = error_msg
        return result
    
    # 復元前バックアップの作成
    if create_backup and os.path.exists(target_path):
        backup_result = backup_database(
            db_path=target_path,
            add_timestamp=True
        )
        result["backup_created"] = backup_result
    
    try:
        # 復元処理
        logger.info(f"バックアップから復元しています: {backup_path} -> {target_path}")
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        # コピー実行
        shutil.copy2(backup_path, target_path)
        logger.info(f"復元が正常に完了しました: {target_path}")
        result["success"] = True
    except Exception as e:
        error_msg = f"復元中にエラーが発生しました: {e}"
        logger.error(error_msg)
        result["error"] = str(e)
    
    return result

def list_backups(pattern: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    利用可能なバックアップのリストを取得
    
    Args:
        pattern: ファイル名フィルターパターン（例: "*.backup"）
        
    Returns:
        バックアップ情報のリスト
    """
    if pattern is None:
        pattern = "*.backup"
        
    backup_files = []
    for f in Path(DEFAULT_BACKUP_DIR).glob(pattern):
        if f.is_file():
            backup_info = {
                "filename": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "created": datetime.datetime.fromtimestamp(f.stat().st_ctime).isoformat(),
                "modified": datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            }
            backup_files.append(backup_info)
            
    # 作成日時の降順でソート
    backup_files.sort(key=lambda x: x["created"], reverse=True)
    return backup_files

def create_full_backup(
    output_path: Optional[str] = None,
    include_db: bool = True,
    include_uploads: bool = True,
    include_logs: bool = False
) -> Dict[str, Any]:
    """
    システム全体のバックアップを作成（ZIP形式）
    
    Args:
        output_path: 出力先パス（省略時は自動生成）
        include_db: データベースを含めるか
        include_uploads: アップロードファイルを含めるか
        include_logs: ログファイルを含めるか
    
    Returns:
        バックアップ結果の情報を含む辞書
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if output_path is None:
        output_path = os.path.join(DEFAULT_BACKUP_DIR, f"fullbackup_{timestamp}.zip")
    
    # 出力ディレクトリの作成
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    result = {
        "success": False,
        "path": output_path,
        "timestamp": datetime.datetime.now().isoformat(),
        "included_files": [],
        "error": None
    }
    
    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # データベースのバックアップを含める
            if include_db and os.path.exists(settings.DB_PATH):
                zipf.write(settings.DB_PATH, os.path.basename(settings.DB_PATH))
                result["included_files"].append(settings.DB_PATH)
            
            # アップロードファイルを含める
            if include_uploads:
                uploads_dir = os.path.join(root_dir, "uploads")
                if os.path.exists(uploads_dir):
                    for root, _, files in os.walk(uploads_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, root_dir)
                            zipf.write(file_path, arcname)
                            result["included_files"].append(arcname)
            
            # ログファイルを含める
            if include_logs:
                logs_dir = os.path.join(root_dir, "logs")
                if os.path.exists(logs_dir):
                    for root, _, files in os.walk(logs_dir):
                        for file in files:
                            if file.endswith('.log'):
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, root_dir)
                                zipf.write(file_path, arcname)
                                result["included_files"].append(arcname)
        
        result["success"] = True
        logger.info(f"システム全体のバックアップが正常に作成されました: {output_path}")
    except Exception as e:
        error_msg = f"システム全体のバックアップ作成中にエラーが発生しました: {e}"
        logger.error(error_msg)
        result["error"] = str(e)
    
    return result

# 以下、互換性のための関数
def backup_database_legacy():
    """db_migration.pyとの互換性のための関数"""
    result = backup_database()
    return result["success"]

if __name__ == "__main__":
    # コマンドラインからの実行テスト
    backup_result = backup_database(add_timestamp=True)
    print(f"バックアップ結果: {backup_result}")
    
    backups = list_backups()
    print(f"利用可能なバックアップ: {len(backups)}個")
    for backup in backups[:3]:  # 最新の3つだけ表示
        print(f" - {backup['filename']} ({backup['created']})") 