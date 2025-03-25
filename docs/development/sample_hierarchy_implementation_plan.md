# サンプル階層導入実装計画

## 1. 概要

### 背景と目的
現在のシステムでは、監査対象データは「バッチ」と「ファイル」の2階層で管理されていますが、関連ファイルのグループ化や、特定のファイル群に対する手続き実行といった要件に対応するために、「サンプル」という中間階層を導入します。

これにより、以下のメリットが実現できます：
- 関連する複数ファイル（例：申請書と領収書）をサンプルとしてグループ化
- サンプル単位での監査手続き実行
- フォルダ単位でのアップロードによる効率的なデータ管理
- 監査結果をサンプル単位で保存・表示

![アーキテクチャ変更](../images/sample_hierarchy_architecture.png)

## 2. システム影響範囲

### 2.1 データベース構造への影響

#### 新規テーブル
```sql
-- サンプルテーブル（バッチとファイルの中間層）
CREATE TABLE samples (
  id VARCHAR(50) PRIMARY KEY,
  batch_id VARCHAR(50) NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  status VARCHAR(20) DEFAULT 'pending',
  file_count INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  metadata JSON,
  FOREIGN KEY (batch_id) REFERENCES sample_batches(id) ON DELETE CASCADE
);

-- サンプル処理結果テーブル
CREATE TABLE sample_results (
  id VARCHAR(50) PRIMARY KEY,
  workflow_id VARCHAR(50) NOT NULL,
  sample_id VARCHAR(50) NOT NULL,
  status VARCHAR(20) DEFAULT 'pending',
  result VARCHAR(20),
  summary TEXT,
  findings JSON,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE,
  FOREIGN KEY (sample_id) REFERENCES samples(id) ON DELETE CASCADE
);

-- バッチアップロードジョブテーブル
CREATE TABLE batch_upload_jobs (
  id VARCHAR(50) PRIMARY KEY,
  batch_id VARCHAR(50) NOT NULL,
  status VARCHAR(20) DEFAULT 'pending',
  total_folders INTEGER DEFAULT 0,
  processed_folders INTEGER DEFAULT 0,
  total_files INTEGER DEFAULT 0,
  processed_files INTEGER DEFAULT 0,
  failed_files INTEGER DEFAULT 0,
  errors JSON,
  started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  estimated_completion TIMESTAMP,
  FOREIGN KEY (batch_id) REFERENCES sample_batches(id) ON DELETE CASCADE
);
```

**実装状況**: ✅ 完了 - SampleBatch、Sample、SampleResult、BatchUploadJobのデータベースモデルとリポジトリクラスが実装されています。

#### 既存テーブル変更
```sql
-- ファイルテーブル：バッチIDからサンプルIDへの参照変更
ALTER TABLE files 
ADD COLUMN sample_id VARCHAR(50),
ADD CONSTRAINT fk_sample FOREIGN KEY (sample_id) REFERENCES samples(id);

-- バッチテーブル：サンプル数カウント追加
ALTER TABLE sample_batches
ADD COLUMN sample_count INTEGER DEFAULT 0;

-- ワークフローテーブル：サンプル処理関連フィールド追加
ALTER TABLE workflows
ADD COLUMN sample_id VARCHAR(50),
ADD CONSTRAINT fk_sample FOREIGN KEY (sample_id) REFERENCES samples(id),
ADD COLUMN is_sample_level BOOLEAN DEFAULT FALSE;
```

**実装状況**: ✅ 完了 - Fileモデルにsample_idフィールドが追加され、SampleBatchモデルにsample_countフィールドが追加されています。

### 2.2 バックエンドAPIへの影響

#### 新規エンドポイント追加
- サンプル管理API
  - `GET /api/sample-batches/{batchId}/samples` ✅ 実装済み
  - `POST /api/sample-batches/{batchId}/samples` ✅ 実装済み
  - `GET /api/sample-batches/{batchId}/samples/{sampleId}` ✅ 実装済み
  - `PUT /api/sample-batches/{batchId}/samples/{sampleId}` ✅ 実装済み
  - `DELETE /api/sample-batches/{batchId}/samples/{sampleId}` ✅ 実装済み

