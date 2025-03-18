# データモデルガイド

このディレクトリには内部監査AIエージェントシステムのデータモデルとリポジトリパターンの実装が含まれています。
システムのデータ構造、永続化ロジック、データアクセスレイヤーが定義されています。

## データモデルの概要

1. **監査エンティティ (`audit_entities.py`)**
   - 監査手続き定義
   - サンプルデータ管理
   - 監査結果記録

2. **エージェント状態管理 (`agent_state.py`)**
   - エージェント状態の永続化
   - エージェント処理履歴の追跡
   - 状態遷移の記録

3. **ユーザー・認証 (`users.py`)**
   - ユーザー情報管理
   - 認証情報と権限管理
   - 監査者・被監査者情報

4. **ワークフロー管理 (`workflows.py`)**
   - ワークフロー定義と状態管理
   - ワークフローステップの追跡
   - タスク依存関係の管理

5. **ドキュメント管理 (`documents.py`)**
   - 文書メタデータ
   - ドキュメント保存場所情報
   - バージョン管理

6. **ツール関連 (`tools.py`)**
   - ツール実行履歴
   - ツールパラメータと結果の記録
   - ツール設定の永続化

7. **監査証跡 (`audit_trail.py`)**
   - 詳細なシステム操作ログ
   - エージェント決定の根拠記録
   - コンプライアンス監査のための証跡

## ファイル構成

```
models/
├── __init__.py              - パッケージ初期化
├── base.py                  - 基本モデルクラス
├── audit_entities.py        - 監査関連エンティティ
├── agent_state.py           - エージェント状態管理
├── users.py                 - ユーザー・認証
├── workflows.py             - ワークフロー管理
├── documents.py             - ドキュメント管理
├── tools.py                 - ツール関連
├── audit_trail.py           - 監査証跡
└── repositories/            - リポジトリパターン実装
    ├── __init__.py          - リポジトリパッケージ初期化
    ├── base_repository.py   - 基本リポジトリインターフェース
    ├── audit_repository.py  - 監査リポジトリ
    ├── user_repository.py   - ユーザーリポジトリ
    └── tool_repository.py   - ツールリポジトリ
```

## 主要モデルの詳細

### 監査エンティティモデル

監査の主要な対象となるエンティティを定義します：

```python
# audit_entities.py モデル例
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from .base import Base

class AuditProcedure(Base):
    """監査手続き定義モデル"""
    __tablename__ = "audit_procedures"
    
    id = Column(Integer, primary_key=True)
    procedure_code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    criteria = Column(JSON)  # 判断基準
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    
    # リレーションシップ
    samples = relationship("AuditSample", back_populates="procedure")
    

class AuditSample(Base):
    """監査サンプルモデル"""
    __tablename__ = "audit_samples"
    
    id = Column(Integer, primary_key=True)
    procedure_id = Column(Integer, ForeignKey("audit_procedures.id"))
    sample_code = Column(String(50), unique=True, nullable=False)
    data_path = Column(String(500))  # サンプルデータの保存パス
    status = Column(String(50))      # 処理状態
    metadata = Column(JSON)          # サンプルメタデータ
    created_at = Column(DateTime)
    
    # リレーションシップ
    procedure = relationship("AuditProcedure", back_populates="samples")
    results = relationship("AuditResult", back_populates="sample")
    

class AuditResult(Base):
    """監査結果モデル"""
    __tablename__ = "audit_results"
    
    id = Column(Integer, primary_key=True)
    sample_id = Column(Integer, ForeignKey("audit_samples.id"))
    agent_id = Column(String(100))   # 処理を実行したエージェントID
    result_type = Column(String(50)) # 結果タイプ（検証、集約、報告など）
    status = Column(String(50))      # 成功、失敗、警告など
    results = Column(JSON)           # 詳細結果
    created_at = Column(DateTime)
    
    # リレーションシップ
    sample = relationship("AuditSample", back_populates="results")
```

### リポジトリパターン

データアクセスロジックをカプセル化するリポジトリパターンを実装しています：

