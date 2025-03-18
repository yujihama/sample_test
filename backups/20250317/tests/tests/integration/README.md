# 統合テスト

## 概要

このディレクトリには、Agent Aノード機能とワークフロー状態管理機能の統合テストが含まれています。
統合テストは、実際のデータベース操作とファイルシステム操作を含む、システム全体の機能を検証するためのものです。

## 利用可能なドキュメント

- [**TEST_GUIDE.md**](./TEST_GUIDE.md): 統合テストの実施方法に関する詳細なガイド
- [**TEST_REPORT.md**](./TEST_REPORT.md): 統合テスト結果のレポート

## テストの主な機能

- **ワークフロー状態の管理**: ワークフロー状態の保存、読み込み、圧縮、展開、クリーンアップのテスト
- **Agent Aノード機能**: データベース操作を含むAgent Aノードの機能テスト
- **エラーハンドリング**: 異常系のテストとエラー処理の検証
- **データベース連携**: 各種データベース（SQLite、PostgreSQL）との連携テスト

## クイックスタート

統合テストを実行するには、プロジェクトのルートディレクトリから以下のコマンドを実行します：

```bash
# デフォルト設定（インメモリSQLite）でテストを実行
python tests/integration/run_integration_tests.py

# ファイルベースSQLiteでテストを実行
python tests/integration/run_integration_tests.py --db-type sqlite

# 詳細なログを出力
python tests/integration/run_integration_tests.py --verbose 2
```

詳細な実行方法については [TEST_GUIDE.md](./TEST_GUIDE.md) を参照してください。 