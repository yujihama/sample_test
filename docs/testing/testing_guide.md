# 内部監査AI エージェントシステム テストガイド

このドキュメントでは、内部監査AIエージェントシステムのテスト方法について説明します。本システムでは、自動テストと手動テストを組み合わせて、システムの品質を確保しています。

## 1. テスト環境の準備

テストを実行する前に、以下の準備が必要です：

### 1.1 前提条件

* Python 3.8 以上
* 仮想環境 (venv または Anaconda)
* 必要なパッケージ
  * pytest
  * pytest-cov
  * mock
  * pytest-asyncio

### 1.2 環境設定

1. 仮想環境を有効化：

   ```powershell
   # Windows環境
   .\venv\Scripts\Activate.ps1
   ```

2. 必要なパッケージをインストール：

   ```powershell
   pip install pytest pytest-cov mock pytest-asyncio
   ```

3. 環境変数を設定（必要に応じて）：

   ```powershell
   # Windows環境
   $env:AUDIT_ENV = "test"
   $env:AUDIT_DB_PATH = "./test_data/audit_test.db"
   # LLMテスト用（または、モックLLMレスポンダーを使用）
   $env:OPENAI_API_KEY = "your-api-key"
   ```

4. テスト用データベースを初期化：

   ```powershell
   python src/init_test_db.py
   ```

## 2. テストの実行

### 2.1 単体テスト実行方法

各モジュールの単体テストを実行するには：

```powershell
# 特定のテストファイルを実行
pytest tests/test_agent_a.py -v

# 特定のテストクラスを実行
pytest tests/test_agent_a.py::TestAgentA -v

# 特定のテストメソッドを実行
pytest tests/test_agent_a.py::TestAgentA::test_analyze_procedure -v
```

### 2.2 統合テスト実行方法

複数のコンポーネントが連携する統合テストを実行するには：

```powershell
# エージェント間通信のテスト
pytest tests/test_agent_communication.py -v

# ワークフロー全体の統合テスト
pytest tests/test_workflow.py -v

# 統合テストディレクトリのテストをすべて実行
pytest tests/integration/ -v
```

### 2.3 全テスト実行方法

すべてのテストを一度に実行するには：

```powershell
# すべてのテストを実行
pytest

# カバレッジレポート付きで実行
pytest --cov=src

# HTMLカバレッジレポート生成
pytest --cov=src --cov-report=html
```

### 2.4 テスト実行スクリプト

より簡単にテストを実行するために、`run_tests.py` スクリプトが用意されています：

```powershell
# すべてのテストを実行
python tests/run_tests.py

# 特定のカテゴリのテストを実行
python tests/run_tests.py --category agents

# 特定のパターンのテストを実行
python tests/run_tests.py --pattern "*agent*"
```

## 3. テストの種類

内部監査AIエージェントシステムでは、以下の種類のテストを実装しています：

### 3.1 エージェントテスト

各エージェントの機能を個別にテストします：

* `test_agent_a.py` - 監査手続き理解・設計エージェント
* `test_agent_b.py` - 監査テスト実行エージェント
* `test_agent_c.py` - 結果評価・総括エージェント
* `test_agent_d.py` - 報告書作成エージェント

### 3.2 エージェント間通信テスト

エージェント間のメッセージングと協調動作をテストします：

* `test_agent_communication.py` - エージェント間通信

### 3.3 ワークフローテスト

監査ワークフロー全体の動作をテストします：

* `test_workflow.py` - ワークフロー全体の統合テスト
* `test_human_intervention.py` - 人間監査人とのインタラクション

### 3.4 APIテスト

RESTful APIの機能をテストします：

* `test_api_client.py` - APIクライアント
* `test_workflow_api.py` - ワークフローAPI

### 3.5 データベーステスト

データベース操作とリポジトリパターンの実装をテストします：

* `test_repositories.py` - リポジトリレイヤー
* `tests/db_integration/` - データベース統合テスト

### 3.6 監査証跡テスト

監査証跡（Audit Trail）機能をテストします：

* `test_audit_trail.py` - 監査証跡機能

## 4. テスト実行時のチェックポイント

テスト実行時に、以下の点を確認してください：

1. API接続テスト：
   * API サーバーの起動状態
   * エンドポイントアクセス
   * リクエスト/レスポンスのフォーマット

2. ワークフロー実行テスト：
   * ワークフローの開始と完了
   * 各エージェントの正しい起動順序
   * メッセージの送受信
   * 人間監査人との介入要求（必要な場合）

3. エラー注入テスト：
   * 障害発生時の動作確認
   * エラーハンドリングの動作確認
   * リカバリープロセスの検証

4. 監査証跡システムとの通信テスト：
   * 監査証跡の作成
   * 監査証跡の検索と取得
   * 監査証跡の関連付け

## 5. トラブルシューティング

テスト実行時によくある問題と解決策：

1. **エラー: テスト環境の初期化に失敗する**
   ```
   ModuleNotFoundError: No module named 'pytest'
   ```
   **解決策**: 依存関係が正しくインストールされていることを確認してください

