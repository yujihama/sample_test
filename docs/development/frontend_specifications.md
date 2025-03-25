# フロントエンド実装仕様書

## 概要
本ドキュメントは、内部監査AIエージェントシステムのフロントエンド実装における最適化仕様を記載しています。既存のフロントエンドを完全に刷新し、最新のReactベストプラクティスと保守性を重視した設計に基づく再実装を行います。

## 技術スタック

### コア技術
- **フレームワーク**: React 19.x
- **言語**: TypeScript 5.x
- **ビルドツール**: Vite 5.x
- **パッケージマネージャー**: npm

### 主要ライブラリ
- **状態管理**: 
  - **Zustand 4.x**（軽量で柔軟なグローバル状態管理）
  - **@tanstack/react-query 5.x**（サーバー状態）
- **UIコンポーネント**: Material UI v5.x
- **スタイリング**: **MUIのテーマシステム + Emotion**
- **ルーティング**: React Router v7.x
- **APIクライアント**: Axios 1.x
- **フォーム管理**: React Hook Form 7.x
- **バリデーション**: Zod 3.x
- **テスト**: **Vitest + Testing Library**
- **リアルタイム通信**: Socket.IO Client 4.x


## プロジェクト構造

現在の実装状況に基づいたプロジェクト構造は以下のとおりです：

```
audit-ai-frontend/
  ├── public/            # 静的ファイル
  ├── src/
  │   ├── assets/        # 静的アセット（画像、フォントなど）
  │   ├── components/    # 共通コンポーネント
  │   │   ├── AppHeader.tsx  # ヘッダーコンポーネント
  │   │   ├── AppFooter.tsx  # フッターコンポーネント
  │   │   ├── Modal.tsx      # モーダルコンポーネント
  │   │   ├── AuditProcedureExecutionForm.tsx  # 監査手続き実行フォーム
  │   │   └── NotificationList.tsx # 通知リストコンポーネント
  │   ├── contexts/      # Reactコンテキスト
  │   ├── hooks/         # カスタムフック
  │   │   └── useNotification.tsx  # 通知管理用フック
  │   ├── layouts/       # レイアウトコンポーネント
  │   │   └── MainLayout.tsx  # メインレイアウト
  │   ├── mocks/         # モックデータ（開発用）
  │   ├── pages/         # ページコンポーネント
  │   │   ├── Dashboard.tsx   # ダッシュボードページ
  │   │   ├── AuditProcedures.tsx # 監査手続きページ
  │   │   ├── Samples.tsx     # サンプル管理ページ
  │   │   ├── ExecuteProcedure.tsx # 監査手続き実行ページ
  │   │   ├── WorkflowResult.tsx # ワークフロー結果表示ページ
  │   │   ├── AgentCommunication.tsx # エージェント通信ページ
  │   │   └── AgentCommunicationDetail.tsx # エージェント通信詳細ページ
  │   ├── services/      # APIサービス
  │   │   ├── api.ts     # APIクライアントの基本設定
  │   │   ├── auditService.ts # 監査手続き用APIサービス
  │   │   ├── sampleService.ts # サンプル管理用APIサービス
  │   │   ├── workflowService.ts # ワークフロー用APIサービス
  │   │   └── agentCommunicationService.ts # エージェント通信用APIサービス
  │   ├── store/         # Zustand状態管理
  │   │   └── useAppStore.ts  # アプリケーション状態ストア
  │   ├── styles/        # スタイルシート
  │   │   ├── App.css    # アプリケーション全体のスタイル
  │   │   ├── index.css  # グローバルスタイル
  │   │   ├── dashboard.css # ダッシュボードのスタイル
  │   │   ├── auditProcedures.css # 監査手続きのスタイル
  │   │   ├── executeProcedure.css # 監査手続き実行ページのスタイル
  │   │   ├── workflowResult.css # ワークフロー結果表示ページのスタイル
  │   │   └── samples.css # サンプル管理のスタイル
  │   ├── types/         # TypeScript型定義
  │   │   ├── audit.ts   # 監査関連の型定義
  │   │   ├── sample.ts  # サンプル関連の型定義
  │   │   └── workflow.ts # ワークフロー関連の型定義
  │   ├── utils/         # ユーティリティ関数
  │   ├── App.tsx        # アプリケーションルート
  │   ├── index.tsx      # エントリーポイント
  │   └── vite-env.d.ts  # Vite環境変数型定義
  ├── build/             # ビルド出力ディレクトリ
  ├── vite.config.ts     # Vite設定ファイル
  ├── tsconfig.json      # TypeScript設定
  ├── tsconfig.node.json # TypeScript Node設定
  ├── package.json       # 依存関係
  ├── index.html         # HTMLエントリーポイント
  └── .env               # 環境変数設定
```

## 実装計画と進捗状況

### フェーズ0: 準備作業
- [x] 既存フロントエンドコードの削除
- [x] 依存関係の更新
- [x] ディレクトリ構造の確立

### フェーズ1: 基盤構築
- [x] TypeScriptの設定
- [x] Vite設定の最適化
- [x] React Routerの設定
- [x] スタイリングのベースセットアップ
- [x] レイアウトコンポーネントの作成
- [x] ナビゲーションの実装
- [x] APIクライアントの設定

### フェーズ2: コア機能実装
- [x] API疎通確認
  - AuditProceduresサービスAPIとの通信テスト
  - ダッシュボード画面での基本的なデータ取得テスト
  - エラーハンドリングの検証
- [x] ダッシュボード画面
  - 監査プロジェクト概要表示
  - ステータスサマリー
  - 最近のアクティビティフィード
- [x] 監査手続き管理
  - 手続きの一覧表示
  - 新規手続き作成モーダル
  - 手続き編集機能
  - React QueryとのAPI連携
- [x] サンプル管理機能
  - サンプルの一覧表示と詳細表示
  - バッチによるフィルタリング
  - 削除機能
  - サンプルの統計情報表示
- [x] エージェント間通信ビューア
  - 会話一覧表示と詳細表示
  - 会話の詳細画面での日付別メッセージグループ化
  - メッセージ送信機能

### フェーズ3：拡張機能実装
- [x] 人間への問い合わせ管理（人間への問い合わせの状況や、回答ができる）
- [x] レポート機能（手続き結果を確認可能）
- [x] **サンプルバッチを使用した監査手続き実行フロー**
  - [x] 監査手続き実行フォームコンポーネントの実装
  - [x] ワークフローサービスの実装
  - [x] 監査手続き実行ページの実装
  - [x] ワークフロー結果表示ページの実装
  - [ ] サンプルページとの連携強化

