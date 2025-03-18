# データベースモデル構造

このドキュメントでは、内部監査サンプルデータ自動テストAIエージェントシステムで使用されるデータベースモデルの構造について説明します。

## エンティティ関連図（ER図）の概要

システムは以下の主要エンティティで構成されています：

```
+------------------+     +----------------+     +----------------+
| AuditProcedure   |<--->| Workflow      |<--->| SampleData     |
+------------------+     +----------------+     +----------------+
         ^                      ^
         |                      |
         v                      v
+------------------+     +----------------+
| HumanIntervention|     | AgentState     |
| Request          |     +----------------+
+------------------+            ^
         ^                      |
         |                      v
         v                +----------------+
+------------------+      | AuditResult    |
| HumanIntervention|      +----------------+
| Response         |
+------------------+
```

## エンティティの詳細

### AuditProcedure（監査手続き）
監査手続きに関する情報を管理します。

**テーブル名**: `audit_procedures`

| フィールド名 | データ型 | 説明 |
|------------|---------|------|
| id | String(36) | 主キー、UUID |
| title | String(255) | 監査手続きのタイトル |
| description | Text | 監査手続きの詳細説明 |
| risk_areas | JSON | リスク領域（JSON配列） |
| required_data_fields | JSON | 必要なデータフィールド（JSON配列） |
| created_at | DateTime | 作成日時 |
| updated_at | DateTime | 更新日時 |

**関連エンティティ**:
- `samples`: SampleDataへのone-to-many関係
- `workflows`: WorkflowへのOne-to-many関係

### SampleData（サンプルデータ）
監査対象のサンプルデータに関する情報を管理します。

**テーブル名**: `sample_data`

| フィールド名 | データ型 | 説明 |
|------------|---------|------|
| id | String(36) | 主キー、UUID |
| procedure_id | String(36) | 外部キー、監査手続きID |
| filename | String(255) | ファイル名 |
| file_path | String(512) | ファイルパス |
| content_type | String(100) | ファイルのコンテンツタイプ |
| row_count | Integer | 行数 |
| columns | JSON | カラム情報（JSON配列） |
| file_metadata | JSON | その他のメタデータ |
| created_at | DateTime | 作成日時 |

**関連エンティティ**:
- `audit_procedure`: AuditProcedureへのMany-to-one関係
- `workflows`: WorkflowへのOne-to-many関係

### Workflow（ワークフロー）
監査手続きとサンプルデータの組み合わせを表し、ワークフローの進行状況を追跡します。

**テーブル名**: `workflows`

| フィールド名 | データ型 | 説明 |
|------------|---------|------|
| id | String | 主キー、"flow-{uuid}" |
| audit_procedure_id | String | 外部キー、監査手続きID |
| sample_data_id | String | 外部キー、サンプルデータID |
| status | String | ワークフローの状態 |
| current_agent | String | 現在のアクティブエージェント |
| created_at | DateTime | 作成日時 |
| updated_at | DateTime | 更新日時 |
| last_activity | DateTime | 最後のアクティビティ時間 |
| completion_percentage | Float | 完了率（0〜100） |
| error_details | JSON | エラー詳細（存在する場合） |

**関連エンティティ**:
- `audit_procedure`: AuditProcedureへのMany-to-one関係
- `sample_data`: SampleDataへのMany-to-one関係
- `agent_states`: AgentStateへのOne-to-many関係
- `results`: AuditResultへのOne-to-many関係
- `messages`: MessageへのOne-to-many関係
- `work_items`: WorkItemへのOne-to-many関係
- `audit_trails`: AuditTrailへのOne-to-many関係
- `agent_decisions`: AgentDecisionへのOne-to-many関係
- `human_intervention_requests`: HumanInterventionRequestへのOne-to-many関係
- `message_logs`: MessageLogへのOne-to-many関係

### AgentState（エージェント状態）
エージェントの状態を管理します。

**テーブル名**: `agent_states`

| フィールド名 | データ型 | 説明 |
|------------|---------|------|
| id | String(36) | 主キー、UUID |
| workflow_id | String(36) | 外部キー、ワークフローID |
| agent_id | String(50) | エージェント識別子 |
| status | String(50) | 状態（not_started, in_progress, completed, failed） |
| progress | Integer | 進捗率（0-100） |
| context | JSON | エージェントのコンテキスト情報 |
| started_at | DateTime | 開始日時 |
| updated_at | DateTime | 更新日時 |
| completed_at | DateTime | 完了日時 |

**関連エンティティ**:
- `workflow`: WorkflowへのMany-to-one関係

### HumanInterventionRequest（人間監査人介入要求）
エージェントから人間監査人への質問、承認依頼、情報提供依頼などを記録します。

**テーブル名**: `human_intervention_requests`

| フィールド名 | データ型 | 説明 |
|------------|---------|------|
| id | String | 主キー、UUID |
| workflow_id | String | 外部キー、ワークフローID |
| requesting_agent | String | 要求元エージェント |
| intervention_type | String | 介入タイプ（question, approval_request, information_request, escalation など） |
| title | String | タイトル |
| description | Text | 説明 |
| options | JSON | 選択肢（該当する場合） |
| context_data | JSON | 関連するコンテキストデータ |
| priority | String | 優先度（low, normal, high） |
| status | String | 状態（pending, responded, cancelled） |
| created_at | DateTime | 作成日時 |
| updated_at | DateTime | 更新日時 |

**関連エンティティ**:
- `workflow`: WorkflowへのMany-to-one関係
- `responses`: HumanInterventionResponseへのOne-to-many関係

### HumanInterventionResponse（人間監査人介入応答）
人間監査人からの回答を記録します。

**テーブル名**: `human_intervention_responses`

| フィールド名 | データ型 | 説明 |
|------------|---------|------|
| id | String | 主キー、UUID |
| request_id | String | 外部キー、介入要求ID |
| responder | String | 回答者（監査人ID） |
| response_type | String | 回答タイプ（answer, clarification, rejection） |
| content | Text | 回答内容 |
| attachment_urls | JSON | 添付資料のURL |
| comment | Text | コメント |
| created_at | DateTime | 作成日時 |

**関連エンティティ**:
- `request`: HumanInterventionRequestへのMany-to-one関係

## 外部キー制約

システム内の主要な外部キー制約は以下の通りです：

1. `sample_data.procedure_id` → `audit_procedures.id`
2. `workflows.audit_procedure_id` → `audit_procedures.id`
3. `workflows.sample_data_id` → `sample_data.id`
4. `agent_states.workflow_id` → `workflows.id`
5. `human_intervention_requests.workflow_id` → `workflows.id`
6. `human_intervention_responses.request_id` → `human_intervention_requests.id`

## カスケード削除動作

以下のエンティティは関連するワークフローが削除された場合に一緒に削除されるカスケード削除動作が設定されています：

- AgentState
- AuditResult
- Message
- WorkItem
- AuditTrail
- AgentDecision
- HumanInterventionRequest
- MessageLog

特に、`human_intervention_requests`と`human_intervention_responses`テーブルは連鎖的に削除されるよう設計されており、ワークフローの削除時に関連する人間監査人介入要求と応答も同時に削除されます。 