- サンプルファイル管理API
  - `GET /api/sample-batches/{batchId}/samples/{sampleId}/files` ✅ 実装済み
  - `POST /api/sample-batches/{batchId}/samples/{sampleId}/files` ✅ 実装済み
  - `DELETE /api/sample-batches/{batchId}/samples/{sampleId}/files` ✅ 実装済み

- フォルダアップロードAPI
  - `POST /api/sample-batches/upload-folder` ✅ 実装済み
  - `POST /api/sample-batches/create-with-folders` ✅ 実装済み
  - `GET /api/sample-batches/upload-status/{jobId}` ✅ 実装済み

- サンプルレベルワークフローAPI
  - ❌ 要件変更により実装削除 - `POST /api/workflows/{workflowId}/samples/{sampleId}`
  - ❌ 要件変更により実装削除 - `GET /api/workflows/{workflowId}/samples/{sampleId}/results`

#### 既存エンドポイント変更
- `GET /api/sample-batches/{batchId}/files`
  - 内部実装：すべてのサンプルのファイルを集約して返却
  ✅ 実装済み - サンプル経由でファイルを取得する互換レイヤーが実装されています
  
- `POST /api/sample-batches/{batchId}/files`
  - 内部実装：システム生成サンプルにファイルを追加
  ✅ 実装済み - 互換性維持のための内部実装が変更されています
  
- `DELETE /api/sample-batches/{batchId}/files`
  - 内部実装：該当サンプルからファイルを削除
  ✅ 実装済み - 互換性維持のための内部実装が変更されています

- `POST /api/workflows`
  - 内部実装：サンプル階層に対応し、バッチ全体、特定サンプル、個別ファイルなど様々なレベルでの処理を指定可能
  ✅ 実装済み
  ```json
  {
    "audit_procedure_id": "proc-001",
    "target": {
      "type": "batch", // "batch"、"sample"、"file"のいずれか
      "id": "batch-001" // バッチID、サンプルID、またはファイルID
    },
    "procedure_text": "購買取引の承認プロセス検証",
    "config": {
      "process_level": "sample", // "sample"または"file"
      "parallel_processing": true,
      "max_parallel_jobs": 5,
      "target_department": "財務部",
      "detailed_analysis": true
    }
  }
  ```
  
- `GET /api/workflows/{workflow_id}/results`
  - 内部実装：サンプル階層に対応し、対象の処理レベルに応じた結果を階層的に返却
  ✅ 実装済み

#### 既存ワークフローAPI拡張

##### POST /api/workflows （既存エンドポイントの仕様変更）
- **現行仕様**:
  ```json
  // 現行のリクエスト形式
  {
    "audit_procedure_id": "proc-001",
    "sample_data_id": "sample-001",
    "procedure_text": "購買取引の承認プロセス検証",
    "initial_state": "created",
    "config": {
      "audit_type": "regular",
      "target_department": "財務部"
    }
  }
  
  // 現行のレスポンス形式
  {
    "workflow_id": "wf-002",
    "status": "created",
    "created_at": "2025-03-15T10:00:00Z",
    "updated_at": "2025-03-15T10:00:00Z",
    "audit_procedure_id": "proc-001",
    "sample_data_id": "sample-001",
    "message": "ワークフローが正常に作成されました"
  }
  ```

- **新仕様**:
  ```json
  // 新しいリクエスト形式
  {
    "audit_procedure_id": "proc-001",
    "target": {
      "type": "batch", // "batch"、"sample"、"file"のいずれか
      "id": "batch-001" // バッチID、サンプルID、またはファイルID
    },
    "procedure_text": "購買取引の承認プロセス検証",
    "config": {
      "process_level": "sample", // "sample"または"file"
      "parallel_processing": true,
      "max_parallel_jobs": 5,
      "target_department": "財務部",
      "detailed_analysis": true
    }
  }
  
  // 新しいレスポンス形式
  {
    "workflow_id": "wf-002",
    "status": "created",
    "created_at": "2025-03-15T10:00:00Z",
    "updated_at": "2025-03-15T10:00:00Z",
    "audit_procedure_id": "proc-001",
    "target": {
      "type": "batch",
      "id": "batch-001"
    },
    "process_level": "sample",
    "sample_count": 25,
    "message": "ワークフローが正常に作成されました"
  }
  ```

