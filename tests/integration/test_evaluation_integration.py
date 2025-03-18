"""
評価機能の統合テスト
"""

import pytest
import asyncio
from typing import List, Dict, Any
from datetime import datetime
import pytest_asyncio

from src.core.evaluation import (
    EvaluationCriteria,
    EvaluationResult,
    RuleBasedEvaluator,
    MLBasedEvaluator
)
from src.core.agent_base import AgentBase
from src.models.schema import MessageType, MessagePriority

# テスト用の評価基準
TEST_CRITERIA = [
    EvaluationCriteria(
        id="test_rule_1",
        name="テスト基準1",
        description="テスト用の評価基準1",
        category="テスト",
        threshold=0.7
    ),
    EvaluationCriteria(
        id="test_rule_2",
        name="テスト基準2",
        description="テスト用の評価基準2",
        category="テスト",
        threshold=0.7
    )
]

# テスト用のルール
def test_rule_1(context: Dict[str, Any]) -> float:
    return float(context["test_value"]) / 100

def test_rule_2(context: Dict[str, Any]) -> float:
    return 0.5 if len(context["test_text"]) > 0 else 0.0

TEST_RULES = {
    "test_rule_1": test_rule_1,
    "test_rule_2": test_rule_2
}

# テスト用の機械学習モデル
class DummyMLModel:
    def predict(self, features: Dict[str, Any]) -> List[float]:
        """ダミーの予測を行う"""
        return [0.8, 0.6]  # テスト用の固定値

@pytest_asyncio.fixture
async def context() -> Dict[str, Any]:
    return {
        "test_value": 80,
        "test_text": "これはテストテキストです"
    }

@pytest.fixture
def rule_based_evaluator() -> RuleBasedEvaluator:
    """ルールベース評価器のフィクスチャ"""
    return RuleBasedEvaluator(TEST_CRITERIA, TEST_RULES)

@pytest.fixture
def ml_based_evaluator() -> MLBasedEvaluator:
    """機械学習ベース評価器のフィクスチャ"""
    return MLBasedEvaluator(TEST_CRITERIA)

@pytest.mark.asyncio
async def test_rule_1(context: Dict[str, Any], rule_based_evaluator: RuleBasedEvaluator) -> None:
    result = await rule_based_evaluator.evaluate_rule(context, "test_rule_1")
    assert result == 0.8

@pytest.mark.asyncio
async def test_rule_2(context: Dict[str, Any], rule_based_evaluator: RuleBasedEvaluator) -> None:
    result = await rule_based_evaluator.evaluate_rule(context, "test_rule_2")
    assert result == 0.5

@pytest.mark.asyncio
async def test_rule_based_evaluation(rule_based_evaluator: RuleBasedEvaluator):
    """ルールベース評価のテスト"""
    # テストコンテキスト
    context = {
        "test_value": 80,  # 期待スコア: 0.8
        "test_text": "これはテストテキストです"  # 期待スコア: 0.5
    }

    # 評価実行
    results = await rule_based_evaluator.evaluate(context)

    # 結果の検証
    assert len(results) == 2
    assert results[0].criteria_id == "test_rule_1"
    assert results[0].score == pytest.approx(0.8)
    assert results[0].status == "passed"
    assert results[1].criteria_id == "test_rule_2"
    assert results[1].score == pytest.approx(0.5)
    assert results[1].status == "failed"

@pytest.mark.asyncio
async def test_ml_based_evaluation(ml_based_evaluator: MLBasedEvaluator):
    """機械学習ベース評価のテスト"""
    # テストコンテキスト
    context = {
        "feature1": 1.0,
        "feature2": 2.0
    }

    # 評価実行
    results = await ml_based_evaluator.evaluate(context)

    # 結果の検証
    assert len(results) == 2
    for result in results:
        assert result.score == pytest.approx(0.85)
        assert result.status == "passed"

@pytest.mark.asyncio
async def test_evaluation_error_handling(rule_based_evaluator: RuleBasedEvaluator):
    """エラーハンドリングのテスト"""
    # 不正なコンテキスト
    context = {
        "test_value": "invalid",  # 数値を期待する箇所に文字列
        "test_text": None  # テキストを期待する箇所にNone
    }

    # 評価実行
    results = await rule_based_evaluator.evaluate(context)

    # エラー結果の検証
    assert len(results) == 2
    for result in results:
        assert result.score == 0.0
        assert result.status == "error"

@pytest.mark.asyncio
async def test_evaluation_integration_with_agent(rule_based_evaluator: RuleBasedEvaluator):
    """エージェントとの統合テスト"""
    # テストコンテキスト
    context = {
        "test_value": 90,  # 期待スコア: 0.9
        "test_text": "統合テスト用のテキスト"  # 期待スコア: 0.5
    }

    # 評価実行
    results = await rule_based_evaluator.evaluate(context)

    # 結果の検証
    assert len(results) == 2
    assert results[0].score == pytest.approx(0.9)
    assert results[0].status == "passed"
    assert results[1].score == pytest.approx(0.5)
    assert results[1].status == "failed" 