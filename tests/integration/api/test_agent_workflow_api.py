import pytest
from fastapi.testclient import TestClient
from src.main import app
import asyncio

client = TestClient(app)

# テスト用の認証トークン
TEST_TOKEN = "test_token"

# リクエストヘッダーに認証トークンを追加
def get_auth_headers():
    """認証ヘッダーを取得します。"""
    return {"Authorization": f"Bearer {TEST_TOKEN}"}

@pytest.mark.integration
@pytest.mark.api
@pytest.mark.workflow
def test_complete_task_workflow():
    """タスクワークフロー全体のAPIテスト"""
    # 1. タスクの送信
    task_data = {
        "task_id": "integration_001",
        "difficulty": 5,
        "description": "統合テストタスク"
    }
    response = client.post("/api/v1/tasks/submit", json=task_data, headers=get_auth_headers())
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    # 2. タスク状態の確認
    response = client.get(f"/api/v1/tasks/{task_id}/status", headers=get_auth_headers())
    assert response.status_code == 200
    assert response.json()["status"] == "assigned"

    # 3. エージェントAの処理結果確認
    response = client.get(f"/api/v1/agents/A/tasks/{task_id}", headers=get_auth_headers())
    assert response.status_code == 200
    assert response.json()["processing_status"] == "completed"

    # 4. エージェントBへの転送確認
    response = client.get(f"/api/v1/agents/B/tasks/{task_id}", headers=get_auth_headers())
    assert response.status_code == 200
    assert response.json()["status"] == "received"

@pytest.mark.integration
@pytest.mark.api
def test_error_handling_workflow():
    """エラー処理ワークフローのAPIテスト"""
    # 1. 無効なタスクデータの送信
    invalid_task = {
        "task_id": "integration_002",
        "difficulty": "invalid",  # 数値であるべき
        "description": "エラーテストタスク"
    }
    response = client.post("/api/v1/tasks/submit", json=invalid_task, headers=get_auth_headers())
    
    # FastAPIのバリデーションエラーは422を返す
    assert response.status_code == 422
    error_detail = response.json()["detail"][0]["msg"].lower()
    assert "valid integer" in error_detail

    # 2. エラーレポートの送信
    error_report = {
        "task_id": "integration_002",
        "error_type": "validation_error",
        "description": "不正なタスクデータ形式"
    }
    response = client.post("/api/v1/errors/report", json=error_report, headers=get_auth_headers())
    assert response.status_code == 200
    assert "error_id" in response.json()

    # 3. エラー状態の確認
    error_id = response.json()["error_id"]
    response = client.get(f"/api/v1/errors/{error_id}", headers=get_auth_headers())
    assert response.status_code == 200
    assert response.json()["status"] == "reported"

@pytest.mark.integration
@pytest.mark.api
def test_human_interaction_workflow():
    """人間との対話ワークフローのAPIテスト"""
    # 1. 高難度タスクの送信
    task_data = {
        "task_id": "integration_003",
        "difficulty": 8,
        "description": "人間の承認が必要なタスク"
    }
    response = client.post("/api/v1/tasks/submit", json=task_data, headers=get_auth_headers())
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    # 2. 人間への問い合わせ生成確認
    response = client.get(f"/api/v1/tasks/{task_id}/status", headers=get_auth_headers())
    assert response.status_code == 200
    assert response.json()["requires_human_approval"] == True

    # 3. 承認リクエストの送信
    approval_data = {
        "task_id": task_id,
        "approved": True,
        "comment": "承認済み"
    }
    response = client.post(f"/api/v1/human/approve", json=approval_data, headers=get_auth_headers())
    assert response.status_code == 200
    assert response.json()["status"] == "approved" 