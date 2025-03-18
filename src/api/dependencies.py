"""
APIの依存関係を定義するモジュール

このモジュールは、FastAPIの依存関係注入に使用される関数を提供します。
"""

from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader, SecurityScopes
from src.core.agent_manager import AgentManager
from src.core.agent_management_service import get_agent_management_service, AgentManagementService
from src.core.workflow_service import get_workflow_service, WorkflowService
from src.core.workflow import get_workflow_status as orig_get_workflow_status
from src.core.agent_workflow import run_workflow as orig_run_workflow
from src.core.config import settings
from src.utils.logger import get_logger
import warnings
import asyncio

logger = get_logger(__name__)

# OAuth2のスキーマを設定
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# テスト用の認証トークン
TEST_TOKEN = "test_token"
TEST_USER = {
    "username": "test_user",
    "role": "admin"
}

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

def get_current_user(security_scopes: SecurityScopes, api_key: str = Depends(api_key_header)):
    """
    現在のユーザーを取得します。

    Args:
        security_scopes: セキュリティスコープ
        api_key: APIキー

    Returns:
        認証されたユーザー情報

    Raises:
        HTTPException: 認証エラーの場合
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="APIキーが必要です",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # APIキーからBearer プレフィックスを削除
    if api_key.startswith("Bearer "):
        api_key = api_key[7:]

    # 開発環境ではダミーのAPIキーを受け入れる
    if settings.APP_ENV == "development" and api_key in ["test_token", "development_token"]:
        return {"username": "developer", "permissions": ["admin"]}

    # TODO: 実際のAPIキー認証を実装する
    # 本番環境ではAPIキーを検証し、対応するユーザー情報を返す
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無効なAPIキーです",
        headers={"WWW-Authenticate": "Bearer"},
    )

_agent_manager: Optional[AgentManager] = None

def get_agent_manager() -> AgentManager:
    """
    エージェントマネージャーのインスタンスを取得します。
    
    非推奨: 代わりに get_agent_management_service() を使用してください。

    Returns:
        AgentManager: エージェントマネージャーのインスタンス
    """
    warnings.warn(
        "get_agent_manager() は非推奨です。代わりに get_agent_management_service() を使用してください。",
        DeprecationWarning,
        stacklevel=2
    )
    
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
    return _agent_manager

def get_agent_management_service_dependency() -> AgentManagementService:
    """
    エージェント管理サービスの依存関係を提供します。
    
    これはFastAPIのDependsで使用するための関数です。

    Returns:
        AgentManagementService: エージェント管理サービスのインスタンス
    """
    return get_agent_management_service()

def get_workflow_service_dependency() -> WorkflowService:
    """
    ワークフロー管理サービスの依存関係を提供します。
    
    これはFastAPIのDependsで使用するための関数です。

    Returns:
        WorkflowService: ワークフロー管理サービスのインスタンス
    """
    return get_workflow_service()

async def get_workflow_status(workflow_id: str) -> Optional[dict]:
    """
    ワークフローの状態を取得します。
    
    非推奨: 代わりに get_workflow_service().get_workflow_status() を使用してください。

    Args:
        workflow_id: ワークフローID
        
    Returns:
        Optional[dict]: ワークフロー状態情報
    """
    warnings.warn(
        "get_workflow_status() は非推奨です。代わりに get_workflow_service().get_workflow_status() を使用してください。",
        DeprecationWarning,
        stacklevel=2
    )
    
    return await orig_get_workflow_status(workflow_id)

async def run_workflow(
    workflow_id: str,
    initial_data: Optional[dict] = None, 
    initial_agent_id: str = settings.AGENT_A_ID,
    config: Optional[dict] = None
) -> dict:
    """
    ワークフローを実行します。
    
    非推奨: 代わりに get_workflow_service().run_workflow() を使用してください。

    Args:
        workflow_id: ワークフローID
        initial_data: 初期データ
        initial_agent_id: 初期エージェントID
        config: 設定
        
    Returns:
        dict: ワークフロー実行結果
    """
    warnings.warn(
        "run_workflow() は非推奨です。代わりに get_workflow_service().run_workflow() を使用してください。",
        DeprecationWarning,
        stacklevel=2
    )
    
    return await orig_run_workflow(
        workflow_id=workflow_id,
        initial_data=initial_data,
        initial_agent_id=initial_agent_id,
        config=config
    )

# 依存関係の型エイリアス
AgentManagerDep = Annotated[AgentManager, Depends(get_agent_manager)]
AgentServiceDep = Annotated[AgentManagementService, Depends(get_agent_management_service_dependency)]
WorkflowServiceDep = Annotated[WorkflowService, Depends(get_workflow_service_dependency)]
CurrentUser = Annotated[dict, Depends(get_current_user)] 