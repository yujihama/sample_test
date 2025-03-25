# フロントエンド実装総合ガイド

## 概要

このドキュメントは、内部監査サンプルデータ自動テストAIエージェントシステムのフロントエンド実装のための総合ガイドです。システムのバックエンド部分は既に実装されており、このガイドではフロントエンド実装に必要な情報を提供します。

## 技術スタック

フロントエンド開発には以下の技術スタックを使用してください：

- **フレームワーク**: React (最新安定版)
- **状態管理**: Redux ToolkitまたはContext API
- **UIライブラリ**: Material-UI または Chakra UI
- **API通信**: axios、React Query
- **リアルタイム通信**: WebSocket (Socket.io)
- **テスト**: Jest、React Testing Library

## システムアーキテクチャ

システムは以下のコンポーネントで構成されています：

1. **バックエンド**: FastAPIを使用したRESTful API
2. **データベース**: SQLiteデータベース
3. **フロントエンド**: Reactベースのシングルページアプリケーション（SPA）

全体的なデータフローは以下の通りです：

```
[ユーザー] <-> [フロントエンドSPA] <-> [FastAPI バックエンド] <-> [データベース]
                      ^                         |
                      |                         v
                  [WebSocket]  <------  [通知サービス]
```

## バックエンドAPIエンドポイント

システムの主要なAPIエンドポイントは以下の通りです：

- `/api/v1/agents` - エージェント管理API
- `/api/v1/tasks` - タスク管理API
- `/api/v1/workflows` - ワークフロー管理API
- `/api/v1/samples` - サンプルデータ管理API
- `/api/v1/dashboard` - ダッシュボードデータAPI
- `/api/v1/notifications` - リアルタイム通知API

詳細なAPIドキュメントは以下のファイルを参照してください：
- [APIドキュメント](../api/README.md)

## リアルタイム通知機能

システムには、WebSocketを使用したリアルタイム通知機能が実装されています。この機能を使用することで、以下のようなイベントをリアルタイムで通知することができます：

- エージェントのステータス変更
- タスクの完了・失敗
- ワークフローの進行状況
- エラー発生

詳細な実装方法については、[リアルタイム通知システム実装ガイド](./frontend_realtime_notifications.md)を参照してください。

### 主要な通知トピック

- `agent_status_changed` - エージェントのステータスが変更された
- `task_completed` - タスクが完了した
- `task_failed` - タスクが失敗した
- `workflow_created` - 新しいワークフローが作成された
- `workflow_completed` - ワークフローが完了した
- `workflow_failed` - ワークフローが失敗した
- `error_occurred` - エラーが発生した

## データ可視化

ダッシュボードやレポート機能の実装には、以下のAPIエンドポイントを使用します：

- `/api/v1/dashboard/system-status` - システム全体のステータス
- `/api/v1/dashboard/workflow-trends` - ワークフローの傾向データ
- `/api/v1/dashboard/agent-performance` - エージェントのパフォーマンス統計
- `/api/v1/dashboard/task-distribution` - タスク分布
- `/api/v1/dashboard/workflow-status-summary` - ワークフローステータス概要

詳細な実装方法については、[データ可視化API実装ガイド](./frontend_data_visualization.md)を参照してください。

## 画面構成

フロントエンドの基本的な画面構成は以下の通りです：

1. **ログイン画面**（後回しでOK）
   - ユーザー認証フォーム

2. **ダッシュボード画面**
   - システム概要
   - アクティブなワークフロー
   - 最近のタスク
   - エージェントステータス

3. **ワークフロー管理画面**
   - ワークフロー一覧
   - ワークフロー作成フォーム
   - ワークフロー詳細・編集
   - 実行ステータス表示

4. **エージェント管理画面**
   - エージェント一覧
   - エージェント詳細
   - エージェント設定

5. **タスク管理画面**
   - タスク一覧
   - タスク詳細
   - タスク割り当て

6. **サンプルデータ管理画面**
   - サンプルデータ一覧
   - アップロードフォーム
   - データ詳細表示

7. **設定画面**
   - ユーザー設定
   - システム設定

## 実装優先順位

1. **認証機能とメインレイアウト**
   - ログイン画面
   - ナビゲーションバー
   - サイドメニュー

2. **ワークフロー管理画面**
   - ワークフロー一覧
   - ワークフロー詳細表示
   - 基本的な操作機能