- **主な変更点**:
  1. `sample_data_id` を `target` オブジェクトに置き換え、処理対象を明示的に指定
  2. `process_level` パラメータにより、処理のレベル（サンプル単位/ファイル単位）を制御
  3. バッチ全体を処理する場合の並列処理オプションを追加
  4. サンプル数などの追加情報をレスポンスに含める

- **後方互換性の確保**:
  1. 既存形式のリクエスト（`sample_data_id`指定）も引き続き受け付け
  2. 内部的に既存形式から新形式への変換を実装:
     ```javascript
     // 既存リクエストを新形式に変換する内部処理
     if (req.body.sample_data_id && !req.body.target) {
       req.body.target = {
         type: 'sample',
         id: req.body.sample_data_id
       };
       
       // デフォルト設定
       req.body.config = req.body.config || {};
       req.body.config.process_level = req.body.config.process_level || 'file';
     }
     ```
  3. 非推奨通知ヘッダーの追加:
     ```
     X-API-Deprecated: true
     X-API-Deprecation-Date: 2025-06-30
     X-API-Alternative: Use 'target' object instead of 'sample_data_id'
     ```

- **移行スケジュール**:
  - 2025年4月: 新形式サポート開始、既存形式も継続サポート
  - 2025年6月: 旧形式の非推奨化を開始（警告ヘッダー追加）
  - 2026年1月: 旧形式のサポート終了

##### GET /api/workflows/{workflow_id}/results （既存エンドポイントの仕様変更）
- **現行仕様**:
  ```json
  // 現行のレスポンス形式
  {
    "workflow_id": "wf-001",
    "status": "completed",
    "completion_rate": 1.0,
    "findings": [
      {
        "id": "finding-001",
        "title": "承認者不在の購買取引",
        "description": "3件の購買取引で承認者の記録がありません。",
        "severity": "high",
        "evidence": {
          "transaction_ids": ["tx-1234", "tx-1235", "tx-1236"],
          "file_id": "file-002"
        }
      }
    ],
    "summary": {
      "total_transactions": 1250,
      "compliant_transactions": 1240,
      "non_compliant_transactions": 10,
      "compliance_rate": 0.992
    },
    "created_at": "2025-03-15T08:00:00Z",
    "completed_at": "2025-03-15T12:10:00Z"
  }
  ```

- **新仕様（バッチレベルのワークフロー）**:
  ```json
  {
    "workflow_id": "wf-001",
    "status": "completed",
    "target": {
      "type": "batch",
      "id": "batch-001",
      "name": "2025年度Q1出張費精算書類"
    },
    "process_level": "sample",
    "completion_rate": 1.0,
    "findings": [
      {
        "id": "finding-001",
        "title": "承認者不在の購買取引",
        "description": "3つのサンプルで承認者の記録がありません。",
        "severity": "high",
        "evidence": {
          "sample_ids": ["sample-003", "sample-008", "sample-015"],
          "file_id": "evidence-001"
        }
      }
    ],
    "summary": {
      "total_samples": 25,
      "compliant_samples": 22,
      "non_compliant_samples": 3,
      "compliance_rate": 0.88
    },
    "sample_results": [
      {
        "sample_id": "sample-001",
        "name": "取引No.001",
        "status": "completed",
        "result": "compliant",
        "findings": [],
        "file_count": 3,
        "completed_at": "2025-03-15T11:10:00Z"
      },
      {
        "sample_id": "sample-003",
        "name": "取引No.003",
        "status": "completed",
        "result": "non_compliant",
        "findings": ["finding-001"],
        "file_count": 4,
        "completed_at": "2025-03-15T11:15:00Z"
      }
      // その他のサンプル結果（省略）
    ],
    "created_at": "2025-03-15T08:00:00Z",
    "completed_at": "2025-03-15T12:10:00Z"
  }
  ```

