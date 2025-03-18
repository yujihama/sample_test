"""
エージェント間の連携テスト
"""

import pytest
import pytest_asyncio
import asyncio
import logging
import json
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from enum import Enum
from pathlib import Path

from src.core.agent import AgentBase
from src.core.messaging import MessageClient
from src.core.context_manager import ContextClient
from src.models.schema import MessageType, MessagePriority
from src.core.evaluation import (
    EvaluationCriteria,
    RuleBasedEvaluator
)
from tests.integration.test_agents import TestAgentA, TestAgentB, AgentLogger, AgentRole

@pytest_asyncio.fixture
async def setup_agents() -> Tuple[TestAgentA, TestAgentB]:
    agent_a = TestAgentA()
    agent_b = TestAgentB()
    await agent_a.initialize()
    await agent_b.initialize()
    yield agent_a, agent_b
    await agent_a.cleanup()
    await agent_b.cleanup()

@pytest.mark.asyncio
async def test_task_assignment_flow(setup_agents: Tuple[TestAgentA, TestAgentB]):
    """タスク割り当てフローのテスト"""
    agent_a, agent_b = setup_agents
    
    # タスクリクエスト
    task_request = {
        "type": "task_request",
        "content": {
            "task_id": "task_001",
            "difficulty": 5,
            "description": "テストタスク"
        }
    }
    
    # エージェントAがタスクを評価
    response_a = await agent_a.process_message(task_request)
    assert response_a["response"] == "task_accepted"
    
    # エージェントBにタスクを割り当て
    task_assignment = {
        "type": "task_assignment",
        "content": {
            "task": {
                "task_id": "task_001",
                "difficulty": 5,
                "description": "テストタスク"
            }
        }
    }
    
    # エージェントBがタスクを受け入れ
    response_b = await agent_b.process_message(task_assignment)
    assert response_b["response"] == "task_accepted"

@pytest.mark.asyncio
async def test_human_query_flow(setup_agents: Tuple[TestAgentA, TestAgentB]):
    """人間への問い合わせフローのテスト"""
    agent_a, agent_b = setup_agents
    
    # 人間への問い合わせが必要なタスク
    task_request = {
        "type": "task_request",
        "content": {
            "task_id": "task_002",
            "difficulty": 8,  # 難易度高め
            "requires_approval": True,
            "description": "承認が必要なタスク"
        }
    }
    
    # エージェントAが処理
    response = await agent_a.process_message(task_request)
    assert response["response"] == "human_query_created"
    
    # 人間からの応答
    human_response = {
        "type": "human_response",
        "content": {
            "task_id": "task_002",
            "approved": True
        }
    }
    
    # エージェントAが応答を処理
    final_response = await agent_a.process_message(human_response)
    assert final_response["response"] == "task_approved"

@pytest.mark.asyncio
async def test_error_handling_flow(setup_agents: Tuple[TestAgentA, TestAgentB]):
    """エラーハンドリングフローのテスト"""
    agent_a, agent_b = setup_agents
    
    # エラーが発生する可能性のあるタスク
    task_assignment = {
        "type": "task_assignment",
        "content": {
            "task": {
                "task_id": "error_task",
                "error_trigger": True,
                "description": "エラーを発生させるタスク"
            }
        }
    }
    
    # エラー発生時のハンドリングをテスト
    response = await agent_b.process_message(task_assignment)
    assert response["response"] == "error_handled"
    assert "error_details" in response

@pytest.mark.asyncio
async def test_status_monitoring_flow(setup_agents: Tuple[TestAgentA, TestAgentB]):
    """ステータス監視フローのテスト"""
    agent_a, agent_b = setup_agents
    
    # ステータス確認メッセージ
    status_check = {
        "type": "status_check",
        "content": {
            "request_id": "status_001"
        }
    }
    
    # エージェントBのステータスを取得
    response = await agent_b.process_message(status_check)
    assert response["response"] == "status_report"
    assert "status" in response
    assert "assigned_tasks" in response

@pytest.mark.asyncio
async def test_priority_task_handling(setup_agents: Tuple[TestAgentA, TestAgentB]):
    """優先タスク処理のテスト"""
    agent_a, agent_b = setup_agents
    
    # 通常タスク
    regular_task = {
        "type": "task_request",
        "content": {
            "task_id": "task_003",
            "priority": "normal",
            "description": "通常の優先度のタスク"
        }
    }
    
    # 優先タスク
    priority_task = {
        "type": "task_request",
        "content": {
            "task_id": "task_004",
            "priority": "high",
            "description": "高優先度のタスク"
        }
    }
    
    # 両方のタスクを処理
    await agent_a.process_message(regular_task)
    response = await agent_a.process_message(priority_task)
    
    # 優先タスクが先に処理されるか確認
    assert response["response"] == "task_accepted"
    assert response["priority_handled"] == True

