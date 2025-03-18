import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from unittest.mock import patch, MagicMock

from src.api.main import app
from src.models.schema import WorkflowStatus
from src.api.dependencies import get_current_user

# テスト用のユーザー情報
TEST_USER = {
    "user_id": "test_user",
    "username": "test_user@example.com",
    "roles": ["auditor"]
}

# get_current_userをモック
def mock_get_current_user():
    return TEST_USER

app.dependency_overrides[get_current_user] = mock_get_current_user

client = TestClient(app)

@pytest.fixture
def mock_db():
    return MagicMock()

def test_create_workflow(mock_db):
    test_workflow = {
        "procedure_id": "test_proc_1",
        "procedure_text": "テスト用監査手続き",
        "sample_id": "sample_1",
        "sample_data": {"key": "value"},
        "config": {"timeout": 300}
    }
    
    with patch("src.api.routers.workflow_management.get_db", return_value=mock_db):
        response = client.post("/api/v1/workflows", json=test_workflow)
    
    assert response.status_code == 200
    data = response.json()
    assert "workflow_id" in data
    assert data["status"] == "created"
    assert data["procedure_id"] == test_workflow["procedure_id"]
    assert data["sample_id"] == test_workflow["sample_id"]

def test_list_workflows(mock_db):
    mock_workflows = [
        {
            "id": "workflow_1",
            "status": "running",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "procedure_id": "proc_1",
            "sample_id": "sample_1"
        },
        {
            "id": "workflow_2",
            "status": "completed",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "procedure_id": "proc_2",
            "sample_id": "sample_2"
        }
    ]
    
    mock_db.query.return_value.filter.return_value.limit.return_value.offset.return_value = mock_workflows
    
    with patch("src.api.routers.workflow_management.get_db", return_value=mock_db):
        response = client.get("/api/v1/workflows")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["workflow_id"] == "workflow_1"
    assert data[1]["workflow_id"] == "workflow_2"

def test_get_workflow(mock_db):
    mock_workflow = {
        "workflow_id": "test_workflow",
        "status": "running",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "procedure_id": "test_proc",
        "sample_id": "test_sample"
    }
    
    with patch("src.api.routers.workflow_management.get_workflow_status", return_value=mock_workflow):
        response = client.get(f"/api/v1/workflows/{mock_workflow['workflow_id']}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"] == mock_workflow["workflow_id"]
    assert data["status"] == mock_workflow["status"]
    assert data["procedure_id"] == mock_workflow["procedure_id"]

def test_start_workflow(mock_db):
    workflow_id = "test_workflow"
    mock_workflow = {
        "workflow_id": workflow_id,
        "status": "created",
        "procedure_text": "テスト用監査手続き"
    }
    
    with patch("src.api.routers.workflow_management.get_workflow_status", return_value=mock_workflow):
        response = client.post(f"/api/v1/workflows/{workflow_id}/actions/start")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert data["workflow_id"] == workflow_id

def test_pause_workflow(mock_db):
    workflow_id = "test_workflow"
    mock_workflow = {
        "workflow_id": workflow_id,
        "status": "running"
    }
    
    with patch("src.api.routers.workflow_management.get_workflow_status", return_value=mock_workflow):
        response = client.post(f"/api/v1/workflows/{workflow_id}/actions/pause")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "paused"
    assert data["workflow_id"] == workflow_id

def test_resume_workflow(mock_db):
    workflow_id = "test_workflow"
    mock_workflow = {
        "workflow_id": workflow_id,
        "status": "paused"
    }
    
    with patch("src.api.routers.workflow_management.get_workflow_status", return_value=mock_workflow):
        response = client.post(f"/api/v1/workflows/{workflow_id}/actions/resume")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["workflow_id"] == workflow_id

def test_delete_workflow(mock_db):
    workflow_id = "test_workflow"
    mock_workflow = {
        "workflow_id": workflow_id,
        "status": "completed"
    }
    
    with patch("src.api.routers.workflow_management.get_workflow_status", return_value=mock_workflow):
        response = client.delete(f"/api/v1/workflows/{workflow_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deleted"
    assert data["workflow_id"] == workflow_id

def test_workflow_not_found(mock_db):
    workflow_id = "nonexistent_workflow"
    
    with patch("src.api.routers.workflow_management.get_workflow_status", return_value=None):
        response = client.get(f"/api/v1/workflows/{workflow_id}")
    
    assert response.status_code == 404
    assert "見つかりません" in response.json()["detail"]

def test_invalid_workflow_state_transition(mock_db):
    workflow_id = "test_workflow"
    mock_workflow = {
        "workflow_id": workflow_id,
        "status": "completed"
    }
    
    with patch("src.api.routers.workflow_management.get_workflow_status", return_value=mock_workflow):
        response = client.post(f"/api/v1/workflows/{workflow_id}/actions/start")
    
    assert response.status_code == 400
    assert "既に開始されているか、完了しています" in response.json()["detail"] 