#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
テスト結果リポジトリ

このモジュールは、テスト結果モデルに対するリポジトリパターンを実装します。
データの作成、取得、更新、削除などの操作をカプセル化します。
"""

import json
from src.utils import json_utils
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from sqlalchemy.sql import text
from sqlalchemy import or_

from src.models.db_models import TestResult
from src.repositories.base_repository import SQLAlchemyRepository
from src.utils.db_manager import get_db_session


class TestResultRepository(SQLAlchemyRepository):
    """テスト結果リポジトリクラス"""
    
    def __init__(self):
        """コンストラクタ"""
        db_session = get_db_session()
        super().__init__(db_session, TestResult)
    
    def get_by_test_plan_id(self, test_plan_id: str) -> List[TestResult]:
        """テストプランIDでテスト結果を取得する

        Args:
            test_plan_id: テストプランID

        Returns:
            テストプランに関連するテスト結果リスト
        """
        with self.session_scope() as session:
            query = session.query(self.model).filter(
                self.model.test_plan_id == test_plan_id
            )
            return query.all()
    
    def get_by_workflow_id(self, workflow_id: str) -> List[TestResult]:
        """ワークフローIDでテスト結果を取得する

        Args:
            workflow_id: ワークフローID

        Returns:
            ワークフローに関連するテスト結果リスト
        """
        with self.session_scope() as session:
            query = session.query(self.model).filter(
                self.model.workflow_id == workflow_id
            )
            return query.all()
    
    def search_by_status(self, status: str) -> List[TestResult]:
        """ステータスでテスト結果を検索する

        Args:
            status: 検索するステータス

        Returns:
            検索結果のテスト結果リスト
        """
        with self.session_scope() as session:
            query = session.query(self.model).filter(
                self.model.status == status
            )
            return query.all()
    
    def create_test_result(self, data: Dict[str, Any]) -> TestResult:
        """テスト結果を作成する

        Args:
            data: テスト結果の属性

        Returns:
            作成されたテスト結果オブジェクト
        """
        # JSONフィールドの処理
        for field in ["result_data", "error_details"]:
            if field in data and not isinstance(data[field], str):
                data[field] = json_utils.json_serialize(data[field])
        
        return self.create(data)
    
    def update_test_result(self, result_id: str, data: Dict[str, Any]) -> Optional[TestResult]:
        """テスト結果を更新する

        Args:
            result_id: 更新するテスト結果ID
            data: 更新する属性

        Returns:
            更新されたテスト結果オブジェクト
        """
        # JSONフィールドの処理
        for field in ["result_data", "error_details"]:
            if field in data and not isinstance(data[field], str):
                data[field] = json_utils.json_serialize(data[field])
        
        data["updated_at"] = datetime.now()
        return self.update(result_id, data)
    
    def delete_test_result(self, result_id: str) -> bool:
        """テスト結果を削除する

        Args:
            result_id: 削除するテスト結果ID

        Returns:
            削除が成功したかどうか
        """
        return self.delete(result_id)
    
    def update_status(self, result_id: str, status: str) -> Optional[TestResult]:
        """テスト結果のステータスを更新する

        Args:
            result_id: 更新するテスト結果ID
            status: 新しいステータス

        Returns:
            更新されたテスト結果オブジェクト
        """
        return self.update(result_id, {"status": status, "updated_at": datetime.now()})


# シングルトンインスタンス
test_result_repository = TestResultRepository() 