- **新仕様（サンプルレベルのワークフロー）**:
  ```json
  {
    "workflow_id": "wf-005",
    "status": "completed",
    "target": {
      "type": "sample",
      "id": "sample-001",
      "name": "取引No.001"
    },
    "process_level": "file",
    "completion_rate": 1.0,
    "findings": [],
    "summary": {
      "total_files": 3,
      "compliant_files": 3,
      "non_compliant_files": 0,
      "compliance_rate": 1.0
    },
    "file_results": [
      {
        "file_id": "file-050",
        "filename": "出張申請書_田中.pdf",
        "result": "compliant",
        "notes": "必要な承認が得られています。"
      },
      {
        "file_id": "file-051",
        "filename": "領収書_田中.jpg",
        "result": "compliant",
        "notes": "金額と日付が精算書と一致しています。"
      },
      {
        "file_id": "file-052",
        "filename": "精算書_田中.xlsx",
        "result": "compliant",
        "notes": "計算が正確で、適切に承認されています。"
      }
    ],
    "cross_file_analysis": {
      "consistency": "high",
      "relationship_findings": []
    },
    "created_at": "2025-03-15T10:00:00Z",
    "completed_at": "2025-03-15T10:10:00Z"
  }
  ```

- **後方互換性の確保**:
  1. クエリパラメータによる形式選択:
     ```
     GET /api/workflows/{workflow_id}/results?format=legacy
     ```
  2. リクエストヘッダによる形式選択:
     ```
     Accept: application/vnd.audit-api.legacy+json
     ```
  3. ワークフロー作成時の形式に基づく自動選択

- **移行スケジュール**:
  - 2025年4月: 新形式サポート開始、既存形式も継続サポート
  - 2025年7月: 新形式をデフォルトに変更（明示的なフォーマット指定なしの場合）
  - 2026年4月: 旧形式のサポート終了

### 2.3 エージェント処理への影響

#### エージェントAの処理変更
```javascript
// 変更前
async function processFiles(batchId) {
  const files = await getFilesByBatchId(batchId);
  for (const file of files) {
    await processFile(file);
  }
}

// 変更後
async function processSamples(batchId) {
  const samples = await getSamplesByBatchId(batchId);
  for (const sample of samples) {
    await processSample(sample);
  }
}

async function processSample(sample) {
  const files = await getFilesBySampleId(sample.id);
  // ファイル間の関連性を考慮した処理
  await processSampleFiles(files, sample.metadata);
}
```

**実装状況**: ✅ 実装済み - サンプル単位ワークフローAPIが削除されましたが、エージェントでのサンプル処理機能は実装されています。

#### エージェントBでのサンプル処理
エージェントBは監査手続きの具体的な実行を担当するため、サンプル階層導入によって以下の変更が必要になります：

```javascript
// 変更前：ファイル単位での処理
async function executeAuditProcedure(file, procedureId, batchContext) {
  // 単一ファイルに対する監査手続きを実行
  const result = await analyzeFile(file, procedureId);
  return result;
}

// 変更後：サンプル単位での処理
async function executeAuditProcedureOnSample(sample, procedureId, batchContext) {
  // サンプルに含まれる全ファイルを取得
  const files = await getFilesBySampleId(sample.id);
  
  // サンプル内の関連ファイル間の整合性確認
  const crossFileAnalysis = await analyzeCrossFileRelationships(files, sample.metadata);
  
  // 各ファイル個別の分析
  const fileResults = await Promise.all(
    files.map(file => analyzeFile(file, procedureId, { sampleContext: sample }))
  );
  
  // サンプル全体としての結果を集約
  const sampleResult = aggregateSampleResults(fileResults, crossFileAnalysis);
  
  return sampleResult;
}
```

**実装状況**: ✅ 実装済み

#### 複合ドキュメント分析ロジック
サンプル内のファイル間関係性を分析する新しいロジックが必要になります：

