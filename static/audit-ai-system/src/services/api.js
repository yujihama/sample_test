import axios from 'axios';

// 実際のAPIサーバーのURL（Json-server用）
const API_BASE_URL = 'http://localhost:3002';

// Axiosインスタンスの作成
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// リクエストインターセプター
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    
    // APIキーが必要な場合は直接指定
    // const apiKey = 'your_api_key_here';
    // if (apiKey) {
    //   config.headers['X-API-Key'] = apiKey;
    // }
    
    console.log('APIリクエスト送信:', {
      method: config.method.toUpperCase(),
      url: config.url,
      baseURL: config.baseURL,
      fullURL: config.baseURL + config.url
    });
    return config;
  },
  (error) => {
    console.error('APIリクエスト送信エラー:', error);
    return Promise.reject(error);
  }
);

// レスポンスインターセプター（例: エラーハンドリングなど）
apiClient.interceptors.response.use(
  (response) => {
    console.log('APIレスポンス受信:', {
      url: response.config.url,
      status: response.status,
      data: response.data
    });
    
    // json-serverからのレスポンス構造をアプリケーションの期待する形式に変換
    // ダッシュボードエンドポイントの場合、ネストされた構造を展開
    if (response.config.url.includes('/api/v1/dashboard')) {
      console.log('ダッシュボードAPI処理:', response.config.url);
      
      // すでにデータがネストされたオブジェクトかどうかを判断
      if (response.data && typeof response.data === 'object' && !Array.isArray(response.data)) {
        if (response.config.url.includes('/summary')) {
          console.log('サマリーデータ変換');
          return { ...response, data: { summary: response.data.summary } };
        }
        if (response.config.url.includes('/process-status')) {
          console.log('処理ステータスデータ変換');
          return { ...response, data: { "process-status": response.data["process-status"] } };
        }
      }
      
      // 活動ログとアラートのエンドポイントの処理
      if (response.config.url.includes('/activity')) {
        console.log('活動ログデータ変換前:', response.data);
        // 配列データをdata配列としてラップする
        if (Array.isArray(response.data)) {
          console.log('活動ログデータ配列を変換します');
          return { ...response, data: { data: response.data } };
        } else {
          console.log('活動ログデータ形式:', typeof response.data);
        }
      }
      
      if (response.config.url.includes('/alerts')) {
        console.log('アラートデータ変換前:', response.data);
        // 配列データをdata配列としてラップする
        if (Array.isArray(response.data)) {
          console.log('アラートデータ配列を変換します');
          return { ...response, data: { data: response.data } };
        } else {
          console.log('アラートデータ形式:', typeof response.data);
        }
      }
    }
    
    return response;
  },
  (error) => {
    // エラーハンドリング（例: 401エラーの場合はログアウトするなど）
    if (error.response && error.response.status === 401) {
      // 認証切れの処理
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    console.error('APIエラー詳細:', {
      url: error.config ? error.config.url : 'URLなし',
      message: error.message,
      response: error.response ? {
        status: error.response.status,
        data: error.response.data
      } : 'レスポンスなし'
    });
    return Promise.reject(error);
  }
);

/**
 * レスポンスを標準形式に変換する関数
 * @param {any} data - レスポンスデータ
 * @returns {Object} 標準化されたレスポンス
 */
const wrapResponse = (data) => {
  return { 
    success: true, 
    data: data 
  };
};

// API呼び出し関数群 
// これらの関数は各コンポーネントから呼び出されます

// ダッシュボード関連API
export const dashboardApi = {
  // ダッシュボード概要データの取得
  getSummary: () => {
    return apiClient.get('/api/v1/dashboard/summary')
      .then(response => wrapResponse(response.data));
  },
  
  // 処理状況データの取得
  getProcessStatus: () => {
    return apiClient.get('/api/v1/dashboard/process-status')
      .then(response => wrapResponse(response.data));
  },
  
  // アクティビティログの取得
  getActivityLog: (params) => {
    return apiClient.get('/api/v1/dashboard/activity', { params })
      .then(response => wrapResponse(response.data));
  },
  
  // アラート一覧の取得
  getAlerts: (params) => {
    return apiClient.get('/api/v1/dashboard/alerts', { params })
      .then(response => wrapResponse(response.data));
  }
};

// エージェント関連API
export const agentApi = {
  // エージェント一覧の取得
  getAgents: () => {
    return apiClient.get('/api/v1/agents')
      .then(response => wrapResponse(response.data));
  },
  
  // エージェント間のメッセージフローの取得
  getMessageFlow: (params) => {
    return apiClient.get('/agentFlow', { params })
      .then(response => wrapResponse(response.data));
  },
  
  // 特定のエージェントの詳細を取得
  getAgentDetails: (agentId) => {
    return apiClient.get(`/api/v1/agents/${agentId}`)
      .then(response => wrapResponse(response.data));
  }
};

// 人間介入インターフェース関連API
export const interventionApi = {
  // 問い合わせ一覧の取得
  getQueries: (params) => {
    return apiClient.get('/api/v1/interventions/queries', { params })
      .then(response => wrapResponse(response.data));
  },
  
  // 特定の問い合わせの詳細を取得
  getQueryDetails: (queryId) => {
    return apiClient.get(`/api/v1/interventions/queries/${queryId}`)
      .then(response => wrapResponse(response.data));
  },
  
  // 問い合わせへの回答を送信
  sendResponse: (queryId, responseData) => {
    return apiClient.post(`/api/v1/interventions/queries/${queryId}/respond`, responseData)
      .then(response => wrapResponse(response.data));
  }
};

// サンプル管理関連API
export const sampleApi = {
  // サンプル一覧の取得
  getSamples: (params) => {
    return apiClient.get('/api/v1/samples', { params })
      .then(response => wrapResponse(response.data));
  },
  
  // 特定のサンプルの詳細を取得
  getSampleDetails: (sampleId) => {
    return apiClient.get(`/api/v1/samples/${sampleId}`)
      .then(response => wrapResponse(response.data));
  },
  
  // 新規サンプルの登録
  createSample: (sampleData) => {
    return apiClient.post('/api/v1/samples', sampleData)
      .then(response => wrapResponse(response.data));
  },
  
  // サンプルの更新
  updateSample: (sampleId, sampleData) => {
    return apiClient.put(`/api/v1/samples/${sampleId}`, sampleData)
      .then(response => wrapResponse(response.data));
  },
  
  // サンプルの削除
  deleteSample: (sampleId) => {
    return apiClient.delete(`/api/v1/samples/${sampleId}`)
      .then(response => wrapResponse(response.data));
  }
};

// 分析ダッシュボード関連API
export const analysisApi = {
  // 異常検出分析データの取得
  getAnomalyData: (params) => {
    return apiClient.get('/api/v1/analysis/anomalies', { params })
      .then(response => wrapResponse(response.data));
  },
  
  // カテゴリ分析データの取得
  getCategoryData: (params) => {
    return apiClient.get('/api/v1/analysis/categories', { params })
      .then(response => wrapResponse(response.data));
  },
  
  // トレンドデータの取得
  getTrendData: (params) => {
    return apiClient.get('/api/v1/analysis/trends', { params })
      .then(response => wrapResponse(response.data));
  },
  
  // リスク相関データの取得
  getRiskCorrelation: (params) => {
    return apiClient.get('/api/v1/analysis/risk-correlation', { params })
      .then(response => wrapResponse(response.data));
  },
  
  // AIインサイトの取得
  getInsights: (params) => {
    return apiClient.get('/api/v1/analysis/insights', { params })
      .then(response => wrapResponse(response.data));
  },
  
  // レポート一覧の取得
  getReports: (params) => {
    return apiClient.get('/api/v1/analysis/reports', { params })
      .then(response => wrapResponse(response.data));
  }
};

// システム設定関連API
export const settingsApi = {
  // エージェント設定の取得
  getAgentSettings: () => {
    return apiClient.get('/api/v1/settings/agents')
      .then(response => wrapResponse(response.data));
  },
  
  // エージェント設定の更新
  updateAgentSettings: (agentId, settingsData) => {
    return apiClient.put(`/api/v1/settings/agents/${agentId}`, settingsData)
      .then(response => wrapResponse(response.data));
  },
  
  // 外部ツール連携設定の取得
  getIntegrations: () => {
    return apiClient.get('/api/v1/settings/integrations')
      .then(response => wrapResponse(response.data));
  },
  
  // 外部ツール連携設定の更新
  updateIntegration: (integrationId, integrationData) => {
    return apiClient.put(`/api/v1/settings/integrations/${integrationId}`, integrationData)
      .then(response => wrapResponse(response.data));
  }
};

// 認証関連API
export const authApi = {
  // ログイン
  login: (credentials) => {
    return apiClient.post('/auth/login', credentials)
      .then(response => wrapResponse(response.data));
  },
  
  // ログアウト
  logout: () => {
    return apiClient.post('/auth/logout')
      .then(response => wrapResponse(response.data));
  },
  
  // ユーザープロファイルの取得
  getProfile: () => {
    return apiClient.get('/auth/profile')
      .then(response => wrapResponse(response.data));
  }
};

export default {
  dashboard: dashboardApi,
  agent: agentApi,
  intervention: interventionApi,
  sample: sampleApi,
  analysis: analysisApi,
  settings: settingsApi,
  auth: authApi
}; 