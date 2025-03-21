import { useState, useEffect } from 'react';

/**
 * API呼び出しを行い、ローディング状態やエラー状態を管理するカスタムフック
 * @param {Function} apiFunction - API呼び出し関数
 * @param {Array} dependencies - useEffect依存配列
 * @param {Object} initialData - データの初期値
 * @param {Object} options - 追加オプション
 * @returns {Object} { data, loading, error, refetch }
 */
const useApi = (apiFunction, dependencies = [], initialData = null, options = {}) => {
  const { params, onSuccess, onError, autoFetch = true } = options;
  
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(autoFetch);
  const [error, setError] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiFunction(params);
      const result = response.data;
      setData(result);
      
      if (onSuccess) {
        onSuccess(result);
      }
      
      return result;
    } catch (err) {
      setError(err);
      
      if (onError) {
        onError(err);
      }
      
      return null;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (autoFetch) {
      fetchData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);

  return { data, loading, error, refetch: fetchData };
};

export default useApi; 