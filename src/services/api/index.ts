import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';

// APIのベースURL
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api';

// デフォルトのタイムアウト設定（ミリ秒）
const DEFAULT_TIMEOUT = 30000;

// API設定タイプ
interface ApiClientConfig extends AxiosRequestConfig {
  onUnauthorized?: () => void;
}

/**
 * APIクライアントクラス
 * APIへのリクエスト処理を集約管理する
 */
class ApiClient {
  private client: AxiosInstance;
  private onUnauthorized?: () => void;

  constructor(config: ApiClientConfig = {}) {
    const { onUnauthorized, ...axiosConfig } = config;
    
    // Axiosインスタンスの作成
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: DEFAULT_TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      ...axiosConfig,
    });

    this.onUnauthorized = onUnauthorized;

    // リクエストインターセプター
    this.client.interceptors.request.use(
      (config) => {
        // ここでリクエスト前の共通処理を行う
        // 例: トークンの付与など
        const token = localStorage.getItem('auth_token');
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // レスポンスインターセプター
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        // エラーハンドリング
        if (error.response?.status === 401) {
          // 認証エラー時の処理
          if (this.onUnauthorized) {
            this.onUnauthorized();
          }
        }
        return Promise.reject(error);
      }
    );
  }

  /**
   * GETリクエスト
   */
  public async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  /**
   * POSTリクエスト
   */
  public async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  /**
   * PUTリクエスト
   */
  public async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  /**
   * DELETEリクエスト
   */
  public async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }

  /**
   * カスタムリクエスト
   * 任意のHTTPメソッドを使用する場合に使用
   */
  public async request<T = any>(config: AxiosRequestConfig): Promise<T> {
    const response = await this.client.request<T>(config);
    return response.data;
  }
}

// デフォルトのAPIクライアントインスタンス
const defaultApiClient = new ApiClient();

export { ApiClient };
export default defaultApiClient; 