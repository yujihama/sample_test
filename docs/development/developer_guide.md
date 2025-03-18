# 開発者ガイド

## 目次

1. [はじめに](#はじめに)
2. [システム構成](#システム構成)
3. [データベースモデル](#データベースモデル)
4. [人間監査人介入機能](#人間監査人介入機能)
5. [開発環境セットアップ](#開発環境セットアップ)
6. [テスト方法](#テスト方法)

## はじめに

このドキュメントは、内部監査サンプルデータ自動テストAIエージェントシステムの開発者向けガイドです。システムの構成、主要コンポーネント、および開発のためのガイドラインを提供します。

## システム構成

システムは以下の主要コンポーネントで構成されています：

- **APIサーバー** (FastAPI): RESTful APIを提供し、フロントエンドとデータベースの間の通信を管理します。
- **データベース** (SQLite): データ永続化のための軽量データベース。
- **AIエージェント**: 監査作業を自動的に実行するためのエージェント。
- **人間監査人インターフェース**: 人間の監査人が介入するためのインターフェース。

## データベースモデル

詳細なデータベースモデルの説明については、[database_model.md](../database/database_model.md)を参照してください。

主要なエンティティ:
- 監査手続き (AuditProcedure)
- サンプルデータ (SampleData)
- ワークフロー (Workflow)
- エージェント状態 (AgentState)
- 人間監査人介入要求 (HumanInterventionRequest)
- 人間監査人介入応答 (HumanInterventionResponse)

## 人間監査人介入機能

### 概要

人間監査人介入機能は、AIエージェントが処理を進める中で人間の判断やインプットが必要な場合に使用される機能です。この機能を使用することで、AIと人間のハイブリッド監査プロセスが実現します。

### 主要コンポーネント

1. **人間監査人介入要求 (HumanInterventionRequest)**
   - AIエージェントから人間監査人への質問、承認依頼、情報提供依頼などを記録します。
   - 各要求には、タイトル、説明、選択肢、優先度などの情報が含まれます。
   - 状態は「pending」（保留中）、「responded」（回答済み）、「cancelled」（キャンセル）のいずれかです。

2. **人間監査人介入応答 (HumanInterventionResponse)**
   - 人間監査人からの回答を記録します。
   - 応答には、回答者、応答タイプ、内容、添付資料、コメントなどの情報が含まれます。

### API エンドポイント

以下のエンドポイントが人間監査人介入機能に関連しています：

1. **人間監査人への応答**
   - エンドポイント: `POST /workflow/intervention/{intervention_id}/respond`
   - 説明: 人間監査人の介入要求に対して応答します。
   - 必須パラメータ: intervention_id, response_data
   - オプションパラメータ: notes
   
   ```json
   {
     "response_data": {
       "decision": "approve",
       "comments": "検証済みのため承認します",
       "additional_info": {"verified_by": "山田太郎", "verification_date": "2025-03-17"}
     },
     "notes": "特に問題なし"
   }
   ```

2. **人間監査人介入要求のキャンセル**
   - エンドポイント: `POST /workflow/intervention/{intervention_id}/cancel`
   - 説明: 保留中の人間監査人介入要求をキャンセルします。
   - 必須パラメータ: intervention_id

3. **保留中の人間監査人介入要求リスト取得**
   - エンドポイント: `GET /workflow/intervention/pending`
   - 説明: 保留中の人間監査人介入要求の一覧を取得します。
   - クエリパラメータ: limit (最大取得件数)

### 使用方法

#### AIエージェントからの介入要求

人間監査人の介入が必要な場合、`HumanInterventionService`クラスを使用して以下のような機能を利用できます：

1. 質問の送信
   ```python
   async def ask_question(self, workflow_id, requesting_agent, title, description, options=None, context_data=None, priority="normal", pause_workflow_execution=True):
       """人間監査人に質問を送信する"""
       # 質問を作成して送信
   ```

2. 承認依頼の送信
   ```python
   async def request_approval(self, workflow_id, requesting_agent, title, description, item_to_approve, context_data=None, priority="normal", pause_workflow_execution=True):
       """人間監査人に承認を依頼する"""
       # 承認依頼を作成して送信
   ```

3. 情報提供依頼の送信
   ```python
   async def request_information(self, workflow_id, requesting_agent, title, description, required_info, context_data=None, priority="normal", pause_workflow_execution=True):
       """人間監査人に情報提供を依頼する"""
       # 情報提供依頼を作成して送信
   ```

4. 問題報告の送信
   ```python
   async def report_issue(self, workflow_id, requesting_agent, title, description, issue_details, priority="high", pause_workflow_execution=True):
       """人間監査人に問題を報告する"""
       # 問題報告を作成して送信
   ```

5. 応答の待機
   ```python
   async def wait_for_response(self, intervention_id, timeout=None):
       """人間監査人からの応答を待機する"""
       # 応答があるまで待機
   ```

#### 人間監査人による応答

人間監査人が介入要求に応答するプロセス：

1. 保留中の介入要求リストを表示します
   ```
   GET /workflow/intervention/pending
   ```

2. 特定の介入要求に対して応答します
   ```
   POST /workflow/intervention/{intervention_id}/respond
   ```

3. 介入要求をキャンセルします（必要に応じて）
   ```
   POST /workflow/intervention/{intervention_id}/cancel
   ```

### ワークフローの一時停止と再開

介入要求の作成時に `pause_workflow_execution` パラメータを `true` に設定すると、関連するワークフローが一時停止されます。人間監査人の応答が作成されると、保留中の他の介入要求がない場合、ワークフローは自動的に再開されます。

### データベース設計

人間監査人介入機能に関連するデータベーステーブルは次の通りです：

1. `human_intervention_requests`
   - 人間監査人への介入要求を格納するテーブル
   - 主要フィールド: id, workflow_id, requesting_agent, intervention_type, title, description, options, context_data, priority, status, created_at, updated_at
   - ワークフローとの外部キー関連付け

2. `human_intervention_responses`
   - 人間監査人からの応答を格納するテーブル
   - 主要フィールド: id, request_id, responder, response_type, content, attachment_urls, comment, created_at
   - 介入要求との外部キー関連付け

詳細なスキーマについては、データベースモデルドキュメントを参照してください。

## 開発環境セットアップ

### 前提条件

- Python 3.8以上
- pip（Pythonパッケージマネージャー）
- Git

### セットアップ手順

1. リポジトリをクローンします
   ```bash
   git clone <repository-url>
   cd audit-ai-system
   ```

2. 仮想環境を作成し、アクティベートします
   ```bash
   python -m venv venv
   source venv/bin/activate  # LinuxまたはmacOS
   # または
   venv\Scripts\activate  # Windows
   ```

3. 依存関係をインストールします
   ```bash
   pip install -r requirements.txt
   ```

4. データベースを初期化します
   ```bash
   python -m src.utils.db_manager
   ```

5. APIサーバーを起動します
   ```bash
   python -m src.main
   ```

## テスト方法

### 自動テスト

1. すべてのテストを実行します
   ```bash
   python -m src.tests.run_tests
   ```

2. 特定のテストを実行します
   ```bash
   python -m src.tests.test_human_intervention
   ```

### 手動テスト

APIエンドポイントを手動でテストするには、以下の方法があります：

1. curl（コマンドラインツール）を使用する
   ```bash
   curl -X POST "http://localhost:8000/workflow/intervention/int-1234/respond" \
        -H "Content-Type: application/json" \
        -d '{"response_data": {"decision": "approve"}, "notes": "確認済み"}'
   ```

2. Postman（GUIツール）を使用する
   - Postmanをダウンロードしてインストールします
   - 新しいリクエストを作成し、エンドポイントURLとパラメータを設定します
   - リクエストを送信し、レスポンスを確認します

3. Swagger UI（APIドキュメント）を使用する
   - ブラウザで `http://localhost:8000/docs` にアクセスします
   - エンドポイントを選択し、「Try it out」をクリックします
   - パラメータを入力し、「Execute」をクリックします 