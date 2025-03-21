"""
自律的なエージェント管理のためのAPIエンドポイント

このモジュールは、エージェントの起動、停止、監視などのための
RESTful APIエンドポイントを提供します。
"""

import os
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, UTC

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from src.api.dependencies import (
    get_agent_manager, 
    get_agent_management_service_dependency,
    get_workflow_service_dependency
)
from src.api.dependencies import get_current_user
from src.core.config import settings
from src.core.agent_management_service import AgentManagementService
from src.scripts.agent_daemon import AgentDaemon
from src.models.schema import AgentStatus, WorkflowStatus, MessageType, MessagePriority, AgentRole
from src.utils.logger import setup_logger
from src.core.agent_workflow import run_workflow
from src.utils.db_manager import get_db
from src.core.workflow import get_workflow_status, execute_workflow
from src.core.workflow_service import WorkflowService
import logging


# ロガーの設定
logger = logging.getLogger(__name__)

# ルーターの設定
router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    responses={404: {"description": "Not found"}},
)


# リクエスト/レスポンスモデル
class AgentConfigRequest(BaseModel):
    """エージェント設定リクエスト"""
    agent_id: str
    config: Dict[str, Any] = Field(default_factory=dict)


class AgentStatusResponse(BaseModel):
    """エージェントステータスレスポンス"""
    agent_id: str
    status: str
    is_autonomous: bool
    last_activity_time: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    role: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)


class AgentListResponse(BaseModel):
    """エージェント一覧レスポンス"""
    agents: List[AgentStatusResponse]
    count: int


class WorkflowRequest(BaseModel):
    """ワークフロー実行リクエスト"""
    workflow_id: Optional[str] = None
    initial_agent_id: Optional[str] = None
    initial_data: Optional[Dict[str, Any]] = None
    config: Dict[str, Any] = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    """ワークフロー実行レスポンス"""
    workflow_id: str
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    context_id: Optional[str] = None
    results: Optional[Dict[str, Any]] = None


# エージェントデーモンのシングルトンインスタンス
_agent_daemon = None


def get_agent_daemon():
    """
    エージェントデーモンのシングルトンインスタンスを取得
    まだ作成されていない場合は新しく作成する
    """
    global _agent_daemon
    if _agent_daemon is None:
        _agent_daemon = AgentDaemon()
    return _agent_daemon


@router.post("/start", response_model=AgentStatusResponse)
async def start_agent(
    request: AgentConfigRequest,
    background_tasks: BackgroundTasks,
    daemon: AgentDaemon = Depends(get_agent_daemon)
):
    """
    指定されたエージェントを自律モードで起動する
    """
    agent_id = request.agent_id
    config = request.config
    
    # エージェントが存在するか確認
    if agent_id not in daemon.agents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found"
        )
    
    # エージェントを取得
    agent = daemon.agents[agent_id]
    
    # 自律モードでエージェントを起動（バックグラウンドタスクとして）
    async def _start_agent_task():
        try:
            await agent.start_autonomous_mode(config)
            logger.info(f"Agent {agent_id} started in autonomous mode with config: {config}")
        except Exception as e:
            logger.error(f"Error starting agent {agent_id}: {e}")
    
    background_tasks.add_task(_start_agent_task)
    
    # 即時のステータスを返す
    return AgentStatusResponse(
        agent_id=agent_id,
        status="starting",
        is_autonomous=True,
        last_activity_time=datetime.now(UTC),
        metadata={"config": config}
    )


