"""
データベースマイグレーションユーティリティ

データベーススキーマの変更を管理し、適用するためのスクリプト
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path

# ルートディレクトリをパスに追加して他のモジュールをインポートできるようにする
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(root_dir)

from src.core.config import settings
from src.models.db_models import Base
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(root_dir, "db_migration.log"))
    ]
)
logger = logging.getLogger(__name__)

def get_db_engine():
    """データベースエンジンを取得する"""
    db_url = settings.DATABASE_URL
    logger.info(f"データベースURL: {db_url}")
    return create_engine(db_url)

def backup_database():
    """データベースのバックアップを作成"""
    db_path = settings.DB_PATH
    backup_path = f"{db_path}.backup"
    logger.info(f"データベースをバックアップしています: {db_path} -> {backup_path}")
    
    try:
        # データベースファイルが存在する場合のみバックアップを作成
        if os.path.exists(db_path):
            import shutil
            shutil.copy2(db_path, backup_path)
            logger.info("バックアップが正常に作成されました")
            return True
        else:
            logger.warning("データベースファイルが存在しないため、バックアップは作成されませんでした")
            return False
    except Exception as e:
        logger.error(f"バックアップの作成中にエラーが発生しました: {e}")
        return False

def create_database():
    """新しいデータベースを作成する"""
    engine = get_db_engine()
    logger.info("データベーススキーマを作成しています...")
    
    try:
        # すべてのテーブルを作成
        Base.metadata.create_all(engine)
        logger.info("データベーススキーマが正常に作成されました")
        return True
    except Exception as e:
        logger.error(f"データベーススキーマの作成中にエラーが発生しました: {e}")
        return False

def migrate_database():
    """既存のデータベースをマイグレーションする"""
    engine = get_db_engine()
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    logger.info(f"既存のテーブル: {existing_tables}")
    logger.info("データベースをマイグレーションしています...")
    
    try:
        # 新しいテーブルの作成とカラムの追加のみを行う
        # 既存のデータは保持される
        Base.metadata.create_all(engine)
        logger.info("データベースマイグレーションが正常に完了しました")
        return True
    except Exception as e:
        logger.error(f"データベースマイグレーション中にエラーが発生しました: {e}")
        return False

def perform_migration():
    """マイグレーションプロセスを実行する"""
    logger.info("データベースマイグレーションを開始します...")
    
    # バックアップを作成
    backup_result = backup_database()
    if not backup_result:
        logger.warning("バックアップが作成されませんでした。既存のデータベースファイルが存在しない可能性があります。")
    
    # マイグレーションを実行
    migration_result = migrate_database()
    
    if migration_result:
        logger.info("マイグレーションが正常に完了しました。")
    else:
        logger.error("マイグレーションに失敗しました。")
        # バックアップから復元するロジックをここに追加することもできます
    
    return migration_result

if __name__ == "__main__":
    perform_migration()
