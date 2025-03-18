#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ロギングユーティリティ

このモジュールはアプリケーション全体で使用するロガーの設定機能を提供します。
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

# ログレベルの定義
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL
}

# デフォルトのログフォーマット
DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ログファイルのデフォルトディレクトリ
LOG_DIR = Path(__file__).absolute().parent.parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(
    name: str,
    level: str = "info",
    log_file: Optional[str] = None,
    console: bool = True,
    log_format: str = DEFAULT_LOG_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT
) -> logging.Logger:
    """
    ロガーをセットアップします。
    
    Args:
        name (str): ロガーの名前
        level (str): ログレベル（"debug", "info", "warning", "error", "critical"）
        log_file (Optional[str]): ログファイルのパス（省略可能）
        console (bool): コンソールにログを出力するかどうか
        log_format (str): ログのフォーマット
        date_format (str): 日付のフォーマット
        
    Returns:
        logging.Logger: 設定されたロガー
    """
    # ロガーを取得
    logger = logging.getLogger(name)
    
    # ログレベルを設定
    log_level = LOG_LEVELS.get(level.lower(), logging.INFO)
    logger.setLevel(log_level)
    
    # 既存のハンドラをクリア
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # フォーマッタを作成
    formatter = logging.Formatter(log_format, date_format)
    
    # コンソールハンドラを追加
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # ファイルハンドラを追加
    if log_file:
        # 相対パスの場合はログディレクトリからの相対パスとして扱う
        if not os.path.isabs(log_file):
            log_file = LOG_DIR / log_file
        
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger 