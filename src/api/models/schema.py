from typing import Any, Dict, Optional
from datetime import datetime
from pydantic import BaseModel

class WorkflowResponse(BaseModel):
    """ワークフロー応答モデル"""
    workflow_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    context_id: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    debug_info: Optional[Dict[str, Any]] = None 