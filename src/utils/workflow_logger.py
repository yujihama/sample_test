#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ワークフローロギングユーティリティ

このモジュールはワークフロー処理のための詳細なロギング機能を提供します。
ワークフローの状態変化、処理ステップ、エラー情報などを詳細に記録します。
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union
from loguru import logger

# ログレベルの定義
LOG_LEVELS = {
    "debug": "DEBUG",
    "info": "INFO",
    "warning": "WARNING", 
    "error": "ERROR",
    "critical": "CRITICAL"
}

# ワークフローログ用のディレクトリ
WORKFLOW_LOG_DIR = Path(__file__).absolute().parent.parent.parent / "logs" / "workflow"
WORKFLOW_LOG_DIR.mkdir(parents=True, exist_ok=True)

# グローバルワークフローロガーのインスタンス
_workflow_logger = None

def get_workflow_logger(
    level: str = "info",
    console: bool = True
) -> logger:
    """
    ワークフローロガーのシングルトンインスタンスを取得します。
    
    Args:
        level (str): ログレベル（"debug", "info", "warning", "error", "critical"）
        console (bool): コンソールにログを出力するかどうか
        
    Returns:
        loguru.logger: 設定されたワークフローロガー
    """
    global _workflow_logger
    
    if _workflow_logger is None:
        # ログレベルを設定
        log_level = LOG_LEVELS.get(level.lower(), "INFO")
        
        # logger のインスタンスを生成
        _workflow_logger = logger.bind(name="workflow")
        
        # 既存のハンドラをクリア
        logger.remove()
        
        # コンソールハンドラを追加
        if console:
            logger.add(
                sys.stderr,
                level=log_level,
                format="{time} | {level} | workflow:{function}:{line} - {message}"
            )
        
        # ファイルハンドラを追加（常に有効）
        log_file = WORKFLOW_LOG_DIR / "workflow.log"
        
        logger.add(
            log_file,
            level=log_level,
            format="{time} | {level} | workflow:{function}:{line} - {message}",
            rotation="10 MB",
            compression="zip"
        )
    
    return _workflow_logger

def log_workflow_event(
    workflow_id: str,
    event_type: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    level: str = "info"
) -> None:
    """
    ワークフローイベントをログに記録します。
    
    Args:
        workflow_id (str): ワークフローID
        event_type (str): イベントタイプ（start, progress, complete, error など）
        status (str): ワークフローの現在のステータス
        details (Optional[Dict[str, Any]]): イベントの詳細情報
        error (Optional[str]): エラーメッセージ（該当する場合）
        level (str): ログレベル
    """
    wf_logger = get_workflow_logger()
    
    # イベント情報を構築
    event_data = {
        "workflow_id": workflow_id,
        "event_type": event_type,
        "status": status,
        "timestamp": datetime.now().isoformat(),
    }
    
    if details:
        event_data["details"] = details
    
    if error:
        event_data["error"] = error
        level = "error"  # エラーがある場合はエラーレベルに設定
    
    # JSON形式でイベントデータをシリアライズ
    event_json = json.dumps(event_data, ensure_ascii=False, default=str)
    
    # ロガーでイベントを記録
    log_method = getattr(wf_logger, level.lower())
    log_method(f"WORKFLOW_EVENT: {event_json}")
    
    # ワークフロー個別のログファイルにも記録
    _log_to_workflow_file(workflow_id, event_data, level)

def log_workflow_state(
    workflow_id: str,
    state: Dict[str, Any],
    level: str = "debug"
) -> None:
    """
    ワークフローの状態を詳細にログに記録します。
    
    Args:
        workflow_id (str): ワークフローID
        state (Dict[str, Any]): ワークフロー状態データ
        level (str): ログレベル
    """
    wf_logger = get_workflow_logger()
    
    # 状態データをJSON形式でシリアライズ（機密情報をフィルタリング）
    filtered_state = _filter_sensitive_data(state)
    state_json = json.dumps(filtered_state, ensure_ascii=False, default=str, indent=2)
    
    # ロガーで状態を記録
    log_method = getattr(wf_logger, level.lower())
    log_method(f"WORKFLOW_STATE [{workflow_id}]: {state_json}")
    
    # ワークフロー個別のログファイルにも記録
    _log_to_workflow_file(
        workflow_id, 
        {"event_type": "state_update", "state": filtered_state},
        level
    )

