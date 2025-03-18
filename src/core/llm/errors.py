"""
LLMサービスに関連するカスタム例外クラス
"""

class LLMError(Exception):
    """LLM関連の基本例外クラス"""
    def __init__(self, message: str = "LLMエラーが発生しました", *args, **kwargs):
        self.message = message
        super().__init__(message, *args, **kwargs)
        
    def __str__(self):
        return self.message


class RateLimitError(LLMError):
    """APIレート制限に達した場合のエラー"""
    def __init__(self, message: str = "APIレート制限に達しました", retry_after: int = 60, *args, **kwargs):
        self.retry_after = retry_after
        super().__init__(message, *args, **kwargs)


class TokenLimitError(LLMError):
    """トークン数制限を超えた場合のエラー"""
    def __init__(self, message: str = "トークン数制限を超えました", token_count: int = None, max_tokens: int = None, *args, **kwargs):
        self.token_count = token_count
        self.max_tokens = max_tokens
        if token_count and max_tokens:
            message = f"{message} (使用: {token_count}, 最大: {max_tokens})"
        super().__init__(message, *args, **kwargs)


class ServiceUnavailableError(LLMError):
    """LLMサービスが利用できない場合のエラー"""
    def __init__(self, message: str = "LLMサービスが一時的に利用できません", *args, **kwargs):
        super().__init__(message, *args, **kwargs)


class ContentPolicyViolationError(LLMError):
    """コンテンツポリシー違反のエラー"""
    def __init__(self, message: str = "コンテンツポリシー違反が検出されました", policy_type: str = None, *args, **kwargs):
        self.policy_type = policy_type
        if policy_type:
            message = f"{message} (違反タイプ: {policy_type})"
        super().__init__(message, *args, **kwargs)


class AuthenticationError(LLMError):
    """認証エラー"""
    def __init__(self, message: str = "APIキーが無効または期限切れです", *args, **kwargs):
        super().__init__(message, *args, **kwargs)


class InvalidRequestError(LLMError):
    """無効なリクエストエラー"""
    def __init__(self, message: str = "無効なリクエストが送信されました", details: str = None, *args, **kwargs):
        self.details = details
        if details:
            message = f"{message} (詳細: {details})"
        super().__init__(message, *args, **kwargs)


class ModelNotFoundError(LLMError):
    """指定されたモデルが見つからない場合のエラー"""
    def __init__(self, model_name: str = None, message: str = "指定されたモデルが見つかりません", *args, **kwargs):
        self.model_name = model_name
        if model_name:
            message = f"{message} (モデル: {model_name})"
        super().__init__(message, *args, **kwargs)


class ContextLengthExceededError(TokenLimitError):
    """コンテキスト長が制限を超えた場合のエラー"""
    def __init__(self, message: str = "コンテキスト長が制限を超えました", *args, **kwargs):
        super().__init__(message, *args, **kwargs)


class QuotaExceededError(LLMError):
    """クォータを超えた場合のエラー"""
    def __init__(self, message: str = "APIクォータを超えました", *args, **kwargs):
        super().__init__(message, *args, **kwargs)


class TimeoutError(LLMError):
    """LLM呼び出しがタイムアウトした場合のエラー"""
    def __init__(self, message: str = "LLM呼び出しがタイムアウトしました", timeout_seconds: int = None, *args, **kwargs):
        self.timeout_seconds = timeout_seconds
        if timeout_seconds:
            message = f"{message} ({timeout_seconds}秒後)"
        super().__init__(message, *args, **kwargs)


class MaxRetriesExceededError(LLMError):
    """最大リトライ回数を超えた場合のエラー"""
    def __init__(self, message: str = "最大リトライ回数を超えました", max_retries: int = None, *args, **kwargs):
        self.max_retries = max_retries
        if max_retries:
            message = f"{message} (最大リトライ回数: {max_retries})"
        super().__init__(message, *args, **kwargs) 