"""
ロギングユーティリティ（互換性のためのスタブ）

このモジュールは旧ロギングコードとの互換性のために存在しています。
src.utils.logger モジュールに実装が移行されました。
"""

from src.utils.logger import setup_logger as _setup_logger
from loguru import logger

def setup_logging():
    """
    アプリケーション全体のロギング設定をセットアップ
    logger モジュールとの互換性のために維持
    """
    # 基本的には何もせず、logger モジュールがすでに設定されていると想定
    return _setup_logger("app", log_file="app.log")

# 互換性のために自動実行
setup_logging() 