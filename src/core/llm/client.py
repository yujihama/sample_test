"""
LLMクライアントモジュール

OpenAI、Anthropic、Hugging Faceなどの各種LLMサービスとの連携機能を提供します。
"""

import json
from src.utils import json_utils
import asyncio
import logging
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime

from src.core.config import Settings, settings
from .errors import (
    LLMError, 
    RateLimitError, 
    TokenLimitError, 
    ServiceUnavailableError,
    ContentPolicyViolationError,
    AuthenticationError,
    InvalidRequestError
)
from .retry_handler import LLMRetryHandler, RetrySettings, with_retry

logger = logging.getLogger(__name__)

@dataclass
class LLMResponse:
    """LLMからのレスポンスを表現するクラス"""
    
    content: str  # 生成されたテキスト
    tokens_used: int  # 使用されたトークン数
    model_used: str  # 使用されたモデル名
    confidence: float = 1.0  # 信頼度スコア（0.0-1.0）
    metadata: Dict = None  # その他のメタデータ
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
            
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            "content": self.content,
            "tokens_used": self.tokens_used,
            "model_used": self.model_used,
            "confidence": self.confidence,
            "metadata": self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'LLMResponse':
        """辞書形式からインスタンスを生成"""
        return cls(
            content=data["content"],
            tokens_used=data["tokens_used"],
            model_used=data["model_used"],
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {})
        )


