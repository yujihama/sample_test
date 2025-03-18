# 初めてのユーザー向けガイド

## 概要

内部監査サンプルデータ自動テストAIエージェントシステムへようこそ。このガイドでは、システムの基本的な使い方を説明します。

## 前提条件

- システムがインストールされ、起動していること
- 必要な権限が付与されていること

## 基本的な利用フロー

内部監査サンプルデータ自動テストAIエージェントシステムの基本的な利用フローは以下の通りです：

1. 監査手続きを登録する
2. サンプルデータを用意する
3. ワークフローを開始する
4. 結果を確認する

以下では、各ステップの詳細を説明します。

## 1. 監査手続きの登録

### APIを使用して登録する場合

```powershell
$procedureRequest = @{
  title = "購買取引の承認プロセス検証"
  description = "購買取引が正しく承認されているか検証します。"
  procedure_text = "購買取引の承認プロセスが正しく実行されているかを確認する。特に高額取引（10万円以上）については、適切な権限を持つ承認者によって承認されているかを検証する。"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/procedures" -Method Post -Body $procedureRequest -ContentType "application/json"
```

### レスポンス例

```json
{
  "procedure_id": "proc-001",
  "status": "created",
  "message": "監査手続きが正常に登録されました。"
}
```

## 2. サンプルデータの準備

### サンプルデータの形式

サンプルデータは、CSVやJSON形式で準備します。以下は購買取引データの例です：

**purchases.csv**:
```csv
transaction_id,date,amount,item,department,requestor,approver,approval_date
1001,2024-01-05,50000,オフィス備品,総務部,山田太郎,佐藤次郎,2024-01-06
1002,2024-01-10,120000,IT機器,IT部,鈴木花子,高橋一郎,2024-01-12
1003,2024-01-15,30000,消耗品,営業部,伊藤誠,中村洋子,2024-01-15
1004,2024-01-20,200000,サーバー機器,IT部,渡辺和子,NULL,NULL
...
```

### APIを使用してサンプルデータを登録する場合

```powershell
$sampleForm = @{
  title = "購買取引データ 2024年1月"
  data_source = "purchases_db"
  description = "2024年1月の購買取引データ"
}

Invoke-RestMethod -Uri "http://localhost:8001/api/samples" -Method Post -Form $sampleForm -InFile "purchases.csv"
```

### レスポンス例

```json
{
  "sample_id": "sample-001",
  "status": "uploaded",
  "record_count": 1250,
  "message": "サンプルデータが正常に登録されました。"
}
```

## 3. ワークフローの開始

登録した監査手続きとサンプルデータを使用して、監査ワークフローを開始します。

### APIを使用してワークフローを開始する場合

```powershell
$workflowRequest = @{
  procedure_id = "proc-001"
  sample_id = "sample-001"
  procedure_text = "購買取引の承認プロセスが正しく実行されているかを確認する。特に高額取引（10万円以上）については、適切な権限を持つ承認者によって承認されているかを検証する。"
  data_source = "purchases_db"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8001/api/workflows" -Method Post -Body $workflowRequest -ContentType "application/json"

# 作成されたワークフローのIDを取得
$workflowId = $response.workflow_id
```

### レスポンス例

```json
{
  "workflow_id": "wf-001",
  "status": "started",
  "message": "ワークフローを開始しました。"
}
```

## 4. ワークフロー状態の確認

ワークフローの状態を確認します。

### APIを使用してワークフロー状態を確認する場合

```powershell
Invoke-RestMethod -Uri "http://localhost:8001/api/workflows/$workflowId" -Method Get
```

### レスポンス例

```json
{
  "workflow_id": "wf-001",
  "procedure_id": "proc-001",
  "sample_id": "sample-001",
  "status": "running",
  "current_agent": "agent_b",
  "progress": {
    "agent_a": "completed",
    "agent_b": "running",
    "agent_c": "pending",
    "agent_d": "pending"
  },
  "created_at": "2025-03-15T12:00:00Z",
  "updated_at": "2025-03-15T12:05:30Z",
  "error": null
}
```

## 5. 結果の取得

ワークフローが完了したら、結果を取得します。

### APIを使用して結果を取得する場合

```powershell
Invoke-RestMethod -Uri "http://localhost:8001/api/workflows/$workflowId/results" -Method Get
```

### レスポンス例（一部抜粋）

```json
{
  "workflow_id": "wf-001",
  "status": "completed",
  "results": {
    "agent_b_output": {
      "test_results": {
        "items": [
          {
            "test_id": "test-001",
            "description": "高額取引（10万円以上）の承認確認",
            "status": "failed",
            "anomalies": [
              {
                "transaction_id": "1004",
                "description": "承認者がいない高額取引",
                "severity": "high"
              }
            ]
          }
        ]
      }
    },
    "agent_c_output": {
      "evaluation": {
        "findings": [
          {
            "finding_id": "finding-001",
            "description": "高額取引の未承認が検出されました",
            "risk_level": "high",
            "impact": "財務リスクの増加、不正の可能性"
          }
        ]
      }
    }
  }
}
```

## 6. 報告書の取得

最終的な監査報告書を取得します。

### APIを使用して報告書を取得する場合

```powershell
Invoke-RestMethod -Uri "http://localhost:8001/api/workflows/$workflowId/report" -Method Get
```

### PDF形式でダウンロードする場合

```powershell
Invoke-WebRequest -Uri "http://localhost:8001/reports/report-$workflowId.pdf" -OutFile "audit_report.pdf"
```

## 次のステップ

- [ワークフロー実行の詳細](./workflow_execution.md)を確認する
- [トラブルシューティング](./troubleshooting.md)方法を学ぶ
- より複雑な監査手続きを登録して実行する 