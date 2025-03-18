"""
監査証跡デコレータモジュール

このモジュールは、監査証跡を自動記録するためのデコレータを提供します。
サービスメソッドを装飾して、操作履歴の自動記録を実現します。
"""

import functools
import inspect
from typing import Dict, Any, Callable, Optional, TypeVar, cast
import logging
from datetime import datetime

from src.utils.regulation_utils import create_audit_details

# 型変数の定義
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

# ロガーの設定
logger = logging.getLogger(__name__)


def audit_trail(
    action: str,
    entity_type: str = "regulation",
    entity_id_param: str = "regulation_id",
    actor_param: str = "actor",
    details_param: Optional[str] = None
) -> Callable[[F], F]:
    """
    監査証跡を自動記録するデコレータ
    
    Args:
        action (str): 実行されるアクション（例: "create", "update", "delete"）
        entity_type (str, optional): エンティティタイプ. デフォルトは "regulation"
        entity_id_param (str, optional): エンティティIDを含むパラメータ名. デフォルトは "regulation_id"
        actor_param (str, optional): 操作者を含むパラメータ名. デフォルトは "actor"
        details_param (Optional[str], optional): 詳細情報を含むパラメータ名. デフォルトはNone
        
    Returns:
        Callable: デコレータ関数
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # selfオブジェクトと引数の確認
            if not args or not hasattr(args[0], 'repository'):
                logger.warning(f"監査デコレータはリポジトリを持つサービスクラスのメソッドにのみ適用できます: {func.__name__}")
                return await func(*args, **kwargs)
                
            self = args[0]
            repo = self.repository
            
            # 引数の抽出
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # エンティティIDと操作者の取得
            entity_id = bound_args.arguments.get(entity_id_param)
            actor = bound_args.arguments.get(actor_param)
            
            # 詳細情報の取得と整形
            details = None
            if details_param and details_param in bound_args.arguments:
                details = create_audit_details(bound_args.arguments[details_param])
            
            # 監査証跡を記録する必要があるか確認
            if not hasattr(repo, 'create_audit_trail') or not entity_id or not actor:
                # 必要な条件を満たさない場合は監査証跡を記録せずに関数を実行
                return await func(*args, **kwargs)
            
            try:
                # 関数の実行
                result = await func(*args, **kwargs)
                
                # 成功した場合のみ監査証跡を記録
                if result is not None:
                    try:
                        # 監査証跡の記録
                        await repo.create_audit_trail(
                            regulation_id=entity_id,
                            action_type=action,
                            user_id=actor,
                            details=details
                        )
                    except Exception as audit_error:
                        # 監査証跡の記録に失敗してもメイン処理は続行
                        logger.error(f"監査証跡の記録に失敗しました: {audit_error}")
                
                return result
                
            except Exception as e:
                # エラー発生時の監査証跡を記録
                try:
                    error_details = {"error": str(e), "timestamp": datetime.now().isoformat()}
                    if details:
                        error_details.update(details)
                    
                    await repo.create_audit_trail(
                        regulation_id=entity_id,
                        action_type=f"{action}_error",
                        user_id=actor,
                        details=error_details
                    )
                except Exception as audit_error:
                    logger.error(f"エラー時の監査証跡の記録に失敗しました: {audit_error}")
                
                # 元の例外を再発生
                raise
        
        return cast(F, wrapper)
    
    return decorator 