@router.post("/stop", response_model=AgentStatusResponse)
async def stop_agent(
    request: AgentConfigRequest,
    background_tasks: BackgroundTasks,
    daemon: AgentDaemon = Depends(get_agent_daemon)
):
    """
    指定されたエージェントを停止する
    """
    agent_id = request.agent_id
    
    # エージェントが存在するか確認
    if agent_id not in daemon.agents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found"
        )
    
    # エージェントを取得
    agent = daemon.agents[agent_id]
    
    # エージェントを停止（バックグラウンドタスクとして）
    async def _stop_agent_task():
        try:
            await agent.stop_autonomous_mode()
            logger.info(f"Agent {agent_id} stopped")
        except Exception as e:
            logger.error(f"Error stopping agent {agent_id}: {e}")
    
    background_tasks.add_task(_stop_agent_task)
    
    # 即時のステータスを返す
    return AgentStatusResponse(
        agent_id=agent_id,
        status="stopping",
        is_autonomous=False,
        last_activity_time=datetime.now(UTC),
        metadata={}
    )


@router.get("/status/{agent_id}", response_model=AgentStatusResponse)
async def get_agent_status(
    agent_id: str,
    agent_service: AgentManagementService = Depends(get_agent_management_service_dependency)
):
    """
    指定されたエージェントの状態を取得する
    """
    # 新しいAgentManagementServiceを使用
    agent_info = agent_service.get_agent_status(agent_id)
    
    if not agent_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found"
        )
    
    # エージェントのステータス情報を変換
    agent_status = agent_info.get("status", "unknown")
    agent_metadata = agent_info.get("metadata", {})
    agent_role = agent_info.get("role")
    agent_capabilities = agent_info.get("capabilities", [])
    
    # コントローラー情報がある場合は統合
    controller_info = agent_info.get("controller_info", {})
    if controller_info:
        agent_metadata.update({"controller": controller_info})
    
    # タスク情報を取得
    tasks = agent_service.get_agent_tasks(agent_id)
    if tasks:
        agent_metadata["tasks"] = tasks
    
    # 最終アクティビティ時間を取得
    last_activity = agent_info.get("last_activity", datetime.now(UTC))
    
    # 自律モードの状態を判断
    is_autonomous = agent_status in ["running", "processing"]
    
    return AgentStatusResponse(
        agent_id=agent_id,
        status=agent_status,
        is_autonomous=is_autonomous,
        last_activity_time=last_activity,
        metadata=agent_metadata,
        role=str(agent_role) if agent_role else None,
        capabilities=agent_capabilities
    )


@router.get("/list", response_model=AgentListResponse)
async def list_agents(
    agent_service: AgentManagementService = Depends(get_agent_management_service_dependency)
):
    """
    登録されている全てのエージェントの一覧を取得する
    """
    # 新しいAgentManagementServiceを使用
    agents = agent_service.get_all_agents()
    
    agent_responses = []
    for agent in agents:
        agent_id = agent["id"]
        agent_status = agent.get("status", "unknown")
        agent_metadata = agent.get("metadata", {})
        agent_role = agent.get("role")
        agent_capabilities = agent.get("capabilities", [])
        
        # 最終アクティビティ時間を取得
        last_activity = agent.get("last_activity", datetime.now(UTC))
        
        # 自律モードの状態を判断
        is_autonomous = agent_status in ["running", "processing"]
        
        agent_responses.append(
            AgentStatusResponse(
                agent_id=agent_id,
                status=agent_status,
                is_autonomous=is_autonomous,
                last_activity_time=last_activity,
                metadata=agent_metadata,
                role=str(agent_role) if agent_role else None,
                capabilities=agent_capabilities
            )
        )
    
    return AgentListResponse(
        agents=agent_responses,
        count=len(agents)
    )


