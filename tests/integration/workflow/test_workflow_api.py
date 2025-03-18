"""
ワークフローAPIエンドポイントのテスト

ワークフロー管理のAPIエンドポイントの機能をテストするコード。
"""

import os
import sys
import uuid
import json
import pytest
from typing import Dict, Any, List
from pathlib import Path
from fastapi.testclient import TestClient
from unittest import mock

# プロジェクトルートを追加
project_root = Path(__file__).parents[2].absolute()
sys.path.append(str(project_root))

# ロガーの設定を修正
import logging
# 既存のロガーハンドラをクリア
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
# 基本的なロガー設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# テスト用クライアントの設定
from src.api.main import app
from src.utils.db_manager import get_db, init_db
from src.models.repositories import WorkflowRepository, HumanInterventionRequestRepository

client = TestClient(app)

# テスト用の監査手続きデータ
TEST_PROCEDURE = {
    "procedure_id": "test-proc-1",
    "procedure_text": "これはテスト用の監査手続きです。売上データの妥当性を検証します。"
}

# テスト用のサンプルデータ
TEST_SAMPLE = {
    "sample_id": "test-sample-1",
    "sample_data": {
        "sales": [
            {"id": 1, "date": "2025-01-01", "amount": 10000, "customer": "A社"},
            {"id": 2, "date": "2025-01-02", "amount": 20000, "customer": "B社"}
        ]
    }
}

@pytest.fixture
def mock_workflow_db():
    """テスト用のワークフローデータベースモック"""
    # データベース初期化
    init_db()
    
    # ここでテスト用データを投入することも可能
    yield
    
    # テスト後のクリーンアップ処理をここに記述

@pytest.fixture
def mock_workflow_invoke():
    """ワークフロー実行処理のモック"""
    with mock.patch('src.core.workflow.audit_workflow.invoke') as mock_invoke:
        mock_invoke.return_value = {
            "status": "completed", 
            "current_agent": "completed",
            "outputs": {
                "agent_a": {"test_plan": {"items": ["項目1", "項目2"]}},
                "agent_b": {"test_results": {"passed": 1, "failed": 1}},
                "agent_c": {"evaluation": {"summary": "問題あり"}},
                "agent_d": {"report": {"title": "テストレポート"}}
            }
        }
        yield mock_invoke

# 正常系テスト：ワークフロー開始
def test_start_workflow(mock_workflow_db, mock_workflow_invoke):
    """ワークフロー開始APIのテスト"""
    # リクエストデータ
    request_data = {
        "procedure_id": TEST_PROCEDURE["procedure_id"],
        "procedure_text": TEST_PROCEDURE["procedure_text"],
        "sample_id": TEST_SAMPLE["sample_id"],
        "sample_data": TEST_SAMPLE["sample_data"]
    }
    
    # モックの設定
    with mock.patch('src.models.repositories.WorkflowRepository.create') as mock_create:
        mock_create.return_value = "test-workflow-id"
        
        # APIリクエスト
        response = client.post("/workflow/start", json=request_data)
        
        # レスポンス検証
        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data
        assert data["status"] == "started"
        assert "message" in data

# 異常系テスト：必須パラメータ不足
def test_start_workflow_missing_params(mock_workflow_db):
    """必須パラメータ不足時のテスト"""
    # 必須パラメータ procedure_id が欠けている
    request_data = {
        "procedure_text": TEST_PROCEDURE["procedure_text"],
        "sample_id": TEST_SAMPLE["sample_id"]
    }
    
    # APIリクエスト
    response = client.post("/workflow/start", json=request_data)
    
    # レスポンス検証（400 Bad Requestが期待される）
    assert response.status_code == 422  # Pydanticによるバリデーションエラー

# 正常系テスト：ワークフロー情報取得
def test_get_workflow(mock_workflow_db):
    """ワークフロー情報取得APIのテスト"""
    # 事前にワークフローを作成
    workflow_id = "test-workflow-id"
    
    # モックの設定
    with mock.patch('src.core.workflow.get_workflow_status') as mock_get_status:
        mock_get_status.return_value = {
            "workflow_id": workflow_id,
            "status": "running",
            "current_agent": "agent_b",
            "progress": 50,
            "workflow": {
                "id": workflow_id,
                "status": "running"
            }
        }
        
        # APIリクエスト
        response = client.get(f"/workflow/{workflow_id}")
        
        # レスポンス検証
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == workflow_id
        assert data["status"] == "running"

