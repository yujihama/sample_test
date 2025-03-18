"""
エージェントD: 報告書作成
"""

import uuid
import os
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import asyncio

from loguru import logger
from pydantic import BaseModel, Field

from src.core.agent_base import AgentBase, AgentState
from src.core.config import settings
from src.utils.llm_utils import (
    get_llm, 
    create_audit_report_generator_prompt
)
from src.core.messaging import MessageClient


class AgentDState(AgentState):
    """エージェントDの状態クラス"""
    # 監査総括関連
    summary_id: Optional[str] = None
    summary: Optional[Dict[str, Any]] = None
    
    # 監査手続き関連
    procedure_text: Optional[str] = None
    
    # 出力関連
    report: Optional[Dict[str, Any]] = None
    report_path: Optional[str] = None
    
    # その他
    is_processing: bool = False
    

class AgentD(AgentBase[AgentDState]):
    """
    報告書作成を担当するエージェントD
    """
    
    def __init__(self, message_client: Optional[MessageClient] = None):
        """
        初期化
        
        Args:
            message_client: メッセージクライアント（オプション）
        """
        super().__init__(
            agent_id=settings.AGENT_D_ID,
            state_class=AgentDState,
            agent_name="レポート作成エージェント"
        )
        self.message_client = message_client
        
        # メッセージングプロパティの追加（テスト用）
        self.messaging = self.message_client
        
        logger.info("AgentD initialized")
    
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
        logger.info(f"Agent D processing message type: {message_type}")
        
        result = {"status": "unknown_message_type", "message_id": message.get("id")}
        
        if message_type == "audit_summary":
            # 監査総括メッセージの処理
            result = await self.handle_audit_summary(content)
        elif message_type == "generate_report":
            # 報告書生成メッセージの処理
            result = await self.handle_generate_report(content)
        elif message_type == "question":
            # 質問メッセージの処理
            result = await self.handle_question(content)
        
        return result
    
    async def handle_audit_summary(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        監査総括メッセージの処理
        
        Args:
            content: メッセージコンテンツ
            
        Returns:
            処理結果
        """
        summary = content.get("summary")
        procedure_text = content.get("procedure_text")
        
        if not summary:
            return {"status": "error", "error": "Audit summary is required"}
        
        # 状態を更新
        self.state.update(
            summary_id=summary.get("id"),
            summary=summary,
            procedure_text=procedure_text,
            status="received_audit_summary"
        )
        
        logger.info(f"Audit summary received with ID: {summary.get('id')}")
        
        # 自動的に報告書を生成
        return await self.handle_generate_report({})
    
    async def handle_generate_report(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        報告書生成メッセージの処理
        
        Args:
            content: メッセージコンテンツ
            
        Returns:
            処理結果
        """
        if self.state.is_processing:
            return {"status": "busy", "error": "Agent is already processing a task"}
        
        if not self.state.summary:
            return {
                "status": "error", 
                "error": "Audit summary is not available. Send audit summary first."
            }
        
        self.state.update(is_processing=True, status="busy")
        
        try:
            # 報告書を生成
            report = await self.generate_audit_report(
                self.state.procedure_text,
                self.state.summary
            )
            
            # 報告書をファイルに保存
            report_path = await self.save_report_to_file(report)
            
            # 状態を更新
            self.state.update(
                report=report,
                report_path=report_path,
                is_processing=False,
                status="idle"
            )
            
            logger.info(f"Audit report generated: {report.get('title')}")
            return {
                "status": "success",
                "report": report,
                "report_path": report_path
            }
        
        except Exception as e:
            logger.error(f"Error in handle_generate_report: {e}")
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
            # LLMを使用して質問に回答
            system_message = """
            あなたは内部監査報告書の作成を担当する専門家です。
            監査総括と報告書の内容について質問に回答してください。
            回答は簡潔で明確、かつ専門的であるべきです。
            """
            
            human_template = """
            以下の情報と質問に基づいて回答してください。
            
            監査総括:
            {summary}
            
            監査報告書:
            {report}
            
            質問:
            {question}
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
                "summary": str(self.state.summary or "情報なし"),
                "report": str(self.state.report or "まだ作成されていません"),
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
    
    async def generate_audit_report(
        self, procedure_text: Optional[str], summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        監査報告書を生成する
        
        Args:
            procedure_text: 監査手続きテキスト
            summary: 監査総括
            
        Returns:
            監査報告書
        """
        logger.info("Generating audit report")
        
        try:
            # 監査手続きが設定されていない場合のフォールバック
            if not procedure_text:
                procedure_text = "監査手続きテキストは提供されていません。"
            
            # 監査報告書生成のためのプロンプトを作成
            chain = create_audit_report_generator_prompt(
                procedure_text=procedure_text,
                summary=summary
            )
            
            # LLMでの処理を実行
            result = await chain.ainvoke({})
            
            # 監査報告書の構造を作成
            report = {
                "id": f"report-{uuid.uuid4().hex[:8]}",
                "summary_id": summary.get("id"),
                "title": result.get("title", "監査報告書"),
                "executive_summary": result.get("executive_summary", ""),
                "background": result.get("background", ""),
                "findings_detail": result.get("findings_detail", ""),
                "recommendations": result.get("recommendations", ""),
                "conclusion": result.get("conclusion", ""),
                "appendices": result.get("appendices", []),
                "created_at": datetime.now().isoformat()
            }
            
            logger.info(f"Audit report generated: {report['title']}")
            return report
        
        except Exception as e:
            logger.error(f"Error generating audit report: {e}")
            raise
    
    async def save_report_to_file(self, report: Dict[str, Any]) -> str:
        """
        監査報告書をファイルに保存する
        
        Args:
            report: 監査報告書
            
        Returns:
            保存先パス
        """
        try:
            # 報告書の保存先ディレクトリを作成
            report_dir = settings.REPORT_DIR
            os.makedirs(report_dir, exist_ok=True)
            
            # 報告書ファイルのパスを生成
            report_id = report.get("id", f"report-{uuid.uuid4().hex[:8]}")
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"{report_id}_{timestamp}.md"
            report_path = os.path.join(report_dir, filename)
            
            # マークダウン形式で報告書を作成
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"# {report['title']}\n\n")
                f.write(f"**報告書ID:** {report['id']}\n")
                f.write(f"**作成日時:** {report['created_at']}\n")
                f.write(f"**監査総括ID:** {report['summary_id']}\n\n")
                
                f.write("## エグゼクティブサマリー\n\n")
                f.write(f"{report['executive_summary']}\n\n")
                
                f.write("## 背景\n\n")
                f.write(f"{report['background']}\n\n")
                
                f.write("## 発見事項の詳細\n\n")
                f.write(f"{report['findings_detail']}\n\n")
                
                f.write("## 推奨事項\n\n")
                f.write(f"{report['recommendations']}\n\n")
                
                f.write("## 結論\n\n")
                f.write(f"{report['conclusion']}\n\n")
                
                if report.get("appendices"):
                    f.write("## 付録\n\n")
                    for i, appendix in enumerate(report["appendices"]):
                        f.write(f"{i+1}. {appendix}\n")
            
            logger.info(f"Audit report saved to: {report_path}")
            return report_path
        
        except Exception as e:
            logger.error(f"Error saving audit report to file: {e}")
            raise
    
    async def generate_report(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析結果に基づいて報告書を生成する

        Args:
            analysis_result: 分析結果
                - status: 分析ステータス（"completed", "failed"）
                - findings: 発見事項のリスト
                - risk_assessment: リスク評価結果
                - compliance_status: コンプライアンス状態
                - recommendations: 追加の推奨事項

        Returns:
            Dict[str, Any]: 報告書
                - status: 報告書の状態（"completed", "failed"）
                - summary: 報告書の要約
                - details: 詳細な報告内容
                - recommendations: 最終的な推奨事項
                - next_steps: 次のステップ
        """
        try:
            if analysis_result["status"] != "completed":
                return {
                    "status": "failed",
                    "error": "分析結果が完了していません"
                }
            
            # 報告書の要約を作成
            summary = {
                "title": "予算変更承認に関する監査報告書",
                "overview": "予算変更要求の評価および分析結果に基づく報告",
                "key_findings": analysis_result["findings"],
                "risk_level": analysis_result["risk_assessment"]["level"]
            }
            
            # 詳細な報告内容を作成
            details = {
                "risk_assessment": {
                    "level": analysis_result["risk_assessment"]["level"],
                    "factors": analysis_result["risk_assessment"]["factors"],
                    "implications": "予算変更が組織に与える潜在的な影響の評価"
                },
                "compliance_review": {
                    "status": analysis_result["compliance_status"]["status"],
                    "details": analysis_result["compliance_status"]["details"],
                    "implications": "コンプライアンス上の考慮事項"
                }
            }
            
            # 推奨事項をまとめる
            recommendations = list(analysis_result["recommendations"])
            
            # 次のステップを決定
            next_steps = []
            if analysis_result["compliance_status"]["status"] == "review_required":
                next_steps.extend([
                    "上級管理職による詳細なレビューの実施",
                    "追加の予算根拠資料の要請",
                    "代替案の検討"
                ])
            else:
                next_steps.extend([
                    "承認プロセスの完了",
                    "予算変更の実施計画の策定",
                    "関係部門への通知"
                ])
            
            return {
                "status": "completed",
                "summary": summary,
                "details": details,
                "recommendations": recommendations,
                "next_steps": next_steps
            }
        except Exception as e:
            logger.error(f"報告書の生成中にエラーが発生しました: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            } 