import { useState, useEffect, useCallback, useRef } from 'react';
import { loggerService } from '../services/logger';

/**
 * APIデータを取得するためのカスタムフック
 * @param {Function} apiFunction - API呼び出し関数
 * @param {Object} options - オプション設定
 * @param {Array} options.dependencies - useEffect依存配列
 * @param {boolean} options.skipInitialFetch - 初回フェッチをスキップするかどうか
 * @param {boolean} options.cacheResults - 結果をキャッシュするかどうか
 * @param {number} options.cacheTime - キャッシュ有効時間（ミリ秒）
 * @param {number} options.retryCount - リトライ回数
 * @param {number} options.retryDelay - リトライ間隔（ミリ秒）
 * @returns {Object} - data, loading, error, refetch, abortRequest
 */
const useApi = (
  apiFunction, 
  options = {}
) => {
  const { 
    dependencies = [],
    skipInitialFetch = false,
    cacheResults = false,
    cacheTime = 5 * 60 * 1000, // デフォルト5分
    retryCount = 0,
    retryDelay = 1000
  } = options;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(!skipInitialFetch);
  const [error, setError] = useState(null);
  
  // キャッシュ管理
  const cacheRef = useRef({
    data: null,
    timestamp: null
  });
  
  // Abortコントローラー
  const abortControllerRef = useRef(null);
  
  // 実行カウンター（リトライ用）
  const retryCounterRef = useRef(0);
  
  // キャッシュの有効性をチェック
  const isCacheValid = useCallback(() => {
    return (
      cacheResults && 
      cacheRef.current.data && 
      cacheRef.current.timestamp && 
      (Date.now() - cacheRef.current.timestamp) < cacheTime
    );
  }, [cacheResults, cacheTime]);

  // リクエスト中止
  const abortRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  // データ取得関数
  const fetchData = useCallback(async (forceRefresh = false) => {
    // キャッシュが有効で強制リフレッシュでない場合はキャッシュを使用
    if (isCacheValid() && !forceRefresh) {
      setData(cacheRef.current.data);
      setLoading(false);
      setError(null);
      return;
    }
    
    // 進行中のリクエストがあれば中止
    abortRequest();
    
    // リトライカウンターリセット
    retryCounterRef.current = 0;
    
    setLoading(true);
    
    const executeRequest = async () => {
      try {
        // 新しいAbortControllerを作成
        abortControllerRef.current = new AbortController();
        
        // apiFunction引数のチェック
        if (typeof apiFunction !== 'function') {
          const error = new Error('apiFunction is not a function');
          loggerService.logError(error, { context: 'useApi' });
          setError('APIリクエスト関数が不正です');
          throw error;
        }
        
        // APIリクエスト実行（AbortSignalを渡す）
        // 関数呼び出し（オプションパラメータがあれば渡す）
        const signalOptions = { signal: abortControllerRef.current.signal };
        const result = await (typeof apiFunction === 'function' 
          ? apiFunction(signalOptions) 
          : Promise.reject(new Error('apiFunction is not a function')));
        
        // データをセット
        setData(result.data);
        
        // エラー状態をクリア
        setError(null);
        
        // キャッシュに保存
        if (cacheResults) {
          cacheRef.current = {
            data: result.data,
            timestamp: Date.now()
          };
        }
        
        return result.data;
      } catch (err) {
        // AbortErrorの場合はエラー表示しない
        if (err.name === 'AbortError') {
          return;
        }
        
        // リトライ可能かチェック
        if (retryCounterRef.current < retryCount) {
          retryCounterRef.current++;
          
          loggerService.logWarning(`APIリクエスト失敗、リトライ中 (${retryCounterRef.current}/${retryCount})`, { 
            error: err.message,
            context: 'useApi'
          });
          
          // リトライ
          await new Promise(resolve => setTimeout(resolve, retryDelay));
          return executeRequest();
        }
        
        // エラーログ
        loggerService.logError(err, { 
          context: 'useApi',
          payload: err.config?.data
        });
        
        setError(err.message || 'APIリクエストに失敗しました');
        throw err;
      }
    };
    
    try {
      await executeRequest();
    } catch (err) {
      // 例外は既に処理されているので何もしない
    } finally {
      setLoading(false);
    }
  }, [apiFunction, isCacheValid, cacheResults, retryCount, retryDelay, abortRequest]);

  // 初期データ取得
  useEffect(() => {
    if (!skipInitialFetch) {
      fetchData();
    }
    
    // コンポーネントアンマウント時にリクエストを中止
    return () => {
      abortRequest();
    };
  }, [...dependencies]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    data,
    loading,
    error,
    refetch: (forceRefresh = true) => fetchData(forceRefresh),
    abortRequest
  };
};

export default useApi; 