### フェーズ4：最適化とテスト
- [ ] パフォーマンス最適化
- [ ] レスポンシブデザインの調整
- [ ] E2Eテストの実装

## 開発環境のセットアップと起動方法

### 環境のセットアップ
1. プロジェクトのクローン後、以下のコマンドで必要なパッケージをインストールします：
```bash
cd audit-ai-frontend
npm install
```

2. 必要に応じて `.env` ファイルを設定します：
```
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=Audit AI System
```

### 開発サーバーの起動
1. `audit-ai-frontend` ディレクトリに移動します：
```bash
cd audit-ai-frontend
```

2. 開発サーバーを起動します：
```bash
npm run dev
```

3. 成功すると、以下のようなメッセージが表示されます：
```
  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

4. ブラウザで `http://localhost:3000` にアクセスして、アプリケーションを確認できます。

### スクリプト一覧
package.json に定義されている主要なスクリプトは以下の通りです：
- `npm run dev` - 開発サーバーの起動
- `npm run build` - プロダクション用ビルドの作成
- `npm run serve` - ビルド済みアプリケーションのプレビュー
- `npm run lint` - ESLintによるコードチェック
- `npm run format` - Prettierによるコードフォーマット
- `npm run test` - Vitestによるテスト実行

## コーディング規約とベストプラクティス

### 1. 状態管理の簡素化

#### Zustandによるグローバル状態管理

```typescript
// store/useAppStore.ts
import { create } from 'zustand';

interface AppState {
  isLoading: boolean;
  setLoading: (loading: boolean) => void;
  darkMode: boolean;
  toggleDarkMode: () => void;
}

const useAppStore = create<AppState>((set) => ({
  isLoading: false,
  setLoading: (loading) => set({ isLoading: loading }),
  darkMode: false,
  toggleDarkMode: () => set((state) => ({ darkMode: !state.darkMode })),
}));

export default useAppStore;
```

#### React Queryによるサーバー状態管理

```typescript
// カスタムクエリフック (auditService.ts)
export const useAuditProcedures = () => {
  return useQuery({
    queryKey: ['auditProcedures'],
    queryFn: async () => {
      const { data } = await apiClient.get<ProceduresResponse>(ENDPOINTS.PROCEDURES);
      return data.procedures;
    },
    staleTime: 1000 * 60 * 5, // 5分間キャッシュを保持
  });
};
```

### 2. API通信の一元管理

```typescript
// services/api.ts
import axios, { InternalAxiosRequestConfig } from 'axios';

// APIクライアントの基本設定
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// リクエストインターセプター
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // APIリクエスト前の処理（認証トークンの追加など）
    const token = localStorage.getItem('auth_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// レスポンスインターセプター
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // エラーハンドリング
    if (error.response) {
      // サーバーからのレスポンスエラー
      console.error('API Error:', error.response.data);
      
      // 401エラーの場合、認証切れとしてログアウト処理
      if (error.response.status === 401) {
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
      }
    } else if (error.request) {
      // リクエストは送信されたがレスポンスがない場合
      console.error('No response received:', error.request);
    } else {
      // リクエスト設定中にエラーが発生した場合
      console.error('Request error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
```

## 実装済み機能の詳細

### 1. ダッシュボード

ダッシュボードは以下の機能を提供します：
- 監査手続きの概要表示（総数、ステータス別件数）
- サンプリング状況（サンプル総数、検証済み、異常検知）
- エージェント活動状況（アクティブエージェント数、処理済みタスク数）
- API接続テスト機能（実行ボタンで実際にAPIに接続し、結果を表示）
- 最近の通知表示

### 2. 監査手続き管理

監査手続き管理画面では以下の機能を提供します：
- 監査手続きの一覧表示
- 新規監査手続きの作成（モーダルフォームを使用）
- 手続き詳細の表示

### 3. サンプル管理

サンプル管理画面では以下の機能を提供します：
- サンプルバッチの一覧表示
- バッチに属するサンプルの表示
- サンプルの詳細表示（ファイル情報）
- サンプルの削除機能
- 未登録ファイルの表示

### 4. エージェント通信

エージェント通信ビューアでは以下の機能を提供します：
- エージェント間通信の可視化
- エージェント識別
- 時系列表示

## API実装状況

### ダッシュボード
- **概要**：進行中/完了済み手続き数、サンプル数
  - 使用API: `GET /api/dashboard/summary` ✓
- **最近のアクティビティ**：タイムライン形式でエージェント活動履歴
  - 使用API: `GET /api/dashboard/activity` ✓
- **未解決の問い合わせ**：対応が必要な問い合わせの件数
  - 使用API: `GET /api/dashboard/alerts` ✓
- **システム状態**：エージェント稼働状況、システムリソース利用状況
  - 使用API: `GET /api/dashboard/system-status` ✓
- **チャート表示**：ワークフロー状態やメトリクスの可視化
  - 使用API: 
    - `GET /api/dashboard/chart/workflow-status` ✓
    - `GET /api/dashboard/chart/time-series/{metric}` ✓
    - `GET /api/dashboard/chart/summary-metrics` ✓

### 監査手続き管理
- **手続き管理**：監査手続きの確認、登録、削除ができる
  - 使用API: 
    - `GET /api/procedures` (一覧取得) ✓
    - `GET /api/procedures/{procedure_id}` (詳細取得) ✓
    - `POST /api/procedures` (新規登録) ✓
- **手続き実行（個別サンプル）**：個別サンプルに対する監査手続き実行
  - 使用API: 
    - `POST /api/workflows` (ワークフロー作成、サンプル階層対応) ✓
    - `POST /api/workflows/{workflow_id}/actions/start` (開始) ✓
- **手続き実行（バッチ単位）**：サンプルバッチ全体に対する監査手続き実行
  - 使用API: 
    - `GET /api/sample-batches` (バッチ一覧取得) ✓
    - `POST /api/workflows` (ワークフロー作成、サンプル階層対応) ✓
    - `POST /api/workflows/{workflow_id}/actions/start` (開始) ✓
- **手続き状況モニタリング**：実行中、完了手続きを一覧化
  - 使用API: 
    - `GET /api/workflows` (状態取得) ✓
    - `POST /api/workflows/{workflow_id}/actions/pause` (一時停止) ✓
    - `POST /api/workflows/{workflow_id}/actions/resume` (再開) ✓
    - `POST /api/workflows/{workflow_id}/actions/cancel` (キャンセル) ✓
