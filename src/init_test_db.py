"""
テスト用データベースの初期化スクリプト

このスクリプトはテスト用データベースのテーブルを全て作成します。
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from models.db_models import Base

# テスト環境フラグを設定
os.environ["TESTING"] = "True"

# 必要なモジュールをインポート（テスト環境フラグ設定後）
from core.config import settings

def main():
    """テスト用データベーステーブルを作成する"""
    # テスト用ディレクトリの作成
    os.makedirs(settings.TEST_DATA_DIR, exist_ok=True)
    
    # データベースのパスを取得
    test_db_path = Path(settings.TEST_DATA_DIR) / "test.db"
    print(f"テスト用データベースパス: {test_db_path}")
    
    # データベースファイルが存在する場合は削除
    if test_db_path.exists():
        test_db_path.unlink()
        print("既存のテスト用データベースファイルを削除しました")
    
    # エンジンを作成
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith('sqlite') else {}
    )
    
    # テーブルを作成
    Base.metadata.create_all(bind=engine)
    print("テスト用データベーステーブルを作成しました")

if __name__ == "__main__":
    main() 