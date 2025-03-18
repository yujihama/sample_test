"""
ワークフロー管理ユーティリティ

このモジュールはワークフローの状態管理と整合性チェックのためのユーティリティを提供します。
- 整合性チェック機能：ワークフローとエージェントの状態の不整合を検出
- 自動修復機能：検出された問題を自動的に修正
"""

import sqlite3
import json
from src.utils import json_utils
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
from sqlalchemy.orm import Session

from src.models.db_models import Workflow, AgentState
from src.models.repositories import workflow_repository, agent_state_repository

# エージェントの状態チェックのルール
AGENT_WORKFLOW_RULES = [
    {
        "workflow_status": "in_progress",
        "current_agent": "agent-a",
        "required_agent_states": {
            "agent-a": "in_progress"
        }
    },
    {
        "workflow_status": "in_progress",
        "current_agent": "agent-b",
        "required_agent_states": {
            "agent-a": "completed",
            "agent-b": "in_progress"
        }
    },
    {
        "workflow_status": "in_progress",
        "current_agent": "agent-c",
        "required_agent_states": {
            "agent-a": "completed",
            "agent-b": "completed",
            "agent-c": "in_progress"
        }
    },
    {
        "workflow_status": "in_progress",
        "current_agent": "agent-d",
        "required_agent_states": {
            "agent-a": "completed",
            "agent-b": "completed",
            "agent-c": "completed",
            "agent-d": "in_progress"
        }
    },
    {
        "workflow_status": "completed",
        "current_agent": None,
        "required_agent_states": {
            "agent-a": "completed",
            "agent-b": "completed",
            "agent-c": "completed",
            "agent-d": "completed"
        }
    },
    {
        "workflow_status": "failed",
        "current_agent": None,
        "required_agent_states": {}  # 任意のエージェントが失敗していれば良い
    }
]

# ワークフローのトランジションルール
WORKFLOW_TRANSITIONS = {
    # 現在の状態: {許容される次の状態のリスト}
    "pending": ["in_progress", "cancelled"],
    "in_progress": ["paused", "completed", "failed", "cancelled"],
    "paused": ["in_progress", "cancelled"],
    "completed": [],  # 終了状態
    "failed": ["in_progress"],  # 失敗状態から再試行可能
    "cancelled": []   # 終了状態
}

# デッドロック検出の最大許容時間（時間単位）
MAX_IDLE_HOURS = 24
# エージェント間の移動の最大許容時間（分単位）
MAX_AGENT_TRANSITION_MINUTES = 30
# 同一エージェントの最大実行時間（時間単位）
MAX_AGENT_EXECUTION_HOURS = 4