- **バッチ処理モニタリング**：バッチ処理の進捗状況と結果確認
  - 使用API: 
    - `GET /api/workflows/{workflow_id}/batch-progress` (バッチ処理進捗状況) ✓
    - WebSocket `/api/notifications/ws/{user_id}` (リアルタイム更新) ✓

### エージェント通信ビューア
- **エージェント間通信の可視化**：エージェント間の会話を視覚化
  - 使用API: `GET /api/agents/agents/messages/{message_id}` ✓
- **エージェント識別**：各エージェント（A/B/C）を色分けして表示
  - 使用API: `GET /api/agents/agents` ✓
- **時系列表示**：通信履歴を時系列で表示（無限スクロール対応）
  - 使用API: WebSocket `/api/notifications/ws/{user_id}` (リアルタイム更新) ✓

### サンプル管理画面
- **サンプルアップロード**：ドラッグ&ドロップ対応アップロードエリア
  - 使用API: `POST /api/files/upload` ✓
- **サンプル一覧**：テーブル形式でID、タイプ、状態などを表示
  - 使用API: `GET /api/files` ✓
- **詳細表示**：サンプルの内容プレビュー（画像/PDF/エクセルなど）
  - 使用API: 
    - `GET /api/files/{file_id}` ✓
    - `GET /api/files/{file_id}/download` ✓
- **メタデータ編集**：サンプルの属性情報編集フォーム
  - 使用API: `PUT /api/files/{file_id}/metadata` ✓

### サンプルバッチ管理画面
- **バッチ一覧**：監査サンプルバッチをカード形式で表示
  - 使用API: `GET /api/sample-batches` ✓
- **バッチ作成**：新規サンプルバッチ作成フォーム
  - 使用API: `POST /api/sample-batches` ✓
- **バッチ詳細**：バッチ情報とバッチ内サンプル一覧の表示
  - 使用API: 
    - `GET /api/sample-batches/{batchId}` ✓
    - `GET /api/sample-batches/{batchId}/files` ✓
- **バッチ編集**：バッチ情報の編集フォーム
  - 使用API: `PUT /api/sample-batches/{batchId}` ✓
- **バッチ操作**：サンプル追加、削除、バッチ複製などの操作
  - 使用API: 
    - `POST /api/sample-batches/{batchId}/files` ✓
    - `DELETE /api/sample-batches/{batchId}/files` ✓
    - `POST /api/sample-batches/{sourceBatchId}/clone` ✓
- **メタデータ一括更新**：バッチ内サンプルのメタデータ一括編集
  - 使用API: `PUT /api/sample-batches/{batchId}/metadata` ✓
- **処理状況モニタリング**：バッチ処理の進行状況を表示
  - 使用API: 
    - `GET /api/sample-batches/{batchId}/status` ✓
    - WebSocket `/api/notifications/ws/{user_id}` ✓

### 人間への問い合わせ管理
- **問い合わせ一覧**：エージェントからの問い合わせを一覧表示
  - 使用API: `GET /api/human/inquiries` ✓
- **問い合わせ詳細**：問い合わせの詳細情報と回答フォーム
  - 使用API: `GET /api/human/inquiries/{inquiry_id}` ✓
- **問い合わせ回答**：問い合わせへの回答を送信
  - 使用API: `POST /api/human/inquiries/{inquiry_id}/respond` ✓
- **問い合わせステータス更新**：問い合わせステータスの変更
  - 使用API: `PUT /api/human/inquiries/{inquiry_id}/status` ✓
- **問い合わせ通知**：未回答の問い合わせに関する通知
  - 使用API: WebSocket `/api/notifications/ws/{user_id}` ✓

## 今後の拡張計画

1. **認証機能の実装**
   - ログイン・ログアウト
   - ユーザー権限管理

2. **人間への問い合わせ管理**
   - 未回答の問い合わせ一覧
   - 回答フォーム
   - 問い合わせ履歴

3. **レポート機能**
   - 監査結果のレポート生成
   - グラフや統計情報の表示
   - エクスポート機能

4. **通知機能の強化**
   - プッシュ通知
   - メール通知連携

5. **リアルタイム更新機能**
   - WebSocket接続による監査状況のリアルタイム更新
   - 処理進捗のプログレスバー表示

## 技術的改善計画

1. **パフォーマンス最適化**
   - コンポーネントのメモ化
   - 不要なレンダリングの削減
   - 画像の最適化

2. **アクセシビリティ向上**
   - ARIA対応
   - キーボードナビゲーション
   - コントラスト比の改善

3. **テスト強化**
   - ユニットテストの拡充
   - E2Eテストの実装
   - モックサーバーの強化

4. **CI/CD整備**
   - 自動テスト
   - 自動デプロイ
   - コード品質チェック

## 追加実装必須機能：サンプルバッチを使用した監査手続き実行フロー

### 1. 監査手続き実行フォームコンポーネント

バッチを選択して監査手続きを実行するためのフォームコンポーネントを実装します。