3. **ダッシュボード画面**
   - システム概要表示
   - 簡易グラフ表示

4. **エージェント管理画面**
   - エージェント一覧
   - 基本的な操作機能

5. **タスク管理画面**
   - タスク一覧
   - タスク詳細表示

6. **サンプルデータ管理画面**
   - サンプルデータ一覧
   - アップロード機能

7. **詳細機能と拡張**
   - 高度なフィルタリング
   - 複雑なチャート
   - バッチ処理UI
   - エクスポート/インポート機能

## 共通コンポーネント

以下のような共通コンポーネントを作成することをお勧めします：

1. **レイアウトコンポーネント**
   - AppLayout (ナビゲーションバー、サイドメニュー、コンテンツエリア)
   - PageHeader
   - ContentCard

2. **データ表示コンポーネント**
   - DataTable (ページネーション、ソート、フィルタリング機能付き)
   - StatusBadge (状態表示)
   - Timeline (時系列イベント表示)
   - Charts (折れ線グラフ、円グラフ、棒グラフなど)

3. **フォームコンポーネント**
   - FormField (ラベル、入力フィールド、エラーメッセージを含む)
   - SelectField (ドロップダウン選択)
   - DateTimePicker
   - FileUploader

4. **ユーティリティコンポーネント**
   - Modal (モーダルダイアログ)
   - Toast (通知メッセージ)
   - Spinner (読み込み表示)
   - ErrorBoundary (エラーハンドリング)

## コーディング規約

- **ファイル構造**
  - コンポーネントファイル: `ComponentName.tsx`
  - スタイルファイル: `ComponentName.module.css` または `ComponentName.styles.ts`
  - テストファイル: `ComponentName.test.tsx`
  - カスタムフック: `useHookName.ts`
  - ユーティリティ関数: `utils.ts`

- **命名規則**
  - コンポーネント: PascalCase (例: `TaskList`, `AgentDetail`)
  - フック: camelCase + use接頭辞 (例: `useTaskData`, `useWorkflowStatus`)
  - 関数: camelCase (例: `formatDate`, `calculateProgress`)
  - 定数: UPPER_SNAKE_CASE (例: `API_BASE_URL`, `MAX_RETRY_COUNT`)

- **コンポーネント構造**
  ```typescript
  // imports
  import React, { useState, useEffect } from 'react';
  
  // types
  interface ComponentProps {
    // ...
  }
  
  // component
  export const ComponentName: React.FC<ComponentProps> = ({ prop1, prop2 }) => {
    // state
    const [state, setState] = useState(...);
    
    // effects
    useEffect(() => {
      // ...
    }, [dependencies]);
    
    // handlers
    const handleEvent = () => {
      // ...
    };
    
    // render
    return (
      <div>
        {/* JSX */}
      </div>
    );
  };
  
  export default ComponentName;
  ```

## エラーハンドリング

APIリクエストのエラーハンドリングには、以下のパターンを使用してください：

```typescript
const fetchData = async () => {
  try {
    const response = await axios.get('/api/v1/endpoint');
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      // Axiosからのエラー
      if (error.response) {
        // サーバーからのレスポンスがあるエラー
        const statusCode = error.response.status;
        const errorMessage = error.response.data.detail || 'Unknown error';
        
        // エラーステータスに応じた処理
        if (statusCode === 401) {
          // 認証エラー
          redirectToLogin();
        } else if (statusCode >= 500) {
          // サーバーエラー
          showServerErrorNotification(errorMessage);
        } else {
          // その他のエラー
          showErrorNotification(errorMessage);
        }
      } else if (error.request) {
        // レスポンスを受け取れなかったエラー
        showNetworkErrorNotification();
      }
    } else {
      // その他のエラー
      showGenericErrorNotification(error.message);
    }
    
    // エラーを再スロー
    throw error;
  }
};
```

## 状態管理

システム全体の状態管理には、以下のいずれかのアプローチを使用してください：

### Context APIとReducerを使用する場合

