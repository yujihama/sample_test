#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
テストプランリポジトリ

このモジュールは、テストプランモデルに対するリポジトリパターンを実装します。
データの作成、取得、更新、削除などの操作をカプセル化します。
"""

import json
from src.utils import json_utils
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from sqlalchemy.sql import text
from sqlalchemy import or_

from src.models.db_models import TestPlan
from src.repositories.base_repository import SQLAlchemyRepository
from src.utils.db_manager import get_db_session


class TestPlanRepository(SQLAlchemyRepository):
    """テストプランリポジトリクラス"""
    
    def __init__(self):
        """コンストラクタ"""
        db_session = get_db_session()
        super().__init__(db_session, TestPlan)
    
    def get_by_workflow_id(self, workflow_id: str) -> List[TestPlan]:
        """ワークフローIDでテストプランを取得する

        Args:
            workflow_id: ワークフローID

        Returns:
            ワークフローに関連するテストプランリスト
        """
        with self.session_scope() as session:
            query = session.query(self.model).filter(
                self.model.workflow_id == workflow_id
            )
            return query.all()
    
    def search_by_name(self, name: str) -> List[TestPlan]:
        """名前でテストプランを検索する

        Args:
            name: 検索する名前（部分一致）

        Returns:
            検索結果のテストプランリスト
        """
        with self.session_scope() as session:
            query = session.query(self.model).filter(
                self.model.name.like(f"%{name}%")
            )
            return query.all()
    
    def create_test_plan(self, data: Dict[str, Any]) -> TestPlan:
        """テストプランを作成する

        Args:
            data: テストプランの属性

        Returns:
            作成されたテストプランオブジェクト
        """
        # JSONフィールドの処理
        for field in ["test_criteria", "test_steps", "expected_results"]:
            if field in data and not isinstance(data[field], str):
                data[field] = json_utils.json_serialize(data[field])
        
        return self.create(data)
    
    def update_test_plan(self, plan_id: str, data: Dict[str, Any]) -> Optional[TestPlan]:
        """テストプランを更新する

        Args:
            plan_id: 更新するテストプランID
            data: 更新する属性

        Returns:
            更新されたテストプランオブジェクト
        """
        # JSONフィールドの処理
        for field in ["test_criteria", "test_steps", "expected_results"]:
            if field in data and not isinstance(data[field], str):
                data[field] = json_utils.json_serialize(data[field])
        
        data["updated_at"] = datetime.now()
        return self.update(plan_id, data)
    
    def delete_test_plan(self, plan_id: str) -> bool:
        """テストプランを削除する

        Args:
            plan_id: 削除するテストプランID

        Returns:
            削除が成功したかどうか
        """
        return self.delete(plan_id)


# シングルトンインスタンス
test_plan_repository = TestPlanRepository() 