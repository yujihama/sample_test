# テストスクリプト整理結果

## 概要

内部監査サンプルデータ自動テストAIエージェントシステムのテストスクリプトを整理しました。重複した機能を持つテストスクリプトを削除し、推奨する利用方法を定義しました。

## テストの種類と目的

テストスクリプトは主に以下の3種類に分類されます：

1. **ユニットテスト（Unit Tests）**: 個々のコンポーネントの機能を確認するテスト
2. **統合テスト（Integration Tests）**: 複数のコンポーネントの連携を確認するテスト
3. **APIテスト（API Tests）**: HTTP APIの機能を確認するテスト

## 整理前のテストスクリプト一覧

整理前は複数のディレクトリに重複したテストスクリプトが存在していました：

* `src/tests/` - メインのテストディレクトリ（pytest形式）
* `tests/` - 補助的なテストディレクトリ
* `tools/` - ユーティリティ機能を含むディレクトリ

## 整理後のテストスクリプト一覧

### testsディレクトリ（メインテスト）

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
| `test_regulation.py` | 規程情報管理機能のテスト | ユニットテスト/統合テスト |
| `mock_llm_responder.py` | テスト用のLLMモックレスポンダー | ユーティリティ |
| `create_test_data.py` | テストデータ作成スクリプト | ユーティリティ |
| `README.md` | テスト結果と実装状況の説明 | ドキュメント |
| `run_tests.py` | テスト実行スクリプト | ユーティリティ |
| `pytest.ini` | pytestの設定ファイル | 設定 |

### testsのサブディレクトリ

各機能ごとに専用のサブディレクトリがあります：

| ディレクトリ名 | 説明 |
|----------------|------|
| `tests/unit/` | ユニットテスト |
| `tests/unit/repositories/` | リポジトリのユニットテスト |
| `tests/unit/services/` | サービスのユニットテスト |
| `tests/unit/tools/` | ツールのユニットテスト |
| `tests/integration/` | 統合テスト |
| `tests/api/` | APIテスト |
| `tests/e2e/` | エンドツーエンドテスト |
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

## テスト実行結果

現在のテスト実行結果は以下の通りです：

- 全テスト: 50/50テスト成功 (100%)
- エージェント関連: 21/21テスト成功 (100%)
- データベース統合: 8/8テスト成功 (100%)
- ワークフロー: 12/12テスト成功 (100%)
- API: 9/9テスト成功 (100%)

## テスト環境の設定

テスト環境の設定には以下のファイルが使用されます：

1. `pytest.ini` - pytestの設定
2. `conftest.py` - テスト共通のフィクスチャとヘルパー関数
3. `tests/data/` - テストで使用するデータファイル

## テスト実行方法

テストを実行するには、以下のコマンドを使用します：

```bash
# すべてのテストを実行
pytest

# 特定のテストファイルを実行
pytest tests/test_agent_a.py

# 特定のテストを実行
pytest tests/test_agent_a.py::TestAgentA::test_analyze_procedure

# カバレッジレポートを生成
pytest --cov=src

# HTMLカバレッジレポートを生成
pytest --cov=src --cov-report=html
```

テスト実行を簡素化するためのスクリプトも用意されています：

```bash
# テスト実行スクリプトを使用
python tests/run_tests.py

# 特定のカテゴリのテストを実行
python tests/run_tests.py --category agents

# 特定のパターンのテストを実行
python tests/run_tests.py --pattern "*agent*"
``` 