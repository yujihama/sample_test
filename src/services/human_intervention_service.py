"""
人間監査人インタラクションサービス

AIエージェントと人間監査人の間の通信を管理するためのサービス。
質問、承認依頼、情報要求などの通信を簡単に行うための関数を提供します。
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from loguru import logger
import asyncio
from sqlalchemy.orm import Session

from src.models.repositories import (
    human_intervention_request_repository,
    human_intervention_response_repository,
    workflow_repository
)
from src.utils.workflow_manager import pause_workflow, resume_workflow


class HumanInterventionService:
    """
    人間監査人とのインタラクションを管理するサービスクラス
    
    AIエージェントが人間監査人と通信するためのユーティリティメソッドを提供します。
    - 質問・承認依頼の送信
    - 応答の待機と取得
    - ワークフローの一時停止と再開の管理
    """
    
    def __init__(self, db: Session):
        """
        人間監査人インタラクションサービスの初期化
        
        Args:
            db: データベースセッション
        """
        self.db = db
    
    async def ask_question(
        self,
        workflow_id: str,
        requesting_agent: str,
        title: str,
        description: str,
        options: Optional[List[str]] = None,
        context_data: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
        pause_workflow_execution: bool = True
    ) -> Dict[str, Any]:
        """
        人間監査人に質問を送信する
        
        Args:
            workflow_id: ワークフローID
            requesting_agent: 要求元エージェントID
            title: 質問のタイトル
            description: 質問の詳細内容
            options: 選択肢（該当する場合）
            context_data: 関連するコンテキストデータ
            priority: 優先度（high, normal, low）
            pause_workflow_execution: ワークフローの実行を一時停止するかどうか
            
        Returns:
            作成された介入要求の情報
        """
        # 介入要求データを作成
        intervention_data = {
            "workflow_id": workflow_id,
            "requesting_agent": requesting_agent,
            "intervention_type": "question",
            "title": title,
            "description": description,
            "options": options or [],
            "context_data": context_data or {},
            "priority": priority,
            "status": "pending"
        }
        
        # 介入要求を保存
        intervention = human_intervention_request_repository.create(self.db, intervention_data)
        logger.info(f"人間監査人への質問を作成しました: {intervention.id}")
        
        # ワークフローの実行を一時停止
        if pause_workflow_execution:
            pause_reason = f"{requesting_agent}からの質問: {title}"
            pause_workflow(self.db, workflow_id, reason=pause_reason)
            logger.info(f"ワークフロー {workflow_id} を一時停止しました")
        
        return {
            "id": intervention.id,
            "workflow_id": intervention.workflow_id,
            "status": intervention.status,
            "created_at": intervention.created_at,
            "message": "人間監査人に質問が送信されました"
        }
    
    async def request_approval(
        self,
        workflow_id: str,
        requesting_agent: str,
        title: str,
        description: str,
        item_to_approve: Dict[str, Any],
        context_data: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
        pause_workflow_execution: bool = True
    ) -> Dict[str, Any]:
        """
        人間監査人に承認を依頼する
        
        Args:
            workflow_id: ワークフローID
            requesting_agent: 要求元エージェントID
            title: 承認依頼のタイトル
            description: 承認依頼の詳細内容
            item_to_approve: 承認が必要な項目のデータ
            context_data: 関連するコンテキストデータ
            priority: 優先度（high, normal, low）
            pause_workflow_execution: ワークフローの実行を一時停止するかどうか
            
        Returns:
            作成された介入要求の情報
        """
        # コンテキストデータに承認項目を追加
        full_context = context_data or {}
        full_context["item_to_approve"] = item_to_approve
        
        # 介入要求データを作成
        intervention_data = {
            "workflow_id": workflow_id,
            "requesting_agent": requesting_agent,
            "intervention_type": "approval_request",
            "title": title,
            "description": description,
            "options": ["承認", "拒否", "条件付き承認"],
            "context_data": full_context,
            "priority": priority,
            "status": "pending"
        }
        
        # 介入要求を保存
        intervention = human_intervention_request_repository.create(self.db, intervention_data)
        logger.info(f"人間監査人への承認依頼を作成しました: {intervention.id}")
        
        # ワークフローの実行を一時停止
        if pause_workflow_execution:
            pause_reason = f"{requesting_agent}からの承認依頼: {title}"
            pause_workflow(self.db, workflow_id, reason=pause_reason)
            logger.info(f"ワークフロー {workflow_id} を一時停止しました")
        
        return {
            "id": intervention.id,
            "workflow_id": intervention.workflow_id,
            "status": intervention.status,
            "created_at": intervention.created_at,
            "message": "人間監査人に承認依頼が送信されました"
        }
    
    async def request_information(
        self,
        workflow_id: str,
        requesting_agent: str,
        title: str,
        description: str,
        required_information: List[str],
        context_data: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
        pause_workflow_execution: bool = True
    ) -> Dict[str, Any]:
        """
        人間監査人に情報提供を依頼する
        
        Args:
            workflow_id: ワークフローID
            requesting_agent: 要求元エージェントID
            title: 情報依頼のタイトル
            description: 情報依頼の詳細内容
            required_information: 必要な情報の項目リスト
            context_data: 関連するコンテキストデータ
            priority: 優先度（high, normal, low）
            pause_workflow_execution: ワークフローの実行を一時停止するかどうか
            
        Returns:
            作成された介入要求の情報
        """
        # コンテキストデータに必要情報を追加
        full_context = context_data or {}
        full_context["required_information"] = required_information
        
        # 介入要求データを作成
        intervention_data = {
            "workflow_id": workflow_id,
            "requesting_agent": requesting_agent,
            "intervention_type": "information_request",
            "title": title,
            "description": description,
            "options": [],
            "context_data": full_context,
            "priority": priority,
            "status": "pending"
        }
        
        # 介入要求を保存
        intervention = human_intervention_request_repository.create(self.db, intervention_data)
        logger.info(f"人間監査人への情報依頼を作成しました: {intervention.id}")
        
        # ワークフローの実行を一時停止
        if pause_workflow_execution:
            pause_reason = f"{requesting_agent}からの情報依頼: {title}"
            pause_workflow(self.db, workflow_id, reason=pause_reason)
            logger.info(f"ワークフロー {workflow_id} を一時停止しました")
        
        return {
            "id": intervention.id,
            "workflow_id": intervention.workflow_id,
            "status": intervention.status,
            "created_at": intervention.created_at,
            "message": "人間監査人に情報依頼が送信されました"
        }
    
    async def report_issue(
        self,
        workflow_id: str,
        requesting_agent: str,
        title: str,
        description: str,
        issue_details: Dict[str, Any],
        priority: str = "high",
        pause_workflow_execution: bool = True
    ) -> Dict[str, Any]:
        """
        人間監査人に問題を報告する
        
        Args:
            workflow_id: ワークフローID
            requesting_agent: 要求元エージェントID
            title: 問題報告のタイトル
            description: 問題の詳細説明
            issue_details: 問題の詳細データ
            priority: 優先度（high, normal, low）
            pause_workflow_execution: ワークフローの実行を一時停止するかどうか
            
        Returns:
            作成された介入要求の情報
        """
        # 介入要求データを作成
        intervention_data = {
            "workflow_id": workflow_id,
            "requesting_agent": requesting_agent,
            "intervention_type": "escalation",
            "title": title,
            "description": description,
            "options": ["対応済み", "後で対応", "無視"],
            "context_data": {"issue_details": issue_details},
            "priority": priority,
            "status": "pending"
        }
        
        # 介入要求を保存
        intervention = human_intervention_request_repository.create(self.db, intervention_data)
        logger.info(f"人間監査人への問題報告を作成しました: {intervention.id}")
        
        # ワークフローの実行を一時停止
        if pause_workflow_execution:
            pause_reason = f"{requesting_agent}からの問題報告: {title}"
            pause_workflow(self.db, workflow_id, reason=pause_reason)
            logger.info(f"ワークフロー {workflow_id} を一時停止しました")
        
        return {
            "id": intervention.id,
            "workflow_id": intervention.workflow_id,
            "status": intervention.status,
            "created_at": intervention.created_at,
            "message": "人間監査人に問題が報告されました"
        }
    
    async def wait_for_response(
        self, 
        intervention_id: str, 
        timeout: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        人間監査人からの応答を待機する
        
        Args:
            intervention_id: 介入要求ID
            timeout: タイムアウト時間（秒）、Noneの場合は無限に待機
            
        Returns:
            人間監査人からの応答データ、またはNone（タイムアウトした場合）
        """
        start_time = datetime.now(timezone.utc)
        
        while True:
            # 介入要求の状態を確認
            intervention = human_intervention_request_repository.get(self.db, intervention_id)
            if not intervention:
                logger.error(f"介入要求 {intervention_id} が見つかりません")
                return None
            
            # 応答があるか確認
            latest_response = human_intervention_response_repository.get_latest_response(self.db, intervention_id)
            
            if latest_response:
                # 応答データを返す
                response_data = {
                    "id": latest_response.id,
                    "request_id": latest_response.request_id,
                    "responder": latest_response.responder,
                    "response_type": latest_response.response_type,
                    "content": latest_response.content,
                    "attachment_urls": latest_response.attachment_urls,
                    "comment": latest_response.comment,
                    "created_at": latest_response.created_at
                }
                
                logger.info(f"介入要求 {intervention_id} への応答を受信しました")
                return response_data
            
            # タイムアウトチェック
            if timeout is not None:
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                if elapsed >= timeout:
                    logger.warning(f"介入要求 {intervention_id} の応答待機がタイムアウトしました")
                    return None
            
            # 少し待機してから再試行
            await asyncio.sleep(1.0)
    
    def get_response(self, intervention_id: str) -> Optional[Dict[str, Any]]:
        """
        人間監査人からの応答を取得する（非同期待機なし）
        
        Args:
            intervention_id: 介入要求ID
            
        Returns:
            人間監査人からの応答データ、または介入要求がまだ完了していない場合はNone
        """
        # 介入要求の状態を確認
        intervention = human_intervention_request_repository.get(self.db, intervention_id)
        if not intervention:
            logger.error(f"介入要求 {intervention_id} が見つかりません")
            return None
        
        # 応答があるか確認
        latest_response = human_intervention_response_repository.get_latest_response(self.db, intervention_id)
        
        if not latest_response:
            logger.info(f"介入要求 {intervention_id} への応答はまだありません")
            return None
        
        # 応答データを返す
        response_data = {
            "id": latest_response.id,
            "request_id": latest_response.request_id,
            "responder": latest_response.responder,
            "response_type": latest_response.response_type,
            "content": latest_response.content,
            "attachment_urls": latest_response.attachment_urls,
            "comment": latest_response.comment,
            "created_at": latest_response.created_at
        }
        
        return response_data 