```typescript
// AuthContext.tsx
import React, { createContext, useReducer, useContext } from 'react';

interface AuthState {
  isAuthenticated: boolean;
  user: any | null;
  token: string | null;
}

type AuthAction = 
  | { type: 'LOGIN', payload: { user: any, token: string } }
  | { type: 'LOGOUT' };

const AuthContext = createContext<{
  state: AuthState;
  dispatch: React.Dispatch<AuthAction>;
} | undefined>(undefined);

const authReducer = (state: AuthState, action: AuthAction): AuthState => {
  switch (action.type) {
    case 'LOGIN':
      return {
        ...state,
        isAuthenticated: true,
        user: action.payload.user,
        token: action.payload.token
      };
    case 'LOGOUT':
      return {
        ...state,
        isAuthenticated: false,
        user: null,
        token: null
      };
    default:
      return state;
  }
};

export const AuthProvider: React.FC = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, {
    isAuthenticated: false,
    user: null,
    token: null
  });
  
  return (
    <AuthContext.Provider value={{ state, dispatch }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
```

### Redux Toolkitを使用する場合

```typescript
// authSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface AuthState {
  isAuthenticated: boolean;
  user: any | null;
  token: string | null;
}

const initialState: AuthState = {
  isAuthenticated: false,
  user: null,
  token: null
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    login(state, action: PayloadAction<{ user: any; token: string }>) {
      state.isAuthenticated = true;
      state.user = action.payload.user;
      state.token = action.payload.token;
    },
    logout(state) {
      state.isAuthenticated = false;
      state.user = null;
      state.token = null;
    }
  }
});

export const { login, logout } = authSlice.actions;
export default authSlice.reducer;
```

## APIデータフェッチング

データフェッチングには、React Queryの使用を推奨します：

```typescript
// useWorkflows.ts
import { useQuery, useMutation, useQueryClient } from 'react-query';
import axios from 'axios';

// ワークフロー一覧を取得するクエリ
export const useWorkflows = (page = 1, limit = 10) => {
  return useQuery(
    ['workflows', page, limit],
    async () => {
      const response = await axios.get(`/api/v1/workflows?page=${page}&limit=${limit}`);
      return response.data;
    },
    {
      keepPreviousData: true,
      staleTime: 5000
    }
  );
};

// ワークフロー詳細を取得するクエリ
export const useWorkflow = (id: string) => {
  return useQuery(
    ['workflow', id],
    async () => {
      const response = await axios.get(`/api/v1/workflows/${id}`);
      return response.data;
    },
    {
      enabled: !!id
    }
  );
};

// ワークフローを作成するミューテーション
export const useCreateWorkflow = () => {
  const queryClient = useQueryClient();
  
  return useMutation(
    async (workflowData: any) => {
      const response = await axios.post('/api/v1/workflows', workflowData);
      return response.data;
    },
    {
      onSuccess: () => {
        // 成功時にワークフロー一覧を再取得
        queryClient.invalidateQueries('workflows');
      }
    }
  );
};
```

## 実装上の注意点

1. **レスポンシブデザイン**
   - 全ての画面は、デスクトップ、タブレット、モバイルで適切に表示されるようにしてください。
   - Flexboxやレスポンシブグリッドを使用して、柔軟なレイアウトを実現してください。

2. **パフォーマンス**
   - 適切なメモ化（React.memo、useMemo、useCallback）を使用して不要な再レンダリングを防止してください。
   - データのプリフェッチを活用して、ユーザー体験を向上させてください。
   - 大きなリストにはウィンドウイング技術（react-window、react-virtualizedなど）を使用してください。

3. **アクセシビリティ**
   - アリアラベルと適切なセマンティックHTML要素を使用してください。
   - キーボードナビゲーションをサポートしてください。
   - 十分なコントラスト比を確保してください。

4. **セキュリティ**
   - クロスサイトスクリプティング（XSS）攻撃を防止するために、ユーザー入力を適切にエスケープしてください。
   - 機密情報はローカルストレージに保存せず、適切な場所（HttpOnly Cookie、メモリなど）に保存してください。

## 優先的に実装すべき機能

以下の機能は優先的に実装する必要があります：

1. **リアルタイム通知機能**
   - WebSocketを使用した通知システム
   - 通知センターUI
   - イベント購読メカニズム

2. **データ可視化用のコンポーネント**
   - 基本的なチャートコンポーネント（折れ線、棒、円）
   - データテーブルコンポーネント
   - ステータスカードコンポーネント

3. **ファイルアップロード/ダウンロード機能**
   - サンプルデータのアップロードUI
   - データプレビュー
   - ダウンロード機能

4. **バッチ処理と一括操作UI**
   - 複数選択とバルク操作
   - バッチ処理の進捗表示
   - 定期的なタスクスケジューリングUI