```javascript
async function analyzeCrossFileRelationships(files, sampleMetadata) {
  // 例：申請書と領収書の整合性確認
  const applicationForms = files.filter(f => f.file_type === 'application_form');
  const receipts = files.filter(f => f.file_type === 'receipt');
  
  const consistencyResults = [];
  
  // 申請書と領収書の金額・日付の一致確認
  for (const form of applicationForms) {
    const formData = await extractDataFromForm(form);
    
    for (const receipt of receipts) {
      const receiptData = await extractDataFromReceipt(receipt);
      
      const matches = compareFormAndReceipt(formData, receiptData);
      consistencyResults.push({
        form_id: form.id,
        receipt_id: receipt.id,
        matches: matches,
        inconsistencies: matches.inconsistentFields
      });
    }
  }
  
  return {
    consistencyResults,
    overallConsistency: evaluateOverallConsistency(consistencyResults)
  };
}
```

**実装状況**: ✅ 実装済み

#### コンテキスト構築の変更
```javascript
// 変更前
const context = {
  batchId: workflow.batchId,
  procedureId: workflow.procedureId,
  files: files.map(f => ({id: f.id, name: f.filename, type: f.file_type}))
};

// 変更後
const context = {
  batchId: workflow.batchId,
  sampleId: workflow.sampleId,
  procedureId: workflow.procedureId,
  sample: {
    name: sample.name,
    metadata: sample.metadata
  },
  files: files.map(f => ({id: f.id, name: f.filename, type: f.file_type}))
};
```

**実装状況**: ✅ 実装済み

#### 進捗状況管理
```javascript
// 変更前
updateWorkflowProgress(workflowId, processedFiles / totalFiles);

// 変更後
// サンプルレベルの進捗管理
updateSampleProgress(workflowId, sampleId, processedFiles / totalFiles);

// バッチレベルの集約進捗
const sampleProgresses = await getSampleProgresses(workflowId);
const avgProgress = sampleProgresses.reduce((sum, p) => sum + p.progress, 0) / sampleProgresses.length;
updateWorkflowProgress(workflowId, avgProgress);
```

**実装状況**: ✅ 実装済み

#### 監査結果保存
```javascript
// 変更前
await saveWorkflowResults(workflowId, {
  status: 'completed',
  findings: findings,
  file_results: fileResults
});

// 変更後
// サンプルごとの結果保存
await saveSampleResults(workflowId, sampleId, {
  status: 'completed',
  findings: sampleFindings,
  file_results: sampleFileResults
});

// ワークフロー全体の結果集約
const allSampleResults = await getAllSampleResults(workflowId);
const aggregatedResults = aggregateResults(allSampleResults);
await saveWorkflowResults(workflowId, aggregatedResults);
```

**実装状況**: ✅ 実装済み

#### エージェント間通信の変更
サンプル階層の導入により、エージェント間通信においても変更が必要です：

```javascript
// 変更前
// エージェントAからBへの要求
const requestToAgentB = {
  action: "analyze_file",
  file_id: fileId,
  procedure_id: procedureId,
  batch_context: { batch_id: batchId }
};

// 変更後
// エージェントAからBへの要求
const requestToAgentB = {
  action: "analyze_sample",
  sample_id: sampleId,
  procedure_id: procedureId,
  batch_context: { 
    batch_id: batchId,
    sample_metadata: sampleMetadata 
  }
};
```

**実装状況**: ✅ 実装済み

## 3. 移行計画

### 3.1 データマイグレーション

#### ステップ1: スキーマ変更（ダウンタイム必要）
1. 新テーブル作成
2. 既存テーブルのスキーマ変更
3. インデックス作成

**実装状況**: ✅ 完了 - データベースマイグレーションが実施されました

#### ステップ2: 既存データ移行
```sql
-- 一時テーブルの作成（バッチごとにファイルをグループ化）
CREATE TEMPORARY TABLE file_groups AS
SELECT 
  batch_id,
  COALESCE(
    REGEXP_REPLACE(filename, '[\._]\d+\.[^\.]+$', ''),  -- ファイル名からグループ名推測
    'default_group'
  ) AS group_name,
  ARRAY_AGG(id) AS file_ids
FROM files
WHERE batch_id IS NOT NULL
GROUP BY batch_id, group_name;

-- 各グループをサンプルとして登録
INSERT INTO samples (id, batch_id, name, description, status, created_at, updated_at)
SELECT 
  CONCAT('sample-', MD5(CONCAT(batch_id, group_name))),
  batch_id,
  CONCAT('移行サンプル: ', group_name),
  '自動データ移行により作成されたサンプル',
  'processed',
  NOW(),
  NOW()
FROM file_groups;

-- ファイルとサンプルの関連付け
UPDATE files f
SET sample_id = (
  SELECT CONCAT('sample-', MD5(CONCAT(fg.batch_id, fg.group_name)))
  FROM file_groups fg
  WHERE fg.batch_id = f.batch_id 
  AND f.id = ANY(fg.file_ids)
)
WHERE batch_id IS NOT NULL;

-- バッチのサンプル数更新
UPDATE sample_batches sb
SET sample_count = (
  SELECT COUNT(*) FROM samples s WHERE s.batch_id = sb.id
);
```

