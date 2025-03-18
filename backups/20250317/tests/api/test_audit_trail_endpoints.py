"""
監査証跡エンドポイントのテスト

このモジュールでは、監査証跡とログ関連のAPIエンドポイントのテストを提供します。
"""

import pytest
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import app
from src.models.repositories import (
    AuditTrailRepository,
    GraphStateHistoryRepository,
    CheckpointRecordRepository
)
from src.models.db_models import AuditTrail, GraphStateHistory, CheckpointRecord


@pytest.fixture
def client():
    """テストクライアントを作成"""
    return TestClient(app)


@pytest.fixture
def mock_audit_trail_repo():
    """AuditTrailRepositoryのモック"""
    now = datetime.now()
    
    # モック用のAuditTrailインスタンス
    audit_trails = [
        MagicMock(
            id="audit-123",
            workflow_id="workflow-123",
            context_id="context-123",
            agent_id="agent-123",
            event_type="message_sent",
            event_data={"message": "テストメッセージ"},
            timestamp=now - timedelta(minutes=10),
            metadata={"importance": "high"}
        ),
        MagicMock(
            id="audit-456",
            workflow_id="workflow-123",
            context_id="context-123",
            agent_id="agent-456",
            event_type="message_received",
            event_data={"message": "テスト応答"},
            timestamp=now - timedelta(minutes=5),
            metadata=None
        )
    ]
    
    # リポジトリのモック
    mock_repo = MagicMock(spec=AuditTrailRepository)
    mock_repo.search.return_value = audit_trails
    return mock_repo


@pytest.fixture
def mock_graph_state_history_repo():
    """GraphStateHistoryRepositoryのモック"""
    now = datetime.now()
    
    # モック用のGraphStateHistoryインスタンス
    state_histories = [
        MagicMock(
            id="history-123",
            workflow_id="workflow-123",
            context_id="context-123",
            agent_id="agent-123",
            node_id="node-123",
            state_snapshot={"data": "テスト状態1"},
            state_diff={"added": ["field1"], "removed": []},
            event_type="state_changed",
            event_data={"trigger": "user_input"},
            timestamp=now - timedelta(minutes=10),
            checkpoint_id=None
        ),
        MagicMock(
            id="history-456",
            workflow_id="workflow-123",
            context_id="context-123",
            agent_id="agent-123",
            node_id="node-456",
            state_snapshot={"data": "テスト状態2"},
            state_diff={"added": [], "removed": ["field2"]},
            event_type="checkpoint_created",
            event_data={"reason": "user_requested"},
            timestamp=now - timedelta(minutes=5),
            checkpoint_id="checkpoint-123"
        )
    ]
    
    # リポジトリのモック
    mock_repo = MagicMock(spec=GraphStateHistoryRepository)
    mock_repo.search.return_value = state_histories
    return mock_repo


@pytest.fixture
def mock_checkpoint_record_repo():
    """CheckpointRecordRepositoryのモック"""
    now = datetime.now()
    
    # モック用のCheckpointRecordインスタンス
    checkpoint_records = [
        MagicMock(
            id="checkpoint-123",
            workflow_id="workflow-123",
            context_id="context-123",
            agent_id="agent-123",
            checkpoint_type="user_requested",
            node_id="node-456",
            state_reference="history-456",
            checkpoint_metadata={"note": "ユーザーによるチェックポイント"},
            created_at=now - timedelta(minutes=5),
            restored_at=None,
            restore_count=0
        ),
        MagicMock(
            id="checkpoint-456",
            workflow_id="workflow-123",
            context_id="context-123",
            agent_id="agent-123",
            checkpoint_type="auto_system",
            node_id="node-789",
            state_reference="history-789",
            checkpoint_metadata={"reason": "自動バックアップ"},
            created_at=now - timedelta(minutes=2),
            restored_at=now - timedelta(minutes=1),
            restore_count=1
        )
    ]
    
    # リポジトリのモック
    mock_repo = MagicMock(spec=CheckpointRecordRepository)
    mock_repo.search.return_value = checkpoint_records
    return mock_repo


@patch("src.api.audit_trail_endpoints.get_db_session")
def test_get_audit_trails(mock_get_db_session, client, mock_audit_trail_repo):
    """監査証跡のリスト取得APIのテスト"""
    # モックの設定
    mock_session = MagicMock()
    mock_get_db_session.return_value = mock_session
    mock_session.__enter__.return_value = mock_session
    
    # AuditTrailRepositoryのインスタンス作成をモック
    with patch("src.api.audit_trail_endpoints.AuditTrailRepository", return_value=mock_audit_trail_repo):
        # APIリクエスト実行
        response = client.get("/audit/trails?workflow_id=workflow-123")
        
        # レスポンスの検証
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "audit-123"
        assert data[0]["event_type"] == "message_sent"
        assert data[1]["id"] == "audit-456"
        assert data[1]["event_type"] == "message_received"
        
        # リポジトリのsearchメソッドが正しいパラメータで呼ばれたことを確認
        mock_audit_trail_repo.search.assert_called_once()
        args, kwargs = mock_audit_trail_repo.search.call_args
        assert kwargs["workflow_id"] == "workflow-123"


