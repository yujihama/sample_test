"""
APIリクエスト・レスポンスのためのPydanticモデル
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum

from src.models.schema import MessagePriority, HumanInteractionMessageType


class HumanInterventionRequestCreate(BaseModel):
    """人間監査人への介入要求作成リクエスト"""
    workflow_id: str = Field(..., description="関連するワークフローID")
    intervention_type: HumanInteractionMessageType = Field(..., description="介入のタイプ")
    title: str = Field(..., description="要求のタイトル")
    description: str = Field(..., description="詳細な説明")
    options: Optional[List[Dict[str, Any]]] = Field(None, description="選択肢（該当する場合）")
    context_data: Dict[str, Any] = Field(default_factory=dict, description="関連するコンテキストデータ")
    priority: MessagePriority = Field(default=MessagePriority.NORMAL, description="優先度")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "wf-12345",
                "intervention_type": "question",
                "title": "売掛金の回収可能性に関する質問",
                "description": "90日以上滞留している債権について、今後の回収見込みをご確認いただけますか？",
                "options": [
                    {"value": "high", "label": "回収見込み高"},
                    {"value": "medium", "label": "回収見込み中"},
                    {"value": "low", "label": "回収見込み低"}
                ],
                "context_data": {
                    "customer_id": "cust-789",
                    "invoice_amount": 150000,
                    "days_overdue": 95
                },
                "priority": "high"
            }
        }
    )


class HumanInterventionResponseCreate(BaseModel):
    """人間監査人からの介入応答作成リクエスト"""
    response_type: str = Field(..., description="応答タイプ（answer, clarification, rejection）")
    content: Dict[str, Any] = Field(..., description="応答内容")
    attachment_urls: Optional[List[str]] = Field(None, description="添付資料のURL（該当する場合）")
    comment: Optional[str] = Field(None, description="コメント")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "response_type": "answer",
                "content": {
                    "selected_option": "medium",
                    "additional_details": "顧客と支払いスケジュールについて協議中です"
                },
                "attachment_urls": ["https://example.com/payment_schedule.pdf"],
                "comment": "今後の対応として、月次で支払い状況を確認することを推奨します"
            }
        }
    )


class HumanInterventionListResponse(BaseModel):
    """人間監査人への介入要求一覧レスポンス"""
    interventions: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "interventions": [
                    {
                        "id": "int-12345",
                        "workflow_id": "wf-12345",
                        "intervention_type": "question",
                        "title": "売掛金の回収可能性に関する質問",
                        "priority": "high",
                        "created_at": "2023-05-10T11:20:00",
                        "status": "pending"
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 20
            }
        }
    )


class HumanInterventionDetailResponse(BaseModel):
    """人間監査人への介入要求詳細レスポンス"""
    id: str
    workflow_id: str
    requesting_agent: str
    intervention_type: str
    title: str
    description: str
    options: Optional[List[Dict[str, Any]]]
    context_data: Dict[str, Any]
    priority: str
    created_at: str
    status: str
    response: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "int-12345",
                "workflow_id": "wf-12345",
                "requesting_agent": "agent-a",
                "intervention_type": "question",
                "title": "売掛金の回収可能性に関する質問",
                "description": "90日以上滞留している債権について、今後の回収見込みをご確認いただけますか？",
                "options": [
                    {"value": "high", "label": "回収見込み高"},
                    {"value": "medium", "label": "回収見込み中"},
                    {"value": "low", "label": "回収見込み低"}
                ],
                "context_data": {
                    "customer_id": "cust-789",
                    "invoice_amount": 150000,
                    "days_overdue": 95
                },
                "priority": "high",
                "created_at": "2023-05-10T11:20:00",
                "status": "completed",
                "response": {
                    "id": "resp-12345",
                    "responder": "auditor-001",
                    "response_type": "answer",
                    "content": {
                        "selected_option": "medium",
                        "additional_details": "顧客と支払いスケジュールについて協議中です"
                    },
                    "comment": "今後の対応として、月次で支払い状況を確認することを推奨します",
                    "created_at": "2023-05-10T13:45:00"
                }
            }
        }
    )


class WorkflowStatusResponse(BaseModel):
    """ワークフローのステータス更新レスポンス"""
    workflow_id: str
    status: str
    message: str
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "wf-12345",
                "status": "resumed",
                "message": "ワークフローを再開しました。"
            }
        }
    ) 