```typescript
// components/AuditProcedureExecutionForm.tsx
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useAuditProcedures } from '../services/auditService';
import { useBatches } from '../services/sampleService';
import { createWorkflow } from '../services/workflowService';

// バリデーションスキーマの定義
const executionFormSchema = z.object({
  procedureId: z.string().min(1, '監査手続きを選択してください'),
  batchId: z.string().min(1, 'サンプルバッチを選択してください'),
  processLevel: z.enum(['sample', 'file']),
  parallelProcessing: z.boolean().optional(),
  maxParallelJobs: z.number().min(1).max(10).optional(),
  detailedAnalysis: z.boolean().optional(),
});

type ExecutionFormData = z.infer<typeof executionFormSchema>;

interface AuditProcedureExecutionFormProps {
  onSuccess?: (workflowId: string) => void;
  onCancel?: () => void;
}

const AuditProcedureExecutionForm: React.FC<AuditProcedureExecutionFormProps> = ({
  onSuccess,
  onCancel,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 監査手続き一覧を取得
  const { data: procedures, isLoading: proceduresLoading } = useAuditProcedures();
  
  // サンプルバッチ一覧を取得
  const { data: batches, isLoading: batchesLoading } = useBatches();

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<ExecutionFormData>({
    resolver: zodResolver(executionFormSchema),
    defaultValues: {
      processLevel: 'sample',
      parallelProcessing: true,
      maxParallelJobs: 5,
      detailedAnalysis: true,
    },
  });

  const parallelProcessing = watch('parallelProcessing');
  const processLevel = watch('processLevel');

  const onSubmit = async (data: ExecutionFormData) => {
    setIsSubmitting(true);
    setError(null);
    
    try {
      // 選択された監査手続きの詳細を取得
      const procedure = procedures?.find(p => p.id === data.procedureId);
      
      if (!procedure) {
        throw new Error('選択された監査手続きが見つかりません');
      }
      
      // ワークフロー作成リクエスト
      const workflowData = {
        audit_procedure_id: data.procedureId,
        target: {
          type: 'batch',
          id: data.batchId
        },
        procedure_text: procedure.title,
        config: {
          process_level: data.processLevel,
          parallel_processing: data.parallelProcessing,
          max_parallel_jobs: data.maxParallelJobs,
          detailed_analysis: data.detailedAnalysis
        }
      };
      
      // ワークフロー作成APIを呼び出し
      const result = await createWorkflow(workflowData);
      
      // 成功時のコールバック
      if (onSuccess && result.workflow_id) {
        onSuccess(result.workflow_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '監査手続きの実行に失敗しました');
      console.error('ワークフロー作成エラー:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isLoading = proceduresLoading || batchesLoading;

  if (isLoading) {
    return <div className="loading">データを読み込んでいます...</div>;
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="audit-execution-form">
      <h2>監査手続き実行</h2>
      
      {error && <div className="error-message">{error}</div>}
      
      <div className="form-group">
        <label htmlFor="procedureId">監査手続き</label>
        <select id="procedureId" {...register('procedureId')}>
          <option value="">監査手続きを選択してください</option>
          {procedures?.map(procedure => (
            <option key={procedure.id} value={procedure.id}>
              {procedure.title}
            </option>
          ))}
        </select>
        {errors.procedureId && (
          <p className="error-text">{errors.procedureId.message}</p>
        )}
      </div>

      <div className="form-group">
        <label htmlFor="batchId">サンプルバッチ</label>
        <select id="batchId" {...register('batchId')}>
          <option value="">サンプルバッチを選択してください</option>
          {batches?.map(batch => (
            <option key={batch.id} value={batch.id}>
              {batch.name}
            </option>
          ))}
        </select>
        {errors.batchId && (
          <p className="error-text">{errors.batchId.message}</p>
        )}
      </div>

      <div className="form-group">
        <label>処理レベル</label>
        <div className="radio-group">
          <label>
            <input
              type="radio"
              value="sample"
              {...register('processLevel')}
            />
            サンプル単位
          </label>
          <label>
            <input
              type="radio"
              value="file"
              {...register('processLevel')}
            />
            ファイル単位
          </label>
        </div>
      </div>

      <div className="form-group checkbox-group">
        <label>
          <input
            type="checkbox"
            {...register('parallelProcessing')}
          />
          並列処理を有効にする
        </label>
      </div>

      {parallelProcessing && (
        <div className="form-group">
          <label htmlFor="maxParallelJobs">最大並列ジョブ数</label>
          <input
            type="number"
            id="maxParallelJobs"
            min="1"
            max="10"
            {...register('maxParallelJobs', { valueAsNumber: true })}
          />
          {errors.maxParallelJobs && (
            <p className="error-text">{errors.maxParallelJobs.message}</p>
          )}
        </div>
      )}

      <div className="form-group checkbox-group">
        <label>
          <input
            type="checkbox"
            {...register('detailedAnalysis')}
          />
          詳細分析を実行
        </label>
      </div>

      <div className="form-actions">
        <button
          type="button"
          className="btn btn-secondary"
          onClick={onCancel}
          disabled={isSubmitting}
        >
          キャンセル
        </button>
        <button
          type="submit"
          className="btn btn-primary"
          disabled={isSubmitting}
        >
          {isSubmitting ? '実行中...' : '実行'}
        </button>
      </div>
    </form>
  );
};

export default AuditProcedureExecutionForm;
```

### 2. ワークフローサービス

監査手続きの実行と結果取得に必要なAPIを呼び出すサービスを実装します。