**実装状況**: ✅ 完了 - 既存データの移行が完了しました

#### ステップ3: 完全性確認
```sql
-- サンプル未割り当てファイルの確認
SELECT COUNT(*) FROM files WHERE batch_id IS NOT NULL AND sample_id IS NULL;

-- サンプルごとのファイル数の確認
SELECT s.id, s.name, COUNT(f.id) as file_count
FROM samples s
LEFT JOIN files f ON f.sample_id = s.id
GROUP BY s.id, s.name;

-- バッチごとのサンプル数の確認
SELECT sb.id, sb.name, sb.sample_count, COUNT(s.id) as actual_sample_count
FROM sample_batches sb
LEFT JOIN samples s ON s.batch_id = sb.id
GROUP BY sb.id, sb.name, sb.sample_count;
```

**実装状況**: ✅ 完了 - データ移行の完全性確認が実施されました

### 3.2 API互換性維持

#### 段階的なAPI移行
1. 旧APIエンドポイントを維持しながら、内部実装を新構造に対応
2. 新APIエンドポイントをリリース
3. 旧APIの非推奨化（廃止予定日の通知）
4. 一定期間後に旧API廃止

**実装状況**: ✅ 完了 - バッチ関連の既存APIエンドポイントは互換性を維持しつつ、内部的には新しいサンプル階層を使用するように実装されています

#### 互換レイヤー実装例
```javascript
// GET /api/sample-batches/{batchId}/files の互換維持
app.get('/api/sample-batches/:batchId/files', async (req, res) => {
  try {
    // 新構造：サンプル経由でファイル取得
    const samples = await getSamplesByBatchId(req.params.batchId);
    const filePromises = samples.map(sample => 
      getFilesBySampleId(sample.id)
    );
    const fileArrays = await Promise.all(filePromises);
    
    // フラット化して旧形式に整形
    const files = fileArrays.flat().map(file => ({
      ...file,
      batch_id: req.params.batchId // 互換性のためにbatch_idを維持
    }));
    
    // 廃止予定通知ヘッダー追加
    res.setHeader('X-API-Deprecated', 'true');
    res.setHeader('X-API-Deprecation-Date', '2025-06-30');
    res.setHeader('X-API-Alternative', '/api/sample-batches/{batchId}/samples and /api/sample-batches/{batchId}/samples/{sampleId}/files');
    
    res.json(files);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

**実装状況**: ✅ 完了 - 互換レイヤーが実装され、既存APIエンドポイントは新しい内部構造を使用しながらも互換性を維持しています

## 4. ブラウザでアクセス可能なエンドポイント一覧

### 実装済みエンドポイント

#### サンプルバッチ管理API
- `GET /api/sample-batches` - サンプルバッチの一覧を取得
- `POST /api/sample-batches` - 新しいサンプルバッチを作成
- `GET /api/sample-batches/{batch_id}` - 指定されたIDのサンプルバッチを取得
- `PUT /api/sample-batches/{batch_id}` - サンプルバッチ情報を更新

#### サンプル管理API
- `GET /api/sample-batches/{batch_id}/samples` - バッチ内のサンプル一覧を取得
- `POST /api/sample-batches/{batch_id}/samples` - バッチに新しいサンプルを作成
- `GET /api/sample-batches/{batch_id}/samples/{sample_id}` - 特定のサンプルの詳細を取得
- `PUT /api/sample-batches/{batch_id}/samples/{sample_id}` - サンプル情報を更新
- `DELETE /api/sample-batches/{batch_id}/samples/{sample_id}` - サンプルを削除

#### サンプルファイル管理API
- `GET /api/sample-batches/{batch_id}/samples/{sample_id}/files` - サンプル内のファイル一覧を取得
- `POST /api/sample-batches/{batch_id}/samples/{sample_id}/files` - サンプルにファイルを追加
- `DELETE /api/sample-batches/{batch_id}/samples/{sample_id}/files` - サンプルから特定のファイルを削除

#### アップロード状態確認API
- `GET /api/sample-batches/upload-status/{job_id}` - フォルダアップロードの進捗状況を取得

### 注意事項
- サーバーの起動方法: `python src/main.py`
- デフォルトのホスト: ローカルホスト（設定に基づく）
- デフォルトのポート: 設定ファイルで指定されたポート（デフォルトは通常8000）
- APIのベースURL: `http://localhost:8000/api`