def log_workflow_transition(
    workflow_id: str,
    from_status: str,
    to_status: str,
    agent_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    level: str = "info"
) -> None:
    """
    ワークフローのステータス遷移をログに記録します。
    
    Args:
        workflow_id (str): ワークフローID
        from_status (str): 遷移前のステータス
        to_status (str): 遷移後のステータス
        agent_id (Optional[str]): 関連するエージェントID
        details (Optional[Dict[str, Any]]): 遷移の詳細情報
        level (str): ログレベル
    """
    wf_logger = get_workflow_logger()
    
    # 遷移情報を構築
    transition_data = {
        "workflow_id": workflow_id,
        "event_type": "status_transition",
        "from_status": from_status,
        "to_status": to_status,
        "timestamp": datetime.now().isoformat(),
    }
    
    if agent_id:
        transition_data["agent_id"] = agent_id
    
    if details:
        transition_data["details"] = details
    
    # JSON形式で遷移データをシリアライズ
    transition_json = json.dumps(transition_data, ensure_ascii=False, default=str)
    
    # ロガーで遷移を記録
    log_method = getattr(wf_logger, level.lower())
    log_method(f"WORKFLOW_TRANSITION: {transition_json}")
    
    # ワークフロー個別のログファイルにも記録
    _log_to_workflow_file(workflow_id, transition_data, level)

def log_workflow_error(
    workflow_id: str,
    error_message: str,
    exception: Optional[Exception] = None,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    ワークフローのエラーをログに記録します。
    
    Args:
        workflow_id (str): ワークフローID
        error_message (str): エラーメッセージ
        exception (Optional[Exception]): 例外オブジェクト
        context (Optional[Dict[str, Any]]): エラーのコンテキスト情報
    """
    wf_logger = get_workflow_logger()
    
    # エラー情報を構築
    error_data = {
        "workflow_id": workflow_id,
        "event_type": "error",
        "error_message": error_message,
        "timestamp": datetime.now().isoformat(),
    }
    
    if exception:
        error_data["exception_type"] = type(exception).__name__
        error_data["exception_args"] = str(exception.args)
    
    if context:
        error_data["context"] = context
    
    # JSON形式でエラーデータをシリアライズ
    error_json = json.dumps(error_data, ensure_ascii=False, default=str)
    
    # ロガーでエラーを記録
    wf_logger.error(f"WORKFLOW_ERROR: {error_json}")
    
    # ワークフロー個別のログファイルにも記録
    _log_to_workflow_file(workflow_id, error_data, "error")

def _log_to_workflow_file(
    workflow_id: str,
    data: Dict[str, Any],
    level: str = "info"
) -> None:
    """
    ワークフロー固有のログファイルにイベントを記録します。
    
    Args:
        workflow_id (str): ワークフローID
        data (Dict[str, Any]): ログに記録するデータ
        level (str): ログレベル
    """
    try:
        # ワークフロー専用のログディレクトリ
        workflow_dir = WORKFLOW_LOG_DIR / workflow_id
        workflow_dir.mkdir(exist_ok=True)
        
        # ワークフロー個別のログファイル
        log_file = workflow_dir / f"{workflow_id}.log"
        
        # タイムスタンプを追加
        if "timestamp" not in data:
            data["timestamp"] = datetime.now().isoformat()
        
        # レベルを追加
        data["log_level"] = level.upper()
        
        # JSONとしてシリアライズ
        log_entry = json.dumps(data, ensure_ascii=False, default=str)
        
        # ファイルに追記
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{log_entry}\n")
    
    except Exception as e:
        # ファイルへの書き込みに失敗した場合でもアプリケーションを停止させない
        logger.error(f"ワークフローログファイルへの書き込みエラー: {e}")

def _filter_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    機密情報をフィルタリングします。
    
    Args:
        data (Dict[str, Any]): フィルタリングするデータ
        
    Returns:
        Dict[str, Any]: フィルタリングされたデータ
    """
    if not isinstance(data, dict):
        return data
    
    filtered_data = {}
    
    # 機密情報のキーのリスト
    sensitive_keys = [
        "password", "token", "api_key", "secret", "credential", 
        "auth", "private", "apikey", "api-key"
    ]
    
    for key, value in data.items():
        # 機密情報のキーかどうかをチェック
        is_sensitive = any(sk in key.lower() for sk in sensitive_keys)
        
        if is_sensitive:
            # 機密情報はマスク
            filtered_data[key] = "********"
        elif isinstance(value, dict):
            # 再帰的に辞書をフィルタリング
            filtered_data[key] = _filter_sensitive_data(value)
        elif isinstance(value, list):
            # リストの各アイテムをフィルタリング
            filtered_data[key] = [
                _filter_sensitive_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            # その他の値はそのまま
            filtered_data[key] = value
    
    return filtered_data 