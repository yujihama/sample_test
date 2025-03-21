import axios from 'axios';

// APIサーバーのURL
const API_BASE_URL = 'http://127.0.0.1:8000';  // バックエンドAPIサーバーの実際のURL
// const API_BASE_URL = 'http://localhost:8000';
// 認証用APIキー - 一時的に無効化
const API_KEY = 'test_token';

// 認証情報なしの基本設定
const loggerAxios = axios.create({
  baseURL: API_BASE_URL,  // 空文字列で相対パスリクエストを行う
  headers: {
    'Content-Type': 'application/json',
  }
});

export const loggerService = {
  // フロントエンドエラーをバックエンドに送信
  logError: (error, context = {}) => {
    // エラーメッセージとスタック情報を確保
    const errorMessage = error.message || 'Unknown error';
    const errorStack = error.stack || 'No stack trace available';
    
    // 常にコンソールにも出力（デバッグ用）
    console.error('エラー発生:', errorMessage);
    console.error('Stack:', errorStack);
    console.error('Context:', context);
    
    // エラー情報をログファイルに送信
    return loggerAxios.post(`/api/v1/logs/client`, {
      level: 'error',
      message: errorMessage,
      stack: errorStack,
      context: { ...context, userAgent: navigator.userAgent, timestamp: new Date().toISOString() }
    })
    .then(response => {
      console.log('エラーログの送信に成功しました');
      return response;
    })
    .catch(err => {
      console.error('エラーログの送信に失敗:', err.message);
      // 認証問題の場合はヘッダー付きで再試行
      if (err.response && err.response.status === 401) {
        console.warn('認証エラー、トークン付きで再試行します');
        return axios.post(`${API_BASE_URL}/api/v1/logs/client`, {
          level: 'error',
          message: errorMessage,
          stack: errorStack,
          context: { ...context, userAgent: navigator.userAgent, timestamp: new Date().toISOString(), retry: true }
        }, {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${API_KEY}`
          }
        });
      }
      return Promise.reject(err);
    });
  },
  
  // 警告ログの送信
  logWarning: (message, context = {}) => {
    console.warn('警告:', message, context);
    
    return loggerAxios.post(`/api/v1/logs/client`, {
      level: 'warning',
      message,
      context: { ...context, userAgent: navigator.userAgent, timestamp: new Date().toISOString() }
    })
    .catch(err => {
      console.warn('警告ログの送信に失敗:', err.message);
    });
  },
  
  // 情報ログの送信
  logInfo: (message, context = {}) => {
    console.info('情報:', message, context);
    
    return loggerAxios.post(`/api/v1/logs/client`, {
      level: 'info',
      message,
      context: { ...context, userAgent: navigator.userAgent, timestamp: new Date().toISOString() }
    })
    .catch(err => {
      console.info('情報ログの送信に失敗:', err.message);
    });
  }
}; 