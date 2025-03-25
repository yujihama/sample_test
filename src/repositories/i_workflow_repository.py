#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ワークフローリポジトリインターフェース

このモジュールは、ワークフローリポジトリのインターフェースを定義します。
"""

from abc import abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from src.repositories.base_repository import IRepository
from src.models.db_models import Workflow


class IWorkflowRepository(IRepository[Workflow]):
    """ワークフローリポジトリインターフェース"""

    @abstractmethod
    def get_by_procedure_id(self, procedure_id: str, db=None) -> List[Workflow]:
        """監査手続きIDでワークフローを取得する

        Args:
            procedure_id: 監査手続きID
            db: データベースセッション（オプション）

        Returns:
            監査手続きに関連するワークフローリスト
        """
        pass

    @abstractmethod
    def get_by_sample_data_id(self, sample_data_id: str, db=None) -> List[Workflow]:
        """サンプルデータIDでワークフローを取得する

        Args:
            sample_data_id: サンプルデータID
            db: データベースセッション（オプション）

        Returns:
            サンプルデータに関連するワークフローリスト
        """
        pass

    @abstractmethod
    def get_by_procedure_and_sample(self, procedure_id: str, sample_id: str, db=None) -> Optional[Workflow]:
        """監査手続きIDとサンプルデータIDでワークフローを取得する

        Args:
            procedure_id: 監査手続きID
            sample_id: サンプルデータID
            db: データベースセッション（オプション）

        Returns:
            該当するワークフロー
        """
        pass

    @abstractmethod
    def get_active_workflows(self, db=None) -> List[Workflow]:
        """アクティブなワークフローを取得する

        Args:
            db: データベースセッション（オプション）

        Returns:
            アクティブなワークフローのリスト
        """
        pass

    @abstractmethod
    def update_status(self, workflow_id: str, status: str, db=None) -> Optional[Workflow]:
        """ワークフローのステータスを更新する

        Args:
            workflow_id: 更新するワークフローID
            status: 新しいステータス
            db: データベースセッション（オプション）

        Returns:
            更新されたワークフローオブジェクト
        """
        pass

    @abstractmethod
    def update_workflow_status(self, workflow_id: str, data: Dict[str, Any], db=None) -> Optional[Workflow]:
        """ワークフローのステータスと関連データを更新する

        Args:
            workflow_id: 更新するワークフローID
            data: 更新するデータ（status, error, started_at, ended_atなど）
            db: データベースセッション（オプション）

        Returns:
            更新されたワークフローオブジェクト
        """
        pass

    @abstractmethod
    async def update_workflow_state(self, workflow_id: str, state_data: Dict[str, Any], db=None) -> Optional[Workflow]:
        """ワークフローの状態データを更新する

        Args:
            workflow_id: 更新するワークフローID
            state_data: 状態データ
            db: データベースセッション（オプション）

        Returns:
            更新されたワークフローオブジェクト
        """
        pass

    @abstractmethod
    async def get_workflow_state(self, workflow_id: str, db=None) -> Optional[Dict[str, Any]]:
        """ワークフローの状態を取得する

        Args:
            workflow_id: ワークフローID
            db: データベースセッション（オプション）

        Returns:
            ワークフローの状態データ
        """
        pass

    @abstractmethod
    def filter(self, status: Optional[str] = None, created_before: Optional[datetime] = None,
               updated_after: Optional[datetime] = None, updated_before: Optional[datetime] = None,
               order_by: Optional[Tuple[str, str]] = None, limit: Optional[int] = None, db=None) -> List[Workflow]:
        """条件に基づいてワークフローをフィルタリングする

        Args:
            status: フィルタするステータス
            created_before: この日時より前に作成されたワークフロー
            updated_after: この日時より後に更新されたワークフロー
            updated_before: この日時より前に更新されたワークフロー
            order_by: 並び順（カラム名, "asc"または"desc"）
            limit: 取得する最大件数
            db: データベースセッション（オプション）

        Returns:
            フィルタリングされたワークフローのリスト
        """
        pass 