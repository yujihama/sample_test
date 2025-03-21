"""
エージェントC: 結果評価・総括
"""

import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import asyncio

from loguru import logger
from pydantic import BaseModel, Field

from src.core.agent_base import AgentBase, AgentState
from src.core.config import settings
from src.utils.llm_utils import (
    get_llm,
    create_test_result_evaluator_prompt
)
from src.core.messaging import MessageClient


class AgentCState(AgentState):
    """エージェントCの状態クラス"""
    # テスト結果関連
    test_results_id: Optional[str] = None
    test_results: Optional[Dict[str, Any]] = None
    test_plan: Optional[Dict[str, Any]] = None
    
    # 出力関連
    summary: Optional[Dict[str, Any]] = None
    
    # 監査手続き関連
    procedure_id: Optional[str] = None
    
    # その他
    is_processing: bool = False
    

class AgentC(AgentBase):
    """
    結果評価・総括を担当するエージェントC
    """
    
    def __init__(self, message_client: Optional[MessageClient] = None):
        """
        初期化
        
        Args:
            message_client: メッセージクライアント（オプション）
        """
        super().__init__(
            agent_id=settings.AGENT_C_ID,
            state_class=AgentCState,
            agent_name="結果評価・総括エージェント"
        )
        self.message_client = message_client
        
        # メッセージングプロパティの追加（テスト用）
        self.messaging = self.message_client
        
        logger.info("AgentC initialized")
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        受信したメッセージを処理
        
        Args:
            message: 受信したメッセージ
            
        Returns:
            処理結果
        """
        message_type = message.get("message_type")
        content = message.get("content", {})
        logger.info(f"Agent C processing message type: {message_type}")
        
        result = {"status": "unknown_message_type", "message_id": message.get("id")}
        
        if message_type == "test_results":
            # テスト結果メッセージの処理
            result = await self.handle_test_results(content)
        elif message_type == "evaluate_results":
            # 結果評価メッセージの処理
            result = await self.handle_evaluate_results(content)
        elif message_type == "question":
            # 質問メッセージの処理
            result = await self.handle_question(content)
        
        return result
    
    async def handle_test_results(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        テスト結果メッセージの処理
        
        Args:
            content: メッセージコンテンツ
            
        Returns:
            処理結果
        """
        results = content.get("results")
        test_plan = content.get("test_plan")
        
        if not results:
            return {"status": "error", "error": "Test results are required"}
        
        if not test_plan:
            return {"status": "error", "error": "Test plan is required"}
        
        # 状態を更新
        self.state.update(
            test_results_id=results.get("id"),
            test_results=results,
            test_plan=test_plan,
            procedure_id=test_plan.get("procedure_id"),
            status="received_test_results"
        )
        
        logger.info(f"Test results received with ID: {results.get('id')}")
        
        # 自動的に結果を評価
        return await self.handle_evaluate_results({})
    
    async def handle_evaluate_results(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        結果評価メッセージの処理
        
        Args:
            content: メッセージコンテンツ
            
        Returns:
            処理結果
        """
        if self.state.is_processing:
            return {"status": "busy", "error": "Agent is already processing a task"}
        
        if not self.state.test_results:
            return {
                "status": "error", 
                "error": "Test results are not available. Send test results first."
            }
        
        if not self.state.test_plan:
            return {
                "status": "error", 
                "error": "Test plan is not available."
            }
        
        self.state.update(is_processing=True, status="busy")
        
        try:
            # テスト結果を評価
            summary = await self.evaluate_test_results(
                self.state.test_plan,
                self.state.test_results
            )
            
            # 状態を更新
            self.state.update(
                summary=summary,
                is_processing=False,
                status="idle"
            )
            
            # エージェントDに監査総括を送信
            self.send_message(
                to_agent=settings.AGENT_D_ID,
                message_type="audit_summary",
                content={
                    "summary": summary,
                    "test_results": self.state.test_results,
                    "test_plan": self.state.test_plan
                }
            )
            
            logger.info(f"Test results evaluated with {len(summary.get('findings', []))} findings")
            return {
                "status": "success",
                "summary": summary
            }
        
        except Exception as e:
            logger.error(f"Error in handle_evaluate_results: {e}")
            self.state.update(is_processing=False, status="error")
            return {"status": "error", "error": str(e)}
    
    async def handle_question(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        質問メッセージの処理
        
        Args:
            content: メッセージコンテンツ
            
        Returns:
            処理結果
        """
        question = content.get("question")
        from_agent = content.get("from_agent")
        
        if not question:
            return {"status": "error", "error": "Question is required"}
        
        try:
            # ここで質問に回答するロジックを実装
            # LLMを使用して回答を生成するシンプルな例
            system_message = """
            あなたは内部監査の結果評価および総括を担当する専門家です。
            与えられた質問に、テスト結果とその評価に基づいて回答してください。
            回答は簡潔で明確、かつ専門的であるべきです。
            """
            
            human_template = """
            以下の情報と質問に基づいて回答してください。
            
            テスト計画: {test_plan}
            
            テスト結果: {test_results}
            
            監査総括: {summary}
            
            質問: {question}
            """
            
            from langchain_core.prompts import ChatPromptTemplate
            
            # テスト環境または実際のLLMが利用できない場合はモックの結果を返す
            if hasattr(settings, "ENV") and settings.ENV == "test":
                return {
                    "status": "success",
                    "answer": f"これはテスト環境での自動応答です。質問: {question}"
                }
            
            chat_prompt = ChatPromptTemplate.from_messages([
                ("system", system_message),
                ("human", human_template),
            ])
            
            # LLMで回答を生成
            llm = get_llm()
            chain = chat_prompt | llm
            response = await chain.ainvoke({
                "test_plan": str(self.state.test_plan or "情報なし"),
                "test_results": str(self.state.test_results or "情報なし"),
                "summary": str(self.state.summary or "まだ作成されていません"),
                "question": question
            })
            
            # 返信メッセージの送信（質問者がいる場合）
            if from_agent:
                self.send_message(
                    to_agent=from_agent,
                    message_type="answer",
                    content={"question": question, "answer": response.content}
                )
            
            return {
                "status": "success",
                "answer": response.content
            }
        
        except Exception as e:
            logger.error(f"Error in handle_question: {e}")
            return {"status": "error", "error": str(e)}
    
    async def evaluate_test_results(
        self, test_plan: Dict[str, Any], test_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        テスト結果を評価する
        
        Args:
            test_plan: テスト計画
            test_results: テスト結果
            
        Returns:
            監査総括
        """
        logger.info("Evaluating test results")
        
        try:
            # テスト結果評価のためのプロンプトを作成
            chain = create_test_result_evaluator_prompt(
                test_plan=test_plan,
                test_results=test_results
            )
            
            # LLMでの処理を実行
            evaluation = await chain.ainvoke({})
            
            # 監査総括の構造を作成
            summary = {
                "id": f"summary-{uuid.uuid4().hex[:8]}",
                "procedure_id": self.state.procedure_id or test_plan.get("procedure_id"),
                "execution_id": test_results.get("id"),
                "findings": evaluation.get("findings", []),
                "conclusion": evaluation.get("conclusion", ""),
                "risk_assessment": evaluation.get("risk_assessment", {}),
                "additional_tests_required": evaluation.get("additional_tests_required", False),
                "additional_test_areas": evaluation.get("additional_test_areas", []),
                "created_at": datetime.now().isoformat()
            }
            
            # 各発見事項にIDを付与
            for i, finding in enumerate(summary["findings"]):
                if "id" not in finding:
                    finding["id"] = f"find-{uuid.uuid4().hex[:8]}"
                if "created_at" not in finding:
                    finding["created_at"] = datetime.now().isoformat()
            
            logger.info(f"Test results evaluated with {len(summary['findings'])} findings")
            return summary
        
        except Exception as e:
            logger.error(f"Error evaluating test results: {e}")
            raise 

    async def analyze_evaluation(self, evaluation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        予算変更の評価結果を分析する

        Args:
            evaluation_result: 評価結果
                - status: 評価ステータス（"completed", "failed"）
                - result: 評価結果（"approved", "rejected", "needs_review"）
                - reason: 評価理由
                - risk_level: リスクレベル（"low", "medium", "high"）
                - recommendations: 推奨事項のリスト
                - analysis: 分析データ
                    - change_amount: 変更金額
                    - change_percentage: 変更率

        Returns:
            Dict[str, Any]: 分析結果
                - status: 分析ステータス（"completed", "failed"）
                - findings: 発見事項のリスト
                - risk_assessment: リスク評価結果
                - compliance_status: コンプライアンス状態
                - recommendations: 追加の推奨事項
        """
        try:
            if evaluation_result["status"] != "completed":
                return {
                    "status": "failed",
                    "error": "評価結果が完了していません"
                }
            
            # 発見事項の分析
            findings = []
            
            # 予算変更率に基づく分析
            change_percentage = evaluation_result["analysis"]["change_percentage"]
            if change_percentage > 50:
                findings.append("予算の大幅な増加（50%以上）が検出されました")
            elif change_percentage > 20:
                findings.append("予算の中程度の増加（20-50%）が検出されました")
            
            # リスクレベルに基づく分析
            risk_assessment = {
                "level": evaluation_result["risk_level"],
                "factors": []
            }
            
            if evaluation_result["risk_level"] == "high":
                risk_assessment["factors"].extend([
                    "大幅な予算増加",
                    "詳細なレビューが必要"
                ])
            elif evaluation_result["risk_level"] == "medium":
                risk_assessment["factors"].extend([
                    "予算執行状況のモニタリングが必要",
                    "コスト削減の検討が推奨"
                ])
            
            # コンプライアンス状態の評価
            compliance_status = {
                "status": "compliant",
                "details": []
            }
            
            if evaluation_result["result"] == "needs_review":
                compliance_status["status"] = "review_required"
                compliance_status["details"].append(
                    "予算変更規程に基づき、詳細なレビューが必要です"
                )
            
            # 追加の推奨事項
            recommendations = list(evaluation_result["recommendations"])
            if change_percentage > 30:
                recommendations.append("四半期ごとの予算執行状況レビューを実施")
            if evaluation_result["risk_level"] in ["medium", "high"]:
                recommendations.append("予算変更の影響分析レポートの作成を推奨")
            
            return {
                "status": "completed",
                "findings": findings,
                "risk_assessment": risk_assessment,
                "compliance_status": compliance_status,
                "recommendations": recommendations
            }
        except Exception as e:
            logger.error(f"評価結果の分析中にエラーが発生しました: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }

    async def evaluate_results(self, test_results: dict, test_plan: dict) -> dict:
        """
        テスト結果を評価する
        
        Args:
            test_results: 評価するテスト結果
            test_plan: 元のテスト計画
            
        Returns:
            評価結果の辞書
        """
        try:
            logger.info(f"[{self.workflow_id}] テスト結果の評価を開始します")
            
            # テスト結果と計画の検証
            if not test_results or "results" not in test_results:
                error_msg = "無効なテスト結果です"
                logger.error(f"[{self.workflow_id}] {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg,
                    "workflow_id": self.workflow_id
                }
            
            if not test_plan or "test_items" not in test_plan:
                error_msg = "無効なテスト計画です"
                logger.error(f"[{self.workflow_id}] {error_msg}")
                return {
                    "status": "error",
                    "error": error_msg,
                    "workflow_id": self.workflow_id
                }
            
            # テスト用のモック実装
            # 実際の実装ではテスト結果を詳細に分析し、コンプライアンスや基準との照合を行います
            results = test_results.get("results", [])
            
            # 発見事項の生成（モック）
            findings = []
            
            # パス/失敗の状態に基づいて発見事項を生成
            failed_tests = [r for r in results if r.get("status") != "passed"]
            
            if failed_tests:
                for test in failed_tests:
                    findings.append({
                        "id": f"finding-{uuid.uuid4().hex[:8]}",
                        "test_id": test.get("test_id", "unknown"),
                        "severity": "高",
                        "description": f"{test.get('test_name')} が失敗しました",
                        "impact": "コンプライアンス違反の可能性",
                        "recommendation": "詳細な調査が必要です"
                    })
            else:
                # すべて成功の場合の一般的な発見事項
                findings.append({
                    "id": f"finding-{uuid.uuid4().hex[:8]}",
                    "severity": "低",
                    "description": "すべてのテストは成功しましたが、一部の点で改善の余地があります",
                    "impact": "軽微な影響",
                    "recommendation": "プロセスの効率化を検討してください"
                })
            
            evaluation = {
                "workflow_id": self.workflow_id,
                "evaluation_id": str(uuid.uuid4()),
                "findings": findings,
                "compliance_status": "準拠" if not failed_tests else "一部非準拠",
                "risk_assessment": {
                    "overall_risk": "低" if not failed_tests else "中",
                    "risk_areas": [
                        {
                            "name": "経費処理の承認手続き",
                            "risk_level": "低" if not failed_tests else "中",
                            "controls_effectiveness": "有効" if not failed_tests else "一部有効"
                        }
                    ]
                },
                "summary": {
                    "total_findings": len(findings),
                    "high_severity": len([f for f in findings if f.get("severity") == "高"]),
                    "medium_severity": len([f for f in findings if f.get("severity") == "中"]),
                    "low_severity": len([f for f in findings if f.get("severity") == "低"]),
                    "evaluation_date": datetime.now().isoformat()
                },
                "status": "completed"
            }
            
            logger.info(f"[{self.workflow_id}] テスト結果評価完了: {len(findings)}件の発見事項")
            return evaluation
            
        except Exception as e:
            logger.error(f"[{self.workflow_id}] テスト結果評価中にエラー: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "workflow_id": self.workflow_id
            } 