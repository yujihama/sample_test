# ワークフロー管理機能

このドキュメントでは、ワークフロー管理機能の使用方法について説明します。

## 概要

ワークフロー管理機能は以下の主要な機能を提供します：

1. **ワークフローリセット**: 特定のワークフローを初期状態に戻す
2. **整合性チェック**: ワークフローとエージェント状態の不整合を検出
3. **自動修復**: 検出された不整合を自動的に修正
4. **データクリーンアップ**: 古いワークフローデータを削除またはアーカイブ

これらの機能により、テスト中や開発時に発生した不整合の解決や、古いテストデータのクリーンアップが容易になります。

## API エンドポイント

### ワークフローリセット

```
POST /api/workflow/{workflow_id}/reset
```

指定したワークフローを初期状態にリセットします。具体的には以下の処理を行います：

- ワークフローの状態を `not_started` に設定
- 現在のエージェントを `null` に設定
- 進捗を `0` に設定
- 既存のエージェント状態をすべて削除
- agent-a の初期状態（`pending`）を作成

#### リクエスト例

```bash
curl -X POST http://localhost:8001/api/workflow/wf_proc_ac30_cfa3/reset
```

#### レスポンス例

```json
{
  "message": "ワークフロー 'wf_proc_ac30_cfa3' がリセットされました",
  "workflow": {
    "id": "wf_proc_ac30_cfa3",
    "status": "not_started",
    "current_agent": null,
    "progress": 0,
    "updated_at": "2025-03-15T17:30:45.123456",
    "previous_states": [
      {
        "id": "8db2ef7f-dfa7-43ab-ad98-6e0b17ab8f33",
        "agent_id": "agent-a",
        "status": "in_progress",
        "progress": 0
      }
    ]
  }
}
```

### 整合性チェック

```
GET /api/workflow/{workflow_id}/check
```

ワークフローとエージェント状態の整合性をチェックし、検出された問題のリストを返します。

#### リクエスト例

```bash
curl http://localhost:8001/api/workflow/wf_proc_ac30_cfa3/check
```

#### レスポンス例

```json
{
  "workflow_id": "wf_proc_ac30_cfa3",
  "issues_count": 1,
  "issues": [
    {
      "timestamp": "2025-03-15T17:31:10.123456",
      "workflow_id": "wf_proc_ac30_cfa3",
      "type": "stalled_agent",
      "description": "ワークフロー 'wf_proc_ac30_cfa3' の agent-a の進捗が0のまま5分以上経過しています",
      "severity": "medium",
      "workflow_status": "in_progress",
      "current_agent": "agent-a",
      "agent_id": "agent-a",
      "expected_status": "progressing",
      "actual_status": "stalled",
      "progress": 0,
      "updated_at": "2025-03-15 07:04:13.954906"
    }
  ]
}
```

### 自動修復

```
POST /api/workflow/{workflow_id}/repair
```

ワークフローの不整合を自動的に修復します。

#### クエリパラメータ

- `repair_type` (任意): 修復するイシューのタイプ（デフォルト: "all"）
- `dry_run` (任意): 実際の変更を行わずに修復計画のみを確認（デフォルト: true）

#### リクエスト例

```bash
# ドライラン（実際の変更なし）
curl -X POST "http://localhost:8001/api/workflow/wf_proc_ac30_cfa3/repair?dry_run=true"

# 実際に修復を実行
curl -X POST "http://localhost:8001/api/workflow/wf_proc_ac30_cfa3/repair?dry_run=false"

# 特定タイプの不整合のみを修復
curl -X POST "http://localhost:8001/api/workflow/wf_proc_ac30_cfa3/repair?repair_type=stalled_agent&dry_run=false"
```

#### レスポンス例

```json
{
  "workflow_id": "wf_proc_ac30_cfa3",
  "repair_type": "all",
  "dry_run": false,
  "repaired_count": 1,
  "repaired_issues": [
    {
      "timestamp": "2025-03-15T17:31:10.123456",
      "workflow_id": "wf_proc_ac30_cfa3",
      "type": "stalled_agent",
      "description": "ワークフロー 'wf_proc_ac30_cfa3' の agent-a の進捗が0のまま5分以上経過しています",
      "severity": "medium",
      "workflow_status": "in_progress",
      "current_agent": "agent-a",
      "agent_id": "agent-a",
      "expected_status": "progressing",
      "actual_status": "stalled",
      "progress": 0,
      "updated_at": "2025-03-15 07:04:13.954906"
    }
  ]
}
```

