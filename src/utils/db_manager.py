"""
SQLAlchemyを使用したデータベース接続とセッション管理
"""

import os
import time
import functools
from sqlalchemy import create_engine, event, pool, exc, text
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.orm import declarative_base
from contextlib import contextmanager
from loguru import logger
from typing import Iterator, Optional, Callable, Any, Generator

from src.core.config import settings
from src.db.session import get_db_session as session_get_db_session

# SQLAlchemy Base classを作成
Base = declarative_base()

# エクスポートする関数のリスト
__all__ = [
    'Base', 'get_db', 'get_db_context', 'get_db_for_test', 'init_db', 
    'execute_sql', 'with_db_session', 'get_db_session'
]

# テスト環境かどうかを確認
is_testing = os.environ.get("TESTING") == "True"

# データベースURLを取得
DATABASE_URL = settings.DATABASE_URL

# デバッグモードの設定
DB_ECHO_LOG = getattr(settings, 'DB_ECHO_LOG', False)

# 接続再試行設定
DB_MAX_RETRIES = getattr(settings, 'DB_MAX_RETRIES', 3)
DB_RETRY_INTERVAL = getattr(settings, 'DB_RETRY_INTERVAL', 0.5)  # 秒
DB_CONNECT_TIMEOUT = getattr(settings, 'DB_CONNECT_TIMEOUT', 5)  # 秒

# データベースのディレクトリが存在しない場合は作成
if DATABASE_URL.startswith('sqlite:///'):
    db_path = DATABASE_URL.replace('sqlite:///', '')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

# 環境に応じたエンジン設定
if DATABASE_URL.startswith('sqlite'):
    # SQLite用の設定
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": DB_CONNECT_TIMEOUT  # 接続タイムアウト
        },
        echo=DB_ECHO_LOG,
        # 接続プールの設定
        pool_pre_ping=True,  # 接続前に生存確認
        pool_recycle=300     # 5分で接続を再利用
    )
elif getattr(settings, 'APP_ENV', 'development') == 'production':
    # 本番環境の設定（PostgreSQL/MySQL）
    # 接続プール、リトライ、タイムアウトなどのパラメータを強化
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,  # 30分で接続を再利用
        pool_pre_ping=True,
        echo=DB_ECHO_LOG
    )
else:
    # 開発環境の設定
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        echo=DB_ECHO_LOG
    )

# SQLiteで外部キー制約を有効にする
if DATABASE_URL.startswith('sqlite'):
    event.listen(engine, 'connect', lambda conn, _: conn.execute('PRAGMA foreign_keys=ON'))

# セッションを作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# SQLite接続失敗時のリトライロジック
@contextmanager
def retry_engine_operation(
    operation: Callable[[], Any], 
    max_retries: int = DB_MAX_RETRIES,
    retry_interval: float = DB_RETRY_INTERVAL
):
    """
    SQLite操作のリトライ処理
    
    Args:
        operation: 実行する操作（関数またはラムダ）
        max_retries: 最大リトライ回数
        retry_interval: リトライの間隔（秒）
    """
    retries = 0
    last_error = None
    
    while retries <= max_retries:
        try:
            result = operation()
            return result
        except exc.OperationalError as e:
            last_error = e
            retries += 1
            if retries <= max_retries:
                time.sleep(retry_interval)
            continue
        except Exception as e:
            raise e
    
    raise last_error

def get_db() -> Iterator[Session]:
    """データベースセッションを取得する"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """データベースセッションをコンテキストマネージャとして取得する"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_for_test() -> Iterator[Session]:
    """テスト用にイテレータとしてデータベースセッションを取得する"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def with_db_session(func):
    """
    データベースセッションを自動的に管理するデコレータ
    
    このデコレータを使うと、関数の最初の引数としてデータベースセッションが渡されます。
    関数の実行後、セッションは自動的に閉じられます。
    
    使用例:
    @with_db_session
    def my_function(db, other_args):
        # dbを使った処理
        return result
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with get_db_context() as db:
            return func(db, *args, **kwargs)
    return wrapper