@patch("src.api.audit_trail_endpoints.get_db_session")
def test_get_graph_state_history(mock_get_db_session, client, mock_graph_state_history_repo):
    """グラフ状態履歴の取得APIのテスト"""
    # モックの設定
    mock_session = MagicMock()
    mock_get_db_session.return_value = mock_session
    mock_session.__enter__.return_value = mock_session
    
    # GraphStateHistoryRepositoryのインスタンス作成をモック
    with patch("src.api.audit_trail_endpoints.GraphStateHistoryRepository", return_value=mock_graph_state_history_repo):
        # APIリクエスト実行
        response = client.get("/audit/state-history?workflow_id=workflow-123&agent_id=agent-123")
        
        # レスポンスの検証
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "history-123"
        assert data[0]["event_type"] == "state_changed"
        assert data[1]["id"] == "history-456"
        assert data[1]["event_type"] == "checkpoint_created"
        
        # リポジトリのsearchメソッドが正しいパラメータで呼ばれたことを確認
        mock_graph_state_history_repo.search.assert_called_once()
        args, kwargs = mock_graph_state_history_repo.search.call_args
        assert kwargs["workflow_id"] == "workflow-123"
        assert kwargs["agent_id"] == "agent-123"


@patch("src.api.audit_trail_endpoints.get_db_session")
def test_get_checkpoint_records(mock_get_db_session, client, mock_checkpoint_record_repo):
    """チェックポイント記録の取得APIのテスト"""
    # モックの設定
    mock_session = MagicMock()
    mock_get_db_session.return_value = mock_session
    mock_session.__enter__.return_value = mock_session
    
    # CheckpointRecordRepositoryのインスタンス作成をモック
    with patch("src.api.audit_trail_endpoints.CheckpointRecordRepository", return_value=mock_checkpoint_record_repo):
        # APIリクエスト実行
        response = client.get("/audit/checkpoints?workflow_id=workflow-123")
        
        # レスポンスの検証
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "checkpoint-123"
        assert data[0]["checkpoint_type"] == "user_requested"
        assert data[1]["id"] == "checkpoint-456"
        assert data[1]["checkpoint_type"] == "auto_system"
        
        # リポジトリのsearchメソッドが正しいパラメータで呼ばれたことを確認
        mock_checkpoint_record_repo.search.assert_called_once()
        args, kwargs = mock_checkpoint_record_repo.search.call_args
        assert kwargs["workflow_id"] == "workflow-123"


@patch("src.api.audit_trail_endpoints.get_db_session")
@patch("src.api.audit_trail_endpoints.get_graph_executor")
def test_visualize_state_transitions(
    mock_get_graph_executor, 
    mock_get_db_session, 
    client, 
    mock_graph_state_history_repo, 
    mock_checkpoint_record_repo
):
    """状態遷移の可視化データ取得APIのテスト"""
    # モックの設定
    mock_session = MagicMock()
    mock_get_db_session.return_value = mock_session
    mock_session.__enter__.return_value = mock_session
    
    mock_executor = MagicMock()
    mock_get_graph_executor.return_value = mock_executor
    
    # リポジトリのインスタンス作成をモック
    with patch("src.api.audit_trail_endpoints.GraphStateHistoryRepository", return_value=mock_graph_state_history_repo), \
         patch("src.api.audit_trail_endpoints.CheckpointRecordRepository", return_value=mock_checkpoint_record_repo):
        # APIリクエスト実行
        response = client.get("/audit/visualize/state-transitions?workflow_id=workflow-123")
        
        # レスポンスの検証
        assert response.status_code == 200
        data = response.json()
        
        # 基本構造の確認
        assert "nodes" in data
        assert "edges" in data
        assert "metadata" in data
        
        # ノードの検証
        assert len(data["nodes"]) >= 2  # 状態履歴とチェックポイントからのノード
        
        # メタデータの検証
        assert data["metadata"]["workflow_id"] == "workflow-123"
        assert data["metadata"]["node_count"] == len(data["nodes"])
        assert data["metadata"]["edge_count"] == len(data["edges"])
        
        # リポジトリのsearchメソッドが正しく呼ばれたことを確認
        mock_graph_state_history_repo.search.assert_called_once()
        mock_checkpoint_record_repo.search.assert_called_once() 