"""
バッチ処理と一括操作用のルーター

複数のエージェントやタスクを一括で操作するAPI、
インポート/エクスポート機能、バッチ処理の進捗管理のためのエンドポイントを提供します。
"""

import os
import uuid
import json
import csv
import time
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from enum import Enum
from sqlalchemy.orm import Session

from src.models.repositories import (
    AgentStateRepository, 
    # TaskRepository, 
    WorkflowRepository,
    SampleDataRepository
)
from src.utils.db_manager import get_db_context
from src.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/batch",
    tags=["batch_operations"],
    responses={404: {"description": "Not found"}}
)

# モデル定義
class BatchJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class BatchOperationType(str, Enum):
    START = "start"
    STOP = "stop"
    RESET = "reset"
    EXPORT = "export"
    IMPORT = "import"
    DELETE = "delete"
    UPDATE = "update"

class AgentBatchOperation(BaseModel):
    """エージェント一括操作モデル"""
    operation: BatchOperationType
    agent_ids: List[str]
    parameters: Optional[Dict[str, Any]] = None

class TaskBatchOperation(BaseModel):
    """タスク一括操作モデル"""
    operation: BatchOperationType
    task_ids: List[str] 
    parameters: Optional[Dict[str, Any]] = None

class WorkflowBatchOperation(BaseModel):
    """ワークフロー一括操作モデル"""
    operation: BatchOperationType
    workflow_ids: List[str]
    parameters: Optional[Dict[str, Any]] = None

class BatchJobInfo(BaseModel):
    """バッチジョブ情報モデル"""
    job_id: str
    operation_type: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    total_items: int
    processed_items: int
    success_count: int
    error_count: int
    target_type: str  # "agent", "task", "workflow", "sample"
    parameters: Optional[Dict[str, Any]] = None
    result_summary: Optional[Dict[str, Any]] = None
    
# バッチジョブのインメモリ保存（実際の実装ではデータベースに保存）
batch_jobs: Dict[str, Dict[str, Any]] = {}

# 非同期バッチ処理ジョブを実行する関数
async def run_batch_job(
    job_id: str,
    operation_type: str,
    target_type: str,
    target_ids: List[str],
    parameters: Optional[Dict[str, Any]] = None
) -> None:
    """
    バックグラウンドでバッチジョブを実行する
    
    Args:
        job_id: ジョブID
        operation_type: 操作タイプ
        target_type: 対象タイプ（agent, task, workflow）
        target_ids: 対象ID一覧
        parameters: 操作パラメータ
    """
    try:
        batch_jobs[job_id]["status"] = BatchJobStatus.RUNNING
        batch_jobs[job_id]["updated_at"] = datetime.now()
        
        total_items = len(target_ids)
        success_count = 0
        error_count = 0
        errors = []
        results = []
        
        # 各アイテムを処理
        for index, item_id in enumerate(target_ids):
            try:
                # 対象タイプに応じた処理
                if target_type == "agent":
                    result = await process_agent_operation(item_id, operation_type, parameters)
                elif target_type == "task":
                    result = await process_task_operation(item_id, operation_type, parameters)
                elif target_type == "workflow":
                    result = await process_workflow_operation(item_id, operation_type, parameters)
                else:
                    raise ValueError(f"不明な対象タイプ: {target_type}")
                
                # 成功した場合
                success_count += 1
                results.append({"id": item_id, "status": "success", "result": result})
                
            except Exception as e:
                # エラーが発生した場合
                error_count += 1
                errors.append({"id": item_id, "error": str(e)})
                logger.error(f"バッチ処理エラー ({target_type} {item_id}): {e}")
            
            # 進捗を更新
            batch_jobs[job_id]["processed_items"] = index + 1
            batch_jobs[job_id]["success_count"] = success_count
            batch_jobs[job_id]["error_count"] = error_count
            batch_jobs[job_id]["updated_at"] = datetime.now()
            
            # キャンセルされた場合は処理を中断
            if batch_jobs[job_id]["status"] == BatchJobStatus.CANCELLED:
                logger.info(f"バッチジョブがキャンセルされました: {job_id}")
                break
                
            # 少し待機（サーバー負荷軽減）
            await asyncio.sleep(0.1)
        
        # 処理結果をまとめる
        batch_jobs[job_id]["status"] = BatchJobStatus.COMPLETED
        batch_jobs[job_id]["updated_at"] = datetime.now()
        batch_jobs[job_id]["result_summary"] = {
            "total": total_items,
            "success": success_count,
            "error": error_count,
            "results": results,
            "errors": errors
        }
        
    except Exception as e:
        # ジョブ全体の実行に失敗した場合
        logger.error(f"バッチジョブ実行エラー: {e}")
        batch_jobs[job_id]["status"] = BatchJobStatus.FAILED
        batch_jobs[job_id]["updated_at"] = datetime.now()
        batch_jobs[job_id]["result_summary"] = {
            "error": str(e)
        }