5. **エラーハンドリングとエラー表示UI**
   - エラーバウンダリー
   - ユーザーフレンドリーなエラーメッセージ
   - リトライメカニズム

## 主要コンポーネントの実装例

### ナビゲーションバー

```tsx
// NavigationBar.tsx
import React from 'react';
import { AppBar, Toolbar, Typography, Button, IconButton, Badge } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import NotificationsIcon from '@mui/icons-material/Notifications';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import { useNotifications } from './hooks/useNotifications';

interface NavigationBarProps {
  title: string;
  onMenuClick: () => void;
  onNotificationsClick: () => void;
  onProfileClick: () => void;
}

const NavigationBar: React.FC<NavigationBarProps> = ({
  title,
  onMenuClick,
  onNotificationsClick,
  onProfileClick
}) => {
  const { unreadCount } = useNotifications();
  
  return (
    <AppBar position="fixed">
      <Toolbar>
        <IconButton
          color="inherit"
          aria-label="open drawer"
          edge="start"
          onClick={onMenuClick}
          sx={{ mr: 2 }}
        >
          <MenuIcon />
        </IconButton>
        
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          {title}
        </Typography>
        
        <IconButton color="inherit" onClick={onNotificationsClick}>
          <Badge badgeContent={unreadCount} color="error">
            <NotificationsIcon />
          </Badge>
        </IconButton>
        
        <IconButton color="inherit" onClick={onProfileClick}>
          <AccountCircleIcon />
        </IconButton>
      </Toolbar>
    </AppBar>
  );
};

export default NavigationBar;
```

### ワークフロー一覧

```tsx
// WorkflowList.tsx
import React, { useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Chip,
  TablePagination,
  Button
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { useWorkflows } from '../hooks/useWorkflows';
import { formatDate } from '../utils/formatters';

const WorkflowList: React.FC = () => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  
  const { data, isLoading, error } = useWorkflows(page + 1, rowsPerPage);
  
  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };
  
  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };
  
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'created': return 'info';
      case 'in_progress': return 'primary';
      case 'completed': return 'success';
      case 'failed': return 'error';
      case 'paused': return 'warning';
      default: return 'default';
    }
  };
  
  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {(error as Error).message}</div>;
  
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2>ワークフロー一覧</h2>
        <Button variant="contained" color="primary">
          新規ワークフロー
        </Button>
      </div>
      
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>ステータス</TableCell>
              <TableCell>監査手続き</TableCell>
              <TableCell>サンプルデータ</TableCell>
              <TableCell>作成日時</TableCell>
              <TableCell>更新日時</TableCell>
              <TableCell>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data.workflows.map((workflow: any) => (
              <TableRow key={workflow.workflow_id}>
                <TableCell>{workflow.workflow_id}</TableCell>
                <TableCell>
                  <Chip
                    label={workflow.status}
                    color={getStatusColor(workflow.status)}
                    size="small"
                  />
                </TableCell>
                <TableCell>{workflow.audit_procedure_id}</TableCell>
                <TableCell>{workflow.sample_data_id}</TableCell>
                <TableCell>{formatDate(workflow.created_at)}</TableCell>
                <TableCell>{workflow.updated_at ? formatDate(workflow.updated_at) : '-'}</TableCell>
                <TableCell>
                  <IconButton size="small" title="詳細">
                    <VisibilityIcon fontSize="small" />
                  </IconButton>
                  {workflow.status === 'created' && (
                    <IconButton size="small" color="primary" title="開始">
                      <PlayArrowIcon fontSize="small" />
                    </IconButton>
                  )}
                  {workflow.status === 'in_progress' && (
                    <IconButton size="small" color="warning" title="一時停止">
                      <PauseIcon fontSize="small" />
                    </IconButton>
                  )}
                  {['created', 'completed', 'failed'].includes(workflow.status) && (
                    <IconButton size="small" color="error" title="削除">
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <TablePagination
          rowsPerPageOptions={[5, 10, 25]}
          component="div"
          count={data.count}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </TableContainer>
    </div>
  );
};

export default WorkflowList;
```

## 参考資料

- [実装仕様書](./frontend_specifications.md)
- [リアルタイム通知実装](./frontend_realtime_notifications.md)
- [データ可視化実装](./frontend_data_visualization.md)
- [実装課題リスト](./frontend_implementation_challenges.md) 