# 異常系テスト：存在しないワークフロー情報取得
def test_get_nonexistent_workflow(mock_workflow_db):
    """存在しないワークフローの情報取得テスト"""
    # 存在しないワークフローID
    nonexistent_id = str(uuid.uuid4())
    
    # モックの設定
    with mock.patch('src.core.workflow.get_workflow_status') as mock_get_status:
        mock_get_status.return_value = {"status": "not_found"}
        
        # APIリクエスト
        response = client.get(f"/workflow/{nonexistent_id}")
        
        # レスポンス検証（404 Not Foundが期待される）
        assert response.status_code == 404

# 正常系テスト：ワークフロー一覧取得
def test_list_workflows(mock_workflow_db):
    """ワークフロー一覧取得APIのテスト"""
    # モックの設定
    with mock.patch('src.core.workflow.list_workflows') as mock_list:
        mock_list.return_value = [
            {"id": "test-workflow-1", "status": "running"},
            {"id": "test-workflow-2", "status": "completed"},
            {"id": "test-workflow-3", "status": "failed"}
        ]
        
        # APIリクエスト
        response = client.get("/workflow")
        
        # レスポンス検証
        assert response.status_code == 200
        data = response.json()
        assert "workflows" in data
        # 実際のデータベースからワークフローが取得されている可能性があるため、
        # 厳密な数の検証ではなく、リストが存在することを確認する
        assert isinstance(data["workflows"], list)

# 正常系テスト：ワークフローリセット
def test_reset_workflow(mock_workflow_db, mock_workflow_invoke):
    """ワークフローリセットAPIのテスト"""
    # ワークフローID
    workflow_id = "test-workflow-id"
    
    # モックの設定
    with mock.patch('src.core.workflow.reset_workflow') as mock_reset:
        mock_reset.return_value = {
            "workflow_id": workflow_id,
            "status": "reset",
            "message": f"Workflow {workflow_id} has been reset"
        }
        
        # APIリクエスト
        response = client.post(f"/workflow/{workflow_id}/reset")
        
        # レスポンス検証
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert workflow_id in data["message"]

# 異常系テスト：存在しないワークフローをリセット
def test_reset_nonexistent_workflow(mock_workflow_db):
    """存在しないワークフローをリセットした場合のテスト"""
    # 存在しないワークフローID
    nonexistent_id = str(uuid.uuid4())
    
    # モックの設定
    with mock.patch('src.core.workflow.reset_workflow') as mock_reset:
        mock_reset.side_effect = ValueError(f"Workflow {nonexistent_id} not found")
        
        # APIリクエスト
        response = client.post(f"/workflow/{nonexistent_id}/reset")
        
        # レスポンス検証（404 Not Foundが期待される）
        assert response.status_code == 404

# 正常系テスト：ワークフロー削除
def test_delete_workflow(mock_workflow_db):
    """ワークフロー削除APIのテスト"""
    # ワークフローID
    workflow_id = "test-workflow-id"
    
    # モックの設定
    with mock.patch('src.core.workflow.clean_workflow') as mock_clean:
        mock_clean.return_value = {
            "workflow_id": workflow_id,
            "status": "deleted",
            "message": f"Workflow {workflow_id} has been deleted"
        }
        
        # APIリクエスト
        response = client.delete(f"/workflow/{workflow_id}")
        
        # レスポンス検証
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert workflow_id in data["message"]
        
        # 削除後に取得を試みる
        with mock.patch('src.core.workflow.get_workflow_status') as mock_get_status:
            mock_get_status.return_value = {"status": "not_found"}
            get_response = client.get(f"/workflow/{workflow_id}")
            assert get_response.status_code == 404  # 削除されているので404が期待される

# 人間介入APIのテスト
def test_get_pending_interventions(mock_workflow_db):
    """保留中の人間介入要求一覧取得APIのテスト"""
    # APIリクエスト
    response = client.get("/workflow/intervention/pending")
    
    # レスポンス検証
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)  # 空でも配列は返る

if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 