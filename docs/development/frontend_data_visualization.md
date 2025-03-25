# データ可視化API - フロントエンド実装ガイド

## 概要
このドキュメントでは、フロントエンドでシステムデータを可視化するためのAPIエンドポイントについて説明します。データ可視化APIは、ダッシュボード、チャート、グラフなどの作成に必要なデータを提供します。

## APIエンドポイント

### 1. システムステータス取得 API

```
GET /api/v1/dashboard/system-status
```

**説明**: システム全体のステータス情報を取得します。ダッシュボードのヘッダー部分や概要パネルの表示に使用できます。

**レスポンス例**:
```json
{
  "agent_count": 5,
  "active_agents": 3,
  "workflow_count": 42,
  "active_workflows": 8,
  "task_count": 127,
  "pending_tasks": 15,
  "completed_tasks": 98,
  "error_count": 4,
  "latest_activity": "2023-06-15T13:45:22.123456",
  "system_health": {
    "cpu_usage": 35.5,
    "memory_usage": 42.8,
    "disk_usage": 68.2,
    "network_status": "healthy",
    "database_status": "healthy",
    "api_response_time": 250
  }
}
```

**使用例**:
```typescript
// システム概要を取得してダッシュボードに表示する
const fetchSystemStatus = async () => {
  try {
    const response = await axios.get('/api/v1/dashboard/system-status');
    setSystemStatus(response.data);
  } catch (error) {
    console.error('Failed to fetch system status', error);
  }
};
```

### 2. ワークフロー傾向データ API

```
GET /api/v1/dashboard/workflow-trends?time_range={time_range}&metric={metric}
```

**説明**: 指定した期間のワークフロー関連メトリクスの時系列データを取得します。

**パラメータ**:
- `time_range`: 時間範囲 ("1h", "24h", "7d", "30d")
- `metric`: 取得するメトリック ("count", "completion_rate")

**レスポンス例**:
```json
{
  "series_name": "workflow_count",
  "data": [
    {
      "timestamp": "2023-06-14T00:00:00",
      "value": 5,
      "label": "06/14"
    },
    {
      "timestamp": "2023-06-15T00:00:00",
      "value": 8,
      "label": "06/15"
    }
  ],
  "metadata": {
    "time_range": "7d",
    "metric": "count",
    "unit": "count"
  }
}
```

**使用例**:
```typescript
// 過去7日間のワークフロー数の傾向をラインチャートで表示
const fetchWorkflowTrends = async () => {
  try {
    const response = await axios.get('/api/v1/dashboard/workflow-trends?time_range=7d&metric=count');
    
    // Chart.jsなどのライブラリ用にデータを変換
    const chartData = {
      labels: response.data.data.map(point => point.label),
      datasets: [{
        label: 'ワークフロー数',
        data: response.data.data.map(point => point.value),
        borderColor: '#4299e1',
        backgroundColor: 'rgba(66, 153, 225, 0.2)'
      }]
    };
    
    setChartData(chartData);
  } catch (error) {
    console.error('Failed to fetch workflow trends', error);
  }
};
```

### 3. エージェントパフォーマンス API

```
GET /api/v1/dashboard/agent-performance?limit={limit}&sort_by={sort_by}
```

**説明**: エージェントのパフォーマンス統計情報を取得します。

**パラメータ**:
- `limit`: 取得する最大エージェント数 (デフォルト: 10, 最大: 50)
- `sort_by`: ソート基準 ("task_count", "completed_tasks", "failed_tasks", "average_completion_time")

**レスポンス例**:
```json
[
  {
    "agent_id": "agent1",
    "agent_type": "validator",
    "task_count": 45,
    "completed_tasks": 42,
    "failed_tasks": 3,
    "average_completion_time": 12.5,
    "last_active": "2023-06-15T14:22:10.123456"
  },
  {
    "agent_id": "agent2",
    "agent_type": "auditor",
    "task_count": 38,
    "completed_tasks": 35,
    "failed_tasks": 1,
    "average_completion_time": 18.2,
    "last_active": "2023-06-15T13:45:22.123456"
  }
]
```

**使用例**:
```typescript
// 完了タスク数順にエージェントパフォーマンスを表示
const fetchTopAgents = async () => {
  try {
    const response = await axios.get('/api/v1/dashboard/agent-performance?limit=5&sort_by=completed_tasks');
    setTopAgents(response.data);
  } catch (error) {
    console.error('Failed to fetch agent performance', error);
  }
};
```

### 4. タスク分布 API

