"""
データベースセッション管理モジュール

このモジュールでは、SQLAlchemyを使用したデータベースセッションの管理機能を提供します。
FastAPIのDependsと組み合わせて使用することを想定しています。
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from src.core.config import settings
import os

# データベース接続設定
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./audit_agent.db")

# エンジン作成
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# セッションファクトリ
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# モデルのベースクラス
Base = declarative_base()


def get_db_session() -> Generator[Session, None, None]:
    """
    データベースセッションを取得するための依存性関数
    
    FastAPIのDependsと組み合わせて使用します。
    セッションはリクエスト処理後に自動的にクローズされます。
    
    Yields:
        Session: SQLAlchemyセッションオブジェクト
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 