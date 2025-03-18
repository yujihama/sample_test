"""
LLM API呼び出しの再試行メカニズムを提供するモジュール
"""

import asyncio
import random
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast
from functools import wraps

from loguru import logger

from src.core.llm.errors import (
    LLMError,
    RateLimitError,
    ServiceUnavailableError,
    TimeoutError,
    AuthenticationError,
    ContentPolicyViolationError,
    QuotaExceededError
)
from src.core.llm.error_utils import LLMErrorParser

# 型変数の定義
T = TypeVar('T')  # 関数の戻り値の型
P = TypeVar('P')  # パラメータの型


class RetrySettings:
    """再試行の設定"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        jitter_factor: float = 0.25,
        retry_on: Optional[List[type]] = None
    ):
        """
        Args:
            max_retries: 最大再試行回数
            base_delay: 初回再試行までの基本遅延（秒）
            max_delay: 最大遅延時間（秒）
            backoff_factor: 再試行毎の遅延増加係数
            jitter: ランダムなゆらぎを追加するかどうか
            jitter_factor: ゆらぎの大きさ（0-1の範囲、遅延時間に対する比率）
            retry_on: 再試行する例外のリスト（Noneの場合はデフォルトセット）
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.jitter_factor = jitter_factor
        
        # デフォルトの再試行対象例外
        self.retry_on = retry_on or [
            RateLimitError,
            ServiceUnavailableError,
            TimeoutError
        ]
    
    def should_retry(self, error: Exception) -> bool:
        """
        指定されたエラーに対して再試行すべきかを判断
        
        Args:
            error: 発生した例外
            
        Returns:
            再試行すべき場合True
        """
        # カスタムLLMエラーに変換
        if not isinstance(error, LLMError):
            llm_error = LLMErrorParser.parse_error(error)
        else:
            llm_error = error
        
        # 特定のエラーは再試行しない
        if isinstance(llm_error, (AuthenticationError, ContentPolicyViolationError, QuotaExceededError)):
            return False
        
        # 設定された再試行対象エラーかどうか確認
        return any(isinstance(llm_error, error_type) for error_type in self.retry_on)
    
    def calculate_delay(self, retry_count: int) -> float:
        """
        再試行までの遅延時間を計算
        
        Args:
            retry_count: 現在の再試行回数（0ベース）
            
        Returns:
            遅延時間（秒）
        """
        # 指数バックオフによる遅延計算
        delay = min(
            self.max_delay,
            self.base_delay * (self.backoff_factor ** retry_count)
        )
        
        # ランダムなゆらぎを追加
        if self.jitter:
            jitter_range = delay * self.jitter_factor
            delay = delay + random.uniform(-jitter_range, jitter_range)
            
            # 最小遅延を保証
            delay = max(self.base_delay * 0.5, delay)
        
        return delay


class LLMRetryHandler:
    """LLM API呼び出しの再試行を管理するハンドラ"""
    
    def __init__(self, settings: Optional[RetrySettings] = None):
        """
        Args:
            settings: 再試行設定。Noneの場合はデフォルト設定が使用される
        """
        self.settings = settings or RetrySettings()
    
    async def execute_with_retry(
        self, func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """
        再試行メカニズム付きで関数を実行
        
        Args:
            func: 実行する関数
            *args: 関数に渡す位置引数
            **kwargs: 関数に渡すキーワード引数
            
        Returns:
            関数の実行結果
            
        Raises:
            LLMError: すべての再試行が失敗した場合
        """
        last_error = None
        
        for retry_count in range(self.settings.max_retries + 1):
            try:
                # 非同期関数と同期関数の両方に対応
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
                    
            except Exception as e:
                last_error = e
                
                # 再試行すべきエラーかどうか判断
                if not self.settings.should_retry(e):
                    logger.warning(f"再試行不可能なエラー: {e}")
                    break
                
                # 最大再試行回数に達したかチェック
                if retry_count >= self.settings.max_retries:
                    logger.warning(f"最大再試行回数({self.settings.max_retries})に達しました")
                    break
                
                # 遅延時間の計算
                delay = self.settings.calculate_delay(retry_count)
                
                # エラーログと再試行情報
                logger.warning(
                    f"LLM API呼び出しエラー ({retry_count+1}/{self.settings.max_retries+1}): "
                    f"{e}. {delay:.2f}秒後に再試行します"
                )
                
                # 遅延後に再試行
                await asyncio.sleep(delay)
        
        # すべての再試行が失敗した場合
        if isinstance(last_error, LLMError):
            raise last_error
        else:
            # 一般的な例外をLLMエラーに変換
            raise LLMErrorParser.parse_error(last_error)


# デコレータとして使用するためのユーティリティ関数
def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_on: Optional[List[type]] = None
):
    """
    LLM API呼び出しに再試行メカニズムを追加するデコレータ
    
    Args:
        max_retries: 最大再試行回数
        base_delay: 初回再試行までの基本遅延（秒）
        max_delay: 最大遅延時間（秒）
        retry_on: 再試行する例外のリスト
        
    Returns:
        デコレータ関数
    """
    def decorator(func):
        settings = RetrySettings(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            retry_on=retry_on
        )
        handler = LLMRetryHandler(settings)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await handler.execute_with_retry(func, *args, **kwargs)
        
        return wrapper
    
    return decorator


# シングルトンインスタンス
default_retry_handler = LLMRetryHandler()


# 簡易ユーティリティ関数
async def retry_llm_call(
    func: Callable[..., Any],
    *args: Any,
    **kwargs: Any
) -> Any:
    """
    LLM API呼び出しを再試行メカニズム付きで実行する簡易関数
    
    Args:
        func: 実行する関数
        *args: 関数に渡す位置引数
        **kwargs: 関数に渡すキーワード引数
        
    Returns:
        関数の実行結果
    """
    return await default_retry_handler.execute_with_retry(func, *args, **kwargs) 