## コマンドラインユーティリティ

### ワークフロークリーンアップ

古いワークフローデータをクリーンアップするコマンドラインツールが用意されています。

#### 使用方法

```bash
python -m src.utils.cleanup_workflows [オプション]
```

#### オプション

- `--days DAYS`: 何日前より古いデータを対象とするか（デフォルト: 30日）
- `--status STATUS`: 特定のステータスのワークフローのみ処理（例: completed, failed）
- `--no-archive`: アーカイブを作成せずに削除する
- `--archive-dir DIR`: アーカイブディレクトリのパス（デフォルト: archives）
- `--execute`: 実際に変更を適用する（指定しない場合はドライラン）

#### 使用例

```bash
# 30日以上前のワークフローをリストアップ（ドライラン）
python -m src.utils.cleanup_workflows

# 7日以上前の完了済みワークフローを削除（実行）
python -m src.utils.cleanup_workflows --days 7 --status completed --execute

# 14日以上前の失敗したワークフローをアーカイブせずに削除（実行）
python -m src.utils.cleanup_workflows --days 14 --status failed --no-archive --execute

# カスタムディレクトリにアーカイブを作成
python -m src.utils.cleanup_workflows --archive-dir ./data/workflow_archives --execute
```

## プログラムでの利用

### ワークフロー整合性チェック

```python
from src.utils.workflow_manager import check_workflow_consistency
from src.utils.db_manager import session_scope

# 特定のワークフローの整合性をチェック
with session_scope() as db:
    issues = check_workflow_consistency(db, "wf_proc_ac30_cfa3")
    
    if issues:
        print(f"{len(issues)}件の問題が見つかりました:")
        for issue in issues:
            print(f"- {issue['type']}: {issue['description']}")
    else:
        print("問題は見つかりませんでした")

# 全ワークフローの整合性をチェック
with session_scope() as db:
    all_issues = check_workflow_consistency(db)
    print(f"合計 {len(all_issues)}件の問題が見つかりました")
```

### 自動修復

```python
from src.utils.workflow_manager import auto_repair_workflows
from src.utils.db_manager import session_scope

# ドライラン（変更なし）
with session_scope() as db:
    count, issues = auto_repair_workflows(db, workflow_id="wf_proc_ac30_cfa3", dry_run=True)
    print(f"{count}件の問題を修復できます")

# 実際に修復を実行
with session_scope() as db:
    count, issues = auto_repair_workflows(db, workflow_id="wf_proc_ac30_cfa3", dry_run=False)
    print(f"{count}件の問題を修復しました")
    
# 特定タイプの問題のみを修復
with session_scope() as db:
    count, issues = auto_repair_workflows(
        db, 
        repair_type="stalled_agent", 
        workflow_id="wf_proc_ac30_cfa3", 
        dry_run=False
    )
    print(f"{count}件の停滞エージェント問題を修復しました")
```

### ワークフローリセット

```python
from src.utils.workflow_manager import reset_workflow
from src.utils.db_manager import session_scope

# ワークフローをリセット
with session_scope() as db:
    result = reset_workflow(db, "wf_proc_ac30_cfa3")
    
    if result:
        print(f"ワークフロー {result['id']} をリセットしました")
        print(f"新しい状態: {result['status']}")
        print(f"以前の状態: {len(result['previous_states'])}件のエージェント状態を削除")
    else:
        print("ワークフローのリセットに失敗しました")
```

## 注意事項

1. **リセット操作の影響**: リセットは元に戻せない操作です。現在のエージェント状態はすべて削除され、ワークフローは初期状態に戻ります。

2. **クリーンアップの永続性**: クリーンアップで削除されたデータは、アーカイブを作成していない場合は復元できません。

3. **整合性チェックの範囲**: 整合性チェックは主にワークフローとエージェント状態の関係に焦点を当てており、データの内容の検証は行いません。

4. **自動修復の制限**: 自動修復は一般的な問題に対応していますが、複雑な状態の不整合を完全に解決できるとは限りません。 