```typescript
// services/workflowService.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from './api';

// 型定義
export interface Workflow {
  workflow_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  audit_procedure_id: string;
  target: {
    type: string;
    id: string;
  };
  progress?: number;
  message?: string;
}

export interface WorkflowResult {
  workflow_id: string;
  status: string;
  target: {
    type: string;
    id: string;
    name: string;
  };
  process_level: string;
  completion_rate: number;
  findings: Array<{
    id: string;
    title: string;
    description: string;
    severity: string;
    evidence: Record<string, any>;
  }>;
  summary: {
    total_samples: number;
    compliant_samples: number;
    non_compliant_samples: number;
    compliance_rate: number;
  };
  sample_results?: Array<{
    sample_id: string;
    name: string;
    status: string;
    result: string;
    findings: string[];
    file_count: number;
    completed_at: string;
  }>;
  created_at: string;
  completed_at: string;
}

export interface WorkflowProgress {
  workflow_id: string;
  batch_id: string;
  status: string;
  progress: number;
  total_files: number;
  processed_files: number;
  pending_files: number;
  started_at: string;
  estimated_completion: string;
  file_progress: Array<{
    file_id: string;
    status: string;
    result?: string;
    progress?: number;
  }>;
}

export interface CreateWorkflowRequest {
  audit_procedure_id: string;
  target: {
    type: string;
    id: string;
  };
  procedure_text: string;
  config: {
    process_level: string;
    parallel_processing?: boolean;
    max_parallel_jobs?: number;
    detailed_analysis?: boolean;
  };
}

// API エンドポイント
const ENDPOINTS = {
  WORKFLOWS: '/workflows',
  WORKFLOW: (id: string) => `/workflows/${id}`,
  WORKFLOW_START: (id: string) => `/workflows/${id}/actions/start`,
  WORKFLOW_PAUSE: (id: string) => `/workflows/${id}/actions/pause`,
  WORKFLOW_RESUME: (id: string) => `/workflows/${id}/actions/resume`,
  WORKFLOW_CANCEL: (id: string) => `/workflows/${id}/actions/cancel`,
  WORKFLOW_RESULTS: (id: string) => `/workflows/${id}/results`,
  WORKFLOW_BATCH_PROGRESS: (id: string) => `/workflows/${id}/batch-progress`,
};

// ワークフロー一覧を取得
export const useWorkflows = () => {
  return useQuery({
    queryKey: ['workflows'],
    queryFn: async () => {
      const { data } = await apiClient.get<{ workflows: Workflow[] }>(ENDPOINTS.WORKFLOWS);
      return data.workflows;
    },
  });
};

// 特定のワークフローを取得
export const useWorkflow = (id: string) => {
  return useQuery({
    queryKey: ['workflows', id],
    queryFn: async () => {
      const { data } = await apiClient.get<Workflow>(ENDPOINTS.WORKFLOW(id));
      return data;
    },
    enabled: !!id,
  });
};

// ワークフロー結果を取得
export const useWorkflowResult = (id: string) => {
  return useQuery({
    queryKey: ['workflows', id, 'results'],
    queryFn: async () => {
      const { data } = await apiClient.get<WorkflowResult>(ENDPOINTS.WORKFLOW_RESULTS(id));
      return data;
    },
    enabled: !!id,
  });
};

// バッチ処理の進捗状況を取得
export const useWorkflowBatchProgress = (id: string) => {
  return useQuery({
    queryKey: ['workflows', id, 'batch-progress'],
    queryFn: async () => {
      const { data } = await apiClient.get<WorkflowProgress>(ENDPOINTS.WORKFLOW_BATCH_PROGRESS(id));
      return data;
    },
    enabled: !!id,
    refetchInterval: (data) => {
      // 完了または失敗の場合はポーリングを停止
      if (data?.status === 'completed' || data?.status === 'cancelled' || data?.status === 'failed') {
        return false;
      }
      // それ以外は5秒ごとに更新
      return 5000;
    },
  });
};

// ワークフローを作成
export const createWorkflow = async (workflowData: CreateWorkflowRequest) => {
  const { data } = await apiClient.post<Workflow>(ENDPOINTS.WORKFLOWS, workflowData);
  return data;
};

// ワークフローを開始
export const startWorkflow = async (id: string) => {
  const { data } = await apiClient.post<Workflow>(ENDPOINTS.WORKFLOW_START(id));
  return data;
};

// ワークフローを一時停止
export const pauseWorkflow = async (id: string) => {
  const { data } = await apiClient.post<Workflow>(ENDPOINTS.WORKFLOW_PAUSE(id));
  return data;
};

// ワークフローを再開
export const resumeWorkflow = async (id: string) => {
  const { data } = await apiClient.post<Workflow>(ENDPOINTS.WORKFLOW_RESUME(id));
  return data;
};

// ワークフローをキャンセル
export const cancelWorkflow = async (id: string) => {
  const { data } = await apiClient.post<Workflow>(ENDPOINTS.WORKFLOW_CANCEL(id));
  return data;
};

// ワークフロー作成ミューテーション
export const useCreateWorkflow = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (workflowData: CreateWorkflowRequest) => {
      return createWorkflow(workflowData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
  });
};

// ワークフロー開始ミューテーション
export const useStartWorkflow = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (id: string) => {
      return startWorkflow(id);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['workflows', data.workflow_id] });
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
  });
};

// ワークフロー一時停止ミューテーション
export const usePauseWorkflow = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (id: string) => {
      return pauseWorkflow(id);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['workflows', data.workflow_id] });
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
  });
};

// ワークフローキャンセルミューテーション
export const useCancelWorkflow = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (id: string) => {
      return cancelWorkflow(id);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['workflows', data.workflow_id] });
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
  });
};
```

### 3. 監査手続き実行ページ

監査手続き実行フォームを表示し、実行を開始するページを実装します。

```typescript
// pages/ExecuteProcedure.tsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AuditProcedureExecutionForm from '../components/AuditProcedureExecutionForm';
import { startWorkflow } from '../services/workflowService';
import '../styles/executeProcedure.css';

const ExecuteProcedure: React.FC = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const handleExecutionSuccess = async (workflowId: string) => {
    try {
      setIsLoading(true);
      // ワークフローを開始
      await startWorkflow(workflowId);
      // 結果ページに遷移
      navigate(`/workflows/${workflowId}/results`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'ワークフローの開始に失敗しました');
      console.error('ワークフロー開始エラー:', err);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleCancel = () => {
    navigate('/audit-procedures');
  };
  
  return (
    <div className="execute-procedure-container">
      <h1 className="page-title">監査手続き実行</h1>
      
      {error && (
        <div className="error-message">
          <p>{error}</p>
          <button 
            className="btn btn-sm btn-secondary" 
            onClick={() => setError(null)}
          >
            閉じる
          </button>
        </div>
      )}
      
      {isLoading ? (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>ワークフローを開始しています...</p>
        </div>
      ) : (
        <div className="form-container">
          <AuditProcedureExecutionForm 
            onSuccess={handleExecutionSuccess}
            onCancel={handleCancel}
          />
        </div>
      )}
    </div>
  );
};

export default ExecuteProcedure;
```

### 4. ワークフロー結果表示ページ

監査手続き実行結果を表示するページを実装します。

