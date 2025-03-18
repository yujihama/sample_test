"""
データベースマイグレーションユーティリティ [非推奨]

このモジュールは非推奨となっており、将来のバージョンで削除される予定です。
以下の新しいモジュールに移行してください：
- バックアップ機能 -> src.utils.backup_manager
- マイグレーション機能 -> Alembic (migrations/ ディレクトリ)
- 互換性関数 -> src.utils.db_adapter
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path
import warnings

# 非推奨警告
warnings.warn(
    "db_migration.pyモジュールは非推奨です。代わりに backup_manager.py と Alembic を使用してください。",
    DeprecationWarning,
    stacklevel=2
)

# ルートディレクトリをパスに追加して他のモジュールをインポートできるようにする
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(root_dir)

from src.core.config import settings
from src.models.db_models import Base
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session
from src.utils.db_adapter import db_adapter

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
    """
    データベースエンジンを取得する [非推奨]
    
    代わりに db_adapter.get_db_engine() を使用してください。
    """
    warnings.warn(
        "get_db_engine() は非推奨です。代わりに db_adapter.get_db_engine() を使用してください。",
        DeprecationWarning,
        stacklevel=2
    )
    return db_adapter.get_db_engine()

def backup_database():
    """
    データベースのバックアップを作成 [非推奨]
    
    代わりに backup_manager.backup_database() を使用してください。
    """
    warnings.warn(
        "backup_database() は非推奨です。代わりに backup_manager.backup_database() を使用してください。",
        DeprecationWarning,
        stacklevel=2
    )
    return db_adapter.backup_database()

def create_database():
    """
    新しいデータベースを作成する [非推奨]
    
    代わりに db_adapter.create_database() を使用してください。
    """
    warnings.warn(
        "create_database() は非推奨です。代わりに db_adapter.create_database() を使用してください。",
        DeprecationWarning,
        stacklevel=2
    )
    return db_adapter.create_database()

def migrate_database():
    """
    既存のデータベースをマイグレーションする [非推奨]
    
    代わりに Alembic または db_adapter.migrate_database() を使用してください。
    """
    warnings.warn(
        "migrate_database() は非推奨です。代わりに Alembic または db_adapter.migrate_database() を使用してください。",
        DeprecationWarning,
        stacklevel=2
    )
    return db_adapter.migrate_database()

def perform_migration():
    """
    マイグレーションプロセスを実行する [非推奨]
    
    代わりに `alembic upgrade head` または db_adapter.perform_migration() を使用してください。
    """
    warnings.warn(
        "perform_migration() は非推奨です。代わりに `alembic upgrade head` または db_adapter.perform_migration() を使用してください。",
        DeprecationWarning,
        stacklevel=2
    )
    return db_adapter.perform_migration()

if __name__ == "__main__":
    print("このモジュールは非推奨です。代わりに以下のコマンドを使用してください：")
    print("  $ alembic upgrade head  # マイグレーションを実行")
    print("  $ python -m src.utils.backup_manager  # バックアップを作成")