```
GET /api/v1/dashboard/task-distribution
```

**説明**: タスクタイプごとの分布を取得します。円グラフなどの表示に適しています。

**レスポンス例**:
```json
{
  "validation": 42,
  "audit": 35,
  "collection": 28,
  "reporting": 15,
  "unknown": 7
}
```

**使用例**:
```typescript
// タスクタイプの分布を円グラフで表示
const fetchTaskDistribution = async () => {
  try {
    const response = await axios.get('/api/v1/dashboard/task-distribution');
    
    // データを円グラフ用に変換
    const chartData = {
      labels: Object.keys(response.data),
      datasets: [{
        data: Object.values(response.data),
        backgroundColor: [
          '#4299e1', '#48bb78', '#ecc94b', '#ed8936', '#a0aec0'
        ]
      }]
    };
    
    setPieChartData(chartData);
  } catch (error) {
    console.error('Failed to fetch task distribution', error);
  }
};
```

### 5. ワークフローステータス概要 API

```
GET /api/v1/dashboard/workflow-status-summary
```

**説明**: ワークフローのステータスごとの数を集計します。

**レスポンス例**:
```json
{
  "created": 5,
  "in_progress": 8,
  "completed": 42,
  "failed": 3,
  "paused": 2
}
```

**使用例**:
```typescript
// ワークフローステータスの概要をバッジで表示
const fetchWorkflowStatusSummary = async () => {
  try {
    const response = await axios.get('/api/v1/dashboard/workflow-status-summary');
    setWorkflowStatusSummary(response.data);
  } catch (error) {
    console.error('Failed to fetch workflow status summary', error);
  }
};
```

## 既存のダッシュボードAPIとの互換性

以下の既存のエンドポイントも引き続き利用可能です：

- `GET /api/v1/dashboard/dashboard/summary` - ダッシュボードの概要データ
- `GET /api/v1/dashboard/dashboard/process-status` - 処理状況データ
- `GET /api/v1/dashboard/dashboard/activity` - アクティビティログ
- `GET /api/v1/dashboard/dashboard/alerts` - アラート情報

## 実装例

### リアルタイムダッシュボード

```typescript
import React, { useEffect, useState } from 'react';
import { Line, Pie, Bar } from 'react-chartjs-2';
import axios from 'axios';
import { useNotifications } from './NotificationProvider';

const Dashboard = () => {
  const [systemStatus, setSystemStatus] = useState(null);
  const [workflowTrends, setWorkflowTrends] = useState(null);
  const [taskDistribution, setTaskDistribution] = useState(null);
  const [topAgents, setTopAgents] = useState([]);
  const { subscribeTopic } = useNotifications();
  
  // データ取得関数の定義
  const fetchDashboardData = async () => {
    try {
      // 並列でデータを取得
      const [
        systemResponse,
        trendsResponse,
        distributionResponse,
        agentsResponse
      ] = await Promise.all([
        axios.get('/api/v1/dashboard/system-status'),
        axios.get('/api/v1/dashboard/workflow-trends?time_range=7d&metric=count'),
        axios.get('/api/v1/dashboard/task-distribution'),
        axios.get('/api/v1/dashboard/agent-performance?limit=5&sort_by=completed_tasks')
      ]);
      
      setSystemStatus(systemResponse.data);
      
      // ワークフロー傾向データをチャート用に変換
      setWorkflowTrends({
        labels: trendsResponse.data.data.map(point => point.label),
        datasets: [{
          label: 'ワークフロー数',
          data: trendsResponse.data.data.map(point => point.value),
          borderColor: '#4299e1',
          backgroundColor: 'rgba(66, 153, 225, 0.2)'
        }]
      });
      
      // タスク分布データをチャート用に変換
      setTaskDistribution({
        labels: Object.keys(distributionResponse.data),
        datasets: [{
          data: Object.values(distributionResponse.data),
          backgroundColor: [
            '#4299e1', '#48bb78', '#ecc94b', '#ed8936', '#a0aec0'
          ]
        }]
      });
      
      setTopAgents(agentsResponse.data);
    } catch (error) {
      console.error('Failed to fetch dashboard data', error);
    }
  };
  
  // コンポーネントマウント時にデータを取得
  useEffect(() => {
    fetchDashboardData();
    
    // 定期的な更新をセットアップ（オプション）
    const interval = setInterval(fetchDashboardData, 60000); // 1分ごとに更新
    
    return () => clearInterval(interval);
  }, []);
  
  // 関連トピックを購読（WebSocket通知機能と連携）
  useEffect(() => {
    subscribeTopic('workflow_completed');
    subscribeTopic('workflow_failed');
    subscribeTopic('agent_status_changed');
    
    // 通知が届いたらデータを更新する処理は
    // NotificationProviderのコールバックで実装可能
  }, [subscribeTopic]);
  
  if (!systemStatus || !workflowTrends || !taskDistribution) {
    return <div>Loading dashboard data...</div>;
  }
  
  return (
    <div className="dashboard">
      {/* システムステータス表示 */}
      <div className="status-cards">
        <StatusCard
          title="エージェント"
          count={systemStatus.agent_count}
          active={systemStatus.active_agents}
        />
        <StatusCard
          title="ワークフロー"
          count={systemStatus.workflow_count}
          active={systemStatus.active_workflows}
        />
        <StatusCard
          title="タスク"
          count={systemStatus.task_count}
          completed={systemStatus.completed_tasks}
          pending={systemStatus.pending_tasks}
        />
        <StatusCard
          title="エラー"
          count={systemStatus.error_count}
          severity="error"
        />
      </div>
      
      {/* チャート表示 */}
      <div className="charts">
        <div className="chart-container">
          <h3>ワークフロー傾向</h3>
          <Line data={workflowTrends} options={lineChartOptions} />
        </div>
        
        <div className="chart-container">
          <h3>タスク分布</h3>
          <Pie data={taskDistribution} options={pieChartOptions} />
        </div>
      </div>
      
      {/* トップエージェント表示 */}
      <div className="top-agents">
        <h3>最もアクティブなエージェント</h3>
        <table>
          <thead>
            <tr>
              <th>エージェントID</th>
              <th>タイプ</th>
              <th>完了タスク数</th>
              <th>失敗タスク数</th>
              <th>平均完了時間</th>
            </tr>
          </thead>
          <tbody>
            {topAgents.map(agent => (
              <tr key={agent.agent_id}>
                <td>{agent.agent_id}</td>
                <td>{agent.agent_type}</td>
                <td>{agent.completed_tasks}</td>
                <td>{agent.failed_tasks}</td>
                <td>{agent.average_completion_time.toFixed(2)}秒</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Dashboard;
```