@pytest.mark.asyncio
async def test_conditional_task_routing(setup_agents: Tuple[TestAgentA, TestAgentB]):
    """条件付きタスクルーティングのテスト"""
    agent_a, agent_b = setup_agents
    
    # カテゴリに基づくルーティングテスト
    task = {
        "type": "task_request",
        "content": {
            "task_id": "task_005",
            "category": "analysis",
            "description": "分析カテゴリのタスク"
        }
    }
    
    # エージェントAがタスクをルーティング
    response = await agent_a.process_message(task)
    assert response["response"] == "task_routed"
    assert response["route_to"] == "agent_b"
    
    # ルーティングされたタスクの処理
    routed_task = {
        "type": "routed_task",
        "content": {
            "task_id": "task_005",
            "category": "analysis",
            "description": "分析カテゴリのタスク",
            "source_agent": "agent_a"
        }
    }
    
    response = await agent_b.process_message(routed_task)
    assert response["response"] == "routed_task_accepted"

@pytest.mark.asyncio
async def test_task_delegation_chain(setup_agents: Tuple[TestAgentA, TestAgentB]):
    """タスク委任チェーンのテスト"""
    agent_a, agent_b = setup_agents
    
    # 初期タスク
    initial_task = {
        "type": "complex_task",
        "content": {
            "task_id": "task_006",
            "requires_delegation": True,
            "description": "複数のエージェントで処理するタスク"
        }
    }
    
    # エージェントAが委任処理を開始
    response = await agent_a.process_message(initial_task)
    assert response["response"] == "task_delegated"
    
    # 委任されたサブタスク
    delegated_task = {
        "type": "delegated_subtask",
        "content": {
            "parent_task_id": "task_006",
            "subtask_id": "subtask_001",
            "description": "サブタスク処理"
        }
    }
    
    # エージェントBがサブタスクを処理
    subtask_response = await agent_b.process_message(delegated_task)
    assert subtask_response["response"] == "subtask_completed"
    
    # 結果報告
    completion_report = {
        "type": "subtask_completion",
        "content": {
            "parent_task_id": "task_006",
            "subtask_id": "subtask_001",
            "result": "処理完了"
        }
    }
    
    # エージェントAが最終結果を統合
    final_response = await agent_a.process_message(completion_report)
    assert final_response["response"] == "task_integration_complete"

@pytest.mark.asyncio
async def test_adaptive_error_handling(setup_agents: Tuple[TestAgentA, TestAgentB]):
    """適応的エラーハンドリングのテスト"""
    agent_a, agent_b = setup_agents
    
    # エラーを引き起こすタスク
    task = {
        "type": "error_prone_task",
        "content": {
            "task_id": "task_007",
            "error_probability": 0.8,
            "description": "エラーが発生しやすいタスク"
        }
    }
    
    # エージェントBがタスクを処理
    response = await agent_b.process_message(task)
    assert response["response"] == "error_detected"
    
    # エラー修正の試み
    error_correction = {
        "type": "error_correction",
        "content": {
            "task_id": "task_007",
            "correction_strategy": "retry_with_params",
            "params": {"timeout": 30, "retries": 3}
        }
    }
    
    # エージェントBが修正を適用
    correction_response = await agent_b.process_message(error_correction)
    assert correction_response["response"] == "correction_applied"
    
    # 再実行の結果
    rerun_task = {
        "type": "rerun_task",
        "content": {
            "task_id": "task_007",
            "description": "修正後の再実行"
        }
    }
    
    final_response = await agent_b.process_message(rerun_task)
    assert final_response["response"] == "task_completed_after_correction"

@pytest.mark.asyncio
async def test_collaborative_decision_making(setup_agents: Tuple[TestAgentA, TestAgentB]):
    """協調的意思決定のテスト"""
    agent_a, agent_b = setup_agents
    
    # 複雑な意思決定が必要なタスク
    complex_task = {
        "type": "decision_task",
        "content": {
            "task_id": "task_008",
            "requires_collaboration": True,
            "description": "複数のエージェントでの意思決定が必要なタスク"
        }
    }
    
    # エージェントAが初期評価
    response_a = await agent_a.process_message(complex_task)
    assert response_a["response"] == "collaboration_initiated"
    
    # エージェントBに分析リクエスト
    analysis_request = {
        "type": "analysis_request",
        "content": {
            "task_id": "task_008",
            "analysis_type": "risk_assessment",
            "data": {"risk_factors": ["factor1", "factor2"]}
        }
    }
    
    # エージェントBが分析を実行
    analysis_response = await agent_b.process_message(analysis_request)
    assert analysis_response["response"] == "analysis_complete"
    
    # 分析結果をエージェントAに送信
    analysis_result = {
        "type": "analysis_result",
        "content": {
            "task_id": "task_008",
            "result": {
                "risk_level": "medium",
                "recommendations": ["action1", "action2"]
            }
        }
    }
    
    # エージェントAが最終決定
    final_decision = await agent_a.process_message(analysis_result)
    assert final_decision["response"] == "decision_made"
    assert "decision" in final_decision
    assert "justification" in final_decision 