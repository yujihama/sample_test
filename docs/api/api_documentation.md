# APIエンドポイント一覧

内部監査サンプルデータ自動テストAIエージェントシステムは、以下のRESTful APIエンドポイントを提供しています。

## 1. システム情報

### GET /health
システムのヘルスチェックを行います。

**レスポンス例**:
```json
{
  "status": "ok",
  "timestamp": "2025-03-15T21:53:00.123456Z"
}
```

### GET /version
システムのバージョン情報を取得します。

**レスポンス例**:
```json
{
  "app_name": "内部監査サンプルデータ自動テストAIエージェントシステム",
  "version": "0.1.0",
  "environment": "development"
}
```

## 2. 監査手続き管理

### GET /api/audit-procedures
登録されている監査手続きの一覧を取得します。

**レスポンス例**:
```json
{
  "procedures": [
    {
      "id": "proc-001",
      "title": "購買取引の承認プロセス検証",
      "created_at": "2025-03-14T10:30:00Z",
      "updated_at": "2025-03-14T10:30:00Z"
    },
    ...
  ],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

### GET /api/audit-procedures/{procedure_id}
特定の監査手続きの詳細を取得します。

**レスポンス例**:
```json
{
  "id": "proc-001",
  "title": "購買取引の承認プロセス検証",
  "description": "購買取引が正しく承認されているか検証します。",
  "risk_areas": ["購買", "内部統制"],
  "required_data_fields": ["取引ID", "金額", "承認者", "承認日"],
  "created_at": "2025-03-14T10:30:00Z",
  "updated_at": "2025-03-14T10:30:00Z"
}
```

### POST /api/audit-procedures
新しい監査手続きを登録します。

**リクエスト例**:
```json
{
  "title": "購買取引の承認プロセス検証",
  "description": "購買取引が正しく承認されているか検証します。",
  "risk_areas": ["購買", "内部統制"],
  "required_data_fields": ["取引ID", "金額", "承認者", "承認日"]
}
```

**レスポンス例**:
```json
{
  "status": "success",
  "message": "監査手続き '購買取引の承認プロセス検証' が正常に作成されました",
  "procedure_id": "proc-001"
}
```

## 3. サンプルデータ管理

### GET /api/samples
登録されているサンプルデータの一覧を取得します。

**レスポンス例**:
```json
{
  "samples": [
    {
      "id": "sample-001",
      "procedure_id": "proc-001",
      "filename": "購買取引データ_2024年1月.csv",
      "row_count": 1250,
      "created_at": "2025-03-14T11:30:00Z"
    },
    ...
  ],
  "total": 5,
  "page": 1,
  "page_size": 20
}
```

### POST /api/upload-sample
新しいサンプルデータをアップロードします。

**リクエスト例**:
マルチパートフォームデータとして、以下のパラメータを送信します：
- `procedure_id`: 関連する監査手続きID
- `file`: アップロードするファイル

**レスポンス例**:
```json
{
  "status": "success",
  "message": "ファイル '購買取引データ_2024年1月.csv' が正常にアップロードされました",
  "sample_id": "sample-001",
  "procedure_id": "proc-001"
}
```

## 4. ワークフロー管理

### POST /api/start-workflow
新しいワークフローを作成して実行を開始します。

**リクエストパラメータ**:
- `procedure_id`: 監査手続きID
- `sample_id`: サンプルデータID

**レスポンス例**:
```json
{
  "workflow_id": "wf-001",
  "status": "in_progress",
  "message": "新しいワークフローが正常に開始されました"
}
```

### GET /api/workflows
すべてのワークフローの一覧を取得します。

**クエリパラメータ**:
- `procedure_id`: 監査手続きIDでフィルタリング（オプション）
- `sample_id`: サンプルデータIDでフィルタリング（オプション）
- `status`: ステータスでフィルタリング（オプション）
- `agent_id`: 特定のエージェントに関連するワークフローでフィルタリング（オプション）
- `start_date`: この日付以降に開始されたワークフローでフィルタリング（YYYY-MM-DD形式）
- `end_date`: この日付以前に開始されたワークフローでフィルタリング（YYYY-MM-DD形式）
- `sort_by`: ソートするフィールド（started_at, updated_at, status, progress）
- `sort_order`: ソート順（asc, desc）
- `skip`: スキップするレコード数（ページネーション用）
- `limit`: 取得するレコードの最大数（ページネーション用）

**レスポンス例**:
```json
{
  "workflows": [
    {
      "id": "wf-001",
      "procedure_id": "proc-001",
      "sample_id": "sample-001",
      "status": "in_progress",
      "current_agent": "agent-b",
      "progress": 45,
      "started_at": "2025-03-15T12:00:00Z",
      "updated_at": "2025-03-15T12:05:30Z",
      "agents": [
        {
          "agent_id": "agent-a",
          "status": "completed",
          "progress": 100
        },
        {
          "agent_id": "agent-b",
          "status": "in_progress",
          "progress": 45
        }
      ]
    },
    ...
  ],
  "total": 3,
  "skip": 0,
  "limit": 20
}
```

### GET /api/workflow/{workflow_id}
特定のワークフローの詳細と状態を取得します。

**パスパラメータ**:
- `workflow_id`: 取得するワークフローのID（必須）

**エラーレスポンス**:
- `404 Not Found`: 指定されたIDのワークフローが存在しない場合
- `500 Internal Server Error`: サーバー内部エラーが発生した場合

**レスポンス例**:
```json
{
  "id": "wf-001",
  "procedure_id": "proc-001",
  "sample_id": "sample-001",
  "status": "in_progress",
  "current_agent": "agent-b",
  "progress": 45,
  "started_at": "2025-03-15T12:00:00Z",
  "updated_at": "2025-03-15T12:05:30Z",
  "completed_at": null,
  "agent_states": [
    {
      "id": "state-001",
      "agent_id": "agent-a",
      "status": "completed",
      "progress": 100
    },
    {
      "id": "state-002",
      "agent_id": "agent-b",
      "status": "in_progress",
      "progress": 45
    }
  ]
}
```

### GET /api/workflow
ワークフローの一覧を取得します。

**クエリパラメータ**:
- `status`: 特定のステータスのワークフローのみを取得（オプション）
- `limit`: 取得するワークフロー数の上限（デフォルト: 10）

**レスポンス例**:
```json
[
  {
    "id": "wf-001",
    "procedure_id": "proc-001",
    "status": "in_progress",
    "current_agent": "agent-b",
    "progress": 45,
    "started_at": "2025-03-15T12:00:00Z"
  },
  {
    "id": "wf-002",
    "procedure_id": "proc-002",
    "status": "completed",
    "current_agent": null,
    "progress": 100,
    "started_at": "2025-03-14T10:30:00Z"
  }
]
```

### POST /api/workflow/{workflow_id}/reset
ワークフローをリセットします。現在の状態をリセットし、最初から再開できる状態にします。

**パスパラメータ**:
- `workflow_id`: リセットするワークフローのID（必須）

**エラーレスポンス**:
- `404 Not Found`: 指定されたIDのワークフローが存在しない場合
- `500 Internal Server Error`: リセット処理中にエラーが発生した場合

**レスポンス例**:
```json
{
  "workflow_id": "wf-001",
  "status": "reset",
  "message": "Workflow wf-001 has been reset"
}
```

### DELETE /api/workflow/{workflow_id}
ワークフローを削除します。関連するすべてのデータも削除されます。

**パスパラメータ**:
- `workflow_id`: 削除するワークフローのID（必須）

**エラーレスポンス**:
- `404 Not Found`: 指定されたIDのワークフローが存在しない場合
- `500 Internal Server Error`: 削除処理中にエラーが発生した場合

**レスポンス例**:
```json
{
  "workflow_id": "wf-001",
  "status": "deleted",
  "message": "Workflow wf-001 has been deleted"
}
```

## 5. 人間監査人とのインタラクション

### GET /workflow/intervention/pending
保留中の人間監査人介入要求の一覧を取得します。

**クエリパラメータ**:
- `limit`: 取得する最大件数 (デフォルト: 10、最小: 1、最大: 100)

**レスポンス例**:
```json
[
  {
    "intervention_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "workflow_id": "wf-001",
    "requesting_agent": "agent-b",
    "intervention_type": "question",
    "title": "異常値の承認依頼",
    "description": "通常範囲を大幅に超える値が検出されました。処理を続行してよいですか？",
    "options": ["承認する", "拒否する", "追加情報が必要"],
    "created_at": "2025-03-16T10:15:30Z",
    "priority": "high"
  },
  {
    "intervention_id": "b2c3d4e5-f6g7-8901-bcde-f12345678901",
    "workflow_id": "wf-002",
    "requesting_agent": "agent-a",
    "intervention_type": "information_request",
    "title": "データの解釈に関する質問",
    "description": "この取引の性質について判断が困難です。追加情報が必要です。",
    "created_at": "2025-03-16T11:20:45Z",
    "priority": "normal"
  }
]
```

### POST /workflow/intervention/{intervention_id}/respond
人間監査人介入要求に対して応答します。

**URLパラメータ**:
- `intervention_id`: 介入要求ID

**リクエスト例**:
```json
{
  "response_data": {
    "decision": "approve",
    "comments": "検証済みのため承認します",
    "additional_info": {
      "verified_by": "山田太郎",
      "verification_date": "2025-03-17"
    }
  },
  "notes": "特に問題なし"
}
```

**レスポンス例**:
```json
{
  "status": "success",
  "message": "Response to intervention a1b2c3d4-e5f6-7890-abcd-ef1234567890 has been recorded",
  "intervention_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### POST /workflow/intervention/{intervention_id}/cancel
人間監査人介入要求をキャンセルします。

**URLパラメータ**:
- `intervention_id`: 介入要求ID

**レスポンス例**:
```json
{
  "status": "success",
  "message": "Intervention a1b2c3d4-e5f6-7890-abcd-ef1234567890 has been cancelled",
  "intervention_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

## 6. 結果取得

### GET /api/results/{workflow_id}
ワークフローの実行結果を取得します。

**レスポンス例**:
```json
{
  "workflow_id": "wf-001",
  "status": "completed",
  "summary": {
    "total_tests": 10,
    "passed": 7,
    "failed": 2,
    "warnings": 1
  },
  "findings": [
    {
      "id": "finding-001",
      "title": "承認者不在の取引",
      "description": "5件の取引で承認者が設定されていません",
      "risk_level": "high",
      "affected_records": 5
    },
    {
      "id": "finding-002",
      "title": "異常な取引金額",
      "description": "3件の取引で通常の3倍以上の金額が検出されました",
      "risk_level": "medium",
      "affected_records": 3
    }
  ],
  "results": [...]
}
```

### GET /api/workflows/{workflow_id}/report
ワークフローの最終報告書を取得します。

**レスポンス例**:
```json
{
  "workflow_id": "wf-001",
  "report_id": "report-001",
  "report_url": "/reports/report-001.pdf",
  "report_data": {
    "title": "購買取引の承認プロセス監査結果",
    "executive_summary": "...",
    "sections": [...],
    "findings_summary": [...],
    "recommendations": [...],
    "conclusion": "..."
  }
}
```

## 7. システム管理

### GET /api/workflow/{workflow_id}/check
ワークフローと関連エージェントの状態の整合性をチェックします。

**レスポンス例**:
```json
{
  "workflow_id": "wf-001",
  "issues_count": 2,
  "issues": [
    {
      "issue_type": "agent_state_mismatch",
      "description": "ワークフローは進行中ですが、現在のエージェント (agent-b) の状態が見つかりません",
      "severity": "high"
    },
    {
      "issue_type": "orphaned_data",
      "description": "このワークフローに紐づいていないメッセージが3件あります",
      "severity": "medium"
    }
  ]
}
```

### POST /api/workflow/{workflow_id}/repair
ワークフローの不整合を自動修復します。

**リクエストパラメータ**:
- `repair_type`: 修復するイシューのタイプ (default: "all")
- `dry_run`: 実際の変更を行わない (default: true)

**レスポンス例**:
```json
{
  "workflow_id": "wf-001",
  "repair_type": "all",
  "dry_run": false,
  "repaired_count": 2,
  "repaired_issues": [
    {
      "issue_type": "agent_state_mismatch",
      "description": "agent-b の状態を作成し、ワークフローに関連付けました",
      "success": true
    },
    {
      "issue_type": "orphaned_data",
      "description": "3件の孤立したメッセージをワークフローに関連付けました",
      "success": true
    }
  ]
}
``` 