```typescript
// pages/WorkflowResult.tsx
import React, { useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useWorkflowResult, useWorkflowBatchProgress } from '../services/workflowService';
import '../styles/workflowResult.css';

const WorkflowResult: React.FC = () => {
  const { workflowId } = useParams<{ workflowId: string }>();
  
  // ワークフロー結果を取得
  const { 
    data: result, 
    isLoading: resultLoading, 
    isError: resultError,
    error: resultErrorDetails
  } = useWorkflowResult(workflowId || '');
  
  // バッチ処理の進捗状況を取得（処理中の場合）
  const { 
    data: progress, 
    isLoading: progressLoading 
  } = useWorkflowBatchProgress(workflowId || '');
  
  // 処理中かどうかを判定
  const isProcessing = progress?.status === 'running' || progress?.status === 'created';
  
  if (!workflowId) {
    return <div className="error-message">ワークフローIDが指定されていません</div>;
  }
  
  if (resultLoading || progressLoading) {
    return (
      <div className="workflow-result-container">
        <h1 className="page-title">監査結果</h1>
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>データを読み込んでいます...</p>
        </div>
      </div>
    );
  }
  
  if (resultError) {
    return (
      <div className="workflow-result-container">
        <h1 className="page-title">監査結果</h1>
        <div className="error-message">
          <p>エラーが発生しました：{resultErrorDetails instanceof Error ? resultErrorDetails.message : '不明なエラー'}</p>
          <Link to="/audit-procedures" className="btn btn-primary">監査手続き一覧に戻る</Link>
        </div>
      </div>
    );
  }
  
  if (isProcessing && progress) {
    // 処理中の場合、進捗状況を表示
    return (
      <div className="workflow-result-container">
        <h1 className="page-title">処理中</h1>
        
        <div className="workflow-info">
          <p><strong>ステータス:</strong> {progress.status === 'running' ? '実行中' : '準備中'}</p>
          <p><strong>バッチID:</strong> {progress.batch_id}</p>
          <p><strong>開始時刻:</strong> {new Date(progress.started_at).toLocaleString('ja-JP')}</p>
          <p><strong>完了予定時刻:</strong> {new Date(progress.estimated_completion).toLocaleString('ja-JP')}</p>
        </div>
        
        <div className="progress-container">
          <h2>進捗状況</h2>
          <div className="progress-bar">
            <div 
              className="progress-bar-fill" 
              style={{ width: `${Math.round(progress.progress * 100)}%` }}
            ></div>
          </div>
          <p className="progress-text">{Math.round(progress.progress * 100)}% 完了</p>
          
          <div className="progress-stats">
            <p><strong>ファイル総数:</strong> {progress.total_files}</p>
            <p><strong>処理済みファイル:</strong> {progress.processed_files}</p>
            <p><strong>未処理ファイル:</strong> {progress.pending_files}</p>
          </div>
        </div>
        
        <div className="file-progress">
          <h2>ファイル処理状況</h2>
          <table className="file-progress-table">
            <thead>
              <tr>
                <th>ファイルID</th>
                <th>ステータス</th>
                <th>進捗</th>
              </tr>
            </thead>
            <tbody>
              {progress.file_progress.map(file => (
                <tr key={file.file_id}>
                  <td>{file.file_id}</td>
                  <td>
                    {file.status === 'completed' ? '完了' : 
                     file.status === 'processing' ? '処理中' : 
                     file.status === 'pending' ? '待機中' : 
                     file.status}
                  </td>
                  <td>
                    {file.status === 'completed' ? '100%' : 
                     file.progress !== undefined ? `${Math.round(file.progress * 100)}%` : 
                     '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        <div className="action-buttons">
          <Link to="/audit-procedures" className="btn btn-secondary">監査手続き一覧に戻る</Link>
          <button 
            className="btn btn-primary"
            onClick={() => window.location.reload()}
          >
            更新
          </button>
        </div>
      </div>
    );
  }
  
  if (!result) {
    return (
      <div className="workflow-result-container">
        <h1 className="page-title">監査結果</h1>
        <div className="error-message">
          <p>結果データが見つかりません。</p>
          <Link to="/audit-procedures" className="btn btn-primary">監査手続き一覧に戻る</Link>
        </div>
      </div>
    );
  }
  
  // 処理完了時の結果表示
  return (
    <div className="workflow-result-container">
      <h1 className="page-title">監査結果</h1>
      
      <div className="workflow-header">
        <div className="workflow-status">
          <span className={`status-badge status-${result.status.toLowerCase()}`}>
            {result.status === 'completed' ? '完了' : 
             result.status === 'failed' ? '失敗' : 
             result.status}
          </span>
        </div>
        
        <div className="workflow-dates">
          <p><strong>作成日時:</strong> {new Date(result.created_at).toLocaleString('ja-JP')}</p>
          <p><strong>完了日時:</strong> {new Date(result.completed_at).toLocaleString('ja-JP')}</p>
        </div>
      </div>
      
      <div className="target-info">
        <h2>対象情報</h2>
        <p><strong>タイプ:</strong> {result.target.type === 'batch' ? 'バッチ' : 'サンプル'}</p>
        <p><strong>名前:</strong> {result.target.name}</p>
        <p><strong>ID:</strong> {result.target.id}</p>
        <p><strong>処理レベル:</strong> {result.process_level === 'sample' ? 'サンプル単位' : 'ファイル単位'}</p>
      </div>
      
      <div className="summary-results">
        <h2>集計結果</h2>
        <div className="summary-cards">
          <div className="summary-card">
            <h3>サンプル総数</h3>
            <div className="summary-value">{result.summary.total_samples}</div>
          </div>
          <div className="summary-card">
            <h3>適合サンプル</h3>
            <div className="summary-value">{result.summary.compliant_samples}</div>
          </div>
          <div className="summary-card">
            <h3>不適合サンプル</h3>
            <div className="summary-value">{result.summary.non_compliant_samples}</div>
          </div>
          <div className="summary-card">
            <h3>適合率</h3>
            <div className="summary-value">{Math.round(result.summary.compliance_rate * 100)}%</div>
          </div>
        </div>
      </div>
      
      {result.findings.length > 0 && (
        <div className="findings-section">
          <h2>検出事項</h2>
          <div className="findings-list">
            {result.findings.map(finding => (
              <div key={finding.id} className="finding-card">
                <div className="finding-header">
                  <h3>{finding.title}</h3>
                  <span className={`severity-badge severity-${finding.severity}`}>
                    {finding.severity === 'high' ? '高' : 
                     finding.severity === 'medium' ? '中' : 
                     finding.severity === 'low' ? '低' : 
                     finding.severity}
                  </span>
                </div>
                <p className="finding-description">{finding.description}</p>
                <div className="finding-evidence">
                  <h4>証拠</h4>
                  <pre>{JSON.stringify(finding.evidence, null, 2)}</pre>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {result.sample_results && (
        <div className="sample-results-section">
          <h2>サンプル別結果</h2>
          <table className="sample-results-table">
            <thead>
              <tr>
                <th>サンプルID</th>
                <th>名前</th>
                <th>ステータス</th>
                <th>結果</th>
                <th>ファイル数</th>
                <th>完了日時</th>
              </tr>
            </thead>
            <tbody>
              {result.sample_results.map(sample => (
                <tr key={sample.sample_id}>
                  <td>{sample.sample_id}</td>
                  <td>{sample.name}</td>
                  <td>{sample.status}</td>
                  <td>
                    <span className={`result-badge result-${sample.result}`}>
                      {sample.result === 'compliant' ? '適合' : '不適合'}
                    </span>
                  </td>
                  <td>{sample.file_count}</td>
                  <td>{new Date(sample.completed_at).toLocaleString('ja-JP')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      
      <div className="action-buttons">
        <Link to="/audit-procedures" className="btn btn-secondary">監査手続き一覧に戻る</Link>
        <Link to={`/sample-batches/${result.target.id}`} className="btn btn-primary">
          バッチ詳細に戻る
        </Link>
      </div>
    </div>
  );
};

export default WorkflowResult;
```