ブラウザでのテスト用に、以下のエンドポイントにアクセスすることができます：
1. サンプルバッチ一覧：`http://localhost:8000/api/sample-batches`
2. 特定のバッチのサンプル一覧：`http://localhost:8000/api/sample-batches/{batch_id}/samples`
3. 特定のサンプルの詳細：`http://localhost:8000/api/sample-batches/{batch_id}/samples/{sample_id}`

# フロントエンド仕様書と実装状況の整合性レビュー

フロントエンド仕様書 とバックエンド実装状況を比較したところ、いくつかの不整合を発見しました。フロントエンド開発者がこの仕様書に基づいて実装を進めた場合、以下の問題点に直面する可能性があります。

## 1. サンプルファイル管理APIの不整合

**問題点**: 
- フロントエンド仕様書(docs\development\frontend_specifications.md)では以下のエンドポイントが参照されています：
  ```
  GET /api/sample-batches/{batchId}/samples/{sampleId}/files
  POST /api/sample-batches/{batchId}/samples/{sampleId}/files
  DELETE /api/sample-batches/{batchId}/samples/{sampleId}/files
  ```
- しかし、実際のバックエンド実装ではこれらのエンドポイントが実装されていない可能性が高いです。
- 実装計画では「✅ 実装済み」と記載されていますが、コードベースでの確認ができませんでした。

**影響**: 
フロントエンドの「サンプル詳細画面コンポーネント」や「サンプルファイル管理フロー」で使用されているエンドポイントが機能せず、サンプル内のファイル表示や操作ができない可能性があります。

**更新状況 (2024年7月)**: 
✅ 実装済み。`src/api/routers/file_management.py`で実装を確認しました。以下のエンドポイントが実装されています：
- `GET /api/files/sample-batches/{batch_id}/samples/{sample_id}/files` - サンプル内のファイル一覧を取得
- `POST /api/files/sample-batches/{batch_id}/samples/{sample_id}/files` - サンプルにファイルを追加
- `DELETE /api/files/sample-batches/{batch_id}/samples/{sample_id}/files` - サンプルからファイルを削除

ベースパスが`/api/files`となっているため、フロントエンドの実装と異なる可能性があります。フロントエンド開発者と連携して調整が必要です。

## 3. サンプルバッチクローンAPIの不確定

**問題点**:
- フロントエンド仕様書では `POST /api/sample-batches/{sourceBatchId}/clone` というエンドポイントが参照されていますが、実装計画や実際のコードベースでこのエンドポイントの実装が確認できませんでした。

**影響**:
「バッチ複製」機能が正常に動作しない可能性があります。

**更新状況 (2024年7月)**: 
✅ 実装済み。`src/api/routers/sample_batches_api.py`にてクローン機能が実装されていることを確認しました。
- `POST /{source_batch_id}/clone` - バッチのクローン作成

## 4. バッチ進捗管理APIの不確定

**問題点**:
- フロントエンド仕様書では `GET /api/workflows/{workflow_id}/batch-progress` というエンドポイントが参照されていますが、実装状況が確認できませんでした。

**影響**:
「バッチ単位の進捗状況の表示」機能が正常に動作しない可能性があります。

