import { api } from './api';

/**
 * サンプルデータ情報
 */
export interface Sample {
  id: string;
  filename: string;
  file_type: string;
  row_count: number;
  column_count: number;
  procedure_id?: string;
  created_at: string;
}

/**
 * サンプルデータ一覧レスポンス
 */
export interface SamplesResponse {
  samples: Sample[];
  total: number;
  page: number;
  per_page: number;
}

/**
 * サンプルデータ関連のAPIサービス
 */
export const sampleService = {
  /**
   * サンプルデータ一覧を取得
   */
  async getSamples(params?: { page?: number, per_page?: number }): Promise<SamplesResponse> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.per_page) queryParams.append('per_page', params.per_page.toString());
      
      const queryString = queryParams.toString();
      const endpoint = `/api/samples${queryString ? `?${queryString}` : ''}`;
      
      return await api.get<SamplesResponse>(endpoint);
    } catch (error) {
      console.error('サンプルデータ一覧の取得に失敗しました:', error);
      throw error;
    }
  },

  /**
   * サンプルデータ詳細を取得
   */
  async getSample(id: string): Promise<Sample> {
    try {
      return await api.get<Sample>(`/api/samples/${id}`);
    } catch (error) {
      console.error(`サンプルデータ詳細の取得に失敗しました (ID: ${id}):`, error);
      throw error;
    }
  }
}; 