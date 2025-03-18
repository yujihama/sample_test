# データベース構成と管理ガイド

## 概要

このドキュメントでは、アプリケーションのデータベース構成、モデル定義、および一般的なデータベース操作と問題解決のためのガイドラインを提供します。

## データベース設定

### 開発環境

開発環境では、SQLiteデータベースが使用されます。データベースファイルは以下の場所に配置されます：

```
./data/app.db
```

### テスト環境

テスト環境では、専用のSQLiteデータベースが使用されます：

```
./tests/data/test.db
```

テスト環境では、環境変数 `TESTING="True"` が設定されている場合に、自動的にテスト用データベースが使用されます。

### 本番環境

本番環境では、より堅牢なデータベース（PostgreSQLなど）の使用が推奨されます。データベース接続情報は環境変数経由で設定されます。

## データベース設定の管理

データベース接続とセッション管理は主に以下のファイルで行われています：

- `src/utils/db_manager.py` - データベース接続とセッション管理
- `src/db/session.py` - セッション管理のユーティリティ関数
- `src/core/config.py` - 設定値の管理

## モデル定義

データベースモデルは `src/models/db_models.py` で定義されています。主要なモデルには以下のものがあります：

- 規程情報関連: `Regulation`, `RegulationAuditTrail`, `RegulationDecisionReference`
- ワークフロー関連: `Workflow`, `AgentState`, `Message`
- 監査関連: `AuditProcedure`, `SampleData`, `TestPlan`, `TestResult`

すべてのモデルは SQLAlchemy の `Base` クラスを継承しています：

```python
from src.utils.db_manager import Base

class SomeModel(Base):
    __tablename__ = "some_models"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    # その他のフィールド
```

## リポジトリパターン

データベース操作はリポジトリパターンに従って実装されています。各モデルのデータアクセス操作は対応するリポジトリクラスで実装されています：

- `src/repositories/regulation_repository.py` - 規程情報リポジトリ
- その他のリポジトリ

リポジトリクラスの例：

```python
class RegulationRepository:
    def __init__(self, db_session):
        self.db_session = db_session
        self.is_async = isinstance(db_session, AsyncSession)
        
    async def get_regulation_by_id(self, regulation_id: str):
        # データ取得処理
```

## データベースの初期化

アプリケーションの起動時またはテストの開始時に、データベースは以下の関数によって初期化されます：

```python
from src.utils.db_manager import init_db

# データベースの初期化
init_db()
```

この関数は `src/utils/db_manager.py` で定義されており、データベースのテーブル作成を担当します。

## トランザクション管理

データベースのトランザクション管理は、SQLAlchemy のセッションオブジェクトを通じて行われます：

```python
try:
    # データベース操作
    self.db_session.add(some_object)
    self.db_session.flush()
    self.db_session.commit()
except Exception as e:
    self.db_session.rollback()
    raise
```

## テスト環境でのデータベース管理

テスト環境では、テストの独立性を確保するために、各テストケースで専用のデータベースセッションが使用されます。これは `tests/conftest.py` で定義された `test_db_session` フィクスチャによって管理されます：

```python
@pytest.fixture
def test_db_session():
    # テスト用のエンジンとセッションを作成
    test_engine = create_engine(...)
    TestSessionLocal = sessionmaker(...)
    
    # テーブルを作成
    Base.metadata.create_all(bind=test_engine)
    
    # セッションを取得
    db_session = TestSessionLocal()
    
    yield db_session
    
    # クリーンアップ
    db_session.close()
```

## よくある問題と解決方法

### テストデータベースの初期化問題

問題: テストケースでデータベース操作が失敗する（テーブルがない、カラムがないなど）

解決策:
1. テストデータベースファイルを削除：
   ```powershell
   Remove-Item -Path tests/data/test.db -Force -ErrorAction SilentlyContinue
   ```
2. 専用のエンジンとセッションを使用するように `test_db_session` フィクスチャを修正:
   ```python
   test_engine = create_engine(
       test_db_url,
       connect_args={"check_same_thread": False}
   )
   
   # テスト用のセッションを作成
   TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
   
   # テーブルを作成
   Base.metadata.create_all(bind=test_engine)
   ```

### データベースロックの問題

問題: SQLiteデータベースのロックエラー（「database is locked」）

解決策:
1. コネクションプールのリサイクル時間を短くする
2. リトライロジックを実装（`retry_engine_operation` 関数を使用）

## JSONフィールドの取り扱い

SQLiteにはネイティブのJSON型がないため、JSONデータは文字列として保存され、読み込み時に変換されます：

```python
# 保存時
structured_content_str = json.dumps(structured_content) if structured_content else None

# 読み込み時
structured_content_obj = json.loads(model.structured_content) if model.structured_content else {}
```

## 非同期データベース操作

リポジトリクラスは、同期および非同期の両方のセッションタイプをサポートするように設計されています：

```python
if self.is_async:
    await self.db_session.flush()
    await self.db_session.commit()
else:
    self.db_session.flush()
    self.db_session.commit()
```

これにより、同じリポジトリコードを通常のウェブリクエストと非同期処理の両方で使用できます。 