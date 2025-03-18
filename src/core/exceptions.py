"""
カスタム例外クラスの定義
"""

class MessageError(Exception):
    """メッセージング関連の基底エラー"""
    pass

class MessageFormatError(MessageError):
    """メッセージフォーマットが無効な場合のエラー"""
    pass

class MessageProcessingError(MessageError):
    """メッセージ処理中のエラー"""
    pass

class MessageRoutingError(MessageError):
    """メッセージルーティング中のエラー"""
    pass

class MessageValidationError(MessageError):
    """メッセージバリデーション中のエラー"""
    pass

class WorkflowError(Exception):
    """ワークフロー関連の基底エラー"""
    pass

class WorkflowExecutionError(WorkflowError):
    """ワークフロー実行中のエラー"""
    pass

class WorkflowValidationError(WorkflowError):
    """ワークフロー検証中のエラー"""
    pass

class AgentError(Exception):
    """エージェント関連の基底エラー"""
    pass

class AgentInitializationError(AgentError):
    """エージェント初期化中のエラー"""
    pass

class AgentCommunicationError(AgentError):
    """エージェント間通信中のエラー"""
    pass

class AgentTaskError(AgentError):
    """エージェントタスク実行中のエラー"""
    pass 