# 各エンティティタイプごとの処理関数
async def process_agent_operation(agent_id: str, operation: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
    """エージェントに対する操作を処理する"""
    with get_db_context() as db:
        repo = AgentStateRepository(db)
        agent = repo.get_by_id(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
        
        if operation == BatchOperationType.START:
            # エージェントを開始
            return {"started": True}
        elif operation == BatchOperationType.STOP:
            # エージェントを停止
            return {"stopped": True}
        elif operation == BatchOperationType.RESET:
            # エージェントをリセット
            return {"reset": True}
        elif operation == BatchOperationType.UPDATE:
            # エージェントを更新
            if parameters:
                return repo.update(agent_id, parameters)
            return {"updated": False, "reason": "No parameters provided"}
        elif operation == BatchOperationType.DELETE:
            # エージェントを削除
            return repo.delete(agent_id)
        else:
            raise ValueError(f"不明な操作タイプ: {operation}")

async def process_task_operation(task_id: str, operation: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
    """タスクに対する操作を処理する"""
    with get_db_context() as db:
        # TaskRepositoryが存在しないため、コメントアウト
        # repo = TaskRepository(db)
        # task = repo.get_by_id(task_id)
        
        # 代わりに、直接SQLを使用するか、別の方法でタスクを取得する必要があります
        # 一時的に例外を発生させる
        raise NotImplementedError("TaskRepository is not implemented")

async def process_workflow_operation(workflow_id: str, operation: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
    """ワークフローに対する操作を処理する"""
    with get_db_context() as db:
        repo = WorkflowRepository(db)
        workflow = repo.get_by_id(workflow_id)
        
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")
        
        if operation == BatchOperationType.START:
            # ワークフローを開始
            return {"started": True}
        elif operation == BatchOperationType.STOP:
            # ワークフローを停止
            return {"stopped": True}
        elif operation == BatchOperationType.RESET:
            # ワークフローをリセット
            return {"reset": True}
        elif operation == BatchOperationType.UPDATE:
            # ワークフローを更新
            if parameters:
                return repo.update(workflow_id, parameters)
            return {"updated": False, "reason": "No parameters provided"}
        elif operation == BatchOperationType.DELETE:
            # ワークフローを削除
            return repo.delete(workflow_id)
        elif operation == BatchOperationType.EXPORT:
            # ワークフローをエクスポート
            return await export_workflow(workflow_id, parameters)
        else:
            raise ValueError(f"不明な操作タイプ: {operation}")

async def export_workflow(workflow_id: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """ワークフローをエクスポートする"""
    with get_db_context() as db:
        repo = WorkflowRepository(db)
        workflow = repo.get_by_id(workflow_id)
        
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")
        
        # ワークフローの全データを取得
        workflow_data = {
            "id": workflow.id,
            "name": workflow.name if hasattr(workflow, "name") else f"Workflow {workflow.id}",
            "status": workflow.status,
            "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
            "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
            "parameters": workflow.parameters if hasattr(workflow, "parameters") else {},
            # その他必要なフィールド
        }
        
        # エクスポート形式に応じた処理
        export_format = parameters.get("format", "json") if parameters else "json"
        
        if export_format == "json":
            # JSONファイルに保存
            export_path = os.path.join(settings.TEMP_DIR, f"workflow_{workflow_id}.json")
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(workflow_data, f, ensure_ascii=False, indent=2)
                
            return {
                "exported": True,
                "format": "json",
                "path": export_path,
                "workflow_id": workflow_id
            }
            
        else:
            raise ValueError(f"サポートされていないエクスポート形式: {export_format}")

# エンドポイント: エージェント一括操作
@router.post("/agents")
async def batch_operate_agents(
    operation: AgentBatchOperation,
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    複数のエージェントに対して一括操作を実行する
    
    Args:
        operation: 一括操作の詳細
        background_tasks: バックグラウンドタスク
        
    Returns:
        Dict[str, Any]: ジョブ情報
    """
    logger.info(f"エージェント一括操作リクエスト: {operation.operation}, {len(operation.agent_ids)}件")
    
    try:
        # ジョブIDを生成
        job_id = f"job-{uuid.uuid4()}"
        
        # ジョブ情報を初期化
        batch_jobs[job_id] = {
            "job_id": job_id,
            "operation_type": operation.operation,
            "status": BatchJobStatus.PENDING,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "total_items": len(operation.agent_ids),
            "processed_items": 0,
            "success_count": 0,
            "error_count": 0,
            "target_type": "agent",
            "parameters": operation.parameters,
            "result_summary": None
        }
        
        # バックグラウンドでジョブを実行
        background_tasks.add_task(
            run_batch_job,
            job_id,
            operation.operation,
            "agent",
            operation.agent_ids,
            operation.parameters
        )
        
        logger.info(f"エージェント一括操作ジョブを開始しました: {job_id}")
        return {
            "job_id": job_id,
            "status": BatchJobStatus.PENDING,
            "message": f"{len(operation.agent_ids)}件のエージェントに対する{operation.operation}操作を開始しました",
            "total_items": len(operation.agent_ids)
        }
        
    except Exception as e:
        logger.error(f"エージェント一括操作の開始に失敗しました: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# エンドポイント: タスク一括操作
@router.post("/tasks")
async def batch_operate_tasks(
    operation: TaskBatchOperation,
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    タスクの一括操作を実行する
    
    Args:
        operation: 実行する操作
        background_tasks: バックグラウンドタスク
        
    Returns:
        Dict[str, Any]: 操作結果
    """
    logger.error("TaskRepository is not implemented")
    raise HTTPException(
        status_code=501, 
        detail="This endpoint is not implemented yet. TaskRepository is missing."
    )

# エンドポイント: ワークフロー一括操作
@router.post("/workflows")
async def batch_operate_workflows(
    operation: WorkflowBatchOperation,
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    複数のワークフローに対して一括操作を実行する
    
    Args:
        operation: 一括操作の詳細
        background_tasks: バックグラウンドタスク
        
    Returns:
        Dict[str, Any]: ジョブ情報
    """
    logger.info(f"ワークフロー一括操作リクエスト: {operation.operation}, {len(operation.workflow_ids)}件")
    
    try:
        # ジョブIDを生成
        job_id = f"job-{uuid.uuid4()}"
        
        # ジョブ情報を初期化
        batch_jobs[job_id] = {
            "job_id": job_id,
            "operation_type": operation.operation,
            "status": BatchJobStatus.PENDING,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "total_items": len(operation.workflow_ids),
            "processed_items": 0,
            "success_count": 0,
            "error_count": 0,
            "target_type": "workflow",
            "parameters": operation.parameters,
            "result_summary": None
        }
        
        # バックグラウンドでジョブを実行
        background_tasks.add_task(
            run_batch_job,
            job_id,
            operation.operation,
            "workflow",
            operation.workflow_ids,
            operation.parameters
        )
        
        logger.info(f"ワークフロー一括操作ジョブを開始しました: {job_id}")
        return {
            "job_id": job_id,
            "status": BatchJobStatus.PENDING,
            "message": f"{len(operation.workflow_ids)}件のワークフローに対する{operation.operation}操作を開始しました",
            "total_items": len(operation.workflow_ids)
        }
        
    except Exception as e:
        logger.error(f"ワークフロー一括操作の開始に失敗しました: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# エンドポイント: ジョブ状態取得
@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str
) -> Dict[str, Any]:
    """
    バッチジョブの状態を取得する
    
    Args:
        job_id: ジョブID
        
    Returns:
        Dict[str, Any]: ジョブ状態
    """
    logger.info(f"ジョブ状態取得リクエスト: {job_id}")
    
    if job_id not in batch_jobs:
        logger.warning(f"ジョブが見つかりません: {job_id}")
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_info = batch_jobs[job_id]
    
    return {
        "job_id": job_info["job_id"],
        "operation_type": job_info["operation_type"],
        "status": job_info["status"],
        "created_at": job_info["created_at"].isoformat(),
        "updated_at": job_info["updated_at"].isoformat(),
        "total_items": job_info["total_items"],
        "processed_items": job_info["processed_items"],
        "success_count": job_info["success_count"],
        "error_count": job_info["error_count"],
        "target_type": job_info["target_type"],
        "progress": (job_info["processed_items"] / job_info["total_items"]) * 100 if job_info["total_items"] > 0 else 0
    }

# エンドポイント: ジョブ結果取得
@router.get("/jobs/{job_id}/results")
async def get_job_results(
    job_id: str
) -> Dict[str, Any]:
    """
    バッチジョブの結果を取得する
    
    Args:
        job_id: ジョブID
        
    Returns:
        Dict[str, Any]: ジョブ結果
    """
    logger.info(f"ジョブ結果取得リクエスト: {job_id}")
    
    if job_id not in batch_jobs:
        logger.warning(f"ジョブが見つかりません: {job_id}")
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_info = batch_jobs[job_id]
    
    # 結果がまだない場合
    if job_info["status"] not in [BatchJobStatus.COMPLETED, BatchJobStatus.FAILED]:
        return {
            "job_id": job_info["job_id"],
            "status": job_info["status"],
            "message": "ジョブはまだ完了していません",
            "progress": (job_info["processed_items"] / job_info["total_items"]) * 100 if job_info["total_items"] > 0 else 0
        }
    
    return {
        "job_id": job_info["job_id"],
        "operation_type": job_info["operation_type"],
        "status": job_info["status"],
        "created_at": job_info["created_at"].isoformat(),
        "updated_at": job_info["updated_at"].isoformat(),
        "total_items": job_info["total_items"],
        "processed_items": job_info["processed_items"],
        "success_count": job_info["success_count"],
        "error_count": job_info["error_count"],
        "target_type": job_info["target_type"],
        "result_summary": job_info["result_summary"]
    }

# エンドポイント: ジョブキャンセル
@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str
) -> Dict[str, Any]:
    """
    実行中のジョブをキャンセルする
    
    Args:
        job_id: ジョブID
        
    Returns:
        Dict[str, Any]: キャンセル結果
    """
    logger.info(f"ジョブキャンセルリクエスト: {job_id}")
    
    if job_id not in batch_jobs:
        logger.warning(f"ジョブが見つかりません: {job_id}")
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_info = batch_jobs[job_id]
    
    # 既に完了済みの場合
    if job_info["status"] in [BatchJobStatus.COMPLETED, BatchJobStatus.FAILED, BatchJobStatus.CANCELLED]:
        return {
            "job_id": job_id,
            "status": job_info["status"],
            "message": f"ジョブは既に {job_info['status']} 状態です"
        }
    
    # キャンセル
    job_info["status"] = BatchJobStatus.CANCELLED
    job_info["updated_at"] = datetime.now()
    
    logger.info(f"ジョブをキャンセルしました: {job_id}")
    return {
        "job_id": job_id,
        "status": BatchJobStatus.CANCELLED,
        "message": "ジョブをキャンセルしました"
    }

# エンドポイント: 一括インポート
@router.post("/import/{entity_type}")
async def import_entities(
    entity_type: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    エンティティを一括インポートする
    
    Args:
        entity_type: エンティティタイプ（workflows, tasks, agents, samplesなど）
        file: インポートするファイル（JSON, CSV）
        background_tasks: バックグラウンドタスク
        
    Returns:
        Dict[str, Any]: インポート結果
    """
    logger.info(f"一括インポートリクエスト: {entity_type}, ファイル: {file.filename}")
    
    try:
        # ファイルをテンポラリディレクトリに保存
        import_file_path = os.path.join(settings.TEMP_DIR, f"import_{uuid.uuid4()}_{file.filename}")
        os.makedirs(os.path.dirname(import_file_path), exist_ok=True)
        
        content = await file.read()
        with open(import_file_path, "wb") as f:
            f.write(content)
        
        # ファイル形式を判断
        if file.filename.endswith(".json"):
            # JSONファイル
            with open(import_file_path, "r", encoding="utf-8") as f:
                import_data = json.load(f)
        elif file.filename.endswith(".csv"):
            # CSVファイル
            with open(import_file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                import_data = list(reader)
        else:
            raise HTTPException(status_code=400, detail=f"サポートされていないファイル形式: {file.filename}")
        
        # ジョブIDを生成
        job_id = f"job-{uuid.uuid4()}"
        
        # 単一オブジェクトの場合はリストに変換
        if isinstance(import_data, dict):
            import_data = [import_data]
        
        # ジョブ情報を初期化
        batch_jobs[job_id] = {
            "job_id": job_id,
            "operation_type": BatchOperationType.IMPORT,
            "status": BatchJobStatus.PENDING,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "total_items": len(import_data),
            "processed_items": 0,
            "success_count": 0,
            "error_count": 0,
            "target_type": entity_type,
            "parameters": {"file_path": import_file_path},
            "result_summary": None
        }
        
        # バックグラウンドでインポート処理を実行
        background_tasks.add_task(
            process_import,
            job_id,
            entity_type,
            import_data
        )
        
        logger.info(f"一括インポートジョブを開始しました: {job_id}")
        return {
            "job_id": job_id,
            "status": BatchJobStatus.PENDING,
            "message": f"{len(import_data)}件の{entity_type}のインポートを開始しました",
            "total_items": len(import_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"一括インポートの開始に失敗しました: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_import(
    job_id: str,
    entity_type: str,
    import_data: List[Dict[str, Any]]
) -> None:
    """インポートジョブを処理する"""
    try:
        # ジョブ状態を更新
        update_job_status(job_id, BatchJobStatus.RUNNING)
        
        # 成功・失敗のカウンター
        success_count = 0
        error_count = 0
        error_details = []
        
        # エンティティタイプに基づいてリポジトリを選択
        with get_db_context() as db:
            if entity_type == "workflows":
                repo = WorkflowRepository(db)
            elif entity_type == "tasks":
                # repo = TaskRepository(db)
                raise NotImplementedError("TaskRepository is not implemented")
            elif entity_type == "agents":
                repo = AgentStateRepository(db)
            elif entity_type == "samples":
                repo = SampleDataRepository(db)
            else:
                update_job_status(
                    job_id, 
                    BatchJobStatus.FAILED, 
                    {
                        "error": f"Unknown entity type: {entity_type}",
                        "success_count": 0,
                        "error_count": 1
                    }
                )
                return
            
            # 各アイテムをインポート
            for index, item_data in enumerate(import_data):
                try:
                    # IDを持つ場合は更新、持たない場合は新規作成
                    if "id" in item_data and item_data["id"]:
                        entity_id = item_data["id"]
                        entity = repo.get_by_id(entity_id)
                        
                        if entity:
                            # 更新
                            result = repo.update(entity_id, item_data)
                            operation = "update"
                        else:
                            # 新規作成（指定IDで）
                            result = repo.create(item_data)
                            operation = "create"
                    else:
                        # 新規作成（自動ID）
                        result = repo.create(item_data)
                        operation = "create"
                    
                    # 成功
                    success_count += 1
                    results.append({
                        "index": index,
                        "operation": operation,
                        "id": getattr(result, "id", None) or (result.get("id") if isinstance(result, dict) else None),
                        "status": "success"
                    })
                    
                except Exception as e:
                    # エラー
                    error_count += 1
                    errors.append({
                        "index": index,
                        "data": item_data,
                        "error": str(e)
                    })
                    logger.error(f"インポートエラー (アイテム {index}): {e}")
                
                # 進捗を更新
                batch_jobs[job_id]["processed_items"] = index + 1
                batch_jobs[job_id]["success_count"] = success_count
                batch_jobs[job_id]["error_count"] = error_count
                batch_jobs[job_id]["updated_at"] = datetime.now()
                
                # キャンセルされた場合は処理を中断
                if batch_jobs[job_id]["status"] == BatchJobStatus.CANCELLED:
                    logger.info(f"インポートジョブがキャンセルされました: {job_id}")
                    break
                
                # 少し待機（サーバー負荷軽減）
                await asyncio.sleep(0.1)
        
        # 処理結果をまとめる
        batch_jobs[job_id]["status"] = BatchJobStatus.COMPLETED
        batch_jobs[job_id]["updated_at"] = datetime.now()
        batch_jobs[job_id]["result_summary"] = {
            "total": total_items,
            "success": success_count,
            "error": error_count,
            "results": results,
            "errors": errors
        }
        
    except Exception as e:
        # ジョブ全体の実行に失敗した場合
        logger.error(f"インポートジョブ実行エラー: {e}")
        batch_jobs[job_id]["status"] = BatchJobStatus.FAILED
        batch_jobs[job_id]["updated_at"] = datetime.now()
        batch_jobs[job_id]["result_summary"] = {
            "error": str(e)
        }

# エンドポイント: 一括エクスポート
@router.post("/export/{entity_type}")
async def export_entities(
    entity_type: str,
    criteria: Dict[str, Any] = Body(...),
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    エンティティを一括エクスポートする
    
    Args:
        entity_type: エンティティタイプ（workflows, tasks, agents, samplesなど）
        criteria: エクスポート条件
        background_tasks: バックグラウンドタスク
        
    Returns:
        Dict[str, Any]: エクスポート結果
    """
    logger.info(f"一括エクスポートリクエスト: {entity_type}")
    
    try:
        # ジョブIDを生成
        job_id = f"job-{uuid.uuid4()}"
        
        # ジョブ情報を初期化
        batch_jobs[job_id] = {
            "job_id": job_id,
            "operation_type": BatchOperationType.EXPORT,
            "status": BatchJobStatus.PENDING,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "total_items": 0,  # 初期値、実際の数は後で更新
            "processed_items": 0,
            "success_count": 0,
            "error_count": 0,
            "target_type": entity_type,
            "parameters": criteria,
            "result_summary": None
        }
        
        # バックグラウンドでエクスポート処理を実行
        background_tasks.add_task(
            process_export,
            job_id,
            entity_type,
            criteria
        )
        
        logger.info(f"一括エクスポートジョブを開始しました: {job_id}")
        return {
            "job_id": job_id,
            "status": BatchJobStatus.PENDING,
            "message": f"{entity_type}のエクスポートを開始しました"
        }
        
    except Exception as e:
        logger.error(f"一括エクスポートの開始に失敗しました: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_export(
    job_id: str,
    entity_type: str,
    criteria: Dict[str, Any]
) -> None:
    """エクスポートジョブを処理する"""
    try:
        # ジョブ状態を更新
        update_job_status(job_id, BatchJobStatus.RUNNING)
        
        # エンティティタイプに基づいてリポジトリを選択
        with get_db_context() as db:
            if entity_type == "workflows":
                repo = WorkflowRepository(db)
            elif entity_type == "tasks":
                # repo = TaskRepository(db)
                raise NotImplementedError("TaskRepository is not implemented")
            elif entity_type == "agents":
                repo = AgentStateRepository(db)
            elif entity_type == "samples":
                repo = SampleDataRepository(db)
            else:
                update_job_status(
                    job_id, 
                    BatchJobStatus.FAILED, 
                    {
                        "error": f"Unknown entity type: {entity_type}",
                        "items_count": 0
                    }
                )
                return
            
            # 条件に一致するアイテムを取得
            # ここでは簡易的な実装として、すべてのアイテムを取得
            items, total = repo.get_all(
                page=1,
                per_page=10000,  # 十分大きな値
                **criteria
            )
            
            # アイテム数を更新
            batch_jobs[job_id]["total_items"] = total
            
            # エクスポートするデータを準備
            export_data = []
            success_count = 0
            error_count = 0
            
            for index, item in enumerate(items):
                try:
                    # SQLAlchemyモデルをディクショナリに変換
                    if hasattr(item, "__dict__"):
                        item_dict = {
                            key: value for key, value in item.__dict__.items()
                            if not key.startswith("_")
                        }
                    else:
                        # 既にディクショナリの場合はそのまま
                        item_dict = item
                    
                    # 日時値をISOフォーマットに変換
                    for key, value in item_dict.items():
                        if isinstance(value, datetime):
                            item_dict[key] = value.isoformat()
                    
                    export_data.append(item_dict)
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"エクスポートデータ変換エラー (アイテム {index}): {e}")
                    error_count += 1
                
                # 進捗を更新
                batch_jobs[job_id]["processed_items"] = index + 1
                batch_jobs[job_id]["success_count"] = success_count
                batch_jobs[job_id]["error_count"] = error_count
                batch_jobs[job_id]["updated_at"] = datetime.now()
                
                # キャンセルされた場合は処理を中断
                if batch_jobs[job_id]["status"] == BatchJobStatus.CANCELLED:
                    logger.info(f"エクスポートジョブがキャンセルされました: {job_id}")
                    break
            
            # エクスポート形式に応じた処理
            export_format = criteria.get("format", "json")
            export_file_name = f"{entity_type}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if export_format == "json":
                # JSONファイルに保存
                export_path = os.path.join(settings.TEMP_DIR, f"{export_file_name}.json")
                os.makedirs(os.path.dirname(export_path), exist_ok=True)
                
                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                    
            elif export_format == "csv":
                # CSVファイルに保存
                export_path = os.path.join(settings.TEMP_DIR, f"{export_file_name}.csv")
                os.makedirs(os.path.dirname(export_path), exist_ok=True)
                
                if export_data:
                    # すべてのアイテムのフィールドを取得
                    fieldnames = set()
                    for item in export_data:
                        fieldnames.update(item.keys())
                    
                    with open(export_path, "w", encoding="utf-8", newline="") as f:
                        writer = csv.DictWriter(f, fieldnames=sorted(fieldnames))
                        writer.writeheader()
                        for item in export_data:
                            writer.writerow(item)
                else:
                    # 空のCSVファイル
                    with open(export_path, "w", encoding="utf-8") as f:
                        f.write("")
            else:
                raise ValueError(f"サポートされていないエクスポート形式: {export_format}")
            
            # 処理結果をまとめる
            batch_jobs[job_id]["status"] = BatchJobStatus.COMPLETED
            batch_jobs[job_id]["updated_at"] = datetime.now()
            batch_jobs[job_id]["result_summary"] = {
                "total": total,
                "success": success_count,
                "error": error_count,
                "format": export_format,
                "file_path": export_path,
                "file_name": os.path.basename(export_path)
            }
        
    except Exception as e:
        # ジョブ全体の実行に失敗した場合
        logger.error(f"エクスポートジョブ実行エラー: {e}")
        batch_jobs[job_id]["status"] = BatchJobStatus.FAILED
        batch_jobs[job_id]["updated_at"] = datetime.now()
        batch_jobs[job_id]["result_summary"] = {
            "error": str(e)
        }

# エンドポイント: エクスポートファイルのダウンロード
@router.get("/exports/{job_id}/download")
async def download_export_file(
    job_id: str
) -> FileResponse:
    """
    エクスポートされたファイルをダウンロードする
    
    Args:
        job_id: ジョブID
        
    Returns:
        FileResponse: エクスポートファイル
    """
    logger.info(f"エクスポートファイルダウンロードリクエスト: {job_id}")
    
    if job_id not in batch_jobs:
        logger.warning(f"ジョブが見つかりません: {job_id}")
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_info = batch_jobs[job_id]
    
    # エクスポートジョブでない場合
    if job_info["operation_type"] != BatchOperationType.EXPORT:
        logger.warning(f"エクスポートジョブではありません: {job_id}")
        raise HTTPException(status_code=400, detail="Not an export job")
    
    # ジョブが完了していない場合
    if job_info["status"] != BatchJobStatus.COMPLETED:
        logger.warning(f"ジョブはまだ完了していません: {job_id}")
        raise HTTPException(status_code=400, detail="Job not completed")
    
    # ファイルパスが見つからない場合
    if not job_info["result_summary"] or "file_path" not in job_info["result_summary"]:
        logger.warning(f"エクスポートファイルが見つかりません: {job_id}")
        raise HTTPException(status_code=404, detail="Export file not found")
    
    file_path = job_info["result_summary"]["file_path"]
    file_name = job_info["result_summary"]["file_name"]
    
    # ファイルが存在しない場合
    if not os.path.exists(file_path):
        logger.warning(f"エクスポートファイルが物理的に存在しません: {file_path}")
        raise HTTPException(status_code=404, detail="Export file not found on disk")
    
    # ファイルのMIMEタイプを判断
    if file_path.endswith(".json"):
        media_type = "application/json"
    elif file_path.endswith(".csv"):
        media_type = "text/csv"
    else:
        media_type = "application/octet-stream"
    
    logger.info(f"エクスポートファイルをダウンロードします: {file_path}")
    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type=media_type
    ) 