class LLMClient:
    """
    各種LLMサービスとの連携機能を提供するクライアントクラス
    """
    
    def __init__(self, config: Settings):
        self.config = config
        self.primary_client = self._initialize_primary_client()
        self.secondary_client = self._initialize_secondary_client()
        
        # 再試行設定を初期化
        self.retry_settings = RetrySettings(
            max_retries=self.config.LLM_MAX_RETRIES,
            base_delay=self.config.LLM_RETRY_BASE_DELAY,
            max_delay=self.config.LLM_RETRY_MAX_DELAY,
            backoff_factor=self.config.LLM_RETRY_BACKOFF_FACTOR
        )
        self.retry_handler = LLMRetryHandler(self.retry_settings)
        
        logger.info(
            f"LLMClient initialized with primary provider: {self.config.LLM_PRIMARY_PROVIDER}, "
            f"model: {self.config.LLM_PRIMARY_MODEL}"
        )
        
    def _initialize_primary_client(self):
        """プライマリLLMクライアントの初期化"""
        llm_type = self.config.LLM_PRIMARY_TYPE
        
        if llm_type == "openai":
            # OpenAIクライアントを初期化
            try:
                from openai import AsyncOpenAI
                return AsyncOpenAI(api_key=self.config.OPENAI_API_KEY)
            except ImportError:
                logger.error("OpenAI APIがインストールされていません。pip install openai を実行してください。")
                raise
        elif llm_type == "anthropic":
            # Anthropicクライアントを初期化
            try:
                from anthropic import AsyncAnthropic
                return AsyncAnthropic(api_key=self.config.ANTHROPIC_API_KEY)
            except ImportError:
                logger.error("Anthropic APIがインストールされていません。pip install anthropic を実行してください。")
                raise
        else:
            raise ValueError(f"未対応のLLMタイプ: {llm_type}")
            
    def _initialize_secondary_client(self):
        """セカンダリLLMクライアントの初期化"""
        llm_type = self.config.LLM_SECONDARY_TYPE
        
        if not llm_type:
            return None
            
        if llm_type == "openai":
            # OpenAIクライアントを初期化
            try:
                from openai import AsyncOpenAI
                return AsyncOpenAI(api_key=self.config.OPENAI_API_KEY)
            except ImportError:
                logger.error("OpenAI APIがインストールされていません。pip install openai を実行してください。")
                return None
        elif llm_type == "anthropic":
            # Anthropicクライアントを初期化
            try:
                from anthropic import AsyncAnthropic
                return AsyncAnthropic(api_key=self.config.ANTHROPIC_API_KEY)
            except ImportError:
                logger.error("Anthropic APIがインストールされていません。pip install anthropic を実行してください。")
                return None
        else:
            logger.warning(f"未対応のセカンダリLLMタイプ: {llm_type}")
            return None
        
    async def generate_response(self, prompt: str, options: Dict = None) -> LLMResponse:
        """
        LLMからのレスポンスを生成する
        
        Args:
            prompt: LLMに送信するプロンプト
            options: 生成オプション（モデル名、温度など）
            
        Returns:
            LLMResponse: 生成されたレスポンス
        """
        options = options or {}
        llm_type = self.config.LLM_PRIMARY_TYPE
        
        if llm_type == "openai":
            return await self._generate_openai_response(prompt, options)
        elif llm_type == "anthropic":
            return await self._generate_anthropic_response(prompt, options)
        else:
            raise ValueError(f"未対応のLLMタイプ: {llm_type}")
        
    async def generate_with_fallback(self, prompt: str, options: Dict = None) -> LLMResponse:
        """
        プライマリLLMで失敗した場合にセカンダリLLMを使用してレスポンスを生成する
        
        Args:
            prompt: LLMに送信するプロンプト
            options: 生成オプション（モデル名、温度など）
            
        Returns:
            LLMResponse: 生成されたレスポンス
        """
        try:
            return await self.generate_response(prompt, options)
        except Exception as e:
            logger.warning(f"プライマリLLMでエラーが発生しました: {str(e)}")
            
            if self.secondary_client is None:
                logger.error("セカンダリLLMクライアントが設定されていません。")
                raise
                
            # セカンダリLLMタイプを一時的に設定
            original_llm_type = self.config.LLM_PRIMARY_TYPE
            self.config.LLM_PRIMARY_TYPE = self.config.LLM_SECONDARY_TYPE
            
            try:
                return await self.generate_response(prompt, options)
            finally:
                # 元の設定に戻す
                self.config.LLM_PRIMARY_TYPE = original_llm_type
        
    async def extract_structured_data(self, text: str, schema: Dict) -> Dict:
        """
        LLMレスポンスから構造化データを抽出する
        
        Args:
            text: 構造化したいテキスト
            schema: 期待されるJSONスキーマ
            
        Returns:
            Dict: 抽出された構造化データ
        """
        prompt = f"""
以下のテキストから、指定されたスキーマに基づいて構造化データを抽出してください。
出力は有効なJSONフォーマットである必要があります。

## テキスト
{text}

## 出力スキーマ
{json_utils.json_serialize(schema)}

## 出力
"""
        
        options = {
            "temperature": 0.1,  # 決定的な出力を得るために低い温度を設定
        }
        
        response = await self.generate_response(prompt, options)
        
        # JSONの抽出
        content = response.content
        try:
            # テキストからJSONブロックを探す
            json_start = content.find('{')
            json_end = content.rfind('}')
            
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end+1]
                return json_utils.json_deserialize(json_str)
            else:
                # JSONが見つからない場合は、全体を解析してみる
                return json_utils.json_deserialize(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSONの解析に失敗しました: {e}")
            # JSON修復を試みる
            return self._attempt_json_repair(content)
            
    def _attempt_json_repair(self, text: str) -> Dict:
        """
        不正なJSON文字列の修復を試みる
        
        Args:
            text: 修復するJSON文字列
            
        Returns:
            Dict: 修復されたJSONオブジェクト
            
        Raises:
            ValueError: 修復が失敗した場合
        """
        # シンプルな修復ルール
        # 1. 末尾のカンマを削除
        text = text.replace(',}', '}').replace(',]', ']')
        
        # 2. シングルクォートをダブルクォートに変換
        text = text.replace("'", '"')
        
        # 3. JSONブロックを抽出
        import re
        json_pattern = r'\{.*\}'
        match = re.search(json_pattern, text, re.DOTALL)
        
        if match:
            try:
                return json_utils.json_deserialize(match.group(0))
            except json.JSONDecodeError:
                pass
                
        # それでも失敗する場合は諦める
        raise ValueError("JSONの修復に失敗しました")
        
    @with_retry()
    async def _generate_openai_response(self, prompt: str, options: Dict) -> LLMResponse:
        """
        OpenAI APIを使用してレスポンスを生成
        
        Args:
            prompt: プロンプト
            options: API呼び出しのオプション
            
        Returns:
            LLMResponse: レスポンス
            
        Raises:
            LLMError: API呼び出し失敗時
        """
        model = options.get("model", self.config.OPENAI_MODEL)
        temperature = options.get("temperature", 0.7)
        max_tokens = options.get("max_tokens", 2000)
        
        try:
            response = await self.primary_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                tokens_used=response.usage.total_tokens,
                model_used=model,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"OpenAI APIエラー: {str(e)}")
            self._handle_openai_error(e)
            
    @with_retry()
    async def _generate_anthropic_response(self, prompt: str, options: Dict) -> LLMResponse:
        """
        Anthropic APIを使用してレスポンスを生成
        
        Args:
            prompt: プロンプト
            options: API呼び出しのオプション
            
        Returns:
            LLMResponse: レスポンス
            
        Raises:
            LLMError: API呼び出し失敗時
        """
        model = options.get("model", self.config.ANTHROPIC_MODEL)
        temperature = options.get("temperature", 0.7)
        max_tokens = options.get("max_tokens", 2000)
        
        try:
            response = await self.secondary_client.completions.create(
                model=model,
                prompt=f"\n\nHuman: {prompt}\n\nAssistant:",
                temperature=temperature,
                max_tokens_to_sample=max_tokens
            )
            
            # トークン数の計算（現在のAnthropicAPIではトークン数が返されないため推定）
            # このロジックは実際のAPIの仕様に合わせて調整が必要
            estimated_tokens = len(prompt) // 4 + len(response.completion) // 4
            
            return LLMResponse(
                content=response.completion,
                tokens_used=estimated_tokens,
                model_used=model,
                metadata={
                    "stop_reason": response.stop_reason,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Anthropic APIエラー: {str(e)}")
            self._handle_anthropic_error(e)
            
    def _handle_openai_error(self, error):
        """OpenAI APIエラーを適切な例外に変換する"""
        import openai
        
        if isinstance(error, openai.RateLimitError):
            raise RateLimitError("APIレート制限に到達しました") from error
        elif isinstance(error, openai.APITimeoutError):
            raise ServiceUnavailableError("APIタイムアウトが発生しました") from error
        elif isinstance(error, openai.APIConnectionError):
            raise ServiceUnavailableError("API接続エラーが発生しました") from error
        elif "maximum context length" in str(error).lower():
            raise TokenLimitError("最大トークン数を超過しました") from error
        else:
            raise LLMError(f"OpenAI APIエラー: {str(error)}") from error
            
    def _handle_anthropic_error(self, error):
        """Anthropic APIエラーを適切な例外に変換する"""
        error_message = str(error).lower()
        
        if "rate limit" in error_message:
            raise RateLimitError("APIレート制限に到達しました") from error
        elif "timeout" in error_message:
            raise ServiceUnavailableError("APIタイムアウトが発生しました") from error
        elif "connection" in error_message:
            raise ServiceUnavailableError("API接続エラーが発生しました") from error
        elif "token" in error_message and "limit" in error_message:
            raise TokenLimitError("最大トークン数を超過しました") from error
        else:
            raise LLMError(f"Anthropic APIエラー: {str(error)}") from error
            
    async def safe_llm_call(self, prompt: str, max_retries: int = 3, options: Dict = None) -> LLMResponse:
        """
        再試行機能付きのLLM呼び出し
        
        Args:
            prompt: プロンプト
            max_retries: 最大再試行回数
            options: API呼び出しのオプション
            
        Returns:
            LLMResponse: 生成されたレスポンス
            
        Raises:
            LLMError: すべての再試行が失敗した場合
        """
        if options is None:
            options = {}
            
        # カスタム再試行設定を作成（呼び出し固有の設定をサポート）
        custom_settings = RetrySettings(
            max_retries=max_retries,
            base_delay=self.retry_settings.base_delay,
            max_delay=self.retry_settings.max_delay,
            backoff_factor=self.retry_settings.backoff_factor
        )
        
        custom_handler = LLMRetryHandler(custom_settings)
        
        try:
            # 主要プロバイダーでの実行を再試行付きで実行
            return await custom_handler.execute_with_retry(
                self.generate_response, prompt, options
            )
        except (ServiceUnavailableError, RateLimitError) as e:
            # 主要プロバイダーがサービス不可またはレート制限の場合、フォールバックを試行
            logger.warning(
                f"Primary LLM provider failed with {e.__class__.__name__}: {e}. "
                f"Attempting fallback provider."
            )
            
            # フォールバックプロバイダーで再試行
            try:
                return await custom_handler.execute_with_retry(
                    self._generate_fallback_response, prompt, options
                )
            except LLMError as fallback_error:
                logger.error(
                    f"Fallback provider also failed: {fallback_error}. "
                    f"No more providers to try."
                )
                raise
        except LLMError as e:
            # その他のLLMエラーは再試行せずに上位に伝播
            logger.error(f"LLM call failed with error: {e}")
            raise
    
    async def _generate_fallback_response(self, prompt: str, options: Dict) -> LLMResponse:
        """
        フォールバックプロバイダーを使用してレスポンスを生成
        
        Args:
            prompt: プロンプト
            options: API呼び出しのオプション
            
        Returns:
            LLMResponse: レスポンス
        """
        fallback_options = options.copy()
        fallback_options["use_fallback"] = True
        
        return await self.generate_with_fallback(prompt, fallback_options)


def validate_llm_output(raw_output: str, expected_schema: Dict) -> Tuple[bool, Dict, str]:
    """
    LLM出力を検証し、問題があればエラーメッセージを返す
    
    Args:
        raw_output: LLMからの生のテキスト出力
        expected_schema: 期待されるJSONスキーマ
        
    Returns:
        Tuple[bool, Dict, str]: (検証成功フラグ, パース済みデータ, エラーメッセージ)
    """
    try:
        # JSON解析を試みる
        json_start = raw_output.find('{')
        json_end = raw_output.rfind('}')
        
        if json_start >= 0 and json_end > json_start:
            json_str = raw_output[json_start:json_end+1]
            parsed_output = json_utils.json_deserialize(json_str)
        else:
            # JSONが見つからない場合は、全体を解析してみる
            parsed_output = json_utils.json_deserialize(raw_output)
        
        # ここではシンプルにキーの存在チェックのみを行う
        # 実際には jsonschema ライブラリなどを使用した完全なスキーマ検証が望ましい
        for key in expected_schema.get("required", []):
            if key not in parsed_output:
                return False, {}, f"必須キー '{key}' がありません"
                
        return True, parsed_output, ""
        
    except json.JSONDecodeError as e:
        # JSON解析エラーの場合、修復を試みる
        try:
            client = LLMClient(Settings())  # 設定を取得するためのダミーインスタンス
            fixed_output = client._attempt_json_repair(raw_output)
            
            # 修復後に再度キーのチェック
            for key in expected_schema.get("required", []):
                if key not in fixed_output:
                    return False, {}, f"修復後も必須キー '{key}' がありません"
                    
            return True, fixed_output, "JSON was repaired"
                
        except Exception:
            return False, {}, f"JSON解析エラー: {str(e)}" 