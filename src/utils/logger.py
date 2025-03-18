#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ロギングユーティリティ

このモジュールはアプリケーション全体で使用するロガーの設定機能を提供します。
loguru を使用して実装されており、src/utils/logging.py の機能と統合されています。
"""

import os
import sys
from pathlib import Path
from typing import Optional
from loguru import logger

# ログレベルの定義
LOG_LEVELS = {
    "debug": "DEBUG",
    "info": "INFO",
    "warning": "WARNING", 
    "error": "ERROR",
    "critical": "CRITICAL"
}

# ログファイルのデフォルトディレクトリ
LOG_DIR = Path(__file__).absolute().parent.parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def setup_logger(
    name: str,
    level: str = "info",
    log_file: Optional[str] = None,
    console: bool = True,
    log_format: Optional[str] = None,
    date_format: Optional[str] = None
) -> logger:
    """
    ロガーをセットアップします。
    
    Args:
        name (str): ロガーの名前
        level (str): ログレベル（"debug", "info", "warning", "error", "critical"）
        log_file (Optional[str]): ログファイルのパス（省略可能）
        console (bool): コンソールにログを出力するかどうか
        log_format (str): ログのフォーマット（未使用 - loguruのデフォルトフォーマットを使用）
        date_format (str): 日付のフォーマット（未使用 - loguruのデフォルトフォーマットを使用）
        
    Returns:
        loguru.logger: 設定されたロガー
    """
    # ログレベルを設定
    log_level = LOG_LEVELS.get(level.lower(), "INFO")
    
    # logger のインスタンスを生成
    logger_instance = logger.bind(name=name)
    
    # 既存のハンドラをクリア
    logger.remove()
    
    # コンソールハンドラを追加
    if console:
        logger.add(
            sys.stderr,
            level=log_level,
            format=f"{{time}} | {{level}} | {name}:{{function}}:{{line}} - {{message}}"
        )
    
    # ファイルハンドラを追加
    if log_file:
        # 相対パスの場合はログディレクトリからの相対パスとして扱う
        if not os.path.isabs(log_file):
            log_file = LOG_DIR / log_file
        
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logger.add(
            log_file,
            level=log_level,
            format=f"{{time}} | {{level}} | {name}:{{function}}:{{line}} - {{message}}",
            rotation="10 MB",
            compression="zip"
        )
    
    return logger_instance

def get_logger(
    name: str,
    level: str = "info",
    log_file: Optional[str] = None,
    console: bool = True
) -> logger:
    """
    設定済みのロガーインスタンスを取得します。

    Args:
        name (str): ロガーの名前
        level (str): ログレベル（"debug", "info", "warning", "error", "critical"）
        log_file (Optional[str]): ログファイルのパス（省略可能）
        console (bool): コンソールにログを出力するかどうか

    Returns:
        loguru.logger: 設定されたロガー
    """
    return setup_logger(
        name=name,
        level=level,
        log_file=log_file,
        console=console
    ) 