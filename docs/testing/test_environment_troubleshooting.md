# テスト環境の設定とテスト実行ガイド

## 概要

このドキュメントでは、本プロジェクトのテスト環境の設定方法、テストの実行方法、および一般的な問題のトラブルシューティングについて説明します。

## テスト環境の設定

### 必要な環境変数

テスト実行時には以下の環境変数が自動的に設定されます：

```python
os.environ["TESTING"] = "True"
os.environ["USE_MOCK_LLM"] = "True"
```

手動でテストを実行する場合は、以下のようにPowerShellで環境変数を設定します：

```powershell
$env:TESTING="True"
```

### テスト用データベース

テスト環境では、実際のアプリケーションデータベースではなく、テスト専用のSQLiteデータベースが使用されます。テストデータベースは以下の場所に作成されます：

```
tests/data/test.db
```

## テストの実行方法

### すべてのテストを実行

```powershell
$env:TESTING="True"; pytest
```

### 特定のテストファイルを実行

```powershell
$env:TESTING="True"; pytest tests/unit/repositories/test_regulation_repository.py
```

### 詳細な出力でテストを実行（verbose モード）

```powershell
$env:TESTING="True"; pytest tests/unit/repositories/test_regulation_repository.py -v
```

## 一般的な問題と解決方法

### テストデータベースの問題

テストが失敗する場合、テストデータベースが正しく初期化されていない可能性があります。以下の手順で問題を解決できる場合があります：

1. テストデータベースファイルを削除します：

```powershell
Remove-Item -Path tests/data/test.db -Force -ErrorAction SilentlyContinue
```

2. テスト環境変数を設定してテストを再実行します：

```powershell
$env:TESTING="True"; pytest tests/unit/repositories/test_regulation_repository.py -v
```

### テストデータベースの手動初期化

テストデータベースを明示的に初期化するには：

```powershell
$env:TESTING="True"; python -c "from src.utils.db_manager import init_db; init_db()"
```

### テーブル構造の確認

テストデータベースのテーブル構造の問題が疑われる場合、以下のPythonスクリプトを実行して確認できます：

```python
import sqlite3
import os

os.environ["TESTING"] = "True"

conn = sqlite3.connect('tests/data/test.db')
cursor = conn.cursor()

# テーブル一覧を取得
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("テーブル一覧:", [table[0] for table in tables])

# 特定のテーブルの構造を確認
for table_name in [table[0] for table in tables]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    print(f"\n{table_name} テーブルの構造:")
    for column in columns:
        print(f"  {column[1]} ({column[2]})")

conn.close()
```

## テストフィクスチャ

主要なテストフィクスチャは `tests/conftest.py` で定義されています。特に重要なのは以下のフィクスチャです：

### test_db_session

このフィクスチャは、テスト用のデータベースセッションを提供します。テストケース内で以下のように使用します：

```python
@pytest.mark.asyncio
async def test_something(test_db_session):
    # テストコード
    repository = SomeRepository(test_db_session)
    # ...
```

このフィクスチャは、テストの開始時にテストデータベースを初期化し、テストの終了時にセッションをクリーンアップします。

## 非同期テスト

非同期関数をテストする場合は、`@pytest.mark.asyncio` デコレータを使用します：

```python
@pytest.mark.asyncio
async def test_async_function(test_db_session):
    # 非同期テストコード
    result = await some_async_function()
    assert result is not None
```

## モックの使用

LLMクライアントなどの外部サービスをモックするためのフィクスチャが `tests/conftest.py` で定義されています：

```python
@pytest.fixture
def mock_llm():
    mock_llm_responder.clear_history()
    yield mock_llm_responder
    mock_llm_responder.clear_history()

@pytest.fixture
def patch_llm_client():
    target = "src.core.llm.client.LLMClient.generate_completion"
    with mock.patch(target) as mock_generate:
        mock_generate.side_effect = mock_llm_responder.generate_response
        yield mock_generate
```

これらのフィクスチャを使用して、外部サービスに依存するコードをテストできます。 