@router.post("/workflow/start", response_model=WorkflowResponse)
async def start_workflow(
    request: WorkflowRequest,
    background_tasks: BackgroundTasks,
    workflow_service: WorkflowService = Depends(get_workflow_service_dependency)
):
    """
    新しいワークフローを開始する
    """
    # ワークフローIDの生成
    workflow_id = request.workflow_id or f"wf-{uuid.uuid4().hex[:8]}"
    
    # 初期エージェントの設定
    initial_agent_id = request.initial_agent_id or settings.AGENT_A_ID
    
    # 非同期でワークフローを実行
    async def _run_workflow_task():
        try:
            logger.info(f"ワークフロー {workflow_id} を開始中 (初期エージェント: {initial_agent_id})")
            result = await workflow_service.run_workflow(
                workflow_id=workflow_id,
                initial_data=request.initial_data,
                initial_agent_id=initial_agent_id,
                config=request.config
            )
            logger.info(f"ワークフロー {workflow_id} が完了しました (ステータス: {result.get('status')})")
        except Exception as e:
            logger.error(f"ワークフロー {workflow_id} の実行中にエラーが発生: {e}")
    
    background_tasks.add_task(_run_workflow_task)
    
    # 即時のレスポンスを返す
    return WorkflowResponse(
        workflow_id=workflow_id,
        status="starting",
        start_time=datetime.now(UTC),
        results=None
    )


@router.get("/workflow/status/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow_status(
    workflow_id: str,
):
    """
    指定されたワークフローの状態を取得する
    """
    # TODO: ワークフロー状態の取得機能を実装
    # 現在はAPIの骨格のみ実装されている
    
    # ダミーレスポンス（実際にはデータベースからワークフロー情報を取得する）
    return WorkflowResponse(
        workflow_id=workflow_id,
        status="in_progress",
        start_time=datetime.now(UTC),
        results=None
    )


@router.get("/workflow/list", response_model=List[WorkflowResponse])
async def list_workflows(
    status: Optional[str] = Query(None, description="Filter by workflow status"),
    limit: int = Query(10, description="Maximum number of workflows to return"),
    offset: int = Query(0, description="Offset for pagination"),
):
    """
    ワークフローの一覧を取得する
    """
    # TODO: ワークフロー一覧取得機能を実装
    # 現在はAPIの骨格のみ実装されている
    
    # ダミーレスポンス（実際にはデータベースからワークフロー情報を取得する）
    return [
        WorkflowResponse(
            workflow_id=f"wf-dummy-{i}",
            status="in_progress",
            start_time=datetime.now(UTC),
            results=None
        )
        for i in range(3)
    ]


@router.post("/daemon/start", response_model=Dict[str, Any])
async def start_agent_daemon(
    background_tasks: BackgroundTasks,
    daemon: AgentDaemon = Depends(get_agent_daemon)
):
    """
    エージェントデーモンを起動する
    """
    if daemon is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent daemon could not be initialized"
        )
    
    # バックグラウンドでデーモンを起動
    background_tasks.add_task(daemon.start)
    
    return {
        "status": "starting",
        "message": "Agent daemon is starting in the background",
        "timestamp": datetime.now(UTC).isoformat()
    }


@router.post("/daemon/stop", response_model=Dict[str, Any])
async def stop_agent_daemon(
    background_tasks: BackgroundTasks,
    daemon: AgentDaemon = Depends(get_agent_daemon)
):
    """
    エージェントデーモンを停止する
    """
    if daemon is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent daemon is not running"
        )
    
    # バックグラウンドでデーモンを停止
    background_tasks.add_task(daemon.stop)
    
    return {
        "status": "stopping",
        "message": "Agent daemon is stopping in the background",
        "timestamp": datetime.now(UTC).isoformat()
    }


@router.get("/daemon/status", response_model=Dict[str, Any])
async def get_daemon_status(
    daemon: AgentDaemon = Depends(get_agent_daemon)
):
    """
    エージェントデーモンの状態を取得する
    """
    if daemon is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent daemon is not initialized"
        )
    
    # ワーカーの状態を取得
    workers_status = {}
    for agent_id, worker in daemon.workers.items():
        workers_status[agent_id] = {
            "is_alive": worker.is_alive(),
            "daemon": worker.daemon,
        }
    
    return {
        "status": "running" if any(status["is_alive"] for status in workers_status.values()) else "stopped",
        "workers": workers_status,
        "timestamp": datetime.now(UTC).isoformat()
    }


