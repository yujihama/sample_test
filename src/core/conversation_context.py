"""
会話コンテキスト管理モジュール

このモジュールは、エージェント間の会話コンテキストを管理するためのクラスを提供します。
会話履歴や状態の追跡、コンテキスト情報の保存と取得の機能を提供します。
"""

import json
import uuid
import time
import logging
import threading
from typing import Dict, List, Any, Optional, Set, Union
from datetime import datetime

from loguru import logger


class ContextClient:
    """コンテキスト情報にアクセスするための共有クライアント"""
    
    def __init__(self, context_id: str = None):
        """
        コンテキストクライアントの初期化
        
        Args:
            context_id: コンテキストID（指定しない場合は新規生成）
        """
        self.context_id = context_id or str(uuid.uuid4())
        self._manager = self._get_context_manager()
    
    def _get_context_manager(self):
        """コンテキストマネージャーの取得"""
        return ConversationManager()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        コンテキスト情報の取得
        
        Args:
            key: 取得するキー
            default: キーが存在しない場合のデフォルト値
            
        Returns:
            コンテキスト情報
        """
        return self._manager.get_context(self.context_id, key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        コンテキスト情報の設定
        
        Args:
            key: 設定するキー
            value: 設定する値
        """
        self._manager.set_context(self.context_id, key, value)
    
    def update(self, data: Dict[str, Any]) -> None:
        """
        複数のコンテキスト情報を一括更新
        
        Args:
            data: 更新するデータ辞書
        """
        self._manager.update_context(self.context_id, data)
    
    def delete(self, key: str) -> bool:
        """
        コンテキスト情報の削除
        
        Args:
            key: 削除するキー
            
        Returns:
            削除が成功したかどうか
        """
        return self._manager.delete_context(self.context_id, key)
    
    def clear(self) -> None:
        """コンテキスト全体をクリア"""
        self._manager.clear_context(self.context_id)
    
    def exists(self, key: str) -> bool:
        """
        指定されたキーが存在するかチェック
        
        Args:
            key: チェックするキー
            
        Returns:
            キーが存在するかどうか
        """
        return self._manager.has_context(self.context_id, key)
    
    def get_all(self) -> Dict[str, Any]:
        """
        全てのコンテキスト情報を取得
        
        Returns:
            コンテキスト情報の辞書
        """
        return self._manager.get_all_context(self.context_id)


