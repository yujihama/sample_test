"""
ロギングユーティリティ
"""

import os
import sys
from pathlib import Path

from loguru import logger

from src.core.config import settings


def setup_logging():
    """
    アプリケーション全体のロギング設定をセットアップ
    """
    # 既存のロガーをクリア
    logger.remove()
    
    # コンソール出力の設定
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format=settings.LOG_FORMAT
    )
    
    # ファイル出力の設定
    log_file = Path(settings.LOGS_DIR) / "app.log"
    logger.add(
        log_file,
        level=settings.LOG_LEVEL,
        format=settings.LOG_FORMAT,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
        compression="zip"
    )
    
    # テスト用のログファイル（テスト時のみ）
    if settings.TESTING:
        test_log_file = Path(settings.LOGS_DIR) / "test.log"
        logger.add(
            test_log_file,
            level="DEBUG",
            format=settings.LOG_FORMAT,
            rotation=settings.LOG_ROTATION,
            retention=settings.LOG_RETENTION,
            compression="zip"
        )
    
    logger.info(f"ロギングを設定しました: レベル={settings.LOG_LEVEL}, ファイル={log_file}")


# アプリケーション起動時にロギングを自動設定
setup_logging() 