### 5. サンプルバッチを使用した監査手続き実行フロー

以下は、完全な監査手続き実行フローの手順です：

1. 監査手続き管理画面で「手続き実行」ボタンをクリック
   - 実行フォーム画面に遷移
   
2. 監査手続き実行フォームに必要な情報を入力
   - 実行する監査手続きを選択
   - 対象のサンプルバッチを選択
   - 処理レベル（サンプル単位またはファイル単位）を選択
   - 詳細設定（並列処理、詳細分析など）を設定
   
3. 「実行」ボタンをクリックしてワークフローを作成・開始
   - `POST /workflows`でワークフロー作成
   - `POST /workflows/{workflow_id}/actions/start`でワークフロー開始
   
4. ワークフロー実行中に人間への問い合わせが必要な場合
   - エージェントが判断できない事項や承認が必要な項目があると問い合わせが発生
   - 問い合わせ通知がダッシュボードに表示される
   - `GET /api/human/inquiries`で未回答の問い合わせを検出
   - ワークフローは問い合わせへの回答待ち状態になる（一時停止）
   
5. 問い合わせへの対応
   - 問い合わせの詳細を確認
   - 適切な回答や承認を提供
   - `POST /api/human/inquiries/{inquiry_id}/respond`で回答を送信
   - ワークフローが自動的に再開
   
6. ワークフロー結果画面に遷移
   - 進行中の場合は進捗状況をリアルタイムで表示
   - `GET /workflows/{workflow_id}/batch-progress`で進捗を定期的に取得
   - 完了した場合は結果の詳細を表示
   - `GET /workflows/{workflow_id}/results`で結果を取得
   - 人間への問い合わせ履歴も結果の一部として表示
   
7. 結果に基づいて必要なアクションを実行
   - 不適合サンプルへの対応
   - 監査手続きの再実行または調整
   - 監査レポートの生成

上記のフローをフロントエンドで実装することで、サンプルバッチを使用した監査手続きの実行と結果確認、および人間との対話が必要な場合の処理が可能になります。

### 6. 人間への問い合わせサービス

監査手続き実行中に発生する人間への問い合わせを管理するサービスを実装します。

```typescript
// services/inquiryService.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from './api';

// 型定義
export interface Inquiry {
  inquiry_id: string;
  title: string;
  content: string;
  type: 'approval_request' | 'information_request' | 'clarification';
  priority: 'high' | 'medium' | 'low';
  status: 'pending' | 'in_progress' | 'resolved' | 'cancelled';
  created_at: string;
  updated_at: string;
  workflow_id?: string;
  context: Record<string, any>;
  response?: {
    response_id: string;
    content: string;
    responded_by: string;
    responded_at: string;
  };
}

export interface CreateInquiryRequest {
  title: string;
  content: string;
  type: 'approval_request' | 'information_request' | 'clarification';
  priority: 'high' | 'medium' | 'low';
  workflow_id?: string;
  context: Record<string, any>;
}

export interface InquiryResponse {
  content: string;
}

// API エンドポイント
const ENDPOINTS = {
  INQUIRIES: '/human/inquiries',
  INQUIRY: (id: string) => `/human/inquiries/${id}`,
  RESPOND: (id: string) => `/human/inquiries/${id}/respond`,
};

// 問い合わせ一覧を取得
export const useInquiries = (status?: string) => {
  return useQuery({
    queryKey: ['inquiries', { status }],
    queryFn: async () => {
      const params = status ? { status } : undefined;
      const { data } = await apiClient.get<{ items: Inquiry[] }>(ENDPOINTS.INQUIRIES, { params });
      return data.items;
    },
  });
};

// 未回答の問い合わせ数を取得
export const useUnrespondedInquiriesCount = () => {
  return useQuery({
    queryKey: ['inquiries', 'count', 'unresponded'],
    queryFn: async () => {
      const { data } = await apiClient.get<{ items: Inquiry[] }>(ENDPOINTS.INQUIRIES, { 
        params: { status: 'pending' } 
      });
      return data.items.length;
    },
    // 1分ごとに更新
    refetchInterval: 60000,
  });
};

// 特定の問い合わせを取得
export const useInquiry = (id: string) => {
  return useQuery({
    queryKey: ['inquiries', id],
    queryFn: async () => {
      const { data } = await apiClient.get<Inquiry>(ENDPOINTS.INQUIRY(id));
      return data;
    },
    enabled: !!id,
  });
};

// 問い合わせに回答
export const respondToInquiry = async (id: string, response: InquiryResponse) => {
  const { data } = await apiClient.post<Inquiry>(ENDPOINTS.RESPOND(id), response);
  return data;
};

// 問い合わせ回答ミューテーション
export const useRespondToInquiry = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, response }: { id: string; response: InquiryResponse }) => {
      return respondToInquiry(id, response);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['inquiries', data.inquiry_id] });
      queryClient.invalidateQueries({ queryKey: ['inquiries'] });
      
      // 関連するワークフローのデータも更新
      if (data.workflow_id) {
        queryClient.invalidateQueries({ queryKey: ['workflows', data.workflow_id] });
      }
    },
  });
};

// ワークフロー関連の問い合わせを取得
export const useWorkflowInquiries = (workflowId: string) => {
  return useQuery({
    queryKey: ['workflows', workflowId, 'inquiries'],
    queryFn: async () => {
      const { data } = await apiClient.get<{ items: Inquiry[] }>(ENDPOINTS.INQUIRIES, { 
        params: { workflow_id: workflowId } 
      });
      return data.items;
    },
    enabled: !!workflowId,
  });
};
```

### 7. 問い合わせ対応コンポーネント

監査手続き実行中に発生した問い合わせに回答するためのコンポーネントを実装します。

