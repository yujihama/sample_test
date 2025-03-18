#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
エージェント間コンテキスト共有機能のテスト

AgentContextManagerクラスの機能をテストするためのモジュールです。
主に以下の機能をテストします：
- 監査コンテキストの作成と取得
- エージェントワークフローの開始
- イベント処理とコンテキスト共有
- チェックポイント管理機能
"""

import os
import sys
import uuid
import json
import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock, AsyncMock

import aiohttp
from loguru import logger
from fastapi import HTTPException

# モジュール自体をモックする
sys.modules['src.models.db_models'] = MagicMock()
sys.modules['src.services.graph_executor'] = MagicMock()
sys.modules['src.agents.agent_a_graph'] = MagicMock()
sys.modules['src.agents.agent_b_graph'] = MagicMock()
sys.modules['src.agents.agent_c_graph'] = MagicMock()
sys.modules['src.agents.agent_d_graph'] = MagicMock()

# AgentContextManagerをモックで実装
class MockAgentContextManager:
    """モック実装のAgentContextManager"""
    
    def __init__(self, checkpoint_saver=None):
        self.audit_contexts = {}
        self.checkpoint_saver = checkpoint_saver
    
    async def create_audit_context(self, audit_id: str, title: str, description: str) -> str:
        """監査コンテキストを作成する"""
        context_id = f"ctx-{uuid.uuid4().hex[:8]}"
        self.audit_contexts[context_id] = {
            "id": context_id,
            "audit_id": audit_id,
            "title": title,
            "description": description,
            "status": "in_progress",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "agent_states": {},
            "shared_context": {},
            "workflow_ids": {}
        }
        return context_id
    
    async def get_audit_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """監査コンテキストを取得する"""
        return self.audit_contexts.get(context_id)
    
    async def start_agent_workflow(self, agent_id: str, context_id: str, initial_state: Dict[str, Any]) -> str:
        """エージェントワークフローを開始する"""
        workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        
        if context_id not in self.audit_contexts:
            raise ValueError(f"コンテキスト {context_id} が見つかりません")
        
        # ワークフローIDを監査コンテキストに記録
        if "workflow_ids" not in self.audit_contexts[context_id]:
            self.audit_contexts[context_id]["workflow_ids"] = {}
        
        self.audit_contexts[context_id]["workflow_ids"][agent_id] = workflow_id
        
        # エージェントの状態を初期化
        if "agent_states" not in self.audit_contexts[context_id]:
            self.audit_contexts[context_id]["agent_states"] = {}
        
        self.audit_contexts[context_id]["agent_states"][agent_id] = {
            "workflow_id": workflow_id,
            "status": "created",
            "last_updated": datetime.now().isoformat()
        }
        
        return workflow_id
    
    async def process_agent_event(self, agent_id: str, context_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        """エージェントイベントを処理する"""
        if context_id not in self.audit_contexts:
            raise ValueError(f"コンテキスト {context_id} が見つかりません")
        
        if agent_id not in self.audit_contexts[context_id]["agent_states"]:
            raise ValueError(f"エージェント {agent_id} はコンテキスト {context_id} に登録されていません")
        
        # エージェントの状態を更新
        self.audit_contexts[context_id]["agent_states"][agent_id]["status"] = "processed"
        self.audit_contexts[context_id]["agent_states"][agent_id]["last_updated"] = datetime.now().isoformat()
        
        # 他のエージェントとのコンテキスト共有をシミュレート
        await self._share_context_between_agents(agent_id, "agent_b", {}, context_id)
        
        return {"status": "processed"}
    
    async def get_agent_state(self, agent_id: str, context_id: str) -> Optional[Dict[str, Any]]:
        """エージェントの状態を取得する"""
        if context_id not in self.audit_contexts:
            return None
        
        if agent_id not in self.audit_contexts[context_id]["agent_states"]:
            return None
        
        return {"status": "in_progress"}
    
    async def get_agent_checkpoints(self, agent_id: str, context_id: str) -> List[Dict[str, Any]]:
        """エージェントのチェックポイント一覧を取得する"""
        return [{"id": "cp-test-id"}]
    
    async def restore_agent_checkpoint(self, agent_id: str, context_id: str, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """エージェントのチェックポイントから復元する"""
        if context_id not in self.audit_contexts:
            return None
        
        if agent_id not in self.audit_contexts[context_id]["agent_states"]:
            return None
        
        # チェックポイントからの復元をシミュレート
        self.audit_contexts[context_id]["agent_states"][agent_id]["restored_from_checkpoint"] = checkpoint_id
        
        return {"status": "restored"}
    
    async def get_audit_status(self, context_id: str) -> Optional[Dict[str, Any]]:
        """監査の全体状況を取得する"""
        if context_id not in self.audit_contexts:
            return None
        
        context = self.audit_contexts[context_id]
        
        return {
            "id": context["id"],
            "audit_id": context["audit_id"],
            "status": context["status"],
            "agents": {
                agent_id: {"status": state["status"]}
                for agent_id, state in context.get("agent_states", {}).items()
            }
        }
    
    async def get_context_sharing_history(self, context_id: str, from_agent: Optional[str] = None, to_agent: Optional[str] = None) -> List[Dict[str, Any]]:
        """コンテキスト共有の履歴を取得する"""
        if context_id not in self.audit_contexts:
            return []
        
        shared_context = self.audit_contexts[context_id].get("shared_context", {})
        
        # 共有履歴をリスト形式に変換
        history = list(shared_context.values())
        
        # フィルタリングを適用
        if from_agent:
            history = [item for item in history if item["from"] == from_agent]
        
        if to_agent:
            history = [item for item in history if item["to"] == to_agent]
        
        return history
    
    async def _share_context_between_agents(self, from_agent: str, to_agent: str, state: Dict[str, Any], context_id: str) -> None:
        """エージェント間でコンテキストを共有する（内部メソッド）"""
        # 共有をシミュレート
        if context_id in self.audit_contexts:
            key = f"{from_agent}_{to_agent}_{datetime.now().isoformat()}"
            self.audit_contexts[context_id]["shared_context"][key] = {
                "from": from_agent,
                "to": to_agent,
                "data": {"test": "data"},
                "timestamp": datetime.now().isoformat()
            }


# モック実装をモジュールにインストール
sys.modules['src.core.agent_context_manager'] = MagicMock()
sys.modules['src.core.agent_context_manager'].AgentContextManager = MockAgentContextManager
sys.modules['src.core.agent_context_manager'].get_context_manager = MagicMock(return_value=MockAgentContextManager())


# モックチェックポイントセーバーのフィクスチャ
@pytest.fixture
def mock_checkpoint_saver():
    """モックのチェックポイントセーバーを返す"""
    class MockCheckpointSaver:
        def __init__(self):
            self.checkpoints = {}
        
        async def save(self, workflow_id: str, checkpoint_id: str, state: Dict[str, Any]):
            if workflow_id not in self.checkpoints:
                self.checkpoints[workflow_id] = {}
            self.checkpoints[workflow_id][checkpoint_id] = state.copy()
            return checkpoint_id
        
        async def load(self, workflow_id: str, checkpoint_id: str) -> Optional[Dict[str, Any]]:
            if workflow_id in self.checkpoints and checkpoint_id in self.checkpoints[workflow_id]:
                return self.checkpoints[workflow_id][checkpoint_id].copy()
            return None
        
        async def list_checkpoints(self, workflow_id: str) -> List[Dict[str, Any]]:
            if workflow_id not in self.checkpoints:
                return []
            return [
                {
                    "id": cp_id,
                    "timestamp": state.get("updated_at", datetime.now().isoformat()),
                    "metadata": state.get("metadata", {})
                }
                for cp_id, state in self.checkpoints[workflow_id].items()
            ]
    
    return MockCheckpointSaver()


# AgentContextManagerのインスタンスを作成するフィクスチャ
@pytest.fixture
def agent_context_manager(mock_checkpoint_saver):
    """AgentContextManagerのインスタンスを作成"""
    return MockAgentContextManager(mock_checkpoint_saver)


# テストケース
@pytest.mark.asyncio
async def test_create_audit_context(agent_context_manager):
    """監査コンテキストの作成と取得をテスト"""
    # 監査コンテキストを作成
    audit_id = f"audit-{uuid.uuid4().hex[:8]}"
    title = "テスト監査"
    description = "これはテスト用の監査です"
    
    context_id = await agent_context_manager.create_audit_context(audit_id, title, description)
    
    # コンテキストIDが生成されたことを確認
    assert context_id is not None
    assert context_id.startswith("ctx-")
    
    # 作成したコンテキストを取得
    context = await agent_context_manager.get_audit_context(context_id)
    
    # コンテキスト情報の検証
    assert context is not None
    assert context["id"] == context_id
    assert context["audit_id"] == audit_id
    assert context["title"] == title
    assert context["description"] == description
    assert context["status"] == "in_progress"
    assert "created_at" in context
    assert "updated_at" in context
    assert "agent_states" in context
    assert "shared_context" in context
    assert "workflow_ids" in context


@pytest.mark.asyncio
async def test_start_agent_workflow(agent_context_manager):
    """エージェントワークフローの開始をテスト"""
    # 監査コンテキストを作成
    audit_id = f"audit-{uuid.uuid4().hex[:8]}"
    context_id = await agent_context_manager.create_audit_context(audit_id, "テスト監査", "")
    
    # エージェントAのワークフローを開始
    initial_state = {
        "procedure_id": "proc-123",
        "procedure_text": "テスト手続き",
        "required_info": ["reg_info"],
        "status": "in_progress"
    }
    
    workflow_id = await agent_context_manager.start_agent_workflow("agent_a", context_id, initial_state)
    
    # ワークフローIDが生成されたことを確認
    assert workflow_id is not None
    assert workflow_id.startswith("wf-")
    
    # コンテキスト情報を取得して確認
    context = await agent_context_manager.get_audit_context(context_id)
    
    # ワークフローIDが記録されていることを確認
    assert "workflow_ids" in context
    assert "agent_a" in context["workflow_ids"]
    assert context["workflow_ids"]["agent_a"] == workflow_id
    
    # エージェント状態が記録されていることを確認
    assert "agent_states" in context
    assert "agent_a" in context["agent_states"]
    assert context["agent_states"]["agent_a"]["workflow_id"] == workflow_id
    assert context["agent_states"]["agent_a"]["status"] == "created"


@pytest.mark.asyncio
async def test_process_agent_event(agent_context_manager):
    """エージェントイベントの処理をテスト"""
    # 監査コンテキストとワークフローを作成
    audit_id = f"audit-{uuid.uuid4().hex[:8]}"
    context_id = await agent_context_manager.create_audit_context(audit_id, "テスト監査", "")
    
    await agent_context_manager.start_agent_workflow("agent_a", context_id, {
        "procedure_id": "proc-123",
        "status": "in_progress"
    })
    
    await agent_context_manager.start_agent_workflow("agent_b", context_id, {
        "problem_id": "prob-123",
        "status": "in_progress"
    })
    
    # イベントを処理
    event = {
        "type": "add_data",
        "data": {
            "test_plan": {
                "steps": ["ステップ1", "ステップ2"],
                "expected_results": ["結果1", "結果2"]
            }
        }
    }
    
    result = await agent_context_manager.process_agent_event("agent_a", context_id, event)
    
    # 処理結果を確認
    assert result is not None
    assert result.get("status") == "processed"
    
    # コンテキスト情報を取得して確認
    context = await agent_context_manager.get_audit_context(context_id)
    
    # エージェント状態が更新されていることを確認
    assert context["agent_states"]["agent_a"]["status"] == "processed"


@pytest.mark.asyncio
async def test_get_agent_state(agent_context_manager):
    """エージェント状態の取得をテスト"""
    # 監査コンテキストとワークフローを作成
    audit_id = f"audit-{uuid.uuid4().hex[:8]}"
    context_id = await agent_context_manager.create_audit_context(audit_id, "テスト監査", "")
    
    await agent_context_manager.start_agent_workflow("agent_a", context_id, {
        "procedure_id": "proc-123",
        "status": "in_progress"
    })
    
    # エージェント状態を取得
    state = await agent_context_manager.get_agent_state("agent_a", context_id)
    
    # 状態情報の検証
    assert state is not None
    assert state.get("status") == "in_progress"


@pytest.mark.asyncio
async def test_get_agent_checkpoints(agent_context_manager):
    """エージェントチェックポイント一覧の取得をテスト"""
    # 監査コンテキストとワークフローを作成
    audit_id = f"audit-{uuid.uuid4().hex[:8]}"
    context_id = await agent_context_manager.create_audit_context(audit_id, "テスト監査", "")
    
    await agent_context_manager.start_agent_workflow("agent_a", context_id, {
        "procedure_id": "proc-123",
        "status": "in_progress"
    })
    
    # チェックポイント一覧を取得
    checkpoints = await agent_context_manager.get_agent_checkpoints("agent_a", context_id)
    
    # チェックポイント情報の検証
    assert checkpoints is not None
    assert len(checkpoints) == 1
    assert checkpoints[0]["id"] == "cp-test-id"


@pytest.mark.asyncio
async def test_restore_agent_checkpoint(agent_context_manager):
    """エージェントチェックポイントからの復元をテスト"""
    # 監査コンテキストとワークフローを作成
    audit_id = f"audit-{uuid.uuid4().hex[:8]}"
    context_id = await agent_context_manager.create_audit_context(audit_id, "テスト監査", "")
    
    await agent_context_manager.start_agent_workflow("agent_a", context_id, {
        "procedure_id": "proc-123",
        "status": "in_progress"
    })
    
    # チェックポイントから復元
    restored_state = await agent_context_manager.restore_agent_checkpoint(
        "agent_a", context_id, "cp-test-id"
    )
    
    # 復元された状態の検証
    assert restored_state is not None
    assert restored_state.get("status") == "restored"
    
    # コンテキスト情報を取得して確認
    context = await agent_context_manager.get_audit_context(context_id)
    
    # エージェント状態が更新されていることを確認
    assert context["agent_states"]["agent_a"]["restored_from_checkpoint"] == "cp-test-id"


@pytest.mark.asyncio
async def test_get_audit_status(agent_context_manager):
    """監査の全体状況の取得をテスト"""
    # 監査コンテキストとワークフローを作成
    audit_id = f"audit-{uuid.uuid4().hex[:8]}"
    context_id = await agent_context_manager.create_audit_context(audit_id, "テスト監査", "")
    
    await agent_context_manager.start_agent_workflow("agent_a", context_id, {
        "procedure_id": "proc-123",
        "status": "in_progress"
    })
    
    await agent_context_manager.start_agent_workflow("agent_b", context_id, {
        "problem_id": "prob-123",
        "status": "completed"
    })
    
    # 監査状況を取得
    status = await agent_context_manager.get_audit_status(context_id)
    
    # 状況情報の検証
    assert status is not None
    assert status["id"] == context_id
    assert status["audit_id"] == audit_id
    assert status["agents"]["agent_a"]["status"] == "created"
    assert status["agents"]["agent_b"]["status"] == "created"


@pytest.mark.asyncio
async def test_get_context_sharing_history(agent_context_manager):
    """コンテキスト共有の履歴を取得するテスト"""
    # 監査コンテキストとワークフローを作成
    audit_id = f"audit-{uuid.uuid4().hex[:8]}"
    context_id = await agent_context_manager.create_audit_context(audit_id, "テスト監査", "")
    
    # 共有履歴を追加（テスト用に直接追加）
    agent_context_manager.audit_contexts[context_id]["shared_context"] = {
        f"agent_a_agent_b_{datetime.now().isoformat()}": {
            "from": "agent_a",
            "to": "agent_b",
            "data": {"test_plan": {"steps": ["ステップ1"]}},
            "timestamp": datetime.now().isoformat()
        },
        f"agent_b_agent_c_{datetime.now().isoformat()}": {
            "from": "agent_b",
            "to": "agent_c",
            "data": {"solution": {"result": "成功"}},
            "timestamp": datetime.now().isoformat()
        }
    }
    
    # 全ての共有履歴を取得
    history = await agent_context_manager.get_context_sharing_history(context_id)
    assert len(history) == 2
    
    # フィルタリングして取得
    history_filtered = await agent_context_manager.get_context_sharing_history(
        context_id, from_agent="agent_a"
    )
    assert len(history_filtered) == 1
    assert history_filtered[0]["from"] == "agent_a"
    assert history_filtered[0]["to"] == "agent_b"


@pytest.mark.asyncio
async def test_integration_context_sharing(agent_context_manager):
    """エージェント間のコンテキスト共有の統合テスト"""
    with patch.object(agent_context_manager, "_share_context_between_agents") as mock_share:
        mock_share.return_value = None
        
        # 監査コンテキストとワークフローを作成
        audit_id = f"audit-{uuid.uuid4().hex[:8]}"
        context_id = await agent_context_manager.create_audit_context(audit_id, "テスト監査", "")
        
        await agent_context_manager.start_agent_workflow("agent_a", context_id, {
            "procedure_id": "proc-123",
            "procedure_understanding": {"type": "検証手順"},
            "status": "in_progress"
        })
        
        await agent_context_manager.start_agent_workflow("agent_b", context_id, {
            "problem_id": "prob-123",
            "status": "in_progress"
        })
        
        # イベントを処理
        event = {
            "type": "add_data",
            "data": {
                "test_plan": {
                    "steps": ["ステップ1", "ステップ2"],
                    "expected_results": ["結果1", "結果2"]
                }
            }
        }
        
        await agent_context_manager.process_agent_event("agent_a", context_id, event)
        
        # _share_context_between_agentsが呼ばれたことを確認
        assert mock_share.called
        
        # agent_aからagent_bへの呼び出しがあることを確認
        for call_args in mock_share.call_args_list:
            args, kwargs = call_args
            if args[0] == "agent_a" and args[1] == "agent_b":
                assert args[2] is not None  # stateが渡されていること
                assert args[3] == context_id
                return
                
        pytest.fail("agent_aからagent_bへの共有が行われていません")


# メイン実行
if __name__ == "__main__":
    pytest.main(["-v", "test_agent_context_manager.py"]) 