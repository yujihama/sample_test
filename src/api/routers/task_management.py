"""
タスク管理APIエンドポイント

このモジュールは、タスクの作成、割り当て、監視などのための
RESTful APIエンドポイントを提供します。
"""

import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, status
from pydantic import BaseModel, Field, UUID4
from sqlalchemy.orm import Session

from src.api.dependencies import get_agent_manager, get_agent_management_service_dependency
from src.api.dependencies import get_current_user
from src.core.agent_management_service import AgentManagementService
from src.models.schema import TaskStatus
from src.utils.db_manager import get_db
import logging


# ロガーの設定
logger = logging.getLogger(__name__)

# ルーターの設定
router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={404: {"description": "Not found"}},
)


# リクエスト/レスポンスモデル
class TaskRequest(BaseModel):
    """タスク作成リクエスト"""
    agent_id: str
    task_type: str
    task_data: Dict[str, Any]
    workflow_id: Optional[str] = None
    context_id: Optional[str] = None
    priority: Optional[int] = 1


class TaskResponse(BaseModel):
    """タスクレスポンス"""
    task_id: str
    agent_id: str
    status: str
    task_type: str
    task_data: Dict[str, Any]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskListResponse(BaseModel):
    """タスク一覧レスポンス"""
    tasks: List[TaskResponse]
    count: int


class TaskSubmissionRequest(BaseModel):
    """タスク送信リクエスト"""
    task_id: str
    difficulty: int
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskSubmissionResponse(BaseModel):
    """タスク送信レスポンス"""
    task_id: str
    status: str = "received"
    timestamp: datetime = Field(default_factory=datetime.now)


@router.post("/submit", response_model=TaskSubmissionResponse)
async def submit_task(
    task: TaskSubmissionRequest,
    agent_service: AgentManagementService = Depends(get_agent_management_service_dependency)
):
    """
    タスクを送信する
    """
    # タスクの検証と処理
    logger.info(f"タスク送信: {task.task_id} - {task.description}")
    
    # 受け付けたことを応答
    return TaskSubmissionResponse(
        task_id=task.task_id
    )


@router.post("/assign", response_model=TaskResponse)
async def assign_task(
    task: TaskRequest,
    agent_service: AgentManagementService = Depends(get_agent_management_service_dependency)
):
    """
    タスクをエージェントに割り当てる
    """
    # タスクIDを生成
    task_id = f"task-{uuid.uuid4().hex[:8]}"
    
    # 新しいAgentManagementServiceを使用してタスクを割り当て
    success = agent_service.assign_task(
        task_id=task_id,
        agent_id=task.agent_id,
        task_data=task.task_data,
        task_type=task.task_type,
        workflow_id=task.workflow_id,
        context_id=task.context_id,
        priority=task.priority
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to assign task to agent {task.agent_id}"
        )
    
    # タスク情報を取得
    agent_tasks = agent_service.get_agent_tasks(task.agent_id)
    assigned_task = next((t for t in agent_tasks if t.get("id") == task_id), None)
    
    if not assigned_task:
        # タスクは割り当てられたがまだ取得できない場合
        return TaskResponse(
            task_id=task_id,
            agent_id=task.agent_id,
            status="assigned",
            task_type=task.task_type,
            task_data=task.task_data,
            created_at=datetime.now(),
            metadata={
                "workflow_id": task.workflow_id,
                "context_id": task.context_id,
                "priority": task.priority
            }
        )
    
    # タスク情報を返す
    return TaskResponse(
        task_id=task_id,
        agent_id=task.agent_id,
        status=assigned_task.get("status", "assigned"),
        task_type=task.task_type,
        task_data=assigned_task.get("data", task.task_data),
        created_at=datetime.now(),
        metadata={
            "workflow_id": task.workflow_id,
            "context_id": task.context_id,
            "priority": task.priority
        }
    )


@router.get("/status/{task_id}", response_model=TaskResponse)
async def get_task_status(
    task_id: str,
    agent_service: AgentManagementService = Depends(get_agent_management_service_dependency)
):
    """
    タスクの状態を取得する
    """
    # すべてのエージェントを取得
    agents = agent_service.get_all_agents()
    
    # 各エージェントのタスクをチェック
    for agent in agents:
        agent_id = agent["id"]
        agent_tasks = agent_service.get_agent_tasks(agent_id)
        
        # 指定されたタスクIDを持つタスクを探す
        task = next((t for t in agent_tasks if t.get("id") == task_id), None)
        if task:
            return TaskResponse(
                task_id=task_id,
                agent_id=agent_id,
                status=task.get("status", "unknown"),
                task_type=task.get("task_type", "generic"),
                task_data=task.get("data", {}),
                created_at=task.get("created_at"),
                updated_at=task.get("updated_at"),
                metadata=task.get("metadata", {})
            )
    
    # タスクが見つからない場合
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task with ID {task_id} not found"
    )


@router.get("/list", response_model=TaskListResponse)
async def list_tasks(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    status: Optional[str] = Query(None, description="Filter by task status"),
    agent_service: AgentManagementService = Depends(get_agent_management_service_dependency)
):
    """
    タスクの一覧を取得する
    """
    tasks = []
    
    # 特定のエージェントのタスクのみを取得する場合
    if agent_id:
        agent_tasks = agent_service.get_agent_tasks(agent_id)
        # ステータスでフィルタリング
        if status:
            agent_tasks = [t for t in agent_tasks if t.get("status") == status]
        
        for task in agent_tasks:
            tasks.append(
                TaskResponse(
                    task_id=task.get("id", "unknown"),
                    agent_id=agent_id,
                    status=task.get("status", "unknown"),
                    task_type=task.get("task_type", "generic"),
                    task_data=task.get("data", {}),
                    created_at=task.get("created_at"),
                    updated_at=task.get("updated_at"),
                    metadata=task.get("metadata", {})
                )
            )
    else:
        # すべてのエージェントのタスクを取得
        agents = agent_service.get_all_agents()
        for agent in agents:
            agent_id = agent["id"]
            agent_tasks = agent_service.get_agent_tasks(agent_id)
            
            # ステータスでフィルタリング
            if status:
                agent_tasks = [t for t in agent_tasks if t.get("status") == status]
            
            for task in agent_tasks:
                tasks.append(
                    TaskResponse(
                        task_id=task.get("id", "unknown"),
                        agent_id=agent_id,
                        status=task.get("status", "unknown"),
                        task_type=task.get("task_type", "generic"),
                        task_data=task.get("data", {}),
                        created_at=task.get("created_at"),
                        updated_at=task.get("updated_at"),
                        metadata=task.get("metadata", {})
                    )
                )
    
    return TaskListResponse(
        tasks=tasks,
        count=len(tasks)
    )
 