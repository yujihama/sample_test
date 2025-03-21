"""
アプリケーション全体の設定管理
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List

from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # 基本設定
    APP_NAME: str = "内部監査サンプルデータ自動テストAIエージェント"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 5000
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # ディレクトリ設定
    BASE_DIR: str = str(Path(__file__).parent.parent.parent.absolute())
    DATA_DIR: str = str(Path(BASE_DIR) / "data")
    LOGS_DIR: str = str(Path(BASE_DIR) / "logs")
    UPLOAD_DIR: str = str(Path(BASE_DIR) / "data" / "uploads")
    
    # LLM設定
    LLM_PROVIDER: str = "openai"  # openai, anthropic
    LLM_MODEL: str = "gpt-4o"  # gpt-4, gpt-3.5-turbo, claude-3-opus, etc.
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 4000
    LLM_RETRY_MAX_ATTEMPTS: int = 3
    LLM_RETRY_BASE_DELAY: float = 1.0
    LLM_RETRY_MAX_DELAY: float = 60.0
    LLM_RETRY_BACKOFF_FACTOR: float = 2.0
    # API キー設定
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # エージェント設定
    AGENT_IDS: List[str] = ["agent_a", "agent_b", "agent_c", "agent_d", "coordinator"]
    # 各エージェントのID
    AGENT_A_ID: str = "agent_a"
    AGENT_B_ID: str = "agent_b"
    AGENT_C_ID: str = "agent_c"
    AGENT_D_ID: str = "agent_d"
    
    # チェックポイント設定
    CHECKPOINT_PATH: str = str(Path(BASE_DIR) / "data" / "checkpoints")
    
    # ログ設定
    LOG_FORMAT: str = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    LOG_ROTATION: str = "20 MB"
    LOG_RETENTION: str = "1 week"
    
    # データベース設定
    DB_URL: str = "sqlite:///./data/db/audit_agent_new.db"
    # DB_URLのエイリアスとしてDATABASE_URLを追加
    DATABASE_URL: str = "sqlite:///./data/db/audit_agent_new.db"
    # SQLiteデータベースファイルの実際のパス
    DB_PATH: str = str(Path(BASE_DIR) / "data" / "db" / "audit_agent_new.db")
    
    # テスト設定
    TESTING: bool = False
    TEST_DATA_DIR: str = str(Path(BASE_DIR) / "tests" / "data")
    MOCK_HUMAN_INTERACTION: bool = True  # テスト時の人間の介入をモック化するかどうか
    
    model_config = ConfigDict(
        env_file="config/.env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# 設定インスタンスを作成
settings = Settings()

# ディレクトリの作成
os.makedirs(settings.DATA_DIR, exist_ok=True)
os.makedirs(settings.LOGS_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(Path(settings.DATA_DIR) / "messages", exist_ok=True)
os.makedirs(Path(settings.DATA_DIR) / "contexts", exist_ok=True)

# テスト中かどうかを確認
if os.environ.get("TESTING") == "True":
    settings.TESTING = True
    settings.DATA_DIR = settings.TEST_DATA_DIR
    settings.UPLOAD_DIR = str(Path(settings.TEST_DATA_DIR) / "uploads")
    settings.DATABASE_URL = f"sqlite:///{settings.TEST_DATA_DIR}/test.db"
    settings.DB_URL = settings.DATABASE_URL
    settings.DB_PATH = str(Path(settings.TEST_DATA_DIR) / "test.db")
    os.makedirs(settings.TEST_DATA_DIR, exist_ok=True)
    os.makedirs(Path(settings.TEST_DATA_DIR) / "messages", exist_ok=True)
    os.makedirs(Path(settings.TEST_DATA_DIR) / "contexts", exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


def initialize_app():
    """
    アプリケーションの初期化処理を行う
    
    Returns:
        初期化されたアプリケーション設定
    """
    from loguru import logger
    
    # ディレクトリの存在確認と作成
    required_dirs = [
        settings.DATA_DIR,
        settings.LOGS_DIR,
        settings.UPLOAD_DIR,
        Path(settings.DATA_DIR) / "messages",
        Path(settings.DATA_DIR) / "contexts"
    ]
    
    for directory in required_dirs:
        os.makedirs(directory, exist_ok=True)
    
    # データベース初期化（必要に応じて）
    if not settings.TESTING:
        try:
            from src.utils.db_manager import init_db
            init_db()
            logger.info("データベースを初期化しました")
        except ImportError:
            logger.warning("データベース初期化モジュールが見つかりません")
        except Exception as e:
            logger.error(f"データベース初期化中にエラーが発生しました: {e}")
    
    logger.info(f"アプリケーション {settings.APP_NAME} v{settings.APP_VERSION} を初期化しました")
    return settings 