"""
アプリケーション設定
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from loguru import logger


# .envファイルをロード
load_dotenv()


class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # アプリケーション全般
    APP_NAME: str = "内部監査サンプルデータ自動テストAIエージェントシステム"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    
    # LLM設定
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o")
    DEFAULT_EMBEDDING_MODEL: str = os.getenv("DEFAULT_EMBEDDING_MODEL", "text-embedding-3-small")
    
    # データベース設定
    DB_TYPE: str = os.getenv("DB_TYPE", "sqlite")
    DB_PATH: str = os.getenv("DB_PATH", "./data/audit_agent.db")
    
    # ログ設定
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "./logs/audit_agent.log")
    
    # エージェント設定
    AGENT_A_ID: str = os.getenv("AGENT_A_ID", "agent-a")
    AGENT_B_ID: str = os.getenv("AGENT_B_ID", "agent-b")
    AGENT_C_ID: str = os.getenv("AGENT_C_ID", "agent-c")
    AGENT_D_ID: str = os.getenv("AGENT_D_ID", "agent-d")
    
    # ファイル保存設定
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "./data"))
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
    REPORT_DIR: Path = Path(os.getenv("REPORT_DIR", "./data/reports"))
    TEMP_DIR: Path = Path(os.getenv("TEMP_DIR", "./data/temp"))
    
    # セキュリティ設定
    SECRET_KEY: str = os.getenv("SECRET_KEY", "generate-a-secure-random-key-here")
    
    # ネットワーク設定
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30").split('#')[0].strip())
    
    # Pydantic 2.x対応: Configクラスの代わりにmodel_configを使用
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


# グローバル設定インスタンス
settings = Settings()


def setup_directories():
    """必要なディレクトリを作成"""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.REPORT_DIR, exist_ok=True)
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    log_dir = os.path.dirname(settings.LOG_FILE)
    os.makedirs(log_dir, exist_ok=True)
    logger.info("アプリケーションディレクトリを作成しました")


def setup_logging():
    """ロギングの設定"""
    # デフォルトのロガーを削除
    logger.remove()
    
    # コンソールへのログ出力設定
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
    
    # ファイルへのログ出力設定
    log_dir = os.path.dirname(settings.LOG_FILE)
    os.makedirs(log_dir, exist_ok=True)
    
    logger.add(
        settings.LOG_FILE,
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="1 week",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )
    
    logger.info(f"ログレベル {settings.LOG_LEVEL} でロギングを初期化しました")


def initialize_app():
    """アプリケーションの初期化"""
    setup_directories()
    setup_logging()
    logger.info(f"アプリケーションを初期化しました: {settings.APP_NAME} v{settings.APP_VERSION}")
