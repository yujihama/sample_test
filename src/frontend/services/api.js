import axios from 'axios';
import { loggerService } from './logger';

// 実際のPythonバックエンドAPIサーバーのURL
const API_BASE_URL = 'http://localhost:3002';  // json-server URL

// 認証用APIキー
const API_KEY = 'test_token';

/**
 * APIレスポンスの標準形式
 * @typedef {Object} ApiResponse
 * @property {boolean} success - リクエスト成功フラグ
 * @property {any} data - レスポンスデータ
 * @property {string|null} error - エラーメッセージ
 * @property {number|null} status - HTTPステータスコード
 */

/**
 * レスポンスを標準形式に変換する関数
 * @param {Object} response - Axiosレスポンス
 * @returns {ApiResponse} 標準化されたレスポンス
 */
const normalizeResponse = (response) => {
  return {
    success: true,
    data: response.data,
    error: null,
    status: response.status
  };
};

/**
 * エラーを標準形式に変換する関数
 * @param {Error} error - エラーオブジェクト
 * @returns {ApiResponse} 標準化されたエラーレスポンス
 */
const normalizeError = (error) => {
  // レスポンスがある場合
  if (error.response) {
    return {
      success: false,
      data: error.response.data || null,
      error: error.response.data?.message || error.message || 'APIリクエストエラー',
      status: error.response.status
    };
  }
  
  // レスポンスがない場合（ネットワークエラーなど）
  return {
    success: false,
    data: null,
    error: error.message || 'ネットワークエラー',
    status: null
  };
};

/**
 * モックデータを標準形式に変換する関数
 * @param {any} mockData - モックデータ
 * @param {string} [errorMessage] - エラーメッセージ（省略時はモックデータを成功レスポンスとして扱う）
 * @returns {ApiResponse} 標準化されたモックレスポンス
 */
const mockResponse = (mockData, errorMessage = null) => {
  if (errorMessage) {
    return {
      success: false,
      data: mockData,
      error: errorMessage,
      status: 200 // モックなのでステータスコードは200を返す
    };
  }
  
  return {
    success: true,
    data: mockData,
    error: null,
    status: 200
  };
};