def init_db():
    """
    データベースの初期化
    - テーブルが存在しない場合は作成
    - テスト環境の場合は既存のテーブルを削除して再作成
    - テーブルとカラムの存在を検証
    """
    try:
        # テスト環境かどうかを確認
        is_testing = os.environ.get("TESTING") == "True"
        
        # 使用するデータベースURLを決定
        db_url = settings.DATABASE_URL
        logger.info(f"データベースを初期化します: {db_url} (テスト環境: {is_testing})")
        
        # モデルをインポート
        from src.models.db_models import (
            AuditProcedure, SampleData, Workflow, TestPlan, TestResult, 
            EvaluationSummary, Report, MessageLog, Regulation, 
            RegulationAuditTrail, RegulationDecisionReference,
            AuditTrail, Finding, Message, AgentState, AgentDecision,
            GraphStateHistory, CheckpointRecord, HumanInterventionRequest,
            HumanInterventionResponse, AuditResult
        )
        
        # テスト環境の場合、既存のテーブルを削除
        if is_testing:
            logger.info("テスト環境: 既存のテーブルを削除します")
            with engine.begin() as conn:
                # 外部キー制約を一時的に無効化
                conn.execute(text("PRAGMA foreign_keys=OFF"))
                try:
                    # 既存のテーブルを削除
                    Base.metadata.drop_all(bind=conn)
                finally:
                    # 外部キー制約を再度有効化
                    conn.execute(text("PRAGMA foreign_keys=ON"))
        
        # テーブルを作成
        logger.info("データベーステーブルを作成します")
        with engine.begin() as conn:
            Base.metadata.create_all(bind=conn)
        
        # テーブルとカラムの検証
        verification_errors = []
        with engine.connect() as conn:
            # 実際のテーブル一覧を取得
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            existing_tables = {row[0] for row in result}
            
            # 期待されるテーブル一覧を取得
            expected_tables = {table.name for table in Base.metadata.sorted_tables}
            
            # 欠落しているテーブルをチェック
            missing_tables = expected_tables - existing_tables
            if missing_tables:
                verification_errors.append(f"欠落しているテーブル: {missing_tables}")
            
            # 各テーブルのカラムを確認
            for table in Base.metadata.sorted_tables:
                table_name = table.name
                if table_name in existing_tables and table_name != 'sqlite_sequence':
                    # テーブル情報を取得
                    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                    existing_columns = {row[1] for row in result}
                    expected_columns = {column.name for column in table.columns}
                    
                    # 欠落しているカラムをチェック
                    missing_columns = expected_columns - existing_columns
                    if missing_columns:
                        verification_errors.append(f"テーブル {table_name} の欠落しているカラム: {missing_columns}")
        
        # 検証エラーがある場合は例外を発生
        if verification_errors:
            raise Exception("データベース検証エラー:\n" + "\n".join(verification_errors))
            
        logger.info("すべてのテーブルとカラムが正しく作成されました")
            
    except ImportError as e:
        logger.error(f"モデルのインポートに失敗しました: {e}")
        raise
    except Exception as e:
        logger.error(f"データベースの初期化中にエラーが発生しました: {e}")
        raise

# テキストSQLの実行
def execute_sql(sql: str, params=None):
    """
    テキストSQLを実行する
    SQLAlchemy 2.0互換性対応 - text()関数を使用
    
    Args:
        sql: 実行するSQL文字列
        params: SQLパラメータ
        
    Returns:
        クエリ結果
    """
    try:
        with SessionLocal() as session:
            result = session.execute(text(sql), params)
            session.commit()
            return result
    except Exception as e:
        logger.error(f"SQL実行中にエラーが発生しました: {sql}, エラー: {e}")
        raise 

def get_db_session() -> Generator[Session, None, None]:
    """
    データベースセッションを取得する
    このラッパー関数は、src.db.session.get_db_sessionを呼び出します
    
    使用例:
    db = next(get_db_session())
    try:
        # dbを使用したコード
    finally:
        db.close()
    """
    return session_get_db_session() 