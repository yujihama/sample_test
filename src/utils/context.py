"""
後方互換性のためのリダイレクトモジュール
元々このモジュールにあった ContextClient クラスは src.core.conversation_context に移動されました
既存のインポート文を壊さないようにリダイレクトします
"""
import warnings
from src.core.conversation_context import ContextClient, ConversationManager

# 非推奨警告
warnings.warn(
    "src.utils.context モジュールは非推奨です。代わりに src.core.conversation_context を使用してください",
    DeprecationWarning,
    stacklevel=2
)

# その他、必要なクラスや関数があればここに追加 