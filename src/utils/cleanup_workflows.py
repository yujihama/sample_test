"""
ワークフロークリーンアップユーティリティ

このモジュールは古いワークフローデータをクリーンアップするためのユーティリティを提供します。
- 古いワークフローの特定
- ワークフローデータのアーカイブ
- データベースからの削除
"""

import os
import json
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
from sqlalchemy.orm import Session

from src.models.db_models import Workflow, AgentState, AuditResult
from src.models.repositories import workflow_repository, agent_state_repository, audit_result_repository
from src.utils.db_manager import session_scope


def find_old_workflows(db: Session, days_old: int = 30, status: Optional[str] = None) -> List[Workflow]:
    """
    指定した日数より古いワークフローを検索する

    Args:
        db: データベースセッション
        days_old: 何日前より古いデータを対象とするか (デフォルト: 30日)
        status: 特定のステータスのワークフローのみ検索 (オプション)

    Returns:
        古いワークフローのリスト
    """
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    filter_by = {"updated_at": cutoff_date}
    if status:
        filter_by["status"] = status
    
    # filter_byは直接比較ではないため、以下のようにカスタム検索を実装
    old_workflows = []
    all_workflows = workflow_repository.get_multi(db)
    
    for workflow in all_workflows:
        if workflow.updated_at and workflow.updated_at < cutoff_date:
            if status is None or workflow.status == status:
                old_workflows.append(workflow)
    
    return old_workflows


def archive_workflow(workflow: Workflow, agent_states: List[AgentState], results: List[AuditResult], archive_dir: str) -> str:
    """
    ワークフローデータをJSONファイルにアーカイブする

    Args:
        workflow: アーカイブするワークフロー
        agent_states: 関連するエージェント状態のリスト
        results: 関連する監査結果のリスト
        archive_dir: アーカイブディレクトリのパス

    Returns:
        アーカイブファイルのパス
    """
    # アーカイブディレクトリが存在しない場合は作成
    os.makedirs(archive_dir, exist_ok=True)
    
    # ワークフロー情報の辞書化
    workflow_dict = {
        "id": workflow.id,
        "procedure_id": workflow.procedure_id,
        "sample_id": workflow.sample_id,
        "status": workflow.status,
        "current_agent": workflow.current_agent,
        "progress": workflow.progress,
        "started_at": workflow.started_at.isoformat() if workflow.started_at else None,
        "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
        "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None
    }
    
    # エージェント状態の辞書化
    agent_states_dict = [{
        "id": state.id,
        "agent_id": state.agent_id,
        "status": state.status,
        "progress": state.progress,
        "context": state.context,
        "started_at": state.started_at.isoformat() if state.started_at else None,
        "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        "completed_at": state.completed_at.isoformat() if state.completed_at else None
    } for state in agent_states]
    
    # 監査結果の辞書化
    results_dict = [{
        "id": result.id,
        "agent_id": result.agent_id,
        "result_type": result.result_type,
        "content": result.content,
        "summary": result.summary,
        "created_at": result.created_at.isoformat() if result.created_at else None
    } for result in results]
    
    # アーカイブデータの構築
    archive_data = {
        "archived_at": datetime.now().isoformat(),
        "workflow": workflow_dict,
        "agent_states": agent_states_dict,
        "results": results_dict
    }
    
    # アーカイブファイルのパス
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_file = os.path.join(archive_dir, f"{workflow.id}_{timestamp}.json")
    
    # JSONファイルに保存
    with open(archive_file, 'w', encoding='utf-8') as f:
        json.dump(archive_data, f, ensure_ascii=False, indent=2)
    
    return archive_file


def cleanup_workflows(days_old: int = 30, status: Optional[str] = None, archive: bool = True, 
                     archive_dir: str = "archives", dry_run: bool = True) -> Tuple[int, List[str]]:
    """
    古いワークフローをクリーンアップする

    Args:
        days_old: 何日前より古いデータを対象とするか (デフォルト: 30日)
        status: 特定のステータスのワークフローのみ処理 (オプション)
        archive: アーカイブを作成するかどうか (デフォルト: True)
        archive_dir: アーカイブディレクトリのパス (デフォルト: "archives")
        dry_run: 実際の変更を行わない (デフォルト: True)

    Returns:
        (処理したワークフロー数, アーカイブファイルのパスのリスト)
    """
    archive_files = []
    processed_count = 0
    
    with session_scope() as db:
        # 古いワークフローを検索
        old_workflows = find_old_workflows(db, days_old, status)
        
        if not old_workflows:
            logger.info(f"{days_old}日以上前のワークフローはありません" + 
                       (f"（ステータス: {status}）" if status else ""))
            return 0, []
        
        logger.info(f"{len(old_workflows)}件の古いワークフローが見つかりました" +
                   (f"（ステータス: {status}）" if status else ""))
        
        if dry_run:
            logger.info("ドライラン: 実際の変更は行われません")
            for wf in old_workflows:
                logger.info(f"  {wf.id} (状態: {wf.status}, 更新: {wf.updated_at})")
            return len(old_workflows), []
    
        # 各ワークフローの処理
        for workflow in old_workflows:
            workflow_id = workflow.id
            
            try:
                # 関連データの取得
                agent_states = agent_state_repository.get_multi(db, filter_by={"workflow_id": workflow_id})
                results = audit_result_repository.get_by_workflow(db, workflow_id)
                
                # アーカイブの作成
                if archive:
                    archive_file = archive_workflow(workflow, agent_states, results, archive_dir)
                    archive_files.append(archive_file)
                    logger.info(f"ワークフロー {workflow_id} をアーカイブしました: {archive_file}")
                
                # 関連データの削除
                for result in results:
                    audit_result_repository.delete(db, id=result.id)
                
                for state in agent_states:
                    agent_state_repository.delete(db, id=state.id)
                
                # ワークフローの削除
                workflow_repository.delete(db, id=workflow_id)
                
                logger.info(f"ワークフロー {workflow_id} を削除しました")
                processed_count += 1
                
            except Exception as e:
                logger.error(f"ワークフロー {workflow_id} の処理中にエラーが発生しました: {e}")
                continue
    
    logger.info(f"合計 {processed_count} 件のワークフローを処理しました")
    return processed_count, archive_files


def main():
    """コマンドラインからの実行用のメイン関数"""
    parser = argparse.ArgumentParser(description='古いワークフローデータをクリーンアップします')
    parser.add_argument('--days', type=int, default=30, help='何日前より古いデータを対象とするか（デフォルト: 30日）')
    parser.add_argument('--status', type=str, help='特定のステータスのワークフローのみ処理（例: completed, failed）')
    parser.add_argument('--no-archive', action='store_false', dest='archive', help='アーカイブを作成せずに削除する')
    parser.add_argument('--archive-dir', type=str, default='archives', help='アーカイブディレクトリのパス（デフォルト: archives）')
    parser.add_argument('--execute', action='store_false', dest='dry_run', help='実際に変更を適用する（指定しない場合はドライラン）')
    
    args = parser.parse_args()
    
    cleanup_workflows(
        days_old=args.days,
        status=args.status,
        archive=args.archive,
        archive_dir=args.archive_dir,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main() 