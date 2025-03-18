#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ワークフロー状態の永続化・管理機能

このモジュールはワークフロー状態を保存、読み込み、圧縮、展開するための関数を提供します。
ワークフロー状態は監査AIエージェントのワークフローの進捗状況を管理するために使用されます。
"""

import os
import json
from src.utils import json_utils
import gzip
import base64
import shutil
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトのルートディレクトリを取得
# プロジェクトルート/src/utils/ から2階層上がルート
ROOT_DIR = Path(__file__).absolute().parent.parent.parent

# ワークフロー状態ファイルを保存するディレクトリ
WORKFLOW_STATES_DIR = ROOT_DIR / "data" / "workflow_states"

# ディレクトリが存在しない場合は作成
WORKFLOW_STATES_DIR.mkdir(parents=True, exist_ok=True)

# ロガーの設定
logger = logging.getLogger(__name__)


def save_workflow_state(workflow_state: Dict[str, Any]) -> str:
    """
    ワークフロー状態をJSONファイルとして保存します。
    大きなデータを含む場合は自動的に圧縮します。
    
    Args:
        workflow_state (Dict[str, Any]): 保存するワークフロー状態の辞書
        
    Returns:
        str: 保存したファイルのパス
    """
    if not workflow_state:
        raise ValueError("ワークフロー状態が空です")
    
    workflow_id = workflow_state.get("workflow_id")
    if not workflow_id:
        raise ValueError("ワークフロー状態にworkflow_idが含まれていません")
    
    # 更新日時を設定
    workflow_state["updated_at"] = datetime.now().isoformat()
    
    # ファイルパスを生成
    file_path = WORKFLOW_STATES_DIR / f"{workflow_id}.json"
    
    try:
        # 状態のサイズを確認
        state_json = json_utils.json_serialize(workflow_state)
        
        # 大きなデータの場合は圧縮
        if len(state_json) > 1024 * 100:  # 100KB以上
            compressed_state = compress_workflow_state(workflow_state)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(compressed_state)
            logger.info(f"ワークフロー状態を圧縮して保存しました: {file_path} (圧縮後サイズ: {len(compressed_state)} バイト)")
        else:
            # 通常の保存
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(workflow_state, f, ensure_ascii=False, indent=2)
            logger.info(f"ワークフロー状態を保存しました: {file_path} (サイズ: {len(state_json)} バイト)")
        
        return str(file_path)
    except Exception as e:
        logger.error(f"ワークフロー状態の保存中にエラーが発生: {e}")
        raise


def load_workflow_state(workflow_id: str) -> Dict[str, Any]:
    """
    ワークフロー状態をJSONファイルから読み込みます。
    圧縮されている場合は自動的に展開します。
    
    Args:
        workflow_id (str): 読み込むワークフローのID
        
    Returns:
        Dict[str, Any]: 読み込んだワークフロー状態の辞書
    """
    if not workflow_id:
        raise ValueError("workflow_idが指定されていません")
    
    # ファイルパスを生成
    file_path = WORKFLOW_STATES_DIR / f"{workflow_id}.json"
    
    if not file_path.exists():
        logger.warning(f"ワークフロー状態ファイルが見つかりません: {file_path}")
        return {}
    
    try:
        # ファイルを読み込む
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 圧縮されているかどうかを確認
        if content.startswith("{"):
            # 通常のJSONの場合
            workflow_state = json_utils.json_deserialize(content)
            logger.info(f"ワークフロー状態を読み込みました: {file_path}")
        else:
            # 圧縮されているJSONの場合
            workflow_state = decompress_workflow_state(content)
            logger.info(f"圧縮されたワークフロー状態を展開して読み込みました: {file_path}")
        
        return workflow_state
    except Exception as e:
        logger.error(f"ワークフロー状態の読み込み中にエラーが発生: {e}")
        raise


def compress_workflow_state(workflow_state: Dict[str, Any]) -> str:
    """
    ワークフロー状態を圧縮します。
    
    Args:
        workflow_state (Dict[str, Any]): 圧縮するワークフロー状態の辞書
        
    Returns:
        str: 圧縮されたワークフロー状態の文字列
    """
    try:
        # 圧縮フラグを追加
        workflow_state["_compressed"] = True
        
        # JSONに変換
        json_data = json_utils.json_serialize(workflow_state)
        
        # GZIP圧縮
        compressed_data = gzip.compress(json_data.encode("utf-8"))
        
        # Base64エンコード
        encoded_data = base64.b64encode(compressed_data).decode("ascii")
        
        return encoded_data
    except Exception as e:
        logger.error(f"ワークフロー状態の圧縮中にエラーが発生: {e}")
        raise


def decompress_workflow_state(compressed_state: str) -> Dict[str, Any]:
    """
    圧縮されたワークフロー状態を展開します。
    
    Args:
        compressed_state (str): 圧縮されたワークフロー状態の文字列
        
    Returns:
        Dict[str, Any]: 展開されたワークフロー状態の辞書
    """
    try:
        # Base64デコード
        decoded_data = base64.b64decode(compressed_state)
        
        # GZIP展開
        decompressed_data = gzip.decompress(decoded_data)
        
        # JSONに変換
        workflow_state = json_utils.json_deserialize(decompressed_data.decode("utf-8"))
        
        # 圧縮フラグを削除
        workflow_state.pop("_compressed", None)
        
        return workflow_state
    except Exception as e:
        logger.error(f"ワークフロー状態の展開中にエラーが発生: {e}")
        raise


def cleanup_old_states(max_age_days: int = 30, max_files: int = 100) -> int:
    """
    古いワークフロー状態ファイルをクリーンアップします。
    
    Args:
        max_age_days (int): 残すファイルの最大日数（これより古いファイルは削除）
        max_files (int): 残すファイルの最大数（これより多い場合は古い順に削除）
        
    Returns:
        int: 削除したファイルの数
    """
    try:
        # ファイル一覧を取得
        files = list(WORKFLOW_STATES_DIR.glob("*.json"))
        
        if not files:
            logger.info("クリーンアップ対象のワークフロー状態ファイルはありません")
            return 0
        
        # 現在の日時
        now = datetime.now()
        
        # 最大日数より古いファイルを削除
        deleted_count = 0
        if max_age_days > 0:
            max_age = now - timedelta(days=max_age_days)
            for file_path in files[:]:
                if datetime.fromtimestamp(file_path.stat().st_mtime) < max_age:
                    file_path.unlink()
                    files.remove(file_path)
                    deleted_count += 1
        
        # 最大ファイル数を超えるファイルを削除
        if len(files) > max_files:
            # 更新日時でソート
            files.sort(key=lambda f: f.stat().st_mtime)
            
            # 古いファイルから削除
            for file_path in files[:(len(files) - max_files)]:
                file_path.unlink()
                deleted_count += 1
        
        logger.info(f"{deleted_count}件の古いワークフロー状態ファイルを削除しました")
        return deleted_count
    except Exception as e:
        logger.error(f"ワークフロー状態のクリーンアップ中にエラーが発生: {e}")
        return 0


def update_agent_states(workflow_state: Dict[str, Any], agent_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    ワークフロー状態内のエージェント状態を更新します。
    
    Args:
        workflow_state (Dict[str, Any]): 現在のワークフロー状態
        agent_id (str): 更新するエージェントのID
        update_data (Dict[str, Any]): 更新するデータ
        
    Returns:
        Dict[str, Any]: 更新されたワークフロー状態
    """
    if not workflow_state:
        raise ValueError("ワークフロー状態が空です")
    
    if "agents" not in workflow_state:
        workflow_state["agents"] = {}
    
    if agent_id not in workflow_state["agents"]:
        workflow_state["agents"][agent_id] = {
            "status": "not_started",
            "data": {},
            "history": []
        }
    
    # エージェントの状態を更新
    agent_state = workflow_state["agents"][agent_id]
    for key, value in update_data.items():
        if key == "data":
            # データフィールドはマージ
            agent_state["data"].update(value)
        elif key == "history":
            # 履歴は追加
            agent_state["history"].extend(value)
        else:
            # その他のフィールドは上書き
            agent_state[key] = value
    
    # 更新日時を設定
    workflow_state["updated_at"] = datetime.now().isoformat()
    
    return workflow_state 