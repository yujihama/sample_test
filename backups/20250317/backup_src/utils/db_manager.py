"""
SQLAlchemyを使用したデータベース接続とセッション管理
"""

import os
import time
from sqlalchemy import create_engine, event, pool, exc, text
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.orm import declarative_base
from contextlib import contextmanager
from loguru import logger
from typing import Iterator, Optional

from src.core.config import settings

# SQLAlchemy Base classを作成
Base = declarative_base()

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
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,  # 接続プールのサイズ
        max_overflow=20,  # 最大オーバーフロー接続数
        pool_timeout=30,  # 接続タイムアウト（秒）
        pool_recycle=1800,  # 接続の再利用時間（秒）
        pool_pre_ping=True,  # 接続前に生存確認
        connect_args={"connect_timeout": DB_CONNECT_TIMEOUT},
        echo=DB_ECHO_LOG
    )
else:
    # 開発/テスト環境の設定（PostgreSQL/MySQL）
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=10,
        pool_recycle=600,  # 10分で接続を再利用
        pool_pre_ping=True,  # 接続前に生存確認
        connect_args={"connect_timeout": DB_CONNECT_TIMEOUT},
        echo=DB_ECHO_LOG
    )

# SQLiteの場合、外部キー制約を有効にする
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")  # WALモードでパフォーマンス向上
        cursor.execute("PRAGMA synchronous=NORMAL")  # 同期レベルの最適化
        cursor.close()

# セッションファクトリを作成 (SQLAlchemy 2.0対応)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)

# アクティブなセッションをトラッキングするためのセット
_active_sessions = set()

def init_db():
    """
    データベースを初期化する
    - テーブルが存在しない場合は作成
    """
    try:
        # インポートエラーを防ぐため、必要なときだけインポート
        from src.models.db_models import Base as ModelsBase
        
        try:
            from src.migrations.manager import run_migrations
            # マイグレーションを実行して最新のスキーマを適用
            run_migrations()
            logger.info("データベーススキーマが初期化されました")
        except ImportError:
            # マイグレーションモジュールがない場合は直接スキーマを作成
            ModelsBase.metadata.create_all(bind=engine)
            logger.info("データベーススキーマが直接作成されました")
    except ImportError as e:
        logger.error(f"データベースモデルのインポートエラー: {e}")
        # 基本的なBaseでスキーマを作成
        Base.metadata.create_all(bind=engine)
        logger.info("基本的なデータベーススキーマを作成しました")
    except Exception as e:
        logger.error(f"データベーススキーマの初期化中にエラーが発生しました: {e}")
        raise


