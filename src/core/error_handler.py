"""
システム全体のエラー処理を担当するエラーハンドラーモジュール
"""

import logging
import asyncio
import traceback
from typing import Dict, Any, Optional, Callable, Tuple, List, Type, Union
from datetime import datetime, timedelta

# 循環インポートを避けるために削除
# from src.core.workflow import WorkflowState
from src.core.llm.errors import (
    LLMError,
    RateLimitError,
    TokenLimitError,
    ServiceUnavailableError,
    ContentPolicyViolationError
)
from src.models.schema import AgentMessage, MessagePriority

logger = logging.getLogger(__name__)

# 最大エラー回数
MAX_ERROR_COUNT = 3
# デフォルトのリトライ間隔（秒）
DEFAULT_RETRY_DELAY = 5
# 最大リトライ間隔（秒）
MAX_RETRY_DELAY = 60
# エクスポネンシャルバックオフ係数
BACKOFF_FACTOR = 2

# エラータイプの定義
ERROR_TYPE_TRANSIENT = "transient"  # 一時的なエラー
ERROR_TYPE_PERMANENT = "permanent"  # 永続的なエラー
ERROR_TYPE_BUSINESS = "business"  # ビジネスロジックエラー
ERROR_TYPE_TIMEOUT = "timeout"  # タイムアウトエラー
ERROR_TYPE_DATA = "data"  # データエラー
ERROR_TYPE_MESSAGING = "messaging"  # メッセージングエラー


