from typing import Dict, Any
from fastapi import APIRouter, Path, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database.db_context import get_db_context
from src.repositories.workflow_repository import WorkflowRepository
from src.repositories.sample_batch_repository import SampleBatchRepository
from src.repositories.sample_repository import SampleRepository
from src.repositories.sample_result_repository import SampleResultRepository
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/{workflow_id}/batch-progress", response_model=Dict[str, Any])
async def get_batch_progress(
    workflow_id: str = Path(..., description="ワークフローID"),
    db: Session = Depends(get_db_context)
):
    """
    ワークフローに関連するバッチの進捗状況を取得する
    """
    try:
        # ワークフロー情報の取得
        workflow_repo = WorkflowRepository(db)
        workflow = workflow_repo.get_by_id(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"ワークフロー {workflow_id} が見つかりません")
        
        # ワークフローのターゲット情報を取得
        target_type = workflow.target_type if hasattr(workflow, 'target_type') else None
        target_id = workflow.target_id if hasattr(workflow, 'target_id') else None
        
        # バッチ処理のみ対応
        if not target_type or target_type != "batch":
            raise HTTPException(status_code=400, detail=f"このワークフローはバッチ処理ではありません")
        
        # バッチ情報の取得
        batch_repo = SampleBatchRepository(db)
        batch = batch_repo.get_by_id(target_id)
        if not batch:
            raise HTTPException(status_code=404, detail=f"バッチ {target_id} が見つかりません")
        
        # サンプル情報の取得
        sample_repo = SampleRepository(db)
        samples, total_samples = sample_repo.get_by_batch_id(
            batch_id=target_id,
            page=1,
            per_page=1000  # 十分大きな数
        )
        
        # サンプル結果の取得
        sample_result_repo = SampleResultRepository(db)
        sample_results = sample_result_repo.get_by_workflow_id(workflow_id)
        
        # サンプルIDによるマッピング
        results_by_sample = {sr.sample_id: sr for sr in sample_results}
        
        # 各ステータスの集計
        status_counts = {
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "error": 0,
            "canceled": 0
        }
        
        # 結果種別の集計
        result_counts = {
            "compliant": 0,
            "non_compliant": 0,
            "not_applicable": 0,
            "pending": 0
        }
        
        # サンプル進捗情報の構築
        sample_progress = []
        for sample in samples:
            # サンプルに対応する結果を取得
            sample_result = results_by_sample.get(sample.id)
            
            # ステータスと結果の決定
            status = "pending"  # デフォルト
            result = "pending"  # デフォルト
            completion_rate = 0.0
            findings = []
            
            if sample_result:
                status = sample_result.status
                result = sample_result.result if sample_result.result else "pending"
                completion_rate = 1.0 if status == "completed" else (0.5 if status == "processing" else 0.0)
                
                # 発見事項の抽出
                if sample_result.findings:
                    if isinstance(sample_result.findings, dict) and "finding_ids" in sample_result.findings:
                        findings = sample_result.findings["finding_ids"]
            
            # ステータスと結果の集計
            status_counts[status] = status_counts.get(status, 0) + 1
            result_counts[result] = result_counts.get(result, 0) + 1
            
            # サンプル進捗情報の追加
            sample_progress.append({
                "sample_id": sample.id,
                "name": sample.name,
                "status": status,
                "result": result,
                "completion_rate": completion_rate,
                "finding_count": len(findings),
                "findings": findings
            })
        
        # 全体の完了率計算
        overall_completion_rate = 0.0
        if total_samples > 0:
            completed_count = status_counts.get("completed", 0)
            processing_count = status_counts.get("processing", 0)
            overall_completion_rate = (completed_count + 0.5 * processing_count) / total_samples
        
        # ワークフローとバッチの詳細情報
        workflow_info = {
            "id": workflow.id,
            "status": workflow.status,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None
        }
        
        batch_info = {
            "id": batch.id,
            "name": batch.name,
            "created_at": batch.created_at.isoformat(),
            "sample_count": total_samples
        }
        
        # 最終レスポンスの構築
        response = {
            "workflow": workflow_info,
            "batch": batch_info,
            "overall_status": {
                "total_samples": total_samples,
                "completion_rate": overall_completion_rate,
                "status_breakdown": status_counts,
                "result_breakdown": result_counts
            },
            "sample_progress": sample_progress
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"バッチ進捗取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 