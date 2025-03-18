"""
LLMエラーを処理するためのユーティリティ関数
"""

import json
from src.utils import json_utils
import re
import logging
from typing import Dict, Any, Optional, Tuple, List, Union
import traceback

from src.core.llm.errors import (
    LLMError,
    RateLimitError,
    TokenLimitError,
    ServiceUnavailableError,
    ContentPolicyViolationError,
    AuthenticationError,
    InvalidRequestError,
    ModelNotFoundError,
    ContextLengthExceededError,
    QuotaExceededError,
    TimeoutError
)

logger = logging.getLogger(__name__)


class LLMErrorParser:
    """
    LLMエラーを解析し、適切なカスタム例外に変換するクラス
    """
    
    # エラーメッセージパターン
    ERROR_PATTERNS = {
        # レート制限エラー
        r"rate\s*limit": RateLimitError,
        r"too\s*many\s*requests": RateLimitError,
        r"请求太频繁": RateLimitError,  # 中国語のレート制限エラー
        
        # トークン制限エラー
        r"token\s*limit": TokenLimitError,
        r"context\s*length": ContextLengthExceededError,
        r"maximum\s*context\s*length": ContextLengthExceededError,
        r"exceeds\s*maximum": TokenLimitError,
        
        # サービス利用不可エラー
        r"service\s*unavailable": ServiceUnavailableError,
        r"server\s*error": ServiceUnavailableError,
        r"internal\s*server\s*error": ServiceUnavailableError,
        r"temporarily\s*unavailable": ServiceUnavailableError,
        r"overloaded": ServiceUnavailableError,
        
        # コンテンツポリシー違反
        r"content\s*policy": ContentPolicyViolationError,
        r"content\s*filter": ContentPolicyViolationError,
        r"violates": ContentPolicyViolationError,
        r"inappropriate": ContentPolicyViolationError,
        r"harmful": ContentPolicyViolationError,
        
        # 認証エラー
        r"authentication": AuthenticationError,
        r"invalid\s*api\s*key": AuthenticationError,
        r"expired\s*api\s*key": AuthenticationError,
        r"unauthorized": AuthenticationError,
        
        # 無効なリクエスト
        r"invalid\s*request": InvalidRequestError,
        r"bad\s*request": InvalidRequestError,
        r"malformed": InvalidRequestError,
        
        # モデル未検出
        r"model\s*not\s*found": ModelNotFoundError,
        r"unknown\s*model": ModelNotFoundError,
        
        # クォータ超過
        r"quota\s*exceeded": QuotaExceededError,
        r"billing\s*quota": QuotaExceededError,
        
        # タイムアウト
        r"timeout": TimeoutError,
        r"timed\s*out": TimeoutError,
    }
    
    # プロバイダー固有のエラーコード
    PROVIDER_ERROR_CODES = {
        # OpenAI
        "rate_limit_exceeded": RateLimitError,
        "token_limit_exceeded": TokenLimitError,
        "context_length_exceeded": ContextLengthExceededError,
        "server_error": ServiceUnavailableError,
        "content_filter": ContentPolicyViolationError,
        "authentication_error": AuthenticationError,
        "invalid_request_error": InvalidRequestError,
        "model_not_found": ModelNotFoundError,
        
        # Anthropic
        "rate_limit_error": RateLimitError,
        "context_too_long": ContextLengthExceededError,
        "content_policy_violation": ContentPolicyViolationError,
        "invalid_api_key": AuthenticationError,
        
        # Google
        "RESOURCE_EXHAUSTED": RateLimitError,
        "INVALID_ARGUMENT": InvalidRequestError,
        "PERMISSION_DENIED": AuthenticationError,
        "UNAVAILABLE": ServiceUnavailableError,
    }
    
    @classmethod
    def parse_error(cls, error: Exception, response_data: Optional[Dict[str, Any]] = None) -> LLMError:
        """
        エラーを解析し、適切なLLMエラーに変換する
        
        Args:
            error: 元のエラー
            response_data: レスポンスデータ（オプション）
            
        Returns:
            適切なLLMエラー
        """
        error_message = str(error)
        error_type = type(error).__name__
        
        # すでにLLMエラーの場合はそのまま返す
        if isinstance(error, LLMError):
            return error
            
        # レスポンスデータからエラーコードを抽出
        error_code = cls._extract_error_code(response_data)
        if error_code and error_code in cls.PROVIDER_ERROR_CODES:
            error_class = cls.PROVIDER_ERROR_CODES[error_code]
            return error_class(message=error_message)
        
        # エラーメッセージからパターンマッチング
        for pattern, error_class in cls.ERROR_PATTERNS.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                return error_class(message=error_message)
        
        # 特定のエラータイプに基づく変換
        if error_type == "TimeoutError":
            return TimeoutError(message=error_message)
        elif error_type == "JSONDecodeError":
            return InvalidRequestError(message=f"JSONデコードエラー: {error_message}")
        
        # デフォルトは一般的なLLMエラー
        return LLMError(message=error_message)
    
    @staticmethod
    def _extract_error_code(response_data: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        レスポンスデータからエラーコードを抽出
        
        Args:
            response_data: レスポンスデータ
            
        Returns:
            エラーコード（存在する場合）
        """
        if not response_data:
            return None
            
        # OpenAI形式
        if "error" in response_data and isinstance(response_data["error"], dict):
            return response_data["error"].get("code") or response_data["error"].get("type")
            
        # Anthropic形式
        if "type" in response_data:
            return response_data.get("type")
            
        # Google形式
        if "error" in response_data and "code" in response_data:
            return response_data.get("code")
            
        return None


class LLMErrorHandler:
    """
    LLMエラーを処理するためのユーティリティクラス
    """
    
    def __init__(self, max_retries: int = 3, initial_backoff: float = 1.0, backoff_factor: float = 2.0):
        """
        初期化
        
        Args:
            max_retries: 最大リトライ回数
            initial_backoff: 初期バックオフ時間（秒）
            backoff_factor: バックオフ係数
        """
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.backoff_factor = backoff_factor
        
    def get_retry_info(self, error: LLMError, retry_count: int) -> Tuple[bool, float, str]:
        """
        エラーに基づいてリトライ情報を取得
        
        Args:
            error: LLMエラー
            retry_count: 現在のリトライ回数
            
        Returns:
            Tuple[bool, float, str]: (リトライすべきか, 待機時間, 理由)
        """
        # リトライ回数が上限に達した場合
        if retry_count >= self.max_retries:
            return False, 0, f"最大リトライ回数({self.max_retries})に達しました"
        
        # エラータイプに基づく処理
        if isinstance(error, RateLimitError):
            # レート制限エラーの場合
            wait_time = getattr(error, "retry_after", None) or self._calculate_backoff(retry_count)
            return True, wait_time, "レート制限に達したため待機中"
            
        elif isinstance(error, ServiceUnavailableError):
            # サービス利用不可エラーの場合
            wait_time = self._calculate_backoff(retry_count, base=5.0)  # サービスエラーは長めに待機
            return True, wait_time, "サービスが一時的に利用できないため待機中"
            
        elif isinstance(error, TokenLimitError) or isinstance(error, ContextLengthExceededError):
            # トークン制限エラーの場合はリトライしない（入力を短くする必要がある）
            return False, 0, "トークン制限を超えています。入力を短くしてください"
            
        elif isinstance(error, ContentPolicyViolationError):
            # コンテンツポリシー違反の場合はリトライしない
            return False, 0, "コンテンツポリシー違反が検出されました"
            
        elif isinstance(error, AuthenticationError):
            # 認証エラーの場合はリトライしない
            return False, 0, "API認証エラーが発生しました"
            
        elif isinstance(error, TimeoutError):
            # タイムアウトの場合
            wait_time = self._calculate_backoff(retry_count)
            return True, wait_time, "タイムアウトが発生したため再試行します"
            
        elif isinstance(error, InvalidRequestError):
            # 無効なリクエストの場合はリトライしない
            return False, 0, "無効なリクエストが送信されました"
            
        else:
            # その他のエラーの場合は一定回数リトライ
            wait_time = self._calculate_backoff(retry_count)
            return True, wait_time, "一時的なエラーが発生したため再試行します"
    
    def _calculate_backoff(self, retry_count: int, base: float = None) -> float:
        """
        指数バックオフ時間を計算
        
        Args:
            retry_count: 現在のリトライ回数
            base: 基本待機時間（指定がなければinitial_backoffを使用）
            
        Returns:
            待機時間（秒）
        """
        base = base or self.initial_backoff
        return base * (self.backoff_factor ** retry_count)


def safe_parse_json(json_str: str) -> Tuple[bool, Union[Dict[str, Any], List[Any], str]]:
    """
    安全にJSONを解析する関数
    
    Args:
        json_str: JSON文字列
        
    Returns:
        Tuple[bool, Union[Dict[str, Any], List[Any], str]]: (成功したか, 解析結果または元の文字列)
    """
    try:
        return True, json_utils.json_deserialize(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"JSONデコードエラー: {str(e)}")
        
        # JSONの修正を試みる
        try:
            # 一般的なJSON構文エラーを修正
            fixed_json = _fix_common_json_errors(json_str)
            return True, json_utils.json_deserialize(fixed_json)
        except Exception:
            # 修正に失敗した場合は元の文字列を返す
            return False, json_str


def _fix_common_json_errors(json_str: str) -> str:
    """
    一般的なJSON構文エラーを修正する
    
    Args:
        json_str: JSON文字列
        
    Returns:
        修正されたJSON文字列
    """
    # 末尾のカンマを削除
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # 不足している閉じ括弧を追加
    open_braces = json_str.count('{')
    close_braces = json_str.count('}')
    if open_braces > close_braces:
        json_str += '}' * (open_braces - close_braces)
    
    open_brackets = json_str.count('[')
    close_brackets = json_str.count(']')
    if open_brackets > close_brackets:
        json_str += ']' * (open_brackets - close_brackets)
    
    # シングルクォートをダブルクォートに変換
    json_str = re.sub(r'(?<!\\)\'', '"', json_str)
    
    # キーの引用符が不足している場合を修正
    json_str = re.sub(r'([{,])\s*([a-zA-Z0-9_]+)\s*:', r'\1"\2":', json_str)
    
    return json_str 