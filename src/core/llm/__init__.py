"""
LLM（大規模言語モデル）との連携機能を提供するモジュール。

このモジュールは、システム内の各エージェントが自然言語処理タスクを実行するための
LLMサービスとの連携機能を提供します。
"""

from .client import LLMClient, LLMResponse
from .errors import (
    LLMError, 
    RateLimitError, 
    TokenLimitError, 
    ServiceUnavailableError,
    ContentPolicyViolationError,
    MaxRetriesExceededError
) 