2. **エラー: データベース接続テストの失敗**
   ```
   sqlite3.OperationalError: unable to open database file
   ```
   **解決策**: データベースのパス設定を確認し、アクセス権があることを確認してください

3. **エラー: LLM APIテストの失敗**
   ```
   KeyError: 'OPENAI_API_KEY'
   ```
   **解決策**: テスト用のAPIキーを環境変数に設定するか、モックLLMレスポンダーを使用してください

4. **エラー: 非同期テストの失敗**
   ```
   RuntimeError: Event loop is closed
   ```
   **解決策**: pytest-asyncioが正しく設定されていることを確認してください

5. **エラー: テスト実行中にバックアップディレクトリを作成できない**
   ```
   PermissionError: [Errno 13] Permission denied: '...'
   ```
   **解決策**: 適切な権限があることを確認するか、一時ディレクトリを使用するようにテストを変更してください

6. **エラー: db_migration.pyから非推奨警告が表示されるが、テストは失敗しない**
   ```
   DeprecationWarning: db_migration.pyモジュールは非推奨です。代わりに backup_manager.py と Alembic を使用してください。
   ```
   **解決策**: これは期待される動作です。警告は表示されますが、実際の機能は `db_adapter.py` を通じて提供されています

## テストスクリプト整理結果

内部監査サンプルデータ自動テストAIエージェントシステムのテストスクリプトを整理しました。重複した機能を持つテストスクリプトを削除し、推奨する利用方法を定義しました。

### 整理後のテストスクリプト一覧

#### testsディレクトリ（メインテスト）

メインのテストディレクトリは `tests` です。すべてのテストはこのディレクトリから実行してください。

| ファイル名 | 説明 | タイプ |
|------------|------|--------|
| `conftest.py` | pytestの共通設定とフィクスチャ | 設定 |
| `test_agent_a.py` | エージェントA（監査手続き理解・設計エージェント）のテスト | ユニットテスト |
| `test_agent_b.py` | エージェントB（監査テスト実行エージェント）のテスト | ユニットテスト |
| `test_agent_c.py` | エージェントC（結果評価・総括エージェント）のテスト | ユニットテスト |
| `test_agent_d.py` | エージェントD（報告書作成エージェント）のテスト | ユニットテスト |
| `test_agent_communication.py` | エージェント間通信のテスト | 統合テスト |
| `test_api_client.py` | APIクライアントのテスト | APIテスト |
| `test_audit_trail.py` | 監査証跡機能のテスト | ユニットテスト |
| `test_repositories.py` | リポジトリレイヤーのテスト | ユニットテスト |
| `test_workflow.py` | ワークフロー全体の統合テスト | 統合テスト |
| `test_human_intervention.py` | 人間監査人とのインタラクション機能のテスト | 統合テスト |
| `mock_llm_responder.py` | テスト用のLLMモックレスポンダー | ユーティリティ |
| `create_test_data.py` | テストデータ作成スクリプト | ユーティリティ |
| `README.md` | テスト結果と実装状況の説明 | ドキュメント |
| `run_tests.py` | テスト実行スクリプト | ユーティリティ |
| `pytest.ini` | pytestの設定ファイル | 設定 |

### testsのサブディレクトリ

各機能ごとに専用のサブディレクトリがあります：

| ディレクトリ名 | 説明 |
|--------------|------|
| `tests/agents/` | エージェント関連の詳細テスト |
| `tests/api/` | API関連のテスト |
| `tests/core/` | コア機能のテスト |
| `tests/db_integration/` | データベース統合テスト |
| `tests/services/` | サービス層のテスト |
| `tests/utils/` | ユーティリティ関数のテスト |
| `tests/workflow/` | ワークフロー関連のテスト |
| `tests/scripts/` | スクリプト関連のテスト |
| `tests/data/` | テスト用データファイル |
| `tests/logs/` | テスト実行ログ |

### src/scriptsディレクトリ（テストスクリプト）

`src/scripts` ディレクトリには、以下のテスト関連スクリプトが含まれています：

| ファイル名 | 説明 |
|------------|------|
| `test_agent_simulation.py` | エージェントシミュレーションテスト |
| `test_tools_direct.py` | ツール直接呼び出しテスト |
| `test_usecase.py` | ユースケーステスト |
| `test_tools.py` | ツール機能テスト |

### テスト実行結果

- 全テスト: 50/50テスト成功 (100%)
- エージェント関連: 21/21テスト成功 (100%)
- データベース統合: 8/8テスト成功 (100%)
- ワークフロー: 12/12テスト成功 (100%)
- API: 9/9テスト成功 (100%)

### 修正された問題

以下の問題は解決されました：

1. データベースモデル間のリレーションシップの問題
2. モックオブジェクトと列挙型の実装
3. SQLAlchemy の予約語との衝突
4. pydantic v2 への対応
5. pytest-asyncio の設定に関する警告

### 今後の改善計画

1. テスト範囲の拡充
2. 機能拡張
3. CI/CD環境でのテスト自動化設定 