class ErrorHandler:
    """
    エラーハンドリングと回復戦略を実装するクラス
    """
    
    def __init__(self, context_store: Any = None, message_broker: Any = None):
        """
        初期化
        
        Args:
            context_store: ワークフローコンテキストストア（オプション）
            message_broker: メッセージブローカー（オプション）
        """
        self.context_store = context_store
        self.message_broker = message_broker
        self.dead_letter_queue = []  # 処理できなかったメッセージのキュー
        
        self.error_strategies = {
            # LLMエラー
            "RateLimitError": (ERROR_TYPE_TRANSIENT, self._handle_rate_limit_error),
            "TokenLimitError": (ERROR_TYPE_TRANSIENT, self._handle_token_limit_error),
            "ServiceUnavailableError": (ERROR_TYPE_TRANSIENT, self._handle_service_unavailable_error),
            "ContentPolicyViolationError": (ERROR_TYPE_PERMANENT, self._handle_content_policy_violation),
            "LLMError": (ERROR_TYPE_TRANSIENT, self._handle_llm_error),
            
            # データエラー
            "JSONDecodeError": (ERROR_TYPE_DATA, self._handle_json_decode_error),
            "ValueError": (ERROR_TYPE_DATA, self._handle_value_error),
            "KeyError": (ERROR_TYPE_DATA, self._handle_key_error),
            "IndexError": (ERROR_TYPE_DATA, self._handle_index_error),
            
            # タイムアウトエラー
            "TimeoutError": (ERROR_TYPE_TIMEOUT, self._handle_timeout_error),
            "asyncio.TimeoutError": (ERROR_TYPE_TIMEOUT, self._handle_timeout_error),
            
            # IOエラー
            "FileNotFoundError": (ERROR_TYPE_PERMANENT, self._handle_file_not_found_error),
            "PermissionError": (ERROR_TYPE_PERMANENT, self._handle_permission_error),
            "IOError": (ERROR_TYPE_TRANSIENT, self._handle_io_error),
            
            # メッセージングエラー
            "MessageDeliveryError": (ERROR_TYPE_MESSAGING, self._handle_message_delivery_error),
            "MessageFormatError": (ERROR_TYPE_MESSAGING, self._handle_message_format_error),
            "MessageProcessingError": (ERROR_TYPE_MESSAGING, self._handle_message_processing_error),
            
            # その他のエラー
            "Exception": (ERROR_TYPE_PERMANENT, self._handle_generic_error)
        }
        
    async def handle_error(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """
        エラーを処理し、回復できた場合はTrue、できなかった場合はFalseを返す
        
        Args:
            state: 現在のワークフロー状態
            error: 発生したエラー
            
        Returns:
            Tuple[bool, WorkflowState]: (回復できたかどうか, 更新されたワークフロー状態)
        """
        error_type_name = type(error).__name__
        
        # エラーカウントの更新
        error_data = state.get("error_data", {})
        error_count = error_data.get("count", 0) + 1
        
        # エラー情報の保存
        error_data.update({
            "count": error_count,
            "last_error": str(error),
            "last_error_type": error_type_name,
            "last_error_time": datetime.now().isoformat(),
            "last_error_agent": state.get("current_agent", "unknown"),
            "traceback": traceback.format_exc()
        })
        
        # 状態を更新
        state = dict(state)  # 不変オブジェクトの場合、コピーを作成
        state["error_data"] = error_data
        
        # 最大エラー回数を超えた場合
        if error_count > MAX_ERROR_COUNT:
            state["status"] = "failed"
            state["error"] = f"最大エラー回数({MAX_ERROR_COUNT})を超えました: {str(error)}"
            logger.error(f"ワークフロー {state.get('workflow_id', 'unknown')} が最大エラー回数を超えました")
            return False, state
        
        # エラータイプに応じた処理
        if error_type_name in self.error_strategies:
            error_category, handler = self.error_strategies[error_type_name]
        else:
            # 未知のエラータイプは汎用ハンドラーで処理
            error_category, handler = self.error_strategies["Exception"]
        
        # エラーログの記録
        logger.error(
            f"エラー発生: {error_type_name} ({error_category}), "
            f"メッセージ: {str(error)}, "
            f"エージェント: {state.get('current_agent', 'unknown')}, "
            f"ワークフローID: {state.get('workflow_id', 'unknown')}"
        )
        
        try:
            # エラーハンドラの実行
            recovered, updated_state = await handler(state, error)
            
            if recovered:
                # 回復成功
                logger.info(f"エラーから回復しました: {error_type_name}")
                # ステータスを更新
                updated_state["status"] = "running"
                updated_state["error"] = None
                return True, updated_state
            else:
                # 回復失敗
                logger.warning(f"エラーから回復できませんでした: {error_type_name}")
                updated_state["status"] = "failed"
                updated_state["error"] = str(error)
                return False, updated_state
                
        except Exception as handler_error:
            # エラーハンドラ自体がエラーを発生させた場合
            logger.exception(f"エラーハンドラでエラーが発生しました: {str(handler_error)}")
            state["status"] = "failed"
            state["error"] = f"エラー処理中にエラーが発生しました: {str(handler_error)}"
            return False, state
    
    async def _handle_rate_limit_error(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """レート制限エラーの処理（一時停止して再試行）"""
        # 状態を更新して一時停止
        state = dict(state)
        state["status"] = "paused"
        state["retry_after"] = datetime.now().timestamp() + 60  # 1分後に再試行
        state["retry_reason"] = "APIレート制限に到達したため待機中"
        
        # コンテキストストアがある場合は保存
        if self.context_store:
            await self.context_store.save_context(state["workflow_id"], state)
            
        return True, state
        
    async def _handle_token_limit_error(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """トークン制限エラーの処理（プロンプトやコンテキストを短縮）"""
        # 現在のエージェントを取得
        current_agent = state.get("current_agent")
        
        # エージェント別の対応
        if current_agent == "agent_a":
            # 監査手続きを要約して短くする
            procedure_text = state.get("procedure_text", "")
            if len(procedure_text) > 1000:
                state["procedure_text"] = procedure_text[:1000] + "...(要約)"
                state["procedure_truncated"] = True
                return True, state
        elif current_agent == "agent_b":
            # サンプルデータを減らす
            # この実装はデータ形式に依存するため、具体的なデータ構造に応じた実装が必要
            return False, state
        elif current_agent == "agent_c" or current_agent == "agent_d":
            # 結果データを要約・簡略化
            # 具体的な実装はデータ構造に依存
            return False, state
            
        # 対応できない場合
        return False, state
        
    async def _handle_service_unavailable_error(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """サービス利用不可エラーの処理（待機して再試行）"""
        # 状態を更新して一時停止
        state = dict(state)
        state["status"] = "paused"
        state["retry_after"] = datetime.now().timestamp() + 300  # 5分後に再試行
        state["retry_reason"] = "サービスが一時的に利用できないため待機中"
        
        # コンテキストストアがある場合は保存
        if self.context_store:
            await self.context_store.save_context(state["workflow_id"], state)
            
        return True, state
        
    async def _handle_content_policy_violation(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """コンテンツポリシー違反の処理（人間の介入が必要）"""
        # 永続的なエラーとして処理
        state = dict(state)
        state["status"] = "human_intervention_required"
        state["error"] = f"コンテンツポリシー違反: {str(error)}"
        state["human_action_required"] = "コンテンツポリシー違反の確認と修正"
        
        logger.warning(f"コンテンツポリシー違反のため人間の介入が必要: {state.get('workflow_id')}")
        
        return False, state
        
    async def _handle_llm_error(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """一般的なLLMエラーの処理"""
        # 一時的なエラーとして処理し、再試行
        return True, state
        
    async def _handle_json_decode_error(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """JSON解析エラーの処理"""
        # データエラーとして処理
        # LLMのレスポンスがJSONでない場合など
        
        # 現在のエージェントを取得
        current_agent = state.get("current_agent")
        agent_output_key = f"{current_agent}_output"
        
        # エラーの詳細を保存
        state = dict(state)
        state["last_json_error"] = str(error)
        
        # LLMを再度呼び出す指示を設定
        state["retry_instruction"] = "JSON形式で出力するよう明示的に指示してください"
        
        return True, state
        
    async def _handle_value_error(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """値エラーの処理"""
        # データエラーとして処理
        return self._generic_data_error_handler(state, error)
        
    async def _handle_key_error(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """キーエラーの処理"""
        # データエラーとして処理
        return self._generic_data_error_handler(state, error)
        
    async def _handle_index_error(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """インデックスエラーの処理"""
        # データエラーとして処理
        return self._generic_data_error_handler(state, error)
        
    async def _handle_timeout_error(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """タイムアウトエラーの処理"""
        # 状態を更新して再試行
        state = dict(state)
        state["timeout_count"] = state.get("timeout_count", 0) + 1
        
        # タイムアウト回数が多すぎる場合は失敗
        if state["timeout_count"] > 2:
            state["status"] = "failed"
            state["error"] = f"処理がタイムアウトを繰り返しています: {str(error)}"
            return False, state
            
        # 次回はタイムアウト時間を延長
        state["extended_timeout"] = True
        return True, state
        
    async def _handle_file_not_found_error(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """ファイル未検出エラーの処理"""
        # 永続的なエラーとして処理
        state = dict(state)
        state["status"] = "failed"
        state["error"] = f"ファイルが見つかりません: {str(error)}"
        
        return False, state
        
    async def _handle_permission_error(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """権限エラーの処理"""
        # 永続的なエラーとして処理
        state = dict(state)
        state["status"] = "failed"
        state["error"] = f"ファイルへのアクセス権限がありません: {str(error)}"
        
        return False, state
        
    async def _handle_io_error(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """IO エラーの処理"""
        # 一時的なエラーとして処理し、再試行
        state = dict(state)
        state["io_error_count"] = state.get("io_error_count", 0) + 1
        
        # IO エラーが多すぎる場合は失敗
        if state["io_error_count"] > 3:
            state["status"] = "failed"
            state["error"] = f"IOエラーが繰り返し発生しています: {str(error)}"
            return False, state
            
        return True, state
        
    async def _handle_generic_error(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """汎用エラーハンドラー"""
        # 回復不能なエラーとして処理
        state = dict(state)
        state["status"] = "failed"
        state["error"] = f"予期しないエラーが発生しました: {str(error)}"
        
        logger.error(f"未処理のエラー: {type(error).__name__}: {str(error)}")
        logger.error(traceback.format_exc())
        
        return False, state
        
    def _generic_data_error_handler(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """データエラー用の汎用ハンドラー"""
        # データエラーとして処理
        state = dict(state)
        state["data_error_count"] = state.get("data_error_count", 0) + 1
        
        # データエラーが多すぎる場合は失敗
        if state["data_error_count"] > 3:
            state["status"] = "failed"
            state["error"] = f"データエラーが繰り返し発生しています: {str(error)}"
            return False, state
            
        # エラーの詳細を保存
        state["last_data_error"] = str(error)
        
        return True, state

    def _calculate_retry_delay(self, error_count: int) -> int:
        """
        エクスポネンシャルバックオフでリトライ間隔を計算
        
        Args:
            error_count: エラー発生回数
            
        Returns:
            次のリトライまでの待機時間（秒）
        """
        delay = DEFAULT_RETRY_DELAY * (BACKOFF_FACTOR ** (error_count - 1))
        return min(delay, MAX_RETRY_DELAY)

    async def _handle_message_delivery_error(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """
        メッセージ配信エラーの処理
        
        Args:
            state: 現在のワークフロー状態
            error: メッセージ配信エラー
            
        Returns:
            (回復できたかどうか, 更新されたワークフロー状態)
        """
        error_data = state.get("error_data", {})
        error_count = error_data.get("count", 0)
        
        if error_count <= MAX_ERROR_COUNT:
            # メッセージの再送を試みる
            message_id = error_data.get("failed_message_id")
            if message_id and self.message_broker:
                try:
                    # リトライ間隔の計算
                    retry_delay = self._calculate_retry_delay(error_count)
                    logger.info(f"メッセージ {message_id} の再送を {retry_delay}秒後に試みます")
                    
                    # 実際のアプリケーションではここで非同期に待機
                    await asyncio.sleep(retry_delay)
                    
                    # メッセージを取得して再送
                    message = self.message_broker.get_message(message_id)
                    if message:
                        # メッセージを再送（実際のコードでは適切なメソッドを呼び出す）
                        logger.info(f"メッセージ {message_id} を再送します")
                        return True, state
                except Exception as e:
                    logger.error(f"メッセージ再送中にエラーが発生しました: {str(e)}")
        
        # 回復不能な場合はデッドレターキューに移動
        self.add_to_dead_letter_queue(state.get("failed_message", {}), error)
        return False, state

    async def _handle_message_format_error(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """
        メッセージフォーマットエラーの処理
        
        Args:
            state: 現在のワークフロー状態
            error: メッセージフォーマットエラー
            
        Returns:
            (回復できたかどうか, 更新されたワークフロー状態)
        """
        # フォーマットエラーは自動回復が難しいため、デッドレターキューに移動
        self.add_to_dead_letter_queue(state.get("failed_message", {}), error)
        return False, state

    async def _handle_message_processing_error(self, state: "Dict[str, Any]", error: Exception) -> Tuple[bool, "Dict[str, Any]"]:
        """
        メッセージ処理エラーの処理
        
        Args:
            state: 現在のワークフロー状態
            error: メッセージ処理エラー
            
        Returns:
            (回復できたかどうか, 更新されたワークフロー状態)
        """
        error_data = state.get("error_data", {})
        error_count = error_data.get("count", 0)
        
        if error_count <= MAX_ERROR_COUNT:
            # 処理を単純化して再試行
            try:
                # リトライ間隔の計算
                retry_delay = self._calculate_retry_delay(error_count)
                logger.info(f"メッセージ処理を {retry_delay}秒後に再試行します")
                
                # 実際のアプリケーションではここで非同期に待機
                await asyncio.sleep(retry_delay)
                
                # 処理を再試行する準備
                state["retry_processing"] = True
                return True, state
            except Exception as e:
                logger.error(f"処理再試行準備中にエラーが発生しました: {str(e)}")
        
        # 回復不能な場合はデッドレターキューに移動
        self.add_to_dead_letter_queue(state.get("failed_message", {}), error)
        return False, state
        
    def add_to_dead_letter_queue(self, message: Union[Dict[str, Any], AgentMessage], error: Exception) -> None:
        """
        処理できなかったメッセージをデッドレターキューに追加
        
        Args:
            message: 失敗したメッセージ
            error: 発生したエラー
        """
        dead_letter = {
            "message": message.to_dict() if hasattr(message, "to_dict") else message,
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": datetime.now().isoformat(),
            "traceback": traceback.format_exc()
        }
        self.dead_letter_queue.append(dead_letter)
        logger.warning(f"メッセージがデッドレターキューに移動されました: {dead_letter.get('message', {}).get('id', 'unknown')}")
    
    def get_dead_letter_queue(self) -> List[Dict[str, Any]]:
        """
        デッドレターキューを取得
        
        Returns:
            デッドレターキューのリスト
        """
        return self.dead_letter_queue
        
    def process_dead_letters(self, handler: Optional[Callable[[Dict[str, Any]], bool]] = None) -> int:
        """
        デッドレターキューの処理を試みる
        
        Args:
            handler: 処理ハンドラー関数（省略時はデフォルト処理）
            
        Returns:
            処理に成功したメッセージ数
        """
        if not self.dead_letter_queue:
            return 0
            
        processed_count = 0
        remaining_queue = []
        
        for dead_letter in self.dead_letter_queue:
            try:
                if handler:
                    # カスタムハンドラーで処理
                    success = handler(dead_letter)
                else:
                    # デフォルト処理（ログに記録するだけ）
                    logger.info(f"デッドレター処理: {dead_letter.get('message', {}).get('id', 'unknown')}")
                    success = True
                    
                if success:
                    processed_count += 1
                    continue
            except Exception as e:
                logger.error(f"デッドレター処理中にエラーが発生: {str(e)}")
                
            # 処理に失敗したメッセージは残す
            remaining_queue.append(dead_letter)
            
        # 処理済みのメッセージをキューから削除
        self.dead_letter_queue = remaining_queue
        logger.info(f"デッドレターキュー処理完了: {processed_count}件処理, {len(remaining_queue)}件残り")
        
        return processed_count 