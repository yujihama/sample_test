"""
データベースの初期化スクリプト

このスクリプトはデータベースのテーブルを全て作成します。
"""

import sys
import os
import subprocess

# srcディレクトリをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.db_models import Base
from sqlalchemy import create_engine, inspect
from src.core.config import settings

def main():
    """データベーステーブルを作成する"""
    # データベースURLを取得
    DATABASE_URL = settings.DATABASE_URL

    # データベースのディレクトリが存在しない場合は作成
    if DATABASE_URL.startswith('sqlite:///'):
        db_path = DATABASE_URL.replace('sqlite:///', '')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Alembicのマイグレーションを実行
    subprocess.run(['alembic', 'upgrade', 'head'], check=True)
    print("マイグレーションを適用しました")

    # エンジンを作成してテーブル構造を確認
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if DATABASE_URL.startswith('sqlite') else {}
    )

    # テーブル構造を確認
    inspector = inspect(engine)
    for table_name in inspector.get_table_names():
        print(f"\nテーブル '{table_name}' のカラム:")
        for column in inspector.get_columns(table_name):
            print(f"  - {column['name']} ({column['type']})")

if __name__ == "__main__":
    main() 