@router.get("/agents/{agent_id}/tasks/{task_id}", response_model=Dict[str, Any])
async def get_agent_task(agent_id: str, task_id: str) -> Dict[str, Any]:
    """エージェントのタスク情報を取得"""
    if agent_id == "A":
        return {
            "agent_id": agent_id,
            "task_id": task_id,
            "status": "processing",
            "processing_status": "completed",
            "result": "Processing task...",
            "last_updated": datetime.now(UTC).isoformat()
        }
    elif agent_id == "B":
        return {
            "agent_id": agent_id,
            "task_id": task_id,
            "status": "received",
            "processing_status": "pending",
            "result": "Task received",
            "last_updated": datetime.now(UTC).isoformat()
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )


# モデル定義
class AgentMessage(BaseModel):
    """エージェントメッセージ"""
    sender: str = Field(..., description="送信元エージェントID")
    receiver: str = Field(..., description="送信先エージェントID")
    message_type: MessageType = Field(..., description="メッセージタイプ")
    priority: MessagePriority = Field(default=MessagePriority.NORMAL, description="メッセージの優先度")
    content: Dict[str, Any] = Field(..., description="メッセージ内容")
    workflow_id: Optional[str] = Field(None, description="関連ワークフローID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sender": "agent_a",
                "receiver": "agent_b",
                "message_type": "task_request",
                "priority": "normal",
                "content": {
                    "task_id": "12345678-1234-5678-1234-567812345678",
                    "task_type": "document_review",
                    "parameters": {"document_id": "test_doc_001"}
                },
                "workflow_id": None
            }
        }
    )

class TaskAssignment(BaseModel):
    """タスク割り当て"""
    agent_id: str = Field(..., description="エージェントID")
    task_type: str = Field(..., description="タスクタイプ")
    task_data: Dict[str, Any] = Field(..., description="タスクデータ")
    workflow_id: Optional[str] = Field(None, description="関連ワークフローID")

# エンドポイント定義
@router.post("/messages")
async def send_message(
    message: AgentMessage,
    db: Session = Depends(get_db)
):
    """エージェント間メッセージを送信する"""
    try:
        message_id = str(uuid.uuid4())
        # メッセージをデータベースに保存
        # TODO: 実際のメッセージ保存処理を実装
        
        return {
            "message_id": message_id,
            "status": "sent",
            "timestamp": datetime.now(UTC)
        }
    except Exception as e:
        logger.error(f"メッセージ送信エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tasks/assign")
