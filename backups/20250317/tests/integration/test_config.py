#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
統合テスト用の設定
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List


# プロジェクトルートディレクトリ
ROOT_DIR = Path(__file__).absolute().parent.parent.parent


# テスト用のデータベース設定
TEST_DB_CONFIG = {
    "dialect": "sqlite",
    "driver": None,
    "username": None,
    "password": None,
    "host": None,
    "port": None,
    "database": ":memory:",
    "query": None
}

# テスト用のデータベースタイプ（デフォルト: sqlite）
TEST_DB_TYPE = os.environ.get("INTEGRATION_TEST_DB_TYPE", "sqlite")

# テスト用のデータベースパス（SQLiteの場合）
TEST_DB_PATH = os.environ.get("INTEGRATION_TEST_DB_PATH", ":memory:")


# テスト用のワークフロー状態ディレクトリ
TEST_WORKFLOW_STATES_DIR = os.path.join(
    tempfile.gettempdir(), 
    "test_workflow_states"
)


def get_temp_db_config() -> Dict[str, Any]:
    """
    一時的なSQLiteデータベース設定を取得
    
    Returns:
        Dict[str, Any]: データベース設定
    """
    # 一時的なSQLiteファイルを作成
    temp_db_file = tempfile.NamedTemporaryFile(
        prefix="test_db_",
        suffix=".sqlite",
        delete=False
    )
    temp_db_file.close()
    
    # 設定を作成
    config = TEST_DB_CONFIG.copy()
    config["database"] = temp_db_file.name
    
    return config


def get_postgres_test_config() -> Dict[str, Any]:
    """
    PostgreSQLテスト用のデータベース設定を取得
    
    環境変数から設定を取得する:
        TEST_DB_HOST: ホスト名 (デフォルト: localhost)
        TEST_DB_PORT: ポート番号 (デフォルト: 5432)
        TEST_DB_USER: ユーザー名 (デフォルト: postgres)
        TEST_DB_PASSWORD: パスワード (デフォルト: postgres)
        TEST_DB_NAME: データベース名 (デフォルト: test_audit_db)
        
    Returns:
        Dict[str, Any]: データベース設定
    """
    return {
        "dialect": "postgresql",
        "driver": "psycopg2",
        "username": os.environ.get("TEST_DB_USER", "postgres"),
        "password": os.environ.get("TEST_DB_PASSWORD", "postgres"),
        "host": os.environ.get("TEST_DB_HOST", "localhost"),
        "port": int(os.environ.get("TEST_DB_PORT", "5432")),
        "database": os.environ.get("TEST_DB_NAME", "test_audit_db"),
        "query": None
    }


# テスト用サンプルデータのパス
TEST_SAMPLE_DATA_PATH = Path(__file__).parent / "data" / "sample_data.json"


# テスト用監査手続きデータ
TEST_AUDIT_PROCEDURES = [
    {
        "id": "proc-001",
        "name": "売掛金確認手続き",
        "description": "売掛金の残高確認手続きを実施します",
        "procedure_text": "顧客に対して売掛金の残高確認を行い、差異がある場合はその原因を調査する。",
        "status": "active",
        "created_at": "2025-03-16T12:00:00",
        "updated_at": "2025-03-16T12:00:00"
    },
    {
        "id": "proc-002",
        "name": "在庫実査手続き",
        "description": "在庫の実地棚卸手続きを実施します",
        "procedure_text": "実地棚卸を行い、帳簿残高との差異がある場合はその原因を調査する。",
        "status": "active",
        "created_at": "2025-03-16T12:00:00",
        "updated_at": "2025-03-16T12:00:00"
    }
]


# テスト用サンプルデータ
TEST_SAMPLE_DATA = []


# サンプルデータを読み込む
def _load_sample_data():
    """
    サンプルデータをJSONファイルから読み込む
    """
    global TEST_SAMPLE_DATA
    
    if TEST_SAMPLE_DATA:
        return
    
    try:
        if TEST_SAMPLE_DATA_PATH.exists():
            with open(TEST_SAMPLE_DATA_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'sample_data' in data:
                    TEST_SAMPLE_DATA = data['sample_data']
    except Exception as e:
        print(f"サンプルデータの読み込みエラー: {e}")
        TEST_SAMPLE_DATA = []


# 初期化時にサンプルデータを読み込む
_load_sample_data()


# テスト用のデータベース初期化SQLファイルのパス
TEST_DB_INIT_SQL_PATH = Path(__file__).parent / "data" / "db_init.sql"


# テスト実行時の最大リトライ回数
MAX_TEST_RETRIES = 3


# テスト実行のタイムアウト（秒）
TEST_TIMEOUT = 30

# テスト用のワークフロー状態ディレクトリ（絶対パス）
TEST_WORKFLOW_STATES_DIR = ROOT_DIR / "tests" / "data" / "workflow_states"
TEST_WORKFLOW_STATES_DIR.mkdir(parents=True, exist_ok=True)

# テスト用のログディレクトリ
TEST_LOGS_DIR = ROOT_DIR / "tests" / "logs"
TEST_LOGS_DIR.mkdir(parents=True, exist_ok=True)

# テスト用のエージェント設定
TEST_AGENT_CONFIG = {
    "agent_a": {
        "id": "agent_a",
        "name": "監査手続き理解・設計エージェント",
        "description": "監査手続きの理解と設計を行うエージェント",
        "model": "gpt-4",
    },
    "agent_b": {
        "id": "agent_b",
        "name": "監査テスト実行エージェント",
        "description": "監査テストの実行を行うエージェント",
        "model": "gpt-4",
    },
    "agent_c": {
        "id": "agent_c",
        "name": "監査評価エージェント",
        "description": "監査テスト結果の評価を行うエージェント",
        "model": "gpt-4",
    },
    "agent_d": {
        "id": "agent_d",
        "name": "監査レポート生成エージェント",
        "description": "最終監査レポートの生成を行うエージェント",
        "model": "gpt-4",
    }
} 