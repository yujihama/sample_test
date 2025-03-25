import { api } from './api';

/**
 * 監査手続き情報
 */
export interface Procedure {
  id: string;
  title: string;
  description: string;
  risk_areas: string[];
  created_at: string;
}

/**
 * 監査手続き一覧レスポンス
 */
export interface ProceduresResponse {
  procedures: Procedure[];
  total: number;
  page: number;
  per_page: number;
}

/**
 * 監査手続き関連のAPIサービス
 */
export const procedureService = {
  /**
   * 監査手続き一覧を取得
   */
  async getProcedures(params?: { page?: number, per_page?: number }): Promise<ProceduresResponse> {
    try {
      const queryParams = new URLSearchParams();
      if (params?.page) queryParams.append('page', params.page.toString());
      if (params?.per_page) queryParams.append('per_page', params.per_page.toString());
      
      const queryString = queryParams.toString();
      const endpoint = `/api/procedures${queryString ? `?${queryString}` : ''}`;
      
      return await api.get<ProceduresResponse>(endpoint);
    } catch (error) {
      console.error('監査手続き一覧の取得に失敗しました:', error);
      throw error;
    }
  },

  /**
   * 監査手続き詳細を取得
   */
  async getProcedure(id: string): Promise<Procedure> {
    try {
      return await api.get<Procedure>(`/api/procedures/${id}`);
    } catch (error) {
      console.error(`監査手続き詳細の取得に失敗しました (ID: ${id}):`, error);
      throw error;
    }
  }
}; 