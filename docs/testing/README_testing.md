# コードベース最適化後のテスト手順

このドキュメントでは、コードベース最適化（特にデータベース関連ユーティリティの重複解消とディレクトリ構造の統合）を行った後のテスト手順について説明します。

## 1. テスト環境の準備

テストを実行する前に、以下の準備が必要です：

1. 仮想環境が有効化されていることを確認する
   ```powershell
   # 仮想環境の有効化
   .\venv\Scripts\Activate.ps1
   ```

2. テスト用の依存関係がインストールされていることを確認する
   ```powershell
   pip install pytest pytest-cov mock pytest-asyncio
   ```

## 2. 個別モジュールの単体テスト

### 2.1 バックアップマネージャーのテスト

`backup_manager.py` の機能をテストします：

```powershell
# 単体テストを実行
pytest tests/utils/test_backup_manager.py -v

# カバレッジレポート付きで実行
pytest tests/utils/test_backup_manager.py --cov=src.utils.backup_manager -v
```

### 2.2 DB アダプターのテスト

`db_adapter.py` の機能をテストします：

```powershell
# 単体テストを実行
pytest tests/utils/test_db_adapter.py -v

# カバレッジレポート付きで実行
pytest tests/utils/test_db_adapter.py --cov=src.utils.db_adapter -v
```

### 2.3 規程情報リポジトリのテスト

`regulation_repository.py` の機能をテストします：

```powershell
# 単体テストを実行
pytest tests/unit/repositories/test_regulation_repository.py -v

# カバレッジレポート付きで実行
pytest tests/unit/repositories/test_regulation_repository.py --cov=src.repositories.regulation_repository -v
```

### 2.4 規程情報サービスのテスト

`regulation_service.py` の機能をテストします：

```powershell
# 単体テストを実行
pytest tests/unit/services/test_regulation_service.py -v

# カバレッジレポート付きで実行
pytest tests/unit/services/test_regulation_service.py --cov=src.services.regulation_service -v
```

### 2.5 規程情報APIのテスト

`regulation_api.py` のRESTful APIエンドポイントをテストします：

```powershell
# API統合テストを実行
pytest tests/api/test_regulation_api.py -v
```

### 2.6 規程情報LangGraphノードのテスト

`regulation_nodes.py` のLangGraphノードをテストします：

```powershell
# 単体テストを実行
pytest tests/unit/core/test_regulation_nodes.py -v

# カバレッジレポート付きで実行
pytest tests/unit/core/test_regulation_nodes.py --cov=src.core.regulation_nodes -v
```

### 2.7 非推奨化された `db_migration.py` のテスト

非推奨警告が正しく表示されることをテストします：

```powershell
pytest tests/utils/test_db_migration.py -v
```

## 3. エージェントテスト

各エージェントの機能をテストします：

```powershell
# エージェントAのテスト
pytest tests/test_agent_a.py -v

# エージェントBのテスト
pytest tests/test_agent_b.py -v

# エージェントCのテスト
pytest tests/test_agent_c.py -v

# エージェントDのテスト
pytest tests/test_agent_d.py -v

# エージェント間通信のテスト
pytest tests/test_agent_communication.py -v
```

## 4. 統合テスト

システム全体の統合テストを実行します：

```powershell
# リポジトリレイヤーのテスト
pytest tests/test_repositories.py -v

# ワークフロー全体の統合テスト
pytest tests/test_workflow.py -v

# API統合テスト
pytest tests/test_api_client.py -v

# 監査証跡機能のテスト
pytest tests/test_audit_trail.py -v

# ヒューマンインタラクションのテスト
pytest tests/test_human_intervention.py -v
```

## 5. 全テストの実行

すべてのテストを一度に実行するには：

```powershell
# すべてのテストを実行
pytest

# カバレッジレポート付きで実行
pytest --cov=src

# HTMLカバレッジレポートの生成
pytest --cov=src --cov-report=html
```

## 6. テスト実行スクリプトの使用

テストをより簡単に実行するために、`run_tests.py` スクリプトが用意されています：

```powershell
# すべてのテストを実行
python tests/run_tests.py

# 特定のカテゴリのテストを実行
python tests/run_tests.py --category agents

# 特定のテストパターンを実行
python tests/run_tests.py --pattern "*agent*"
```

## 7. よくあるトラブルシューティング

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

## 8. 次のステップ

1. 非推奨モジュールの使用状況を監視
2. アプリケーションコードを徐々に新しいモジュールを使用するように更新
3. 非推奨モジュールを削除する時期を計画（3ヶ月後を目安）
4. 全体的なテスト戦略を見直し、テストカバレッジを向上
5. 規程情報管理機能のさらなるテスト拡充（シナリオベースのエンドツーエンドテスト）