def get_db() -> Iterator[Session]:
    """
    データベース接続を取得するための依存性関数。
    
    FastAPIの依存性注入システムで使用するためのジェネレータ関数です。
    セッションはリクエストの終了時に自動的にクローズされます。
    
    Yields:
        Session: アクティブなデータベースセッション
        
    Raises:
        Exception: セッション使用中に発生した例外
    """
    db = None
    retries = 0
    last_error = None
    
    # 接続試行
    while retries <= DB_MAX_RETRIES:
        try:
            db = db_session()
            # 接続テスト - 軽量なSQLを実行
            db.execute(text("SELECT 1"))
            _active_sessions.add(db)
            logger.debug(f"データベースセッションを作成しました (ID: {id(db)})")
            break
        except exc.DBAPIError as e:
            last_error = e
            retries += 1
            if retries <= DB_MAX_RETRIES:
                logger.warning(f"データベース接続に失敗しました。再試行中... ({retries}/{DB_MAX_RETRIES}): {e}")
                time.sleep(DB_RETRY_INTERVAL * retries)  # 指数バックオフ
            else:
                logger.error(f"データベース接続の最大再試行回数に達しました: {e}")
                raise ConnectionError(f"データベースへの接続に失敗しました: {e}")
    
    if db is None:
        raise ConnectionError(f"データベースへの接続に失敗しました: {last_error}")
    
    try:
        yield db
    except exc.DBAPIError as e:
        db.rollback()
        logger.error(f"データベースAPI操作中にエラーが発生しました: {e}")
        raise
    except exc.SQLAlchemyError as e:
        db.rollback()
        logger.error(f"SQLAlchemy操作中にエラーが発生しました: {e}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"データベースセッション使用中に予期しないエラーが発生しました: {e}")
        raise
    finally:
        if db in _active_sessions:
            _active_sessions.remove(db)
        db.close()
        logger.debug(f"データベースセッションを閉じました (ID: {id(db)})")


@contextmanager
def session_scope():
    """
    トランザクションをラップするコンテキストマネージャー
    
    使用例:
    ```
    with session_scope() as session:
        obj = session.query(Model).filter(Model.id == 1).first()
        obj.name = 'New Name'
    ```
    
    Yields:
        Session: データベースセッション
        
    Raises:
        ConnectionError: データベース接続に失敗した場合
        IntegrityError: データ整合性違反が発生した場合
        SQLAlchemyError: SQLAlchemyでの操作中にエラーが発生した場合
        Exception: 予期しないエラーが発生した場合
    """
    session = None
    retries = 0
    last_error = None
    
    # 接続試行
    while retries <= DB_MAX_RETRIES:
        try:
            session = SessionLocal()
            # 接続テスト - 軽量なSQLを実行
            session.execute("SELECT 1")
            _active_sessions.add(session)
            logger.debug(f"データベーストランザクションを開始しました (ID: {id(session)})")
            break
        except exc.DBAPIError as e:
            last_error = e
            retries += 1
            if retries <= DB_MAX_RETRIES:
                logger.warning(f"データベース接続に失敗しました。再試行中... ({retries}/{DB_MAX_RETRIES}): {e}")
                time.sleep(DB_RETRY_INTERVAL * retries)  # 指数バックオフ
            else:
                logger.error(f"データベース接続の最大再試行回数に達しました: {e}")
                raise ConnectionError(f"データベースへの接続に失敗しました: {e}")
    
    if session is None:
        raise ConnectionError(f"データベースへの接続に失敗しました: {last_error}")
    
    try:
        yield session
        session.commit()
        logger.debug(f"データベーストランザクションをコミットしました (ID: {id(session)})")
    except exc.IntegrityError as e:
        session.rollback()
        logger.error(f"データ整合性違反によりトランザクションをロールバックしました: {e}")
        raise ValueError(f"データ整合性違反が発生しました: {e}")
    except exc.OperationalError as e:
        session.rollback()
        logger.error(f"データベース操作エラーによりトランザクションをロールバックしました: {e}")
        if "timeout" in str(e).lower():
            raise TimeoutError(f"データベース操作がタイムアウトしました: {e}")
        raise RuntimeError(f"データベース操作エラーが発生しました: {e}")
    except exc.SQLAlchemyError as e:
        session.rollback()
        logger.error(f"SQLAlchemyエラーによりトランザクションをロールバックしました: {e}")
        raise RuntimeError(f"データベースエラーが発生しました: {e}")
    except Exception as e:
        session.rollback()
        logger.error(f"予期しないエラーによりトランザクションをロールバックしました: {e}")
        raise
    finally:
        if session in _active_sessions:
            _active_sessions.remove(session)
        session.close()
        logger.debug(f"データベースセッションを閉じました (ID: {id(session)})")


def close_db_connections():
    """
    アクティブなすべてのデータベース接続を閉じる
    アプリケーション終了時に呼び出すことでリソースリークを防止
    """
    active_count = len(_active_sessions)
    if active_count > 0:
        logger.warning(f"{active_count}個のアクティブなデータベースセッションを強制的に閉じています")
        for session in list(_active_sessions):
            try:
                session.close()
                _active_sessions.remove(session)
            except Exception as e:
                logger.error(f"セッションのクローズ中にエラーが発生しました: {e}")
    
    # スコープ付きセッションの破棄
    db_session.remove()
    
    # エンジン接続プールの破棄
    try:
        engine.dispose()
    except Exception as e:
        logger.error(f"エンジン接続プールの破棄中にエラーが発生しました: {e}")
    
    logger.info("データベース接続を閉じました") 