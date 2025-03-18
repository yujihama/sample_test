"""
監査証跡APIエンドポイント

このモジュールでは、監査証跡とログ関連のAPIエンドポイントを提供します。
以下の機能を含みます：
- 監査証跡の取得
- グラフ状態履歴の取得
- チェックポイント記録の取得
- 状態遷移の可視化データの取得
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
import json
from datetime import datetime, timedelta

from loguru import logger
from src.models.repositories import (
    AuditTrailRepository, 
    GraphStateHistoryRepository, 
    CheckpointRecordRepository
)
from src.utils.audit_trail_utils import export_audit_trail_to_json
from src.services.graph_executor import GraphExecutor, get_graph_executor
from src.db.session import get_db_session


# モデル定義
class AuditTrailResponse(BaseModel):
    """監査証跡レスポンス"""
    id: str
    workflow_id: str
    context_id: Optional[str]
    agent_id: Optional[str]
    event_type: str
    event_data: Dict[str, Any]
    timestamp: datetime
    metadata: Optional[Dict[str, Any]]


class GraphStateHistoryResponse(BaseModel):
    """グラフ状態履歴レスポンス"""
    id: str
    workflow_id: str
    context_id: Optional[str]
    agent_id: Optional[str]
    node_id: Optional[str]
    state_snapshot: Optional[Dict[str, Any]]
    state_diff: Optional[Dict[str, Any]]
    event_type: str
    event_data: Optional[Dict[str, Any]]
    timestamp: datetime
    checkpoint_id: Optional[str]


class CheckpointRecordResponse(BaseModel):
    """チェックポイント記録レスポンス"""
    id: str
    workflow_id: str
    context_id: Optional[str]
    agent_id: Optional[str]
    checkpoint_type: str
    node_id: Optional[str]
    state_reference: Optional[str]
    checkpoint_metadata: Optional[Dict[str, Any]]
    created_at: datetime
    restored_at: Optional[datetime]
    restore_count: int


class StateTransitionVisualization(BaseModel):
    """状態遷移可視化データ"""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    metadata: Dict[str, Any]


# ルーター定義
router = APIRouter(prefix="/audit", tags=["audit"])


# エンドポイント
@router.get("/trails", response_model=List[AuditTrailResponse])
async def get_audit_trails(
    workflow_id: Optional[str] = Query(None, description="ワークフローID"),
    context_id: Optional[str] = Query(None, description="コンテキストID"),
    agent_id: Optional[str] = Query(None, description="エージェントID"),
    event_type: Optional[str] = Query(None, description="イベントタイプ"),
    start_time: Optional[datetime] = Query(None, description="検索開始時間"),
    end_time: Optional[datetime] = Query(None, description="検索終了時間"),
    limit: int = Query(100, description="結果の最大数"),
    skip: int = Query(0, description="スキップする結果の数"),
    db_session = Depends(get_db_session)
):
    """
    監査証跡のリストを取得する
    
    クエリパラメータでフィルタリングして監査証跡を取得します。
    """
    try:
        repo = AuditTrailRepository(db_session)
        results = repo.search(
            workflow_id=workflow_id,
            context_id=context_id,
            agent_id=agent_id,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=skip
        )
        return results
    except Exception as e:
        logger.error(f"監査証跡の取得に失敗しました: {str(e)}")
        raise HTTPException(status_code=500, detail=f"監査証跡の取得に失敗しました: {str(e)}")


@router.get("/trails/export", response_model=Dict[str, Any])
async def export_audit_trails(
    workflow_id: str = Query(..., description="ワークフローID"),
    format: str = Query("json", description="エクスポート形式 (json)"),
    db_session = Depends(get_db_session)
):
    """
    監査証跡をエクスポートする
    
    指定されたワークフローの全監査証跡をエクスポートします。
    """
    try:
        if format.lower() != "json":
            raise HTTPException(status_code=400, detail="現在サポートされているフォーマットはJSONのみです")
        
        export_data = export_audit_trail_to_json(workflow_id, db_session)
        return export_data
    except Exception as e:
        logger.error(f"監査証跡のエクスポートに失敗しました: {str(e)}")
        raise HTTPException(status_code=500, detail=f"監査証跡のエクスポートに失敗しました: {str(e)}")


@router.get("/state-history", response_model=List[GraphStateHistoryResponse])
async def get_graph_state_history(
    workflow_id: Optional[str] = Query(None, description="ワークフローID"),
    context_id: Optional[str] = Query(None, description="コンテキストID"),
    agent_id: Optional[str] = Query(None, description="エージェントID"),
    node_id: Optional[str] = Query(None, description="ノードID"),
    event_type: Optional[str] = Query(None, description="イベントタイプ"),
    checkpoint_id: Optional[str] = Query(None, description="チェックポイントID"),
    start_time: Optional[datetime] = Query(None, description="検索開始時間"),
    end_time: Optional[datetime] = Query(None, description="検索終了時間"),
    limit: int = Query(100, description="結果の最大数"),
    skip: int = Query(0, description="スキップする結果の数"),
    db_session = Depends(get_db_session)
):
    """
    グラフ状態履歴を取得する
    
    クエリパラメータでフィルタリングしてグラフ状態履歴を取得します。
    """
    try:
        repo = GraphStateHistoryRepository(db_session)
        results = repo.search(
            workflow_id=workflow_id,
            context_id=context_id,
            agent_id=agent_id,
            node_id=node_id,
            event_type=event_type,
            checkpoint_id=checkpoint_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=skip
        )
        return results
    except Exception as e:
        logger.error(f"グラフ状態履歴の取得に失敗しました: {str(e)}")
        raise HTTPException(status_code=500, detail=f"グラフ状態履歴の取得に失敗しました: {str(e)}")


@router.get("/checkpoints", response_model=List[CheckpointRecordResponse])
async def get_checkpoint_records(
    workflow_id: Optional[str] = Query(None, description="ワークフローID"),
    context_id: Optional[str] = Query(None, description="コンテキストID"),
    agent_id: Optional[str] = Query(None, description="エージェントID"),
    checkpoint_type: Optional[str] = Query(None, description="チェックポイントタイプ"),
    is_restored: Optional[bool] = Query(None, description="復元済みフラグ"),
    start_time: Optional[datetime] = Query(None, description="検索開始時間"),
    end_time: Optional[datetime] = Query(None, description="検索終了時間"),
    limit: int = Query(100, description="結果の最大数"),
    skip: int = Query(0, description="スキップする結果の数"),
    db_session = Depends(get_db_session)
):
    """
    チェックポイント記録のリストを取得する
    
    クエリパラメータでフィルタリングしてチェックポイント記録を取得します。
    """
    try:
        repo = CheckpointRecordRepository(db_session)
        results = repo.search(
            workflow_id=workflow_id,
            context_id=context_id,
            agent_id=agent_id,
            checkpoint_type=checkpoint_type,
            is_restored=is_restored,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=skip
        )
        return results
    except Exception as e:
        logger.error(f"チェックポイント記録の取得に失敗しました: {str(e)}")
        raise HTTPException(status_code=500, detail=f"チェックポイント記録の取得に失敗しました: {str(e)}")


@router.get("/visualize/state-transitions", response_model=StateTransitionVisualization)
async def visualize_state_transitions(
    workflow_id: str = Query(..., description="ワークフローID"),
    start_time: Optional[datetime] = Query(None, description="検索開始時間"),
    end_time: Optional[datetime] = Query(None, description="検索終了時間"),
    include_state_data: bool = Query(False, description="状態データを含めるかどうか"),
    executor: GraphExecutor = Depends(get_graph_executor),
    db_session = Depends(get_db_session)
):
    """
    状態遷移の可視化データを取得する
    
    グラフの状態遷移を可視化するためのノードとエッジデータを取得します。
    """
    try:
        # GraphStateHistory から状態遷移データを取得
        state_history_repo = GraphStateHistoryRepository(db_session)
        checkpoint_repo = CheckpointRecordRepository(db_session)
        
        # 履歴データを時系列順に取得
        history_records = state_history_repo.search(
            workflow_id=workflow_id,
            start_time=start_time,
            end_time=end_time,
            limit=1000,  # 可視化用に多めに取得
            order_by="timestamp"
        )
        
        # チェックポイントデータを取得
        checkpoint_records = checkpoint_repo.search(
            workflow_id=workflow_id,
            start_time=start_time,
            end_time=end_time,
            limit=1000
        )
        
        # ノードとエッジの作成
        nodes = []
        edges = []
        node_map = {}
        
        # 状態履歴からノードを作成
        for record in history_records:
            node_id = f"{record.id}"
            label = f"{record.event_type}: {record.node_id or 'unknown'}"
            
            # ノード情報を構築
            node_data = {
                "id": node_id,
                "label": label,
                "event_type": record.event_type,
                "node_id": record.node_id,
                "timestamp": record.timestamp.isoformat(),
                "agent_id": record.agent_id
            }
            
            # オプションで状態データを含める
            if include_state_data:
                node_data["state_snapshot"] = record.state_snapshot
                node_data["state_diff"] = record.state_diff
            
            nodes.append(node_data)
            node_map[record.id] = node_id
            
            # 前のノードがあればエッジを作成
            if len(nodes) > 1:
                prev_node_id = nodes[-2]["id"]
                edges.append({
                    "id": f"e{len(edges)}",
                    "source": prev_node_id,
                    "target": node_id
                })
        
        # チェックポイントからノードを作成
        for record in checkpoint_records:
            node_id = f"cp_{record.id}"
            label = f"Checkpoint: {record.checkpoint_type}"
            
            # ノード情報を構築
            node_data = {
                "id": node_id,
                "label": label,
                "checkpoint_type": record.checkpoint_type,
                "created_at": record.created_at.isoformat(),
                "restored_at": record.restored_at.isoformat() if record.restored_at else None,
                "restore_count": record.restore_count,
                "agent_id": record.agent_id,
                "type": "checkpoint"
            }
            
            nodes.append(node_data)
            
            # 対応する状態履歴ノードがあればエッジを作成
            if record.state_reference and record.state_reference in node_map:
                edges.append({
                    "id": f"e{len(edges)}",
                    "source": node_map[record.state_reference],
                    "target": node_id,
                    "type": "checkpoint_reference"
                })
        
        # 可視化データを作成
        visualization_data = {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "workflow_id": workflow_id,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "time_range": {
                    "start": start_time.isoformat() if start_time else None,
                    "end": end_time.isoformat() if end_time else None
                }
            }
        }
        
        return visualization_data
    
    except Exception as e:
        logger.error(f"状態遷移の可視化データの取得に失敗しました: {str(e)}")
        raise HTTPException(status_code=500, detail=f"状態遷移の可視化データの取得に失敗しました: {str(e)}") 