"""
監査証跡ユーティリティ

このモジュールは監査証跡の記録、検索、エクスポート機能を提供します。
エージェント間の通信や意思決定の追跡を可能にし、監査プロセスの透明性を確保します。
"""

import json
from src.utils import json_utils
import csv
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from loguru import logger
from pathlib import Path

from src.models.db_models import AuditTrail, MessageLog, AgentDecision, GraphStateHistory, CheckpointRecord
from src.models.repositories import (
    audit_trail_repository, message_log_repository, agent_decision_repository,
    AuditTrailRepository, MessageLogRepository, AgentDecisionRepository,
    GraphStateHistoryRepository, CheckpointRecordRepository
)
from src.models.schema import AgentMessage, MessagePriority
from src.core.config import settings

# ロガーの設定
logger = logging.getLogger(__name__)

# JSONエンコーダーを追加
class CustomJSONEncoder(json.JSONEncoder):
    """カスタムJSONエンコーダー - 日付型などの特殊な型を処理"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.visited_objects = set()
        
    def default(self, obj):
        # 循環参照の検出と処理
        obj_id = id(obj)
        if obj_id in self.visited_objects:
            return f"<circular reference to {type(obj).__name__}>"
        
        self.visited_objects.add(obj_id)
        
        try:
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
                return obj.to_dict()
            elif hasattr(obj, '__dict__'):
                return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
            return super().default(obj)
        finally:
            self.visited_objects.remove(obj_id)


def record_audit_trail(
    db: Session,
    workflow_id: str,
    agent_id: str,
    action_type: str,
    action_details: Dict[str, Any],
    source_message_id: Optional[str] = None,
    target_message_id: Optional[str] = None,
    source_decision_id: Optional[str] = None,
    decision_factors: Optional[Dict[str, Any]] = None,
    result_summary: Optional[str] = None
) -> str:
    """
    監査証跡の記録
    
    Args:
        db: データベースセッション
        workflow_id: ワークフローID
        agent_id: エージェントID
        action_type: アクションタイプ
        action_details: アクション詳細
        source_message_id: ソースメッセージID
        target_message_id: ターゲットメッセージID
        source_decision_id: ソース決定ID
        decision_factors: 決定要因
        result_summary: 結果サマリー
        
    Returns:
        作成された監査証跡のID
    """
    try:
        # データベースセッションを渡してリポジトリを初期化
        repo = AuditTrailRepository(db)
        
        audit_trail = repo.create(
            workflow_id=workflow_id,
            agent_id=agent_id,
            action_type=action_type,
            action_details=action_details,
            timestamp=datetime.now(),
            source_message_id=source_message_id,
            target_message_id=target_message_id,
            source_decision_id=source_decision_id,
            decision_factors=decision_factors or {},
            result_summary=result_summary
        )
        
        return audit_trail.id
    except Exception as e:
        logger.error(f"監査証跡の記録中にエラーが発生しました: {str(e)}")
        # エラー時はエラーIDを返す
        return f"error-{datetime.now().timestamp()}"


def record_message_log(db: Session, message: AgentMessage, delivery_status: str = "SENT") -> str:
    """
    メッセージログの記録
    
    Args:
        db: データベースセッション
        message: 記録するメッセージ
        delivery_status: メッセージの配信状態（"SENT", "DELIVERED", "READ", "FAILED"など）
        
    Returns:
        作成されたメッセージログのID
    """
    try:
        # データベースセッションを渡してリポジトリを初期化
        repo = MessageLogRepository(db)
        
        # メッセージの内容を安全にJSONに変換
        if isinstance(message.content, dict):
            content = message.content
        else:
            try:
                content = json_utils.json_deserialize(message.content)
            except (json.JSONDecodeError, TypeError):
                content = {"raw_content": str(message.content)}
        
        # メタデータを安全にJSONに変換
        if isinstance(message.metadata, dict):
            metadata = message.metadata
        else:
            try:
                metadata = json_utils.json_deserialize(message.metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {"raw_metadata": str(message.metadata)}
        
        # メッセージログの作成
        message_log = repo.create(
            message_id=message.id,
            from_agent=message.from_agent,
            to_agent=message.to_agent,
            message_type=message.message_type,
            content=content,
            created_at=message.created_at,
            workflow_id=message.workflow_id,
            context_id=message.context_id,
            in_response_to=message.in_response_to,
            priority=message.priority.value if hasattr(message.priority, 'value') else message.priority,
            requires_response=message.requires_response,
            message_metadata=metadata,
            delivery_status=delivery_status  # 配信状態を設定
        )
        
        return message_log.id
    except Exception as e:
        logger.error(f"メッセージログの記録中にエラーが発生しました: {str(e)}")
        # エラー時はNoneを返す
        return None


def record_agent_decision(
    db: Session,
    workflow_id: str,
    agent_id: str,
    decision_type: str,
    decision_context: Dict[str, Any],
    input_data: Dict[str, Any],
    decision_output: Dict[str, Any],
    confidence_score: float = 0.0,
    reasoning_steps: List[Dict[str, Any]] = None,
    related_message_ids: List[str] = None
) -> str:
    """
    エージェント決定の記録
    
    Args:
        db: データベースセッション
        workflow_id: ワークフローID
        agent_id: エージェントID
        decision_type: 決定タイプ
        decision_context: 決定コンテキスト
        input_data: 入力データ
        decision_output: 決定出力
        confidence_score: 確信度スコア
        reasoning_steps: 推論ステップ
        related_message_ids: 関連メッセージID
        
    Returns:
        作成された決定ID
    """
    try:
        # データベースセッションを渡してリポジトリを初期化
        repo = AgentDecisionRepository(db)
        
        # 監査証跡の記録
        audit_trail_id = record_audit_trail(
            db,
            workflow_id=workflow_id,
            agent_id=agent_id,
            action_type="DECISION",
            action_details={
                "decision_type": decision_type,
                "confidence_score": confidence_score
            },
            decision_factors=decision_context
        )
        
        # エージェント決定の作成
        decision = repo.create(
            workflow_id=workflow_id,
            agent_id=agent_id,
            decision_type=decision_type,
            decision_context=decision_context,
            input_data=input_data,
            decision_output=decision_output,
            timestamp=datetime.now(),
            confidence_score=confidence_score,
            reasoning_steps=reasoning_steps or [],
            related_message_ids=related_message_ids or [],
            audit_trail_id=audit_trail_id
        )
        
        return decision.id
    except Exception as e:
        logger.error(f"エージェント決定の記録中にエラーが発生しました: {str(e)}")
        return None


def get_workflow_audit_trail(
    db: Session,
    workflow_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    action_types: Optional[List[str]] = None,
    agent_ids: Optional[List[str]] = None,
    include_message_logs: bool = True,
    include_agent_decisions: bool = True
) -> Dict[str, Any]:
    """
    ワークフローの監査証跡を取得
    
    Args:
        db: データベースセッション
        workflow_id: ワークフローID
        start_time: 開始時間
        end_time: 終了時間
        action_types: アクションタイプのリスト
        agent_ids: エージェントIDのリスト
        include_message_logs: メッセージログを含めるかどうか
        include_agent_decisions: エージェント決定を含めるかどうか
        
    Returns:
        監査証跡、メッセージログ、エージェント決定を含む辞書
    """
    try:
        # リポジトリの初期化
        audit_repo = AuditTrailRepository(db)
        message_repo = MessageLogRepository(db)
        decision_repo = AgentDecisionRepository(db)
        
        # 検索条件の構築
        from sqlalchemy import and_, or_
        
        # 監査証跡の取得
        audit_trails = audit_repo.get_by_workflow_id(workflow_id)
        
        # フィルタリング
        if start_time or end_time or action_types or agent_ids:
            filtered_audit_trails = []
            for at in audit_trails:
                if start_time and at.timestamp < start_time:
                    continue
                if end_time and at.timestamp > end_time:
                    continue
                if action_types and at.action_type not in action_types:
                    continue
                if agent_ids and at.agent_id not in agent_ids:
                    continue
                filtered_audit_trails.append(at)
            audit_trails = filtered_audit_trails
        
        # 関連するメッセージログとエージェント決定のIDを収集
        source_message_ids = [at.source_message_id for at in audit_trails if at.source_message_id]
        target_message_ids = [at.target_message_id for at in audit_trails if at.target_message_id]
        decision_ids = [at.source_decision_id for at in audit_trails if at.source_decision_id]
        audit_trail_ids = [at.id for at in audit_trails]
        
        # メッセージログとエージェント決定を取得
        message_logs = []
        agent_decisions = []
        
        if include_message_logs:
            # ワークフローIDに関連するメッセージログを取得
            workflow_messages = message_repo.search(workflow_id=workflow_id)
            message_logs.extend(workflow_messages)
            
            # 監査証跡に関連するメッセージログも取得
            for msg_id in source_message_ids + target_message_ids:
                if msg_id:
                    message = message_repo.get_by_message_id(msg_id)
                    if message and message not in message_logs:
                        message_logs.append(message)
        
        if include_agent_decisions:
            # 監査証跡に関連する決定を取得
            for decision_id in decision_ids:
                if decision_id:
                    decision = decision_repo.get_by_id(decision_id)
                    if decision not in agent_decisions:
                        agent_decisions.append(decision)
            
            # ワークフローIDに関連する決定も取得
            workflow_decisions = decision_repo.get_by_workflow_id(workflow_id)
            for decision in workflow_decisions:
                if decision not in agent_decisions:
                    agent_decisions.append(decision)
        
        # 結果を構築（オブジェクトを辞書に変換）
        result = {
            "workflow_id": workflow_id,
            "audit_trails": [_convert_audit_trail_to_dict(at) for at in audit_trails],
            "message_logs": [_convert_message_log_to_dict(ml) for ml in message_logs],
            "agent_decisions": [_convert_agent_decision_to_dict(ad) for ad in agent_decisions]
        }
        
        return result
    except Exception as e:
        logger.error(f"監査証跡の取得中にエラーが発生しました: {str(e)}")
        return {
            "workflow_id": workflow_id,
            "error": str(e),
            "audit_trails": [],
            "message_logs": [],
            "agent_decisions": []
        }


def export_workflow_audit_trail(
    db: Session,
    workflow_id: str,
    file_path: str,
    format_type: str = "json",
    **kwargs
) -> bool:
    """
    ワークフローの監査証跡をエクスポート
    
    Args:
        db: データベースセッション
        workflow_id: ワークフローID
        file_path: 出力ファイルパス
        format_type: 出力形式 ("json" または "csv")
        **kwargs: get_workflow_audit_trailへの追加パラメータ
        
    Returns:
        エクスポートが成功したかどうか
    """
    try:
        # 監査証跡データの取得
        audit_data = get_workflow_audit_trail(db, workflow_id, **kwargs)
        
        # ディレクトリの作成
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # JSONフォーマットでエクスポート
        if format_type.lower() == "json":
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(audit_data, f, indent=2, ensure_ascii=False, cls=CustomJSONEncoder)
            
            logger.info(f"監査証跡をJSONとしてエクスポートしました: {file_path}")
            return True
        
        # CSVフォーマットでエクスポート
        elif format_type.lower() == "csv":
            # 各データタイプに対して別々のCSVファイルを作成
            base_path, ext = os.path.splitext(file_path)
            
            # 監査証跡
            audit_trail_path = f"{base_path}_audit_trails{ext}"
            if audit_data["audit_trails"]:
                with open(audit_trail_path, 'w', encoding='utf-8', newline='') as f:
                    # 日付型などを文字列に変換
                    rows = []
                    for trail in audit_data["audit_trails"]:
                        row = trail.copy()
                        for key, value in row.items():
                            if isinstance(value, datetime):
                                row[key] = value.isoformat()
                            elif isinstance(value, (dict, list)):
                                row[key] = json_utils.json_serialize(value)
                        rows.append(row)
                    
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
            
            # メッセージログ
            if audit_data["message_logs"]:
                message_log_path = f"{base_path}_message_logs{ext}"
                with open(message_log_path, 'w', encoding='utf-8', newline='') as f:
                    # 辞書型フィールドをJSON文字列に変換
                    rows = []
                    for log in audit_data["message_logs"]:
                        row = log.copy()
                        for key, value in row.items():
                            if isinstance(value, datetime):
                                row[key] = value.isoformat()
                            elif isinstance(value, (dict, list)):
                                row[key] = json_utils.json_serialize(value)
                        rows.append(row)
                    
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
            
            # エージェント決定
            if audit_data["agent_decisions"]:
                agent_decision_path = f"{base_path}_agent_decisions{ext}"
                with open(agent_decision_path, 'w', encoding='utf-8', newline='') as f:
                    # 辞書型フィールドとリストをJSON文字列に変換
                    rows = []
                    for decision in audit_data["agent_decisions"]:
                        row = decision.copy()
                        for key, value in row.items():
                            if isinstance(value, datetime):
                                row[key] = value.isoformat()
                            elif isinstance(value, (dict, list)):
                                row[key] = json_utils.json_serialize(value)
                        rows.append(row)
                    
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
            
            logger.info(f"監査証跡をCSVとしてエクスポートしました")
            return True
        
        else:
            logger.error(f"サポートされていないエクスポート形式: {format_type}")
            return False
    
    except Exception as e:
        logger.error(f"監査証跡のエクスポート中にエラーが発生しました: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def get_agent_conversation(
    db: Session,
    agent1_id: str,
    agent2_id: str,
    workflow_id: Optional[str] = None,
    limit: int = 50,
    include_content: bool = True
) -> List[Dict[str, Any]]:
    """
    2つのエージェント間の会話を取得
    
    Args:
        db: データベースセッション
        agent1_id: エージェント1のID
        agent2_id: エージェント2のID
        workflow_id: ワークフローID（指定した場合、そのワークフロー内の会話のみを取得）
        limit: 返すメッセージの最大数
        include_content: コンテンツを含めるかどうか
        
    Returns:
        会話メッセージのリスト
    """
    try:
        # リポジトリの初期化
        from sqlalchemy import and_, or_
        message_repo = MessageLogRepository(db)
        
        # 会話の取得
        if workflow_id:
            # ワークフローIDが指定されている場合、SQLクエリでフィルタリング
            query = message_repo.db.query(MessageLog).filter(
                and_(
                    or_(
                        and_(MessageLog.from_agent == agent1_id, MessageLog.to_agent == agent2_id),
                        and_(MessageLog.from_agent == agent2_id, MessageLog.to_agent == agent1_id)
                    ),
                    MessageLog.workflow_id == workflow_id
                )
            ).order_by(MessageLog.created_at).limit(limit)
            messages = query.all()
        else:
            # ワークフローIDが指定されていない場合、通常の会話取得
            messages = message_repo.get_conversation(agent1_id, agent2_id, limit)
        
        # 結果を構築
        result = []
        for msg in messages:
            message_dict = {
                "id": msg.id,
                "message_id": msg.message_id,
                "from_agent": msg.from_agent,
                "to_agent": msg.to_agent,
                "message_type": msg.message_type,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "workflow_id": msg.workflow_id,
                "context_id": msg.context_id,
                "priority": msg.priority,
                "requires_response": msg.requires_response,
                "in_response_to": msg.in_response_to,
                "delivery_status": msg.delivery_status
            }
            
            if include_content:
                message_dict["content"] = msg.content
                message_dict["message_metadata"] = msg.message_metadata
            
            result.append(message_dict)
        
        return result
    
    except Exception as e:
        logger.error(f"エージェント間会話の取得中にエラーが発生しました: {str(e)}")
        return []


def get_decision_chain(
    db: Session,
    decision_id: str,
    include_messages: bool = True,
    include_audit_trails: bool = True
) -> Dict[str, Any]:
    """
    決定チェーン（決定とそれに関連するメッセージ、監査証跡）を取得
    
    Args:
        db: データベースセッション
        decision_id: 決定ID
        include_messages: 関連メッセージを含めるかどうか
        include_audit_trails: 関連監査証跡を含めるかどうか
        
    Returns:
        決定チェーン情報
    """
    try:
        # リポジトリの初期化
        decision_repo = AgentDecisionRepository(db)
        message_repo = MessageLogRepository(db)
        audit_repo = AuditTrailRepository(db)
        
        # 決定の取得
        decision = decision_repo.get_by_id(decision_id)
        if not decision:
            return {"error": f"決定ID {decision_id} が見つかりません"}
        
        # 決定情報を構築
        decision_dict = _convert_agent_decision_to_dict(decision)
        decision_dict["decision_id"] = decision.id
        result = [decision_dict]
        
        # 関連メッセージの取得
        if include_messages and decision.related_message_ids:
            related_messages = []
            for message_id in decision.related_message_ids:
                message = message_repo.get_by_message_id(message_id)
                if message:
                    message_dict = _convert_message_log_to_dict(message)
                    related_messages.append(message_dict)
            
            if related_messages:
                result.extend(related_messages)
        
        # 関連監査証跡の取得
        if include_audit_trails:
            # 決定に関連する監査証跡を検索
            audit_trails = []
            
            # 決定IDに関連する監査証跡
            source_audit_trails = audit_repo.get_by_decision_id(decision_id)
            audit_trails.extend(source_audit_trails)
            
            # 決定に関連する監査証跡ID
            if decision.audit_trail_id:
                audit_trail = audit_repo.get_by_id(decision.audit_trail_id)
                if audit_trail:
                    audit_trails.append(audit_trail)
            
            for audit_trail in audit_trails:
                audit_dict = _convert_audit_trail_to_dict(audit_trail)
                result.append(audit_dict)
        
        return result
    
    except Exception as e:
        logger.error(f"決定チェーンの取得中にエラーが発生しました: {str(e)}")
        return {"error": str(e)}


# 内部ヘルパー関数
def _convert_audit_trail_to_dict(audit_trail: AuditTrail) -> Dict[str, Any]:
    """監査証跡をディクショナリに変換"""
    return {
        "id": audit_trail.id,
        "workflow_id": audit_trail.workflow_id,
        "agent_id": audit_trail.agent_id,
        "action_type": audit_trail.action_type,
        "action_details": audit_trail.action_details,
        "timestamp": audit_trail.timestamp.isoformat() if audit_trail.timestamp else None,
        "source_message_id": audit_trail.source_message_id,
        "target_message_id": audit_trail.target_message_id,
        "source_decision_id": audit_trail.source_decision_id,
        "decision_factors": audit_trail.decision_factors,
        "result_summary": audit_trail.result_summary
    }


def _convert_message_log_to_dict(message_log: MessageLog) -> Dict[str, Any]:
    """メッセージログをディクショナリに変換"""
    return {
        "id": message_log.id,
        "message_id": message_log.message_id,
        "workflow_id": message_log.workflow_id,
        "from_agent": message_log.from_agent,
        "to_agent": message_log.to_agent,
        "message_type": message_log.message_type,
        "content": message_log.content,
        "created_at": message_log.created_at.isoformat() if message_log.created_at else None,
        "context_id": message_log.context_id,
        "priority": message_log.priority,
        "requires_response": message_log.requires_response,
        "in_response_to": message_log.in_response_to,
        "metadata": message_log.metadata,
        "delivery_status": message_log.delivery_status
    }


def _convert_agent_decision_to_dict(agent_decision: AgentDecision) -> Dict[str, Any]:
    """エージェント決定をディクショナリに変換"""
    return {
        "id": agent_decision.id,
        "workflow_id": agent_decision.workflow_id,
        "agent_id": agent_decision.agent_id,
        "decision_type": agent_decision.decision_type,
        "decision_context": agent_decision.decision_context,
        "input_data": agent_decision.input_data,
        "decision_output": agent_decision.decision_output,
        "timestamp": agent_decision.timestamp.isoformat() if agent_decision.timestamp else None,
        "confidence_score": agent_decision.confidence_score,
        "reasoning_steps": agent_decision.reasoning_steps,
        "related_message_ids": agent_decision.related_message_ids,
        "audit_trail_id": agent_decision.audit_trail_id
    }


def export_audit_trail_to_json(
    workflow_id: str,
    db: Session,
    include_messages: bool = True,
    include_decisions: bool = True,
    include_state_history: bool = True,
    include_checkpoints: bool = True
) -> Dict[str, Any]:
    """
    監査証跡をJSON形式でエクスポートする
    
    Args:
        workflow_id: ワークフローID
        db: データベースセッション
        include_messages: メッセージログを含めるかどうか
        include_decisions: エージェント決定を含めるかどうか
        include_state_history: グラフ状態履歴を含めるかどうか
        include_checkpoints: チェックポイント記録を含めるかどうか
        
    Returns:
        Dict[str, Any]: エクスポートされた監査証跡データ
    """
    try:
        # 監査証跡の取得
        audit_trail_repo = AuditTrailRepository(db)
        audit_trails = audit_trail_repo.search(workflow_id=workflow_id, limit=1000)
        
        # 結果の初期化
        result = {
            "workflow_id": workflow_id,
            "export_timestamp": datetime.now().isoformat(),
            "audit_trails": [_convert_audit_trail_to_dict(trail) for trail in audit_trails],
            "metadata": {
                "audit_trail_count": len(audit_trails)
            }
        }
        
        # メッセージログの取得
        if include_messages:
            message_log_repo = MessageLogRepository(db)
            message_logs = message_log_repo.search(workflow_id=workflow_id, limit=1000)
            result["message_logs"] = [_convert_message_log_to_dict(log) for log in message_logs]
            result["metadata"]["message_log_count"] = len(message_logs)
        
        # エージェント決定の取得
        if include_decisions:
            decision_repo = AgentDecisionRepository(db)
            decisions = decision_repo.search(workflow_id=workflow_id, limit=1000)
            result["agent_decisions"] = [_convert_agent_decision_to_dict(decision) for decision in decisions]
            result["metadata"]["agent_decision_count"] = len(decisions)
        
        # グラフ状態履歴の取得
        if include_state_history:
            state_history_repo = GraphStateHistoryRepository(db)
            state_histories = state_history_repo.search(workflow_id=workflow_id, limit=1000)
            result["state_histories"] = [_convert_state_history_to_dict(history) for history in state_histories]
            result["metadata"]["state_history_count"] = len(state_histories)
        
        # チェックポイント記録の取得
        if include_checkpoints:
            checkpoint_repo = CheckpointRecordRepository(db)
            checkpoints = checkpoint_repo.search(workflow_id=workflow_id, limit=1000)
            result["checkpoints"] = [_convert_checkpoint_to_dict(checkpoint) for checkpoint in checkpoints]
            result["metadata"]["checkpoint_count"] = len(checkpoints)
        
        return result
    
    except Exception as e:
        logger.error(f"監査証跡のエクスポートに失敗しました: {str(e)}")
        raise


def _convert_state_history_to_dict(state_history: GraphStateHistory) -> Dict[str, Any]:
    """GraphStateHistoryをディクショナリに変換"""
    result = {
        "id": state_history.id,
        "workflow_id": state_history.workflow_id,
        "context_id": state_history.context_id,
        "agent_id": state_history.agent_id,
        "node_id": state_history.node_id,
        "event_type": state_history.event_type,
        "timestamp": state_history.timestamp.isoformat() if state_history.timestamp else None,
        "checkpoint_id": state_history.checkpoint_id
    }
    
    # JSONフィールドの処理
    if state_history.state_snapshot:
        try:
            result["state_snapshot"] = json_utils.json_deserialize(state_history.state_snapshot)
        except:
            result["state_snapshot"] = state_history.state_snapshot
    
    if state_history.state_diff:
        try:
            result["state_diff"] = json_utils.json_deserialize(state_history.state_diff)
        except:
            result["state_diff"] = state_history.state_diff
    
    if state_history.event_data:
        try:
            result["event_data"] = json_utils.json_deserialize(state_history.event_data)
        except:
            result["event_data"] = state_history.event_data
    
    return result


def _convert_checkpoint_to_dict(checkpoint: CheckpointRecord) -> Dict[str, Any]:
    """CheckpointRecordをディクショナリに変換"""
    result = {
        "id": checkpoint.id,
        "workflow_id": checkpoint.workflow_id,
        "context_id": checkpoint.context_id,
        "agent_id": checkpoint.agent_id,
        "checkpoint_type": checkpoint.checkpoint_type,
        "node_id": checkpoint.node_id,
        "created_at": checkpoint.created_at.isoformat() if checkpoint.created_at else None,
        "restored_at": checkpoint.restored_at.isoformat() if checkpoint.restored_at else None,
        "restore_count": checkpoint.restore_count
    }
    
    # JSONフィールドの処理
    if checkpoint.state_reference:
        try:
            result["state_reference"] = json_utils.json_deserialize(checkpoint.state_reference)
        except:
            result["state_reference"] = checkpoint.state_reference
    
    if checkpoint.checkpoint_metadata:
        try:
            result["metadata"] = json_utils.json_deserialize(checkpoint.checkpoint_metadata)
        except:
            result["metadata"] = checkpoint.checkpoint_metadata
    
    return result 