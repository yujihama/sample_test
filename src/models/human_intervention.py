"""
人間介入モデルのサポートモジュール
このモジュールはdb_modelsからHumanInterventionRequestクラスをインポートし使用します
"""

from datetime import datetime
from .db_models import HumanInterventionRequest, HumanInterventionResponse

# HumanInterventionRequestの使用例
def create_intervention_request(db, workflow_id, description, request_type=None):
    """
    人間介入リクエストを作成するヘルパー関数
    
    Args:
        db: データベースセッション
        workflow_id: ワークフローID
        description: リクエストの説明
        request_type: リクエストタイプ（デフォルトはエラー解決）
        
    Returns:
        作成されたHumanInterventionRequestオブジェクト
    """
    request = HumanInterventionRequest(
        workflow_id=workflow_id,
        requesting_agent="system",
        intervention_type="error_resolution" if request_type is None else request_type,
        title="エラー発生 - 人間の介入が必要です",
        description=description,
        status="pending"
    )
    db.add(request)
    db.commit()
    return request

def get_pending_interventions(db, workflow_id):
    """
    ワークフローの未解決の介入リクエストを取得する
    
    Args:
        db: データベースセッション
        workflow_id: ワークフローID
        
    Returns:
        未解決の介入リクエストのリスト
    """
    return db.query(HumanInterventionRequest).filter(
        HumanInterventionRequest.workflow_id == workflow_id,
        HumanInterventionRequest.status == "pending"
    ).all()

def resolve_intervention(db, intervention_id, resolution):
    """
    介入リクエストを解決済みにする
    
    Args:
        db: データベースセッション
        intervention_id: 介入リクエストID
        resolution: 解決内容
        
    Returns:
        更新された介入リクエスト
    """
    intervention = db.query(HumanInterventionRequest).filter(
        HumanInterventionRequest.id == intervention_id
    ).first()
    
    if intervention:
        intervention.status = "resolved"
        intervention.resolution = resolution
        intervention.resolved_at = datetime.now()
        db.commit()
        
    return intervention 