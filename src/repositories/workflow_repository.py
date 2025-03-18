#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ワークフローリポジトリ

このモジュールは、ワークフローモデルに対するリポジトリパターンを実装します。
データの作成、取得、更新、削除などの操作をカプセル化します。
"""

import json
from src.utils import json_utils
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from sqlalchemy.sql import text
from sqlalchemy import or_, and_

from src.models.db_models import Workflow
from src.repositories.base_repository import SQLAlchemyRepository
from src.utils.db_manager import get_db_session


class WorkflowRepository(SQLAlchemyRepository):
    """ワークフローリポジトリクラス"""
    
    def __init__(self):
        """コンストラクタ"""
        db_session = get_db_session()
        super().__init__(db_session, Workflow)
    
    def get_by_procedure_id(self, procedure_id: str) -> List[Workflow]:
        """監査手続きIDでワークフローを取得する

        Args:
            procedure_id: 監査手続きID

        Returns:
            監査手続きに関連するワークフローリスト
        """
        with self.session_scope() as session:
            query = session.query(self.model).filter(
                self.model.audit_procedure_id == procedure_id
            )
            return query.all()
    
    def get_by_sample_data_id(self, sample_data_id: str) -> List[Workflow]:
        """サンプルデータIDでワークフローを取得する

        Args:
            sample_data_id: サンプルデータID

        Returns:
            サンプルデータに関連するワークフローリスト
        """
        with self.session_scope() as session:
            query = session.query(self.model).filter(
                self.model.sample_data_id == sample_data_id
            )
            return query.all()
    
    def get_by_procedure_and_sample(self, procedure_id: str, sample_id: str) -> Optional[Workflow]:
        """監査手続きIDとサンプルデータIDでワークフローを取得する

        Args:
            procedure_id: 監査手続きID
            sample_id: サンプルデータID

        Returns:
            該当するワークフロー
        """
        with self.session_scope() as session:
            query = session.query(self.model).filter(
                and_(
                    self.model.audit_procedure_id == procedure_id,
                    self.model.sample_data_id == sample_id
                )
            )
            return query.first()
    
    def create_workflow(self, data: Dict[str, Any]) -> Workflow:
        """ワークフローを作成する

        Args:
            data: ワークフローの属性

        Returns:
            作成されたワークフローオブジェクト
        """
        # JSONフィールドの処理
        for field in ["settings", "results", "metadata"]:
            if field in data and not isinstance(data[field], str):
                data[field] = json_utils.json_serialize(data[field])
        
        return self.create(data)
    
    def update_workflow(self, workflow_id: str, data: Dict[str, Any]) -> Optional[Workflow]:
        """ワークフローを更新する

        Args:
            workflow_id: 更新するワークフローID
            data: 更新する属性

        Returns:
            更新されたワークフローオブジェクト
        """
        # JSONフィールドの処理
        for field in ["settings", "results", "metadata"]:
            if field in data and not isinstance(data[field], str):
                data[field] = json_utils.json_serialize(data[field])
        
        data["updated_at"] = datetime.now()
        return self.update(workflow_id, data)
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """ワークフローを削除する

        Args:
            workflow_id: 削除するワークフローID

        Returns:
            削除が成功したかどうか
        """
        return self.delete(workflow_id)
    
    def update_status(self, workflow_id: str, status: str) -> Optional[Workflow]:
        """ワークフローのステータスを更新する

        Args:
            workflow_id: 更新するワークフローID
            status: 新しいステータス

        Returns:
            更新されたワークフローオブジェクト
        """
        return self.update(workflow_id, {"status": status, "updated_at": datetime.now()})


# シングルトンインスタンス
workflow_repository = WorkflowRepository() 