## データキャッシュ戦略

APIから取得したデータをキャッシュして、パフォーマンスを向上させるには、React Queryなどのライブラリを使用することをお勧めします：

```typescript
import { useQuery } from 'react-query';
import axios from 'axios';

// APIからデータを取得する関数
const fetchSystemStatus = () => axios.get('/api/v1/dashboard/system-status').then(res => res.data);

// コンポーネント内で使用
const SystemStatusComponent = () => {
  const { data, isLoading, error } = useQuery(
    'systemStatus',  // クエリキー
    fetchSystemStatus,
    {
      refetchInterval: 60000,  // 1分ごとに自動的に再取得
      staleTime: 30000,        // 30秒間はデータを新鮮と見なす
      cacheTime: 3600000,      // 1時間キャッシュを保持
      retry: 3                 // エラー時に3回まで再試行
    }
  );
  
  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  
  return (
    <div>
      <h2>システムステータス</h2>
      <p>アクティブエージェント: {data.active_agents}/{data.agent_count}</p>
      <p>実行中ワークフロー: {data.active_workflows}/{data.workflow_count}</p>
    </div>
  );
};
```

## エラーハンドリング

APIリクエストでエラーが発生した場合の処理例：

```typescript
const fetchData = async () => {
  try {
    const response = await axios.get('/api/v1/dashboard/system-status');
    return response.data;
  } catch (error) {
    if (error.response) {
      // サーバーからのレスポンスがあるエラー（4xx/5xx）
      console.error(`Server error: ${error.response.status} - ${error.response.data.detail || 'Unknown error'}`);
      
      // ステータスコードに応じた処理
      if (error.response.status === 401) {
        // 認証エラー - ログインページにリダイレクト
        navigate('/login');
      } else if (error.response.status === 503) {
        // サービス利用不可 - メンテナンス中の可能性
        setMaintenanceMode(true);
      }
    } else if (error.request) {
      // リクエストは送信されたがレスポンスがない
      console.error('Network error: No response received');
      setOfflineMode(true);
    } else {
      // リクエスト設定時に発生したエラー
      console.error(`Request error: ${error.message}`);
    }
    
    // エラーをスローして呼び出し元で処理できるようにする
    throw error;
  }
};
``` 