class ConversationManager:
    """会話コンテキスト管理クラス（シングルトン）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """シングルトンパターンの実装"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConversationManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """マネージャーの初期化（1回だけ実行）"""
        if getattr(self, "_initialized", False):
            return
            
        self._initialized = True
        self._context_store: Dict[str, Dict[str, Any]] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._creation_times: Dict[str, float] = {}
        self._access_times: Dict[str, float] = {}
        self._ttl_seconds = 3600  # デフォルトの有効期限（1時間）
        
        # 自動クリーンアップの設定
        self._enable_cleanup = True
        self._cleanup_interval = 300  # 5分ごとにクリーンアップ
        
        if self._enable_cleanup:
            self._start_cleanup_thread()
    
    def _start_cleanup_thread(self) -> None:
        """期限切れコンテキストを定期的にクリーンアップするスレッドを開始"""
        
        def cleanup_job():
            while self._enable_cleanup:
                try:
                    self._cleanup_expired_contexts()
                except Exception as e:
                    logger.error(f"コンテキストクリーンアップ中にエラーが発生: {e}")
                
                time.sleep(self._cleanup_interval)
        
        cleanup_thread = threading.Thread(target=cleanup_job, daemon=True)
        cleanup_thread.start()
    
    def _cleanup_expired_contexts(self) -> None:
        """期限切れのコンテキストを削除"""
        current_time = time.time()
        expired_contexts = []
        
        with self._lock:
            for context_id, last_access in self._access_times.items():
                # 最終アクセスから有効期限が経過しているかチェック
                if current_time - last_access > self._ttl_seconds:
                    expired_contexts.append(context_id)
            
            # 期限切れコンテキストを削除
            for context_id in expired_contexts:
                self._delete_context_internal(context_id)
        
        if expired_contexts:
            logger.debug(f"{len(expired_contexts)}個の期限切れコンテキストを削除しました")
    
    def _delete_context_internal(self, context_id: str) -> None:
        """内部的にコンテキストを完全に削除"""
        if context_id in self._context_store:
            del self._context_store[context_id]
        
        if context_id in self._metadata:
            del self._metadata[context_id]
        
        if context_id in self._creation_times:
            del self._creation_times[context_id]
        
        if context_id in self._access_times:
            del self._access_times[context_id]
    
    def _ensure_context_exists(self, context_id: str) -> None:
        """必要に応じてコンテキストコンテナを初期化"""
        current_time = time.time()
        
        with self._lock:
            if context_id not in self._context_store:
                self._context_store[context_id] = {}
                self._metadata[context_id] = {"created_by": "system"}
                self._creation_times[context_id] = current_time
            
            # アクセス時間を更新
            self._access_times[context_id] = current_time
    
    def get_context(self, context_id: str, key: str, default: Any = None) -> Any:
        """
        指定されたキーのコンテキスト情報を取得
        
        Args:
            context_id: コンテキストID
            key: 取得するキー
            default: キーが存在しない場合のデフォルト値
            
        Returns:
            コンテキスト情報または指定されたデフォルト値
        """
        self._ensure_context_exists(context_id)
        
        with self._lock:
            return self._context_store[context_id].get(key, default)
    
    def get_all_context(self, context_id: str) -> Dict[str, Any]:
        """
        指定されたコンテキストのすべての情報を取得
        
        Args:
            context_id: コンテキストID
            
        Returns:
            コンテキスト情報の辞書
        """
        self._ensure_context_exists(context_id)
        
        with self._lock:
            # 辞書の新しいコピーを返して参照の問題を回避
            return dict(self._context_store[context_id])
    
    def set_context(self, context_id: str, key: str, value: Any) -> None:
        """
        コンテキスト情報を設定
        
        Args:
            context_id: コンテキストID
            key: 設定するキー
            value: 設定する値
        """
        self._ensure_context_exists(context_id)
        
        with self._lock:
            self._context_store[context_id][key] = value
    
    def update_context(self, context_id: str, data: Dict[str, Any]) -> None:
        """
        複数のコンテキスト情報を一括で更新
        
        Args:
            context_id: コンテキストID
            data: 更新するデータ辞書
        """
        self._ensure_context_exists(context_id)
        
        with self._lock:
            self._context_store[context_id].update(data)
    
    def delete_context(self, context_id: str, key: str) -> bool:
        """
        指定されたキーのコンテキスト情報を削除
        
        Args:
            context_id: コンテキストID
            key: 削除するキー
            
        Returns:
            削除が成功したかどうか
        """
        self._ensure_context_exists(context_id)
        
        with self._lock:
            if key in self._context_store[context_id]:
                del self._context_store[context_id][key]
                return True
        
        return False
    
    def clear_context(self, context_id: str) -> None:
        """
        指定されたコンテキストの全ての情報をクリア
        
        Args:
            context_id: コンテキストID
        """
        with self._lock:
            if context_id in self._context_store:
                self._context_store[context_id] = {}
                # メタデータ、作成時間、アクセス時間は保持
                self._access_times[context_id] = time.time()
    
    def has_context(self, context_id: str, key: str) -> bool:
        """
        指定されたキーが存在するかチェック
        
        Args:
            context_id: コンテキストID
            key: チェックするキー
            
        Returns:
            キーが存在するかどうか
        """
        self._ensure_context_exists(context_id)
        
        with self._lock:
            return key in self._context_store[context_id]
    
    def set_metadata(self, context_id: str, key: str, value: Any) -> None:
        """
        コンテキストに関するメタデータを設定
        
        Args:
            context_id: コンテキストID
            key: メタデータキー
            value: メタデータ値
        """
        self._ensure_context_exists(context_id)
        
        with self._lock:
            self._metadata[context_id][key] = value
    
    def get_metadata(self, context_id: str, key: str, default: Any = None) -> Any:
        """
        コンテキストのメタデータを取得
        
        Args:
            context_id: コンテキストID
            key: メタデータキー
            default: デフォルト値
            
        Returns:
            メタデータ値またはデフォルト値
        """
        self._ensure_context_exists(context_id)
        
        with self._lock:
            return self._metadata[context_id].get(key, default)
    
    def get_all_metadata(self, context_id: str) -> Dict[str, Any]:
        """
        コンテキストの全メタデータを取得
        
        Args:
            context_id: コンテキストID
            
        Returns:
            メタデータの辞書
        """
        self._ensure_context_exists(context_id)
        
        with self._lock:
            return dict(self._metadata[context_id])
    
    def get_creation_time(self, context_id: str) -> Optional[float]:
        """
        コンテキストの作成時間を取得
        
        Args:
            context_id: コンテキストID
            
        Returns:
            作成時間（UNIXタイムスタンプ）または None
        """
        with self._lock:
            return self._creation_times.get(context_id)
    
    def get_last_access_time(self, context_id: str) -> Optional[float]:
        """
        コンテキストの最終アクセス時間を取得
        
        Args:
            context_id: コンテキストID
            
        Returns:
            最終アクセス時間（UNIXタイムスタンプ）または None
        """
        with self._lock:
            return self._access_times.get(context_id)
    
    def set_ttl(self, seconds: int) -> None:
        """
        コンテキストのデフォルト有効期限を設定
        
        Args:
            seconds: 有効期限（秒）
        """
        with self._lock:
            self._ttl_seconds = seconds
    
    def list_contexts(self) -> List[str]:
        """
        全てのアクティブなコンテキストIDのリストを取得
        
        Returns:
            コンテキストIDのリスト
        """
        with self._lock:
            return list(self._context_store.keys())
    
    def export_context(self, context_id: str) -> Dict[str, Any]:
        """
        指定されたコンテキストの全データをエクスポート
        
        Args:
            context_id: コンテキストID
            
        Returns:
            コンテキストデータと関連メタデータを含む辞書
        """
        with self._lock:
            if context_id not in self._context_store:
                return {}
            
            return {
                "data": dict(self._context_store[context_id]),
                "metadata": dict(self._metadata[context_id]),
                "created_at": self._creation_times.get(context_id),
                "last_accessed_at": self._access_times.get(context_id)
            }
    
    def import_context(self, context_id: str, data: Dict[str, Any]) -> bool:
        """
        エクスポートされたデータからコンテキストをインポート
        
        Args:
            context_id: コンテキストID
            data: インポートするデータ（export_contextの出力フォーマット）
            
        Returns:
            インポートが成功したかどうか
        """
        try:
            with self._lock:
                context_data = data.get("data", {})
                metadata = data.get("metadata", {})
                created_at = data.get("created_at")
                
                # コンテキストデータの設定
                self._context_store[context_id] = dict(context_data)
                self._metadata[context_id] = dict(metadata)
                
                # タイムスタンプの設定
                current_time = time.time()
                self._creation_times[context_id] = created_at or current_time
                self._access_times[context_id] = current_time
                
                return True
        except Exception as e:
            logger.error(f"コンテキストのインポート中にエラーが発生: {e}")
            return False


# シングルトンインスタンスへの参照を提供する関数
def get_conversation_manager() -> ConversationManager:
    """
    ConversationManagerのシングルトンインスタンスを取得
    
    Returns:
        ConversationManagerのインスタンス
    """
    return ConversationManager()