def check_workflow_consistency(db: Session, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    ワークフローとエージェント状態の整合性をチェック
    
    Args:
        db: DBセッション
        workflow_id: チェック対象のワークフローID（省略時は全ワークフロー）
        
    Returns:
        整合性の問題のリスト
    """
    try:
        issues = []
        
        # ワークフローの取得
        if workflow_id:
            workflows = workflow_repository.get_by_id(db, workflow_id)
            if workflows:
                workflows = [workflows]
            else:
                workflows = []
        else:
            workflows = workflow_repository.get_all(db)
        
        # 取得したワークフローの整合性チェック
        for workflow in workflows:
            # ワークフローデータを辞書に変換
            workflow_dict = workflow.__dict__ if hasattr(workflow, "__dict__") else workflow
            
            # エージェントの状態を取得
            agent_states = {}
            agent_state_records = agent_state_repository.get_by_workflow_id(db, workflow_dict.get("id", ""))
            
            for state in agent_state_records:
                state_dict = state.__dict__ if hasattr(state, "__dict__") else state
                agent_states[state_dict.get("agent_id")] = state_dict
            
            # 単一ワークフローの整合性チェック
            workflow_issues = _check_single_workflow_consistency(workflow_dict, agent_states)
            
            # デッドロックの検出
            deadlock_issues = _check_workflow_deadlock(workflow_dict, agent_states)
            workflow_issues.extend(deadlock_issues)
            
            if workflow_issues:
                issues.extend(workflow_issues)
        
        return issues
    
    except Exception as e:
        logger.error(f"ワークフロー整合性チェック中にエラーが発生: {str(e)}")
        return [{
            "workflow_id": workflow_id or "unknown",
            "error": f"整合性チェック中にエラー: {str(e)}",
            "error_type": "system_error",
            "severity": "high"
        }]

def _check_single_workflow_consistency(
    workflow: Dict[str, Any], 
    agent_states: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    単一ワークフローの整合性チェック
    
    Args:
        workflow: ワークフローデータ
        agent_states: エージェントの状態データ
        
    Returns:
        整合性の問題のリスト
    """
    issues = []
    workflow_id = workflow.get("id", "unknown")
    workflow_status = workflow.get("status", "unknown")
    current_agent = workflow.get("current_agent")
    
    # 基本的な整合性チェック - ステータスが有効か
    if workflow_status not in ["pending", "in_progress", "paused", "completed", "failed", "cancelled"]:
        issues.append({
            "workflow_id": workflow_id,
            "issue": f"無効なワークフローステータス: {workflow_status}",
            "issue_type": "invalid_status",
            "severity": "high",
            "fix_suggestion": "ステータスを有効な値に更新"
        })
    
    # 現在のエージェントがNoneでないのに、ワークフローが完了または失敗状態
    if current_agent and workflow_status in ["completed", "failed", "cancelled"]:
        issues.append({
            "workflow_id": workflow_id,
            "issue": f"終了状態 '{workflow_status}' なのに現在のエージェントが設定されています: {current_agent}",
            "issue_type": "agent_in_final_state",
            "severity": "medium",
            "fix_suggestion": "current_agentをnullに設定"
        })
    
    # 現在のエージェントがないのに、ワークフローが進行中
    if not current_agent and workflow_status == "in_progress":
        issues.append({
            "workflow_id": workflow_id,
            "issue": f"ステータスが '{workflow_status}' なのに現在のエージェントが設定されていません",
            "issue_type": "missing_agent",
            "severity": "high",
            "fix_suggestion": "適切なエージェントを設定するか、ステータスを変更"
        })
    
    # ワークフローのルールに基づく整合性チェック
    for rule in AGENT_WORKFLOW_RULES:
        # ルールが現在のワークフロー状態に適用されるか確認
        if rule["workflow_status"] == workflow_status and rule["current_agent"] == current_agent:
            # 必要なエージェント状態をチェック
            for agent_id, required_state in rule["required_agent_states"].items():
                agent_state = agent_states.get(agent_id, {})
                actual_state = agent_state.get("status", "unknown")
                
                if actual_state != required_state:
                    issues.append({
                        "workflow_id": workflow_id,
                        "issue": f"エージェント {agent_id} の状態が不整合です。期待: {required_state}, 実際: {actual_state}",
                        "issue_type": "agent_state_mismatch",
                        "severity": "medium", 
                        "fix_suggestion": f"エージェント {agent_id} の状態を {required_state} に更新"
                    })
    
    # エージェント状態の不整合をチェック
    agent_ids = list(agent_states.keys())
    for agent_id in agent_ids:
        agent_state = agent_states.get(agent_id, {})
        agent_status = agent_state.get("status", "unknown")
        
        # 完了したワークフローで実行中のエージェントがある
        if workflow_status in ["completed", "cancelled"] and agent_status == "in_progress":
            issues.append({
                "workflow_id": workflow_id,
                "issue": f"ワークフローが {workflow_status} なのにエージェント {agent_id} が実行中です",
                "issue_type": "agent_running_in_completed_workflow",
                "severity": "medium",
                "fix_suggestion": f"エージェント {agent_id} の状態を completed に更新"
            })
    
    return issues

def _check_workflow_deadlock(
    workflow: Dict[str, Any], 
    agent_states: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    ワークフローのデッドロック状態をチェック
    
    Args:
        workflow: ワークフローデータ
        agent_states: エージェントの状態データ
        
    Returns:
        デッドロックの問題のリスト
    """
    issues = []
    workflow_id = workflow.get("id", "unknown")
    workflow_status = workflow.get("status", "unknown")
    current_agent = workflow.get("current_agent")
    updated_at = workflow.get("updated_at")
    
    # 更新時刻がない場合は早期リターン
    if not updated_at:
        return []
    
    # 文字列からdatetimeに変換
    if isinstance(updated_at, str):
        try:
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            # 変換エラーの場合はスキップ
            return []
    
    # 現在時刻との差分を計算
    now = datetime.now()
    if updated_at.tzinfo:
        now = now.replace(tzinfo=updated_at.tzinfo)
    
    idle_hours = (now - updated_at).total_seconds() / 3600
    
    # 長時間アイドル状態のワークフローをチェック
    if workflow_status in ["in_progress", "paused"] and idle_hours > MAX_IDLE_HOURS:
        issues.append({
            "workflow_id": workflow_id,
            "issue": f"ワークフローが {idle_hours:.1f} 時間アイドル状態です（最大許容: {MAX_IDLE_HOURS}時間）",
            "issue_type": "workflow_idle",
            "severity": "high",
            "fix_suggestion": "ワークフローを再開するか、失敗状態に設定"
        })
    
    # 同一エージェントでの長時間実行をチェック
    if workflow_status == "in_progress" and current_agent:
        agent_state = agent_states.get(current_agent, {})
        agent_updated_at = agent_state.get("updated_at")
        
        if agent_updated_at:
            # 文字列からdatetimeに変換
            if isinstance(agent_updated_at, str):
                try:
                    agent_updated_at = datetime.fromisoformat(agent_updated_at.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    # 変換エラーの場合はスキップ
                    agent_updated_at = None
            
            if agent_updated_at:
                agent_hours = (now - agent_updated_at).total_seconds() / 3600
                
                if agent_hours > MAX_AGENT_EXECUTION_HOURS:
                    issues.append({
                        "workflow_id": workflow_id,
                        "issue": f"エージェント {current_agent} が {agent_hours:.1f} 時間実行中です（最大許容: {MAX_AGENT_EXECUTION_HOURS}時間）",
                        "issue_type": "agent_execution_timeout",
                        "severity": "medium",
                        "fix_suggestion": "エージェントの実行を終了し、次のエージェントに移行するか、ワークフローを一時停止"
                    })
    
    return issues

def auto_repair_workflows(db: Session, repair_type: str = "all", workflow_id: Optional[str] = None, dry_run: bool = True) -> Tuple[int, List[Dict[str, Any]]]:
    """
    問題のあるワークフローを自動修復
    
    Args:
        db: DBセッション
        repair_type: 修復タイプ（"all", "agent_states", "workflow_states", "deadlocks"）
        workflow_id: 修復対象のワークフローID（省略時は全ワークフロー）
        dry_run: 実際に修復せずにシミュレーションのみ行う
        
    Returns:
        (修復件数, 修復詳細のリスト)
    """
    try:
        # 整合性チェックを実行
        issues = check_workflow_consistency(db, workflow_id)
        
        if not issues:
            logger.info("修復対象の問題が見つかりませんでした")
            return 0, []
        
        # 修復タイプに基づいてフィルタリング
        if repair_type != "all":
            filtered_issues = []
            for issue in issues:
                issue_type = issue.get("issue_type", "")
                
                if repair_type == "agent_states" and "agent" in issue_type:
                    filtered_issues.append(issue)
                elif repair_type == "workflow_states" and "status" in issue_type:
                    filtered_issues.append(issue)
                elif repair_type == "deadlocks" and ("idle" in issue_type or "timeout" in issue_type):
                    filtered_issues.append(issue)
            
            issues = filtered_issues
        
        # 修復処理
        repairs = []
        repair_count = 0
        
        for issue in issues:
            workflow_id = issue.get("workflow_id")
            issue_type = issue.get("issue_type", "")
            severity = issue.get("severity", "low")
            
            # 修復プランを作成
            repair_plan = _create_repair_plan(issue)
            
            if not repair_plan:
                continue
            
            # シミュレーションモードの場合は修復せずに記録のみ
            if dry_run:
                repairs.append({
                    "workflow_id": workflow_id,
                    "issue_type": issue_type,
                    "severity": severity,
                    "repair_plan": repair_plan
                })
                repair_count += 1
                continue
            
            # 実際の修復処理
            try:
                success = _execute_repair(db, repair_plan)
                
                if success:
                    repairs.append({
                        "workflow_id": workflow_id,
                        "issue_type": issue_type,
                        "severity": severity,
                        "repair_plan": repair_plan,
                        "status": "success"
                    })
                    repair_count += 1
                else:
                    repairs.append({
                        "workflow_id": workflow_id,
                        "issue_type": issue_type,
                        "severity": severity,
                        "repair_plan": repair_plan,
                        "status": "failed"
                    })
            except Exception as e:
                repairs.append({
                    "workflow_id": workflow_id,
                    "issue_type": issue_type,
                    "severity": severity,
                    "repair_plan": repair_plan,
                    "status": "error",
                    "error": str(e)
                })
        
        mode = "シミュレーション" if dry_run else "実行"
        logger.info(f"ワークフロー修復{mode}完了: {repair_count}件の修復プラン")
        
        return repair_count, repairs
    
    except Exception as e:
        logger.error(f"ワークフロー修復中にエラーが発生: {str(e)}")
        return 0, [{
            "workflow_id": workflow_id or "unknown",
            "status": "error", 
            "error": f"修復中にエラー: {str(e)}",
            "repair_type": repair_type
        }]

def _create_repair_plan(issue: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    問題に対する修復プランを作成
    
    Args:
        issue: 問題の詳細
        
    Returns:
        修復プラン
    """
    workflow_id = issue.get("workflow_id")
    issue_type = issue.get("issue_type", "")
    
    # 問題の種類に応じた修復プラン
    if issue_type == "invalid_status":
        return {
            "type": "workflow_update",
            "workflow_id": workflow_id,
            "update": {"status": "in_progress"}
        }
    
    elif issue_type == "agent_in_final_state":
        return {
            "type": "workflow_update",
            "workflow_id": workflow_id,
            "update": {"current_agent": None}
        }
    
    elif issue_type == "missing_agent":
        return {
            "type": "workflow_update",
            "workflow_id": workflow_id,
            "update": {"status": "paused", "metadata": {"requires_attention": True}}
        }
    
    elif issue_type == "agent_state_mismatch":
        # 修復対象のエージェントを抽出
        agent_id = None
        required_state = None
        
        issue_desc = issue.get("issue", "")
        agent_match = re.search(r'エージェント (\S+) の状態', issue_desc)
        state_match = re.search(r'期待: (\S+),', issue_desc)
        
        if agent_match and state_match:
            agent_id = agent_match.group(1)
            required_state = state_match.group(1)
            
            return {
                "type": "agent_update",
                "workflow_id": workflow_id,
                "agent_id": agent_id,
                "update": {"status": required_state}
            }
    
    elif issue_type == "agent_running_in_completed_workflow":
        # 修復対象のエージェントを抽出
        agent_id = None
        
        issue_desc = issue.get("issue", "")
        agent_match = re.search(r'エージェント (\S+) が実行中', issue_desc)
        
        if agent_match:
            agent_id = agent_match.group(1)
            
            return {
                "type": "agent_update",
                "workflow_id": workflow_id,
                "agent_id": agent_id,
                "update": {"status": "completed"}
            }
    
    elif issue_type == "workflow_idle":
        return {
            "type": "workflow_update",
            "workflow_id": workflow_id,
            "update": {"status": "paused", "metadata": {"requires_attention": True, "paused_reason": "idle_timeout"}}
        }
    
    elif issue_type == "agent_execution_timeout":
        # 修復対象のエージェントを抽出
        agent_id = None
        
        issue_desc = issue.get("issue", "")
        agent_match = re.search(r'エージェント (\S+) が', issue_desc)
        
        if agent_match:
            agent_id = agent_match.group(1)
            
            return {
                "type": "agent_update",
                "workflow_id": workflow_id,
                "agent_id": agent_id,
                "update": {"status": "paused", "metadata": {"requires_attention": True, "paused_reason": "execution_timeout"}}
            }
    
    # その他の問題は手動対応が必要
    return None

def _execute_repair(db: Session, repair_plan: Dict[str, Any]) -> bool:
    """
    修復プランを実行
    
    Args:
        db: DBセッション
        repair_plan: 修復プラン
        
    Returns:
        成功したかどうか
    """
    plan_type = repair_plan.get("type")
    workflow_id = repair_plan.get("workflow_id")
    
    if plan_type == "workflow_update":
        # ワークフローの更新
        update_data = repair_plan.get("update", {})
        
        # 既存のメタデータがある場合はマージ
        if "metadata" in update_data:
            workflow = workflow_repository.get_by_id(db, workflow_id)
            
            if workflow and hasattr(workflow, "metadata") and workflow.metadata:
                current_metadata = workflow.metadata
                if isinstance(current_metadata, str):
                    try:
                        current_metadata = json_utils.json_deserialize(current_metadata)
                    except:
                        current_metadata = {}
                
                # 新しいメタデータと既存のメタデータをマージ
                merged_metadata = {**current_metadata, **update_data["metadata"]}
                update_data["metadata"] = merged_metadata
        
        # ワークフローの更新実行
        result = workflow_repository.update(db, workflow_id, update_data)
        logger.info(f"ワークフロー修復: ID {workflow_id} の更新 {update_data}")
        return result is not None
    
    elif plan_type == "agent_update":
        # エージェントの更新
        agent_id = repair_plan.get("agent_id")
        update_data = repair_plan.get("update", {})
        
        # エージェント状態の更新実行
        result = agent_state_repository.update(
            db,
            workflow_id=workflow_id,
            agent_id=agent_id,
            update_data=update_data
        )
        logger.info(f"エージェント修復: ワークフロー {workflow_id}, エージェント {agent_id} の更新 {update_data}")
        return result is not None
    
    return False

def reset_workflow(db: Session, workflow_id: str) -> Optional[Dict[str, Any]]:
    """
    ワークフローをリセット（新規やり直し）
    
    Args:
        db: DBセッション
        workflow_id: リセット対象のワークフローID
        
    Returns:
        リセット後のワークフロー情報
    """
    try:
        # ワークフローの存在確認
        workflow = workflow_repository.get_by_id(db, workflow_id)
        
        if not workflow:
            logger.warning(f"リセット対象のワークフロー {workflow_id} が存在しません")
            return None
        
        # 現在のエージェント状態を取得
        agent_states = agent_state_repository.get_by_workflow_id(db, workflow_id)
        
        # エージェント状態をすべて削除
        for state in agent_states:
            agent_state_repository.delete(db, state.id)
        
        # 最初のエージェントを特定（通常はagent-a）
        first_agent = "agent-a"
        
        # ワークフローを更新
        update_data = {
            "status": "in_progress",
            "current_agent": first_agent,
            "updated_at": datetime.now()
        }
        
        updated_workflow = workflow_repository.update(db, workflow_id, update_data)
        
        # 最初のエージェントの状態を作成
        agent_state_data = {
            "workflow_id": workflow_id,
            "agent_id": first_agent,
            "status": "in_progress",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        agent_state_repository.create(db, agent_state_data)
        
        logger.info(f"ワークフロー {workflow_id} をリセットしました")
        
        # 更新後のワークフロー情報を返す
        if updated_workflow:
            workflow_dict = updated_workflow.__dict__.copy() if hasattr(updated_workflow, "__dict__") else updated_workflow.copy()
            if "_sa_instance_state" in workflow_dict:
                del workflow_dict["_sa_instance_state"]
            return workflow_dict
        
        return None
    
    except Exception as e:
        logger.error(f"ワークフローリセット中にエラーが発生: {str(e)}")
        return None

def check_valid_transition(current_status: str, new_status: str) -> bool:
    """
    ワークフローステータスの遷移が有効かチェック
    
    Args:
        current_status: 現在のステータス
        new_status: 新しいステータス
        
    Returns:
        遷移が有効かどうか
    """
    if current_status not in WORKFLOW_TRANSITIONS:
        return False
    
    allowed_transitions = WORKFLOW_TRANSITIONS[current_status]
    return new_status in allowed_transitions

def get_workflow_metrics(db: Session, workflow_id: Optional[str] = None, 
                        start_date: Optional[datetime] = None, 
                        end_date: Optional[datetime] = None) -> Dict[str, Any]:
    """
    ワークフローの実行メトリクスを取得
    
    Args:
        db: DBセッション
        workflow_id: 取得対象のワークフローID（省略時は全ワークフロー）
        start_date: 集計開始日時
        end_date: 集計終了日時
        
    Returns:
        メトリクス情報
    """
    try:
        # 日時範囲の設定
        if not end_date:
            end_date = datetime.now()
        
        if not start_date:
            # デフォルトは7日前
            start_date = end_date - timedelta(days=7)
        
        # ワークフローの取得
        if workflow_id:
            workflows = [workflow_repository.get_by_id(db, workflow_id)]
            workflows = [w for w in workflows if w]  # Noneを除外
        else:
            workflows = workflow_repository.get_all(db)
        
        # 日時範囲でフィルタリング
        filtered_workflows = []
        for workflow in workflows:
            wf_dict = workflow.__dict__ if hasattr(workflow, "__dict__") else workflow
            created_at = wf_dict.get("created_at")
            
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    continue
            
            if start_date <= created_at <= end_date:
                filtered_workflows.append(wf_dict)
        
        # メトリクスの計算
        total_workflows = len(filtered_workflows)
        status_counts = {
            "pending": 0,
            "in_progress": 0,
            "paused": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0
        }
        
        for wf in filtered_workflows:
            status = wf.get("status", "unknown")
            if status in status_counts:
                status_counts[status] += 1
        
        # 完了率
        completion_rate = 0
        if total_workflows > 0:
            completion_rate = (status_counts["completed"] / total_workflows) * 100
        
        # 平均実行時間（完了したワークフローのみ）
        avg_duration = None
        completed_workflows = [
            wf for wf in filtered_workflows 
            if wf.get("status") == "completed" and wf.get("created_at") and wf.get("updated_at")
        ]
        
        if completed_workflows:
            durations = []
            for wf in completed_workflows:
                created_at = wf.get("created_at")
                updated_at = wf.get("updated_at")
                
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                if isinstance(updated_at, str):
                    updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                
                duration_seconds = (updated_at - created_at).total_seconds()
                durations.append(duration_seconds)
            
            avg_duration = sum(durations) / len(durations) if durations else None
        
        metrics = {
            "total_workflows": total_workflows,
            "status_counts": status_counts,
            "completion_rate": completion_rate,
            "avg_duration_seconds": avg_duration,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }
        
        return metrics
    
    except Exception as e:
        logger.error(f"ワークフローメトリクス取得中にエラーが発生: {str(e)}")
        return {
            "error": f"メトリクス取得エラー: {str(e)}",
            "workflow_id": workflow_id
        }

def pause_workflow(db: Session, workflow_id: str, reason: str = "人間監査人の介入が必要") -> Optional[Dict[str, Any]]:
    """
    ワークフローを一時停止する
    
    人間監査人の介入が必要な場合など、ワークフローを一時的に停止します。
    現在のエージェントの状態を保存し、ワークフローステータスを 'human_intervention_required' に更新します。
    
    Args:
        db: データベースセッション
        workflow_id: 一時停止するワークフローのID
        reason: 一時停止の理由
        
    Returns:
        更新したワークフロー情報の辞書、またはNone（ワークフローが見つからない場合）
    """
    logger.info(f"ワークフロー {workflow_id} を一時停止します。理由: {reason}")
    
    try:
        # ワークフローの取得
        workflow = workflow_repository.get(db, workflow_id)
        if not workflow:
            logger.error(f"ワークフロー {workflow_id} が見つかりません")
            return None
        
        # 現在のステータスを確認
        # 既に完了しているまたはエラー状態の場合は一時停止しない
        if workflow.status in ["completed", "error", "human_intervention_required"]:
            logger.warning(f"ワークフロー {workflow_id} は既に {workflow.status} 状態のため一時停止できません")
            return {
                "id": workflow.id,
                "status": workflow.status,
                "message": f"ワークフローは既に {workflow.status} 状態です"
            }
        
        # 現在のエージェントの状態を保存
        agents = agent_state_repository.get_multi(db, filter_by={"workflow_id": workflow_id})
        for agent in agents:
            if agent.status == "in_progress":
                # 進行中のエージェントを一時停止
                agent_state_repository.update(db, agent.id, {
                    "status": "paused",
                    "context_data": {
                        **(agent.context_data or {}),
                        "paused_at": datetime.now().isoformat(),
                        "pause_reason": reason
                    }
                })
                logger.info(f"エージェント {agent.agent_id} を一時停止しました")
        
        # ワークフローのステータスを更新
        old_status = workflow.status
        workflow_data = {
            "status": "human_intervention_required",
            "last_activity": datetime.now(),
            "error_details": {
                "pause_reason": reason,
                "previous_status": old_status,
                "paused_at": datetime.now().isoformat()
            }
        }
        
        workflow_repository.update(db, workflow_id, workflow_data)
        logger.info(f"ワークフロー {workflow_id} のステータスを 'human_intervention_required' に更新しました")
        
        # 更新後のワークフローを取得
        updated_workflow = workflow_repository.get(db, workflow_id)
        
        return {
            "id": updated_workflow.id,
            "status": updated_workflow.status,
            "previous_status": old_status,
            "message": f"ワークフローを一時停止しました。理由: {reason}"
        }
        
    except Exception as e:
        logger.error(f"ワークフロー {workflow_id} の一時停止中にエラーが発生しました: {str(e)}")
        return None

def resume_workflow(db: Session, workflow_id: str) -> Optional[Dict[str, Any]]:
    """
    一時停止したワークフローを再開する
    
    人間監査人の介入が完了した後など、一時停止していたワークフローを再開します。
    保存されていたエージェントの状態を復元し、ワークフローステータスを 'in_progress' に更新します。
    
    Args:
        db: データベースセッション
        workflow_id: 再開するワークフローのID
        
    Returns:
        更新したワークフロー情報の辞書、またはNone（ワークフローが見つからない場合）
    """
    logger.info(f"ワークフロー {workflow_id} を再開します")
    
    try:
        # ワークフローの取得
        workflow = workflow_repository.get(db, workflow_id)
        if not workflow:
            logger.error(f"ワークフロー {workflow_id} が見つかりません")
            return None
        
        # 現在のステータスを確認
        # 一時停止状態でない場合は再開しない
        if workflow.status != "human_intervention_required":
            logger.warning(f"ワークフロー {workflow_id} は 'human_intervention_required' 状態ではないため再開できません")
            return {
                "id": workflow.id,
                "status": workflow.status,
                "message": "ワークフローは一時停止状態ではありません"
            }
        
        # 保存された以前のステータスを取得
        previous_status = "in_progress"
        if workflow.error_details and "previous_status" in workflow.error_details:
            previous_status = workflow.error_details["previous_status"]
        
        # 一時停止していたエージェントを再開
        agents = agent_state_repository.get_multi(db, filter_by={"workflow_id": workflow_id})
        for agent in agents:
            if agent.status == "paused":
                # エージェントを再開
                agent_state_repository.update(db, agent.id, {
                    "status": "in_progress",
                    "context_data": {
                        **(agent.context_data or {}),
                        "resumed_at": datetime.now().isoformat()
                    }
                })
                logger.info(f"エージェント {agent.agent_id} を再開しました")
        
        # ワークフローのステータスを更新
        workflow_data = {
            "status": previous_status,
            "last_activity": datetime.now(),
            "error_details": None
        }
        
        workflow_repository.update(db, workflow_id, workflow_data)
        logger.info(f"ワークフロー {workflow_id} のステータスを '{previous_status}' に更新しました")
        
        # 更新後のワークフローを取得
        updated_workflow = workflow_repository.get(db, workflow_id)
        
        return {
            "id": updated_workflow.id,
            "status": updated_workflow.status,
            "message": "ワークフローを再開しました"
        }
        
    except Exception as e:
        logger.error(f"ワークフロー {workflow_id} の再開中にエラーが発生しました: {str(e)}")
        return None 