#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
テスト用のモックリポジトリクラス
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Union


class MockSampleData:
    """サンプルデータのモックオブジェクト"""
    def __init__(self, sample_id: str, name: str = None, description: str = None, data_source: str = None):
        self.id = sample_id
        self.name = name or f"Sample {sample_id}"
        self.description = description or f"Sample data for testing - {sample_id}"
        self.data_source = data_source or "test_db"
        self.created_at = datetime.now()
        self.updated_at = datetime.now()


class MockSampleDataRepository:
    """SampleDataRepositoryのモック実装"""
    def __init__(self):
        self.samples = {}  # サンプルデータをID->オブジェクトのマップで保存
    
    def add_sample(self, sample_id: str, name: str = None, description: str = None, data_source: str = None) -> MockSampleData:
        """モックサンプルをリポジトリに追加"""
        sample = MockSampleData(sample_id, name, description, data_source)
        self.samples[sample_id] = sample
        return sample
    
    def get(self, db, sample_id: str) -> Optional[MockSampleData]:
        """IDでサンプルを取得"""
        return self.samples.get(sample_id)
    
    def find(self, db, filters: Dict[str, Any], limit: int = 100) -> List[MockSampleData]:
        """フィルタ条件でサンプルを検索"""
        results = []
        
        for sample in self.samples.values():
            match = True
            for key, value in filters.items():
                if not hasattr(sample, key) or getattr(sample, key) != value:
                    match = False
                    break
            
            if match:
                results.append(sample)
            
            if len(results) >= limit:
                break
        
        return results
    
    def create(self, db, data: Dict[str, Any]) -> str:
        """サンプルを作成（テスト用）"""
        sample_id = data.get("id") or f"sample-{uuid.uuid4().hex[:8]}"
        sample = MockSampleData(
            sample_id=sample_id,
            name=data.get("name"),
            description=data.get("description"),
            data_source=data.get("data_source")
        )
        self.samples[sample_id] = sample
        return sample_id
    
    def update(self, db, sample_id: str, data: Dict[str, Any]) -> bool:
        """サンプルを更新（テスト用）"""
        if sample_id not in self.samples:
            return False
        
        sample = self.samples[sample_id]
        
        for key, value in data.items():
            if hasattr(sample, key):
                setattr(sample, key, value)
        
        sample.updated_at = datetime.now()
        return True
    
    def delete(self, db, sample_id: str) -> bool:
        """サンプルを削除（テスト用）"""
        if sample_id in self.samples:
            del self.samples[sample_id]
            return True
        return False
    
    def get_by_procedure_id(self, db, procedure_id: str) -> List[MockSampleData]:
        """手続きIDに基づいてサンプルを取得（テスト用）"""
        return [s for s in self.samples.values() if getattr(s, 'procedure_id', None) == procedure_id]


# モック用のパッチ関数
def mock_get_db():
    """get_db関数のモック版"""
    yield None 