```python
# repositories/base_repository.py 例
from typing import TypeVar, Generic, List, Optional, Type, Any, Dict
from sqlalchemy.orm import Session
from ..base import Base

T = TypeVar('T', bound=Base)

class BaseRepository(Generic[T]):
    """基本リポジトリクラス"""
    
    def __init__(self, session: Session, model_class: Type[T]):
        self.session = session
        self.model_class = model_class
    
    def get_by_id(self, id: Any) -> Optional[T]:
        """IDによるエンティティ取得"""
        return self.session.query(self.model_class).filter(self.model_class.id == id).first()
    
    def get_all(self) -> List[T]:
        """全エンティティ取得"""
        return self.session.query(self.model_class).all()
    
    def create(self, entity: T) -> T:
        """エンティティ作成"""
        self.session.add(entity)
        self.session.commit()
        return entity
    
    def update(self, entity: T) -> T:
        """エンティティ更新"""
        self.session.merge(entity)
        self.session.commit()
        return entity
    
    def delete(self, entity: T) -> None:
        """エンティティ削除"""
        self.session.delete(entity)
        self.session.commit()
```

## ユースケースとの関連

データモデルはユースケースの実現に重要な役割を果たします：

1. **監査エンティティモデル**
   - ユースケースで説明される監査手続きや検証基準を `AuditProcedure` モデルとして表現
   - サンプルデータは `AuditSample` モデルで管理し、検証結果を `AuditResult` に保存

2. **エージェント状態管理**
   - ユースケースにあるエージェント間の連携履歴を `AgentState` モデルで追跡
   - エージェントの判断プロセスを監査証跡として記録

3. **ワークフロー管理**
   - ユースケースのフローを `Workflow` モデルとして表現
   - 各ステップの進捗と結果を追跡

## データモデルの拡張

### 新しいモデルの追加

1. 新しいモデルファイルの作成
   ```python
   # models/new_entity.py
   from sqlalchemy import Column, Integer, String, DateTime
   from .base import Base
   
   class NewEntity(Base):
       """新しいエンティティの説明"""
       __tablename__ = "new_entities"
       
       id = Column(Integer, primary_key=True)
       name = Column(String(100), nullable=False)
       description = Column(String(500))
       created_at = Column(DateTime)
   ```

2. リポジトリの実装
   ```python
   # repositories/new_entity_repository.py
   from ..new_entity import NewEntity
   from .base_repository import BaseRepository
   
   class NewEntityRepository(BaseRepository[NewEntity]):
       """新しいエンティティのリポジトリ"""
       
       def __init__(self, session):
           super().__init__(session, NewEntity)
           
       # 必要に応じて特殊なクエリメソッドを追加
       def find_by_name(self, name: str):
           return self.session.query(NewEntity).filter(NewEntity.name == name).all()
   ```

3. パッケージへの登録
   ```python
   # models/__init__.py に追加
   from .new_entity import NewEntity
   ```

### 既存モデルの拡張

既存のモデルを拡張するには、対象のモデルファイルに新しいフィールドやリレーションシップを追加します：

```python
# 既存の audit_entities.py に新しいフィールドを追加
class AuditProcedure(Base):
    # 既存のフィールド...
    
    # 新しいフィールド
    priority = Column(String(50))
    estimated_duration = Column(Integer)  # 推定所要時間（分）
    
    # 新しいリレーションシップ
    assigned_users = relationship("User", secondary="procedure_user_map")
```

## マイグレーション管理

データモデルの変更は `alembic` を使用して管理します：

```bash
# マイグレーションファイルの作成
alembic revision --autogenerate -m "説明メッセージ"

# マイグレーションの適用
alembic upgrade head
```

## データモデル設計の原則

1. **単一責任の原則**
   - 各モデルは明確に定義された単一の責任を持つ

2. **正規化**
   - 適切な正規化レベルを維持し、データの一貫性を確保

3. **参照整合性**
   - 外部キー制約で参照整合性を保証

4. **監査証跡**
   - 重要な操作の履歴を保持

5. **ドメイン主導設計**
   - ビジネスドメインの概念をモデルに反映

## パフォーマンス最適化のヒント

1. **インデックス戦略**
   - 頻繁に検索されるフィールドにはインデックスを設定
   ```python
   procedure_code = Column(String(50), unique=True, nullable=False, index=True)
   ```

2. **遅延ロード vs 即時ロード**
   - リレーションシップの読み込み戦略を適切に選択
   ```python
   # 即時ロードの例
   samples = relationship("AuditSample", back_populates="procedure", lazy="joined")
   ```

3. **複合インデックス**
   - 複数フィールドによる検索が多い場合は複合インデックスを検討
   ```python
   from sqlalchemy import Index
   
   __table_args__ = (
       Index('idx_sample_procedure_status', 'procedure_id', 'status'),
   )
   ``` 