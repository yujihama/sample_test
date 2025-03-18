"""
汎用的な評価機能を提供するモジュール
"""

from typing import Dict, Any, List, Optional, Union, Callable
from abc import ABC, abstractmethod
from datetime import datetime
import logging
from pydantic import BaseModel, Field
import asyncio

logger = logging.getLogger(__name__)

class EvaluationCriteria:
    """Evaluation criteria definition."""
    def __init__(self, id: str, name: str, description: str, category: str, threshold: float = 0.7):
        self.id = id
        self.name = name
        self.description = description
        self.category = category
        self.threshold = threshold

class EvaluationResult:
    """Result of an evaluation."""
    def __init__(self, criteria_id: str, score: float, status: str = "passed"):
        self.criteria_id = criteria_id
        self.score = score
        self.status = status

class EvaluatorBase(ABC):
    """評価機能の基底クラス"""
    
    def __init__(self, criteria: List[EvaluationCriteria]):
        self.criteria = criteria
        
    @abstractmethod
    async def evaluate(self, context: Dict[str, Any]) -> List[EvaluationResult]:
        """
        評価を実行
        
        Args:
            context: 評価コンテキスト
            
        Returns:
            評価結果のリスト
        """
        pass
        
    def calculate_overall_score(self, results: List[EvaluationResult]) -> float:
        """
        総合評価スコアを計算
        
        Args:
            results: 評価結果のリスト
            
        Returns:
            総合評価スコア
        """
        if not results:
            return 0.0
            
        total_weight = sum(
            next(c.weight for c in self.criteria if c.id == r.criteria_id)
            for r in results
        )
        
        weighted_sum = sum(
            r.score * next(c.weight for c in self.criteria if c.id == r.criteria_id)
            for r in results
        )
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
        
    def get_evaluation_summary(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        評価結果のサマリーを生成
        
        Args:
            results: 評価結果のリスト
            
        Returns:
            評価サマリー
        """
        overall_score = self.calculate_overall_score(results)
        
        # カテゴリごとの結果を集計
        category_results = {}
        for result in results:
            criteria = next(c for c in self.criteria if c.id == result.criteria_id)
            if criteria.category not in category_results:
                category_results[criteria.category] = []
            category_results[criteria.category].append(result)
            
        # カテゴリごとのスコアを計算
        category_scores = {
            category: self.calculate_overall_score(results)
            for category, results in category_results.items()
        }
        
        # 合格/不合格の判定
        failed_criteria = [
            result for result in results
            if result.score < next(c.threshold for c in self.criteria if c.id == result.criteria_id)
        ]
        
        return {
            "overall_score": overall_score,
            "status": "failed" if failed_criteria else "passed",
            "category_scores": category_scores,
            "failed_criteria": [
                {
                    "criteria_id": r.criteria_id,
                    "score": r.score,
                    "details": r.details
                }
                for r in failed_criteria
            ],
            "timestamp": datetime.now().isoformat()
        }

class RuleBasedEvaluator:
    """Rule-based evaluation implementation."""
    
    def __init__(self, criteria: List[EvaluationCriteria], rules: Dict[str, Callable[[Dict[str, Any]], float]]):
        self.criteria = criteria
        self.rules = rules
    
    async def evaluate_rule(self, context: Dict[str, Any], rule_id: str) -> float:
        """Evaluate a single rule."""
        if rule_id in self.rules:
            return self.rules[rule_id](context)
        raise ValueError(f"Unknown rule: {rule_id}")
        
    async def evaluate(self, context: Dict[str, Any]) -> List[EvaluationResult]:
        """Evaluate all rules."""
        results = []
        for criteria in self.criteria:
            try:
                score = await self.evaluate_rule(context, criteria.id)
                status = "passed" if score >= criteria.threshold else "failed"
                results.append(EvaluationResult(criteria.id, score, status))
            except Exception as e:
                results.append(EvaluationResult(criteria.id, 0.0, "error"))
        return results

class MLBasedEvaluator:
    """Machine learning based evaluation implementation."""
    
    def __init__(self, criteria: List[EvaluationCriteria], model: Optional[Any] = None):
        self.criteria = criteria
        self.model = model
    
    async def evaluate(self, context: Dict[str, Any]) -> List[EvaluationResult]:
        """Evaluate using ML model."""
        # Simulate ML evaluation
        await asyncio.sleep(0.1)
        results = []
        for criteria in self.criteria:
            # Simulate model prediction
            score = 0.85
            status = "passed" if score >= criteria.threshold else "failed"
            results.append(EvaluationResult(criteria.id, score, status))
        return results 