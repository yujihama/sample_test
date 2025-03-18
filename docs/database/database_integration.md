# データベース統合計画

## 現状分析

現在、プロジェクトには2つの異なるデータベースアクセス方法が存在しています：

1. **db_manager.py** - SQLAlchemyを使用したORM（オブジェクト関係マッピング）アプローチ
   - セッション管理
   - トランザクション制御
   - モデルベースのデータアクセス

2. **db_utils.py** - 直接SQLiteを使用した低レベルアプローチ
   - 生のSQLクエリ実行
   - シンプルなCRUD操作
   - 辞書ベースのデータアクセス

## 統合目標

1. SQLAlchemyベースの単一のデータアクセス層に統合
2. 既存の機能を維持しながら、コードの重複を排除
3. 移行期間中の下位互換性の確保
4. パフォーマンスとセキュリティの向上

## 統合アプローチ

### フェーズ1: 準備と分析

- [x] 両方のモジュールの機能テスト
- [ ] 依存関係の特定（どのコードがどのモジュールに依存しているか）
- [ ] 共通インターフェースの設計

### フェーズ2: SQLAlchemyモデルの拡張

- [ ] 既存のテーブル構造をSQLAlchemyモデルとして定義
- [ ] マイグレーションスクリプトの作成
- [ ] モデル間のリレーションシップの定義

### フェーズ3: db_utils.py機能のSQLAlchemy実装への移行

- [ ] DatabaseManagerクラスの各メソッドに対応するSQLAlchemy実装の作成
- [ ] 特殊なクエリやカスタム機能の移行
- [ ] パフォーマンステストと最適化

### フェーズ4: 移行とテスト

- [ ] 既存のコードをSQLAlchemy実装に移行するためのアダプターの作成
- [ ] 単体テストの作成と実行
- [ ] 統合テストの作成と実行

### フェーズ5: クリーンアップと文書化

- [ ] 古いコードの削除または非推奨化
- [ ] 新しいデータアクセス層の文書化
- [ ] パフォーマンスメトリクスの収集と分析

## 実装詳細

### 新しいモデル構造

```python
# models/base.py
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class AuditProcedure(Base):
    __tablename__ = "audit_procedures"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    risk_areas = Column(Text)  # JSON文字列
    required_data_fields = Column(Text)  # JSON文字列
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # リレーションシップ
    sample_data = relationship("SampleData", back_populates="procedure")
    workflows = relationship("Workflow", back_populates="procedure")

# 他のモデルも同様に定義
```

### 新しいリポジトリパターン

```python
# repositories/base_repository.py
from typing import TypeVar, Generic, Type, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from models.base import Base

T = TypeVar('T', bound=Base)

class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model
    
    def get_by_id(self, session: Session, id: str) -> Optional[T]:
        return session.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, session: Session) -> List[T]:
        return session.query(self.model).all()
    
    def create(self, session: Session, obj_in: Dict[str, Any]) -> T:
        obj = self.model(**obj_in)
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj
    
    def update(self, session: Session, db_obj: T, obj_in: Dict[str, Any]) -> T:
        for key, value in obj_in.items():
            setattr(db_obj, key, value)
        session.add(db_obj)
        session.commit()
        session.refresh(db_obj)
        return db_obj
    
    def delete(self, session: Session, id: str) -> None:
        obj = session.query(self.model).filter(self.model.id == id).first()
        if obj:
            session.delete(obj)
            session.commit()
    
    def execute_raw_query(self, session: Session, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        生のSQLクエリを実行する（db_utils.pyの互換性のため）
        """
        result = session.execute(text(query), params or {})
        return [dict(row) for row in result]
```

## タイムライン

1. フェーズ1: 1週間
2. フェーズ2: 2週間
3. フェーズ3: 2週間
4. フェーズ4: 2週間
5. フェーズ5: 1週間

合計: 約8週間

## リスクと緩和策

1. **リスク**: 既存のアプリケーションコードが中断する
   **緩和策**: 段階的な移行と広範なテスト

2. **リスク**: パフォーマンスの低下
   **緩和策**: クエリの最適化とインデックス作成

3. **リスク**: データの整合性の問題
   **緩和策**: トランザクション管理の強化とバリデーション

4. **リスク**: 開発の遅延
   **緩和策**: 明確なマイルストーンと優先順位付け 