```typescript
// components/InquiryResponseForm.tsx
import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Inquiry, useRespondToInquiry } from '../services/inquiryService';

// バリデーションスキーマの定義
const responseFormSchema = z.object({
  content: z.string().min(1, '回答を入力してください'),
});

type ResponseFormData = z.infer<typeof responseFormSchema>;

interface InquiryResponseFormProps {
  inquiry: Inquiry;
  onSuccess?: () => void;
  onCancel?: () => void;
}

const InquiryResponseForm: React.FC<InquiryResponseFormProps> = ({
  inquiry,
  onSuccess,
  onCancel,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const respondMutation = useRespondToInquiry();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResponseFormData>({
    resolver: zodResolver(responseFormSchema),
  });

  const onSubmit = async (data: ResponseFormData) => {
    setIsSubmitting(true);
    setError(null);
    
    try {
      await respondMutation.mutateAsync({
        id: inquiry.inquiry_id,
        response: {
          content: data.content,
        },
      });
      
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '回答の送信に失敗しました');
      console.error('問い合わせ回答エラー:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="inquiry-response-form">
      <div className="inquiry-details">
        <h3>{inquiry.title}</h3>
        <div className="inquiry-meta">
          <span className={`priority priority-${inquiry.priority}`}>
            {inquiry.priority === 'high' ? '優先度：高' :
             inquiry.priority === 'medium' ? '優先度：中' :
             '優先度：低'}
          </span>
          <span className={`type type-${inquiry.type}`}>
            {inquiry.type === 'approval_request' ? '承認依頼' :
             inquiry.type === 'information_request' ? '情報請求' :
             '確認依頼'}
          </span>
          <span className="created-at">
            作成日時: {new Date(inquiry.created_at).toLocaleString('ja-JP')}
          </span>
        </div>
        <div className="inquiry-content">
          <p>{inquiry.content}</p>
        </div>
        {inquiry.context && (
          <div className="inquiry-context">
            <h4>コンテキスト情報</h4>
            <pre>{JSON.stringify(inquiry.context, null, 2)}</pre>
          </div>
        )}
      </div>
      
      {error && <div className="error-message">{error}</div>}
      
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="form-group">
          <label htmlFor="content">回答</label>
          <textarea
            id="content"
            rows={5}
            {...register('content')}
            placeholder="問い合わせへの回答を入力してください"
          />
          {errors.content && (
            <p className="error-text">{errors.content.message}</p>
          )}
        </div>
        
        <div className="form-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onCancel}
            disabled={isSubmitting}
          >
            キャンセル
          </button>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={isSubmitting}
          >
            {isSubmitting ? '送信中...' : '回答を送信'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default InquiryResponseForm;
```

### 8. ワークフロー結果ページの拡張

ワークフロー結果ページに問い合わせ履歴セクションを追加します。

```typescript
// WorkflowResult.tsxの追加部分
import { useWorkflowInquiries } from '../services/inquiryService';

// 既存のコード...

// 問い合わせ履歴を取得
const {
  data: inquiries,
  isLoading: inquiriesLoading
} = useWorkflowInquiries(workflowId || '');

// 結果表示部分に追加
{inquiries && inquiries.length > 0 && (
  <div className="inquiries-section">
    <h2>問い合わせ履歴</h2>
    <div className="inquiries-list">
      {inquiries.map(inquiry => (
        <div key={inquiry.inquiry_id} className="inquiry-card">
          <div className="inquiry-header">
            <h3>{inquiry.title}</h3>
            <span className={`status-badge status-${inquiry.status}`}>
              {inquiry.status === 'pending' ? '未回答' :
               inquiry.status === 'in_progress' ? '対応中' :
               inquiry.status === 'resolved' ? '解決済み' :
               '取消'}
            </span>
          </div>
          <p className="inquiry-content">{inquiry.content}</p>
          <div className="inquiry-meta">
            <span className="created-at">
              作成日時: {new Date(inquiry.created_at).toLocaleString('ja-JP')}
            </span>
            <span className={`priority priority-${inquiry.priority}`}>
              優先度: {inquiry.priority === 'high' ? '高' :
                      inquiry.priority === 'medium' ? '中' : '低'}
            </span>
          </div>
          {inquiry.response && (
            <div className="inquiry-response">
              <h4>回答</h4>
              <p>{inquiry.response.content}</p>
              <div className="response-meta">
                <span>回答者: {inquiry.response.responded_by}</span>
                <span>回答日時: {new Date(inquiry.response.responded_at).toLocaleString('ja-JP')}</span>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  </div>
)}
```

これらのコンポーネントとサービスを実装することで、監査手続き実行中に人間への問い合わせが必要な場合の対応が可能になります。問い合わせの通知、詳細表示、回答送信、ワークフロー再開までの一連のフローがシームレスに行えるようになります。

### サンプルバッチ管理画面
- **バッチ一覧**：監査サンプルバッチをカード形式で表示
  - 使用API: `GET /api/sample-batches` ✓
- **バッチ作成**：新規サンプルバッチ作成フォーム
  - 使用API: `POST /api/sample-batches` ✓
- **バッチ詳細**：バッチ情報とバッチ内サンプル一覧の表示
  - 使用API: 
    - `GET /api/sample-batches/{batchId}` ✓
    - `GET /api/sample-batches/{batchId}/files` ✓
- **バッチ編集**：バッチ情報の編集フォーム
  - 使用API: `PUT /api/sample-batches/{batchId}` ✓
- **バッチ操作**：サンプル追加、削除、バッチ複製などの操作
  - 使用API: 
    - `POST /api/sample-batches/{batchId}/files` ✓
    - `DELETE /api/sample-batches/{batchId}/files` ✓
    - `POST /api/sample-batches/{sourceBatchId}/clone` ✓
- **サンプル作成**：バッチ内に新規サンプルを作成
  - 使用API: `POST /api/sample-batches/{batchId}/samples` ✓
- **ファイルアップロード**：サンプルにファイルをアップロード
  - 使用API: `POST /api/sample-batches/{batchId}/samples/{sampleId}/files` ✓
- **サンプル＋ファイルの一括作成**：サンプル作成とファイルアップロードを一括で実行
  - 使用API: 
    - `POST /api/sample-batches/{batchId}/samples` ✓ 
    - `POST /api/sample-batches/{batchId}/samples/{sampleId}/files` ✓
- **メタデータ一括更新**：バッチ内サンプルのメタデータ一括編集
  - 使用API: `PUT /api/sample-batches/{batchId}/metadata` ✓
- **処理状況モニタリング**：バッチ処理の進行状況を表示

#### サンプル管理の階層構造

サンプル管理では、以下の階層構造によってデータを整理します：

1. **バッチ（Batch）**：最上位の分類単位。複数のサンプルをグループ化します。
2. **サンプル（Sample）**：バッチに属する個別のデータ単位。一つ以上のファイルを含みます。
3. **ファイル（File）**：サンプルを構成する実際のデータファイル。

この階層構造により、大量のデータを効率的に管理し、バッチ単位での監査手続きの実行が可能になります。ユーザーは：
- バッチレベルで監査対象データをグループ化
- サンプルレベルで関連ファイルをまとめて管理
- ファイルレベルで個別のデータを詳細に確認・操作

することができます。