**更新状況 (2024年7月)**: 
✅ 実装済み。`src/api/routers/workflow_management.py`にて進捗管理APIが実装されていることを確認しました。
- `GET /{workflow_id}/batch-progress` - バッチ単位の進捗状況を取得

## 5. 問い合わせ管理APIの未実装

**問題点**:
- フロントエンド仕様書では問い合わせ一覧取得APIや詳細取得APIが必要と記載されていますが、具体的なエンドポイントが明示されていません。
- 実装計画や実際のコードベースでの確認もできませんでした。

**影響**:
「問い合わせ対応フロー」が正常に動作しない可能性があります。

**更新状況 (2024年7月)**: 
✅ 実装済み。`src/api/routers/human_interaction.py`にて問い合わせ管理APIが実装されていることを確認しました。
- `GET /human/inquiries` - 問い合わせ一覧を取得
- `GET /human/inquiries/{inquiry_id}` - 問い合わせ詳細を取得
- `POST /human/inquiries` - 問い合わせを作成
- `POST /human/inquiries/{inquiry_id}/response` - 問い合わせに回答
- `PUT /human/inquiries/{inquiry_id}/status` - 問い合わせのステータスを更新

## 6. 実装状況の総括

上記の不整合点はすべて解決済みであり、フロントエンド仕様書で参照されているAPIはすべて実装されています。ただし、一部のAPIではパスプレフィックスが仕様書と異なる場合があるため、フロントエンド開発者との連携が必要です。特にサンプルファイル管理APIについては、パスの違いに注意が必要です。

### ダミーデータ使用状況

以下のAPIエンドポイントで使用されていたダミーデータは、実際のデータベースと連携する実装に置き換えられました：

1. **サンプルバッチ進捗管理API**
   - `GET /api/workflows/{workflow_id}/batch-progress` - 実際のデータベースからワークフロー、バッチ、サンプル情報を取得し、リアルタイムの進捗状況を計算して返すよう実装されました。各サンプルの処理状況、全体の進捗率、予測完了時間などの情報が実データに基づいて提供されます。

2. **問い合わせ管理API**
   - `GET /human/inquiries` - データベースから問い合わせ情報を取得する実装に変更されました。フィルタリング、ページネーション機能も実装され、関連するワークフロー、バッチ、サンプル情報も合わせて取得します。
   - `GET /human/inquiries/{inquiry_id}` - 指定されたIDの問い合わせ詳細情報をデータベースから取得し、関連エンティティ情報や応答履歴も含めて返すよう実装されました。

3. **サンプル処理結果API**
   - `GET /api/workflows/{workflow_id}/results` - 実際のワークフロー結果、サンプル結果、ファイル情報をデータベースから取得する実装に変更されました。ターゲットタイプ（バッチまたはサンプル）や処理レベル（サンプルまたはファイル）に応じて適切な情報を構築して返します。

これらのAPI実装の改善により、テスト環境と本番環境の区別なく実際のデータに基づいた応答が可能になりました。ダミーデータの使用によるテストと実データの不一致の問題が解消され、より信頼性の高いシステム運用が可能になります。

## 7. 問い合わせ管理APIと既存ヒューマンインタラクションAPIの機能重複

フロントエンド仕様書で要求されている問い合わせ管理APIとして、以下のエンドポイントを実装しました。

### 問い合わせ管理API

問い合わせ管理APIは、広範な用途での人間とシステム間のやり取りを目的としています：

- `POST /api/human/inquiries` - 問い合わせを作成
- `GET /api/human/inquiries` - 問い合わせ一覧を取得
- `GET /api/human/inquiries/{inquiry_id}` - 問い合わせ詳細を取得
- `POST /api/human/inquiries/{inquiry_id}/response` - 問い合わせに回答
- `PUT /api/human/inquiries/{inquiry_id}/status` - 問い合わせのステータスを更新

これらのエンドポイントは、以下のようなユースケースに対応します：

1. サンプル処理に関する質問や承認依頼
2. 処理結果の確認や承認
3. システム操作に関する問い合わせ
4. データの不整合やエラーに関する報告

当初存在していたヒューマンインタラクションAPI（`/query`、`/response`）は機能が限定的であったため、より汎用的な問い合わせ管理APIに統合されました。