// Axiosインスタンスの作成
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// リクエストインターセプター - APIキーを追加
apiClient.interceptors.request.use(
  (config) => {
    // API認証用トークンを設定
    config.headers['Authorization'] = `Bearer ${API_KEY}`;

    // URLの修正: すでに完全なURLまたは/api/v1で始まるパスの場合は修正しない
    if (!config.url.startsWith('http') && 
        !config.url.startsWith('/api/v1/') && 
        !config.url.includes('api/v1/') && 
        !config.url.startsWith('/health') && 
        !config.url.startsWith('/version')) {
      config.url = `/api/v1/${config.url.startsWith('/') ? config.url.substring(1) : config.url}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// レスポンスインターセプターの追加
apiClient.interceptors.response.use(
  (response) => {
    // 成功時の処理
    return response;
  },
  (error) => {
    // エラーログの送信
    if (error.response) {
      // サーバーからのレスポンスがある場合
      loggerService.logError(
        new Error(`API Error: ${error.response.status} ${error.response.statusText}`),
        {
          url: error.config.url,
          method: error.config.method,
          responseData: error.response.data
        }
      );
    } else if (error.request) {
      // レスポンスを受け取れなかった場合
      loggerService.logError(
        new Error('ネットワークエラー: サーバーからの応答がありません'),
        {
          url: error.config.url,
          method: error.config.method
        }
      );
    } else {
      // リクエスト設定中のエラー
      loggerService.logError(error, {
        message: 'リクエスト設定エラー',
        config: error.config
      });
    }
    
    return Promise.reject(error);
  }
);

/**
 * 安全なAPIリクエスト実行関数
 * @param {Function} apiCall - API呼び出し関数
 * @param {Object} mockData - APIが失敗した場合のフォールバックモックデータ
 * @param {string} logContext - ログコンテキスト
 * @param {boolean} useMockOnError - エラー時にモックデータを使用するかどうか
 * @returns {Promise<ApiResponse>} 標準化されたレスポンス
 */
const safeApiCall = async (apiCall, mockData, logContext, useMockOnError = false) => {
  try {
    const response = await apiCall();
    return normalizeResponse(response);
  } catch (error) {
    if (error.name === 'AbortError') {
      throw error; // アボートエラーはそのまま再スロー
    }
    
    // エラーロギング（インターセプターですでに記録されているが、コンテキストを追加）
    loggerService.logError(`${logContext}のAPIエンドポイントでエラーが発生しました。`, {
      error: error.message,
      useMock: false // 常にfalseに設定
    });
    
    // モックデータを使用しない - 常にエラーを返す
    return normalizeError(error);
  }
};

// API呼び出し関数群
// これらの関数は各コンポーネントから呼び出されます

// ダッシュボード関連API
export const dashboardApi = {
  // ダッシュボード概要データの取得
  getSummary: async (options = {}) => {
    const mockData = { 
      summary: { 
        processingSamples: 0,
        processingSamplesTrend: 0,
        completedSamples: 0,
        completedSamplesTrend: 0,
        pendingSamples: 0,
        pendingSamplesTrend: 0,
        alertCount: 0,
        alertCountTrend: 0
      }
    };
    
    try {
      // パスを直接指定（完全なパス）
      return await safeApiCall(
        () => apiClient.get('dashboard/summary', options),
        mockData,
        'ダッシュボード概要',
        false // モックデータを使用しない（重要な機能）
      );
    } catch (error) {
      // AbortErrorはそのまま再スロー
      if (error.name === 'AbortError') {
        throw error;
      }
      
      // エラーをそのまま返却
      return normalizeError(error);
    }
  },
  
  // 処理状況データの取得
  getProcessStatus: async (options = {}) => {
    const mockData = { 
      'process-status': { 
        categories: [],
        periodData: [],
        sampleStatus: []
      }
    };
    
    try {
      return await safeApiCall(
        () => apiClient.get('dashboard/process-status', options),
        mockData,
        '処理状況',
        false // モックデータを使用しない（重要な機能）
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      return normalizeError(error);
    }
  },
  
  // アクティビティログの取得
  getActivityLog: async (params = {}, options = {}) => {
    const mockData = { activities: [] };
    
    try {
      return await safeApiCall(
        () => apiClient.get('dashboard/activity', { 
          params,
          ...options 
        }),
        mockData,
        'アクティビティログ',
        false // モックデータを使用しない（重要度がそれほど高くない補助的機能でも本番データを使用）
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      return normalizeError(error);
    }
  },
  
  // アラート一覧の取得
  getAlerts: async (params = {}, options = {}) => {
    const mockData = { alerts: [] };
    
    try {
      return await safeApiCall(
        () => apiClient.get('dashboard/alerts', { 
          params,
          ...options 
        }),
        mockData,
        'アラート一覧',
        false // モックデータを使用しない（重要度がそれほど高くない補助的機能でも本番データを使用）
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      return normalizeError(error);
    }
  }
};

// エージェント関連API
export const agentApi = {
  // エージェント一覧の取得
  getAgents: async (options = {}) => {
    const mockData = {
      agents: [
        { id: 'agent_a', type: '異常検出', status: 'active', stats: { completed: 42, inProgress: 5 } },
        { id: 'agent_b', type: 'ルール検証', status: 'active', stats: { completed: 38, inProgress: 3 } },
        { id: 'agent_c', type: 'サンプル分析', status: 'warning', stats: { completed: 27, inProgress: 8 } },
        { id: 'agent_d', type: '報告生成', status: 'error', stats: { completed: 18, inProgress: 2 } },
        { id: 'coordinator', type: '調整', status: 'active', stats: { completed: 120, inProgress: 0 } }
      ]
    };
    
    try {
      return await safeApiCall(
        () => apiClient.get('/api/v1/agents', options),
        mockData,
        'エージェント一覧',
        false // モックデータを使用しない（重要な機能）
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      return normalizeError(error);
    }
  },
  
  // エージェント間のメッセージフロー取得
  getMessageFlow: async (options = {}) => {
    const mockData = {
      nodes: [
        { id: 'agent_a', label: '異常検出エージェント', type: 'detection' },
        { id: 'agent_b', label: 'ルール検証エージェント', type: 'validation' },
        { id: 'agent_c', label: 'サンプル分析エージェント', type: 'analysis' },
        { id: 'agent_d', label: '報告生成エージェント', type: 'reporting' },
        { id: 'coordinator', label: '調整エージェント', type: 'coordinator' }
      ],
      links: [
        { source: 'agent_a', target: 'coordinator', value: 25 },
        { source: 'coordinator', target: 'agent_b', value: 18 },
        { source: 'agent_b', target: 'coordinator', value: 15 },
        { source: 'coordinator', target: 'agent_c', value: 12 },
        { source: 'agent_c', target: 'coordinator', value: 10 },
        { source: 'coordinator', target: 'agent_d', value: 8 },
        { source: 'agent_d', target: 'coordinator', value: 6 }
      ]
    };
    
    try {
      return await safeApiCall(
        () => apiClient.get('/agentFlow', options),
        mockData,
        'メッセージフロー',
        false // モックデータを使用しない（グラフ表示でも本番データを使用）
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      return normalizeError(error);
    }
  },
  
  // 特定のエージェント詳細情報の取得
  getAgentDetails: async (agentId, options = {}) => {
    if (!agentId) {
      return mockResponse(null, 'エージェントIDが指定されていません');
    }
    
    const mockData = {
      id: agentId,
      type: 'サンプル分析',
      status: 'active',
      created_at: new Date().toISOString(),
      last_active: new Date().toISOString(),
      capabilities: ['データ分析', 'パターン検出'],
      stats: {
        completed: 45,
        inProgress: 3,
        failed: 2,
        totalProcessingTime: '2h 15m'
      }
    };
    
    try {
      return await safeApiCall(
        () => apiClient.get(`/api/v1/agents/${agentId}`, options),
        mockData,
        'エージェント詳細',
        false // モックデータを使用しない（重要な機能）
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      return normalizeError(error);
    }
  }
};

// 人間介入関連API
export const interventionApi = {
  // 介入リクエスト一覧の取得
  getQueries: async (options = {}) => {
    const mockData = { 
      queries: [
        {
          id: 'mock-query-1',
          title: 'サンプル承認要求',
          description: 'これはサンプルの承認要求です。実際のAPIエンドポイントが実装されていないか、正しく動作していません。',
          status: 'pending',
          created_at: new Date().toISOString(),
          priority: 'medium'
        }
      ] 
    };
    
    try {
      // GETメソッドを使用してクエリ一覧を取得
      return await safeApiCall(
        () => apiClient.get('/api/v1/human/query', options),
        mockData,
        '人間介入リクエスト',
        false // モックデータを使用しない
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      return mockResponse(mockData);
    }
  },
  
  // フィルター付きクエリの取得
  getQueriesWithFilter: async (filter, options = {}) => {
    const mockData = { 
      queries: [
        {
          id: 'mock-query-1',
          title: 'サンプル承認要求',
          description: 'これはサンプルの承認要求です。実際のAPIエンドポイントが実装されていないか、正しく動作していません。',
          status: 'pending',
          created_at: new Date().toISOString(),
          priority: 'medium'
        }
      ] 
    };
    
    try {
      // query_textを含めたPOSTリクエスト
      const payload = {
        filter: filter,
        query_text: ""  // 必須フィールド
      };
      
      return await safeApiCall(
        () => apiClient.post('/api/v1/human/query', payload, options),
        mockData,
        'フィルター付き人間介入リクエスト',
        false // モックデータを使用しない
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      return mockResponse(mockData);
    }
  },
  
  // 介入リクエストへの回答
  respondToQuery: async (queryId, response, options = {}) => {
    if (!queryId) {
      return mockResponse(null, 'クエリIDが指定されていません');
    }
    
    const mockData = { 
      status: 'success',
      message: 'この機能はモックされています。実際の応答は送信されていません。'
    };
    
    const payload = {
      query_id: queryId,
      response_text: typeof response === 'string' ? response : JSON.stringify(response),
      additional_data: typeof response === 'object' ? response : {}
    };
    
    try {
      return await safeApiCall(
        () => apiClient.post('/api/v1/human/response', payload, options),
        mockData,
        '人間介入レスポンス',
        false // モックデータを使用しない
      );
    } catch (error) {
      // まずバックアップエンドポイントを試す
      try {
        const result = await apiClient.post(`/api/v1/interventions/queries/${queryId}/respond`, { response }, options);
        return normalizeResponse(result);
      } catch (backupError) {
        if (error.name === 'AbortError' || backupError.name === 'AbortError') {
          throw error;
        }
        
        return mockResponse(mockData);
      }
    }
  }
};

// サンプル管理API
export const sampleApi = {
  // サンプル一覧の取得
  getSamples: async (params = {}, options = {}) => {
    const mockData = {
      samples: [
        {
          id: 'sample-001',
          name: 'テストサンプル1',
          status: 'processing',
          created_at: new Date(Date.now() - 3600000).toISOString(),
          type: 'financial'
        },
        {
          id: 'sample-002',
          name: 'テストサンプル2',
          status: 'completed',
          created_at: new Date(Date.now() - 7200000).toISOString(),
          type: 'operational'
        }
      ],
      total: 2,
      page: 1,
      per_page: 10
    };
    
    try {
      // RESTful APIに準拠してGETメソッドを使用
      return await safeApiCall(
        () => apiClient.get('/api/v1/samples', { 
          params,
          ...options 
        }),
        mockData,
        'サンプル一覧',
        false // モックデータを使用しない
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      // エラー時はエラーを返し、モックデータは使用しない
      return normalizeError(error);
    }
  },
  
  // サンプル詳細の取得
  getSampleDetails: async (sampleId, options = {}) => {
    if (!sampleId) {
      return mockResponse(null, 'サンプルIDが指定されていません');
    }
    
    const mockData = {
      id: sampleId,
      name: `テストサンプル ${sampleId}`,
      description: 'これはテスト用のサンプルデータです',
      status: 'completed',
      created_at: new Date(Date.now() - 3600000).toISOString(),
      updated_at: new Date().toISOString(),
      type: 'financial',
      metadata: {
        source: 'manual',
        format: 'excel',
        size: '250KB',
        rows: 500
      },
      results: {
        anomalies: 2,
        validation_errors: 0,
        warnings: 3
      }
    };
    
    try {
      return await safeApiCall(
        () => apiClient.get(`/api/v1/samples/${sampleId}`, options),
        mockData,
        'サンプル詳細'
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      return mockResponse(mockData);
    }
  },
  
  // 新規サンプルの登録
  createSample: async (sampleData, options = {}) => {
    if (!sampleData) {
      return mockResponse(null, 'サンプルデータが指定されていません');
    }
    
    const mockData = {
      id: `sample-${Date.now()}`,
      ...sampleData,
      created_at: new Date().toISOString(),
      status: 'pending'
    };
    
    try {
      // バックエンドAPIと整合性を保つため、file_sizeフィールドを除外
      const requestParams = {
        ...sampleData,
        filename: sampleData.filename || '',
        file_path: sampleData.file_path || '',
        file_type: sampleData.file_type || ''
      };
      
      return await safeApiCall(
        () => apiClient.post('/api/v1/samples', requestParams, options),
        mockData,
        'サンプル作成',
        false // モックデータを使用しない
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      // エラー時はエラーを返し、モックデータは使用しない
      return normalizeError(error);
    }
  },
  
  // サンプル情報の更新
  updateSample: async (sampleId, sampleData, options = {}) => {
    if (!sampleId) {
      return mockResponse(null, 'サンプルIDが指定されていません');
    }
    
    if (!sampleData) {
      return mockResponse(null, '更新データが指定されていません');
    }
    
    const mockData = {
      id: sampleId,
      ...sampleData,
      updated_at: new Date().toISOString()
    };
    
    try {
      return await safeApiCall(
        () => apiClient.put(`/api/v1/samples/${sampleId}`, sampleData, options),
        mockData,
        'サンプル更新'
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      return mockResponse(mockData);
    }
  }
};

// 分析結果API
export const analysisApi = {
  // 分析結果一覧の取得
  getResults: async (params = {}, options = {}) => {
    const mockData = {
      results: [
        {
          id: 'result-001',
          sample_id: 'sample-001',
          status: 'completed',
          created_at: new Date(Date.now() - 3600000).toISOString(),
          agent_id: 'agent_c',
          findings_count: 5
        },
        {
          id: 'result-002',
          sample_id: 'sample-002',
          status: 'completed',
          created_at: new Date(Date.now() - 7200000).toISOString(),
          agent_id: 'agent_c',
          findings_count: 0
        }
      ],
      total: 2,
      page: 1,
      per_page: 10
    };
    
    try {
      return await safeApiCall(
        () => apiClient.get('/api/v1/analysis/results', { 
          params,
          ...options
        }),
        mockData,
        '分析結果一覧'
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      return mockResponse(mockData);
    }
  },
  
  // 分析結果詳細の取得
  getResultDetails: async (resultId, options = {}) => {
    if (!resultId) {
      return mockResponse(null, '結果IDが指定されていません');
    }
    
    const mockData = {
      id: resultId,
      sample_id: 'sample-001',
      status: 'completed',
      created_at: new Date(Date.now() - 3600000).toISOString(),
      completed_at: new Date().toISOString(),
      agent_id: 'agent_c',
      findings: [
        {
          id: 'finding-001',
          type: 'anomaly',
          severity: 'high',
          description: '異常値が検出されました',
          location: 'シート1、B15セル',
          details: 'データ値が標準偏差の3倍を超えています'
        },
        {
          id: 'finding-002',
          type: 'warning',
          severity: 'medium',
          description: '不整合データ',
          location: 'シート2、E7セル',
          details: '参照先のデータと一致しません'
        }
      ],
      summary: {
        anomaly_count: 1,
        warning_count: 1,
        error_count: 0,
        processing_time: '2.5秒'
      }
    };
    
    try {
      return await safeApiCall(
        () => apiClient.get(`/api/v1/analysis/results/${resultId}`, options),
        mockData,
        '分析結果詳細'
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      return mockResponse(mockData);
    }
  }
};

// システム設定API
export const settingsApi = {
  // エージェント設定の取得
  getAgentSettings: async (options = {}) => {
    const mockData = {
      agents: [
        {
          id: 'agent-1',
          name: '検証エージェント',
          role: 'validator',
          status: 'active',
          version: '1.0.0',
          lastModified: new Date().toISOString()
        },
        {
          id: 'agent-2',
          name: '監査エージェント',
          role: 'auditor',
          status: 'active',
          version: '1.0.0',
          lastModified: new Date().toISOString()
        },
        {
          id: 'agent-3',
          name: 'レポート生成エージェント',
          role: 'reporter',
          status: 'idle',
          version: '1.0.0',
          lastModified: new Date().toISOString()
        }
      ]
    };
    
    try {
      return await safeApiCall(
        () => apiClient.get('/api/v1/settings/agents', options),
        mockData,
        'エージェント設定',
        false // モックデータを使用しない
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      return normalizeError(error);
    }
  },
  
  // ワークフロー設定の取得
  getWorkflowSettings: async (options = {}) => {
    const mockData = {
      workflows: [
        {
          id: 'wf-001',
          name: '購買取引検証ワークフロー',
          status: 'active',
          lastModified: new Date().toISOString(),
          agents: ['agent-1', 'agent-2'],
          steps: 4
        },
        {
          id: 'wf-002',
          name: '経費精算検証ワークフロー',
          status: 'completed',
          lastModified: new Date().toISOString(),
          agents: ['agent-1', 'agent-3'],
          steps: 3
        }
      ]
    };
    
    try {
      return await safeApiCall(
        () => apiClient.get('/api/v1/settings/workflows', options),
        mockData,
        'ワークフロー設定',
        false // モックデータを使用しない
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      return normalizeError(error);
    }
  },
  
  // システム情報の取得
  getSystemInfo: async (options = {}) => {
    const mockData = {
      systemInfo: {
        name: '内部監査AIエージェントシステム',
        version: '1.0.0',
        lastUpdated: new Date().toISOString(),
        status: 'running',
        environment: 'development',
        apiVersion: 'v1',
        database: 'PostgreSQL',
        serverOS: 'Linux'
      }
    };
    
    try {
      return await safeApiCall(
        () => apiClient.get('/api/v1/settings/system', options),
        mockData,
        'システム情報',
        false // モックデータを使用しない
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      return normalizeError(error);
    }
  },
  
  // システム設定の更新
  updateSettings: async (settingsData, options = {}) => {
    if (!settingsData) {
      return mockResponse(null, '設定データが指定されていません');
    }
    
    const mockData = {
      ...settingsData,
      updated_at: new Date().toISOString()
    };
    
    try {
      return await safeApiCall(
        () => apiClient.put('/api/v1/settings', settingsData, options),
        mockData,
        '設定更新',
        false // モックデータを使用しない
      );
    } catch (error) {
      if (error.name === 'AbortError') {
        throw error;
      }
      
      return normalizeError(error);
    }
  }
}; 