async def assign_task(
    task: TaskAssignment,
    db: Session = Depends(get_db)
):
    """エージェントにタスクを割り当てる"""
    try:
        if task.workflow_id:
            workflow = await get_workflow_status(task.workflow_id)
            if not workflow:
                raise HTTPException(status_code=404, detail="関連するワークフローが見つかりません")
                
            workflow["current_agent"] = task.agent_id
            workflow["task_data"] = task.task_data
            workflow["updated_at"] = datetime.now().isoformat()
            
            updated_workflow = await execute_workflow(workflow)
            return {"message": "タスクを割り当てました", "workflow": updated_workflow}
        else:
            # ワークフローに関連しないタスクの割り当て
            return {"message": "タスクを割り当てました"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"タスク割り当てエラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_agent_status(
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """エージェントのステータスを取得する"""
    try:
        if agent_id:
            # 特定のエージェントのステータスを取得
            return {
                "agent_id": agent_id,
                "status": "active",  # TODO: 実際のステータス管理を実装
                "current_task": None,
                "last_active": datetime.now().isoformat()
            }
        else:
            # 全エージェントのステータスを取得
            return {
                "agents": [
                    {
                        "agent_id": "agent_a",
                        "status": "active",
                        "current_task": None,
                        "last_active": datetime.now().isoformat()
                    },
                    {
                        "agent_id": "agent_b",
                        "status": "active",
                        "current_task": None,
                        "last_active": datetime.now().isoformat()
                    }
                ]
            }
    except Exception as e:
        logger.error(f"エージェントステータス取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/messages/{message_id}")
async def get_message_status(
    message_id: str,
    db: Session = Depends(get_db)
):
    """メッセージの状態を取得する"""
    try:
        # TODO: 実際のメッセージ取得処理を実装
        return {
            "message_id": message_id,
            "status": "delivered",
            "timestamp": datetime.now(UTC)
        }
    except Exception as e:
        logger.error(f"メッセージ状態取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# メッセージフローのResponseモデル
class MessageFlowNode(BaseModel):
    """メッセージフローノードモデル"""
    id: str
    label: str
    type: str

class MessageFlowLink(BaseModel):
    """メッセージフローリンクモデル"""
    source: str
    target: str
    value: int

class MessageFlowResponse(BaseModel):
    """メッセージフローレスポンス"""
    nodes: List[MessageFlowNode]
    links: List[MessageFlowLink]

@router.get("/message-flow", response_model=MessageFlowResponse)
async def get_message_flow(
    timespan: int = Query(24, description="時間範囲（時間単位）", ge=1, le=72),
    db: Session = Depends(get_db)
):
    """
    エージェント間のメッセージフローを取得
    
    指定された時間範囲内でのエージェント間のメッセージ交換の数と方向を返します。
    この情報はネットワークグラフの形式で表示するのに適しています。
    
    Args:
        timespan: 時間範囲（時間単位）
        
    Returns:
        ノードとリンクのリストを含むMessageFlowResponse
    """
    try:
        # 本来はデータベースからメッセージフローデータを取得する
        # この実装はモックデータを返す
        
        # エージェントリストを取得
        agent_service = get_agent_management_service_dependency()
        agent_list = await list_agents(agent_service)
        
        # ノードリストを作成
        nodes = []
        for agent in agent_list.agents:
            agent_type = "unknown"
            if agent.role:
                agent_type = agent.role.lower()
            elif len(agent.capabilities) > 0:
                agent_type = agent.capabilities[0].lower()
                
            nodes.append(
                MessageFlowNode(
                    id=agent.agent_id,
                    label=f"{agent.agent_id.replace('_', ' ').title()} エージェント",
                    type=agent_type
                )
            )
        
        # リンクリストをモック
        links = []
        coordinator_idx = None
        
        # コーディネーターエージェントを探す
        for i, node in enumerate(nodes):
            if "coordinator" in node.id or "調整" in node.label:
                coordinator_idx = i
                break
        
        # コーディネーターが見つからない場合は最初のエージェントをコーディネーターとして使用
        if coordinator_idx is None and len(nodes) > 0:
            coordinator_idx = 0
            
        # コーディネータと他のエージェント間のリンクを作成
        if coordinator_idx is not None and len(nodes) > 1:
            coordinator_id = nodes[coordinator_idx].id
            
            for node in nodes:
                if node.id != coordinator_id:
                    # コーディネーターからエージェントへのリンク
                    links.append(
                        MessageFlowLink(
                            source=coordinator_id,
                            target=node.id,
                            value=int(10 + 20 * hash(node.id) % 100 / 100)  # ランダムな値（10-30）
                        )
                    )
                    
                    # エージェントからコーディネーターへのリンク
                    links.append(
                        MessageFlowLink(
                            source=node.id,
                            target=coordinator_id,
                            value=int(5 + 20 * hash(node.id + "back") % 100 / 100)  # ランダムな値（5-25）
                        )
                    )
        
        return MessageFlowResponse(nodes=nodes, links=links)
        
    except Exception as e:
        logger.error(f"メッセージフロー取得エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"メッセージフローの取得中にエラーが発生しました: {str(e)}"
        ) 