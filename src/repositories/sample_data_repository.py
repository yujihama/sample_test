#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
サンプルデータリポジトリ

このモジュールは、サンプルデータモデルに対するリポジトリパターンを実装します。
データの作成、取得、更新、削除などの操作をカプセル化します。
"""

import json
from src.utils import json_utils
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from sqlalchemy.sql import text
from sqlalchemy import or_

from src.models.db_models import SampleData
from src.repositories.base_repository import SQLAlchemyRepository
from src.utils.db_manager import get_db_session


class SampleDataRepository(SQLAlchemyRepository):
    """サンプルデータリポジトリクラス"""
    
    def __init__(self):
        """リポジトリの初期化"""
        db_session = get_db_session()
        super().__init__(db_session, SampleData)
    
    def search_by_filename(self, filename: str) -> List[SampleData]:
        """ファイル名でサンプルデータを検索する

        Args:
            filename: 検索するファイル名（部分一致）

        Returns:
            検索結果のサンプルデータリスト
        """
        with self.session_scope() as session:
            query = session.query(self.model).filter(
                self.model.filename.like(f"%{filename}%")
            )
            return query.all()
    
    def get_by_procedure_id(self, procedure_id: str) -> List[SampleData]:
        """監査手続きIDでサンプルデータを取得する

        Args:
            procedure_id: 監査手続きID

        Returns:
            監査手続きに関連するサンプルデータリスト
        """
        with self.session_scope() as session:
            query = session.query(self.model).filter(
                self.model.procedure_id == procedure_id
            )
            return query.all()
    
    def create_sample_data(self, data: Dict[str, Any]) -> SampleData:
        """サンプルデータを作成する

        Args:
            data: サンプルデータの属性

        Returns:
            作成されたサンプルデータオブジェクト
        """
        # JSONフィールドの処理
        for field in ["columns", "file_metadata"]:
            if field in data and not isinstance(data[field], str):
                data[field] = json_utils.json_serialize(data[field])
        
        return self.create(data)
    
    def update_sample_data(self, sample_id: str, data: Dict[str, Any]) -> Optional[SampleData]:
        """サンプルデータを更新する

        Args:
            sample_id: 更新するサンプルデータID
            data: 更新する属性

        Returns:
            更新されたサンプルデータオブジェクト
        """
        # JSONフィールドの処理
        for field in ["columns", "file_metadata"]:
            if field in data and not isinstance(data[field], str):
                data[field] = json_utils.json_serialize(data[field])
        
        return self.update(sample_id, data)
    
    def delete_sample_data(self, sample_id: str) -> bool:
        """サンプルデータを削除する

        Args:
            sample_id: 削除するサンプルデータID

        Returns:
            削除が成功したかどうか
        """
        return self.delete(sample_id)


# シングルトンインスタンス
sample_data_repository = SampleDataRepository() 