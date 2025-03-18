# 統合テスト実施ガイド

このガイドでは、Agent Aノード機能とワークフロー状態管理機能の統合テストの実施方法について説明します。

## 前提条件

- Pythonがインストールされていること（Python 3.10以上推奨）
- 依存パッケージがインストールされていること（requirements.txtを参照）
- テストデータがテスト用ディレクトリに配置されていること

## テスト実行方法

### 基本的な実行コマンド

統合テストを実行するには、プロジェクトのルートディレクトリで以下のコマンドを実行します：

```bash
python tests/integration/run_integration_tests.py
```

### コマンドラインオプション

以下のオプションを指定することで、テストの実行方法をカスタマイズできます：

- `--verbose` または `-v`: 詳細なログを出力します。レベルを指定できます（0: 最小限, 1: 通常, 2: 詳細）
- `--db-type`: データベースタイプを指定します（sqlite_memory, sqlite, postgresql）
- `--test-pattern`: 特定のテストのみを実行する場合、テスト名のパターンを指定します
- `--no-cleanup`: テスト後にテスト用ファイルを削除しない場合に指定します

### データベースタイプの設定

統合テストでは、以下の3種類のデータベース設定が利用可能です：

1. **SQLite（インメモリ）**: デフォルトのデータベース設定です。
   ```bash
   python tests/integration/run_integration_tests.py --db-type sqlite_memory
   ```

2. **SQLite（ファイルベース）**: 実際のSQLiteファイルを使用してテストを実行します。
   ```bash
   python tests/integration/run_integration_tests.py --db-type sqlite
   ```

3. **PostgreSQL**: 実際のPostgreSQLデータベースを使用してテストを実行します（設定が必要）。
   ```bash
   python tests/integration/run_integration_tests.py --db-type postgresql
   ```

   PostgreSQLを使用する場合は、以下の環境変数を設定する必要があります：
   - `INTEGRATION_TEST_DB_HOST`: データベースホスト（デフォルト: localhost）
   - `INTEGRATION_TEST_DB_PORT`: データベースポート（デフォルト: 5432）
   - `INTEGRATION_TEST_DB_NAME`: データベース名（デフォルト: test_db）
   - `INTEGRATION_TEST_DB_USER`: データベースユーザー名（デフォルト: postgres）
   - `INTEGRATION_TEST_DB_PASSWORD`: データベースパスワード

### 詳細なログの取得

テスト実行時の詳細なログを確認するには、`--verbose` オプションを使用します：

```bash
python tests/integration/run_integration_tests.py --verbose 2
```

詳細度レベル：
- レベル 0: エラーと重要な情報のみ
- レベル 1: 基本的なテスト情報
- レベル 2: 詳細なデバッグ情報

### 特定のテストの実行

特定のテストのみを実行する場合は、`--test-pattern` オプションを使用します：

```bash
python tests/integration/run_integration_tests.py --test-pattern test_workflow_state_persistence
```

### テスト環境のカスタマイズ

テスト実行前にテスト環境をカスタマイズする場合は、以下の環境変数を設定できます：

- `INTEGRATION_TEST_WORKFLOW_STATE_DIR`: ワークフロー状態ファイルの格納先ディレクトリ
- `INTEGRATION_TEST_LOG_LEVEL`: ログレベル（DEBUG, INFO, WARNING, ERROR）

## テスト結果の確認

テスト実行後は、以下の形式で結果が出力されます：

```
----------------------------------------------------------------------
Ran X tests in Y.YYYs

OK  # すべてのテストが成功した場合
FAILED (failures=N, errors=M)  # 失敗またはエラーがあった場合
```

また、詳細なログには以下の情報が含まれます：
- テスト環境のセットアップ情報
- 各テストケースの実行状況
- データベース操作の情報
- ワークフロー状態ファイルの操作情報
- クリーンアップ処理の情報

## パフォーマンス比較

各データベース設定でのテスト実行時間の比較（代表的な値）：

- SQLite（インメモリ）: 約0.11秒
- SQLite（ファイルベース）: 約0.15秒
- PostgreSQL: 環境に依存（通常は0.2〜0.5秒程度）

## トラブルシューティング

### よくある問題と解決策

1. **テストデータベースへの接続エラー**
   - 環境変数が正しく設定されているか確認してください
   - データベースサーバーが実行中であることを確認してください
   - ファイアウォール設定を確認してください

2. **ワークフロー状態ディレクトリのアクセス権限エラー**
   - ディレクトリの読み書き権限を確認してください
   - `--no-cleanup` オプションを使用して、ディレクトリの状態を確認してください

3. **テスト実行が遅い場合**
   - 不要なログ出力を減らすために `--verbose 0` を使用してください
   - インメモリSQLiteを使用して実行速度を向上させてください

### ログ分析

問題解決のためのログ分析方法：

1. `--verbose 2` オプションを使用して詳細なログを取得します
2. ログ内の ERROR や WARNING メッセージを探します
3. データベース操作とファイル操作のログを確認します
4. テスト失敗時の前後のログを詳しく分析します

## 次のステップ

より複雑なテストシナリオや拡張機能のテストについては、[TEST_REPORT.md](./TEST_REPORT.md) の「次のステップ」セクションを参照してください。実際の本番環境に近い条件でのテストを実施することが推奨されます。 