# トラブルシューティングガイド

## 概要
このガイドでは、内部監査サンプルデータ自動テストAIエージェントシステムを使用中に発生する可能性のある一般的な問題とその解決策を説明します。

## システム起動の問題

### サーバーが起動しない
**症状**: `python -m src.main`コマンドを実行してもサーバーが起動しない

**解決策**:
1. 環境変数の設定を確認
   ```powershell
   $env:PYTHONPATH = $PWD  # プロジェクトルートを設定
   ```

2. 依存パッケージのインストール確認
   ```powershell
   pip install -r requirements.txt
   ```

3. ポートの競合がないか確認
   ```powershell
   netstat -ano | findstr 8001
   ```

### モジュールインポートエラー
**症状**: `ModuleNotFoundError: No module named 'src'`のようなエラーが表示される

**解決策**:
1. 正しいディレクトリにいるか確認
   ```powershell
   pwd  # プロジェクトルートディレクトリに移動
   ```

2. PYTHONPATHの設定
   ```powershell
   $env:PYTHONPATH = $PWD
   ```

## ワークフロー実行の問題

### ワークフローが開始されない
**症状**: ワークフローを作成しても処理が開始されない

**解決策**:
1. ワークフローのステータスを確認
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8001/api/workflows/{workflow_id}" -Method Get
   ```

2. ログを確認
   ```powershell
   Get-Content -Path "./logs/app.log" -Tail 50
   ```

3. データベースの状態を確認
   ```powershell
   python -c "import sqlite3; conn = sqlite3.connect('./data/db/audit_agent_new.db'); cursor = conn.cursor(); cursor.execute('SELECT status FROM workflows WHERE workflow_id = \'{workflow_id}\''); print(cursor.fetchone()); conn.close()"
   ```

### エージェントがエラーを報告する
**症状**: ワークフロー実行中にエージェントがエラーを報告する

**解決策**:
1. エラーの詳細を確認
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8001/api/workflows/{workflow_id}/errors" -Method Get
   ```

2. エラーに応じた対応:
   - **レート制限エラー**: しばらく待って再試行
   - **トークン制限エラー**: 監査手続きやデータ量を削減
   - **認証エラー**: API設定を確認
   - **その他**: ログで詳細を確認し、開発者に報告

### ワークフローが一時停止状態のまま
**症状**: ワークフローが`paused`状態のままで再開しない

**解決策**:
1. 一時停止の原因を確認
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8001/api/workflows/{workflow_id}" -Method Get
   ```

2. 手動で再開する
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:8001/api/workflows/{workflow_id}/resume" -Method Post
   ```

## LLM関連の問題

### LLMのレスポンスが遅い
**症状**: エージェントの処理に通常よりも時間がかかる

**解決策**:
1. LLMサービスのステータスを確認
2. ネットワーク接続を確認
3. プロンプトのサイズを削減
4. バックアップのLLMプロバイダーに切り替え

### LLMから不適切なレスポンス
**症状**: LLMからの出力が期待通りでない、または形式が不正

**解決策**:
1. プロンプトテンプレートを確認
2. 出力形式の制約を強化
3. LLM温度パラメータを調整（低い値に設定）

## データ関連の問題

### データベース接続エラー
**症状**: データベースに接続できない

**解決策**:
1. データベースファイルの存在を確認
   ```powershell
   Test-Path "./data/db/audit_agent_new.db"
   ```

2. 権限を確認
   ```powershell
   icacls "./data/db/audit_agent_new.db"
   ```

3. 必要に応じてデータベースを再初期化
   ```powershell
   python -m src.utils.db_init
   ```

### サンプルデータが見つからない
**症状**: サンプルデータが見つからないというエラーが表示される

**解決策**:
1. データソースの設定を確認
2. サンプルデータファイルの存在を確認
3. データ取得ロジックのデバッグ

## 高度なトラブルシューティング

### システムの強制リセット
システムが回復不能な状態になった場合のリセット方法:

```powershell
# サーバーを停止
# Ctrl+Cでサーバープロセスを停止

# データベースをリセット
Remove-Item "./data/db/audit_agent_new.db"
python -m src.utils.db_init

# サーバーを再起動
$env:PYTHONPATH = $PWD
python -m src.main
```

### ログの詳細レベル変更
より詳細なログを取得するための設定:

```powershell
$env:LOG_LEVEL = "DEBUG"
python -m src.main
```

## サポート

問題が解決しない場合は、以下の情報を添えて開発者に連絡してください:
1. 発生した問題の詳細な説明
2. ワークフローID（該当する場合）
3. エラーメッセージのスクリーンショットまたはコピー
4. ログファイル（./logs/app.log）
5. 環境情報（OS、Pythonバージョンなど） 