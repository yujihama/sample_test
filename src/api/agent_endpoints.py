"""
エージェント間メッセージングAPI

このモジュールは、エージェント間のメッセージングを管理するAPIエンドポイントを提供します。
各エージェントはこれらのエンドポイントを使用して、他のエージェントとの通信やツールの実行を行います。
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Body
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import json
from src.utils import json_utils
import uuid
from datetime import datetime
import asyncio
import logging
from sqlalchemy.orm import Session

from src.utils.db_manager import get_db
from src.models.repositories import agent_state_repository, message_repository
from src.tools.tool_registry import registry

router = APIRouter(prefix="/agents", tags=["agents"])
logger = logging.getLogger(__name__)

# モデル定義
class MessageRequest(BaseModel):
    """エージェント間メッセージ送信リクエスト"""
    from_agent: str = Field(..., description="送信元エージェントID")
    to_agent: str = Field(..., description="宛先エージェントID")
    message_type: str = Field(..., description="メッセージタイプ(instruction, response, question, etc)")
    content: Dict[str, Any] = Field(..., description="メッセージ内容")
    workflow_id: Optional[str] = Field(None, description="ワークフローID（省略可能）")

class MessageResponse(BaseModel):
    """メッセージ応答"""
    message_id: str
    status: str
    timestamp: str

class ToolRequest(BaseModel):
    """ツール実行リクエスト"""
    tool_name: str = Field(..., description="実行するツール名")
    operation: str = Field(..., description="実行する操作")
    parameters: Dict[str, Any] = Field(..., description="ツールパラメータ")
    requesting_agent: str = Field(..., description="リクエスト元エージェントID")
    workflow_id: Optional[str] = Field(None, description="ワークフローID（省略可能）")

class ToolResponse(BaseModel):
    """ツール実行応答"""
    request_id: str
    tool_name: str
    operation: str
    status: str
    result: Dict[str, Any]
    error: Optional[str] = None
    execution_time: float

# エンドポイント定義
@router.post("/messages", response_model=MessageResponse)
async def send_message(
    message: MessageRequest,
    db: Session = Depends(get_db)
):
    """
    エージェント間でメッセージを送信する
    """
    try:
        message_id = f"msg-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now().isoformat()
        
        # メッセージをデータベースに保存
        message_data = {
            "id": message_id,
            "from_agent": message.from_agent,
            "to_agent": message.to_agent,
            "message_type": message.message_type,
            "content": json_utils.json_serialize(message.content),
            "workflow_id": message.workflow_id,
            "created_at": datetime.now(),
            "status": "sent"
        }
        
        message_repository.create(db, message_data)
        
        # エージェントの状態を更新
        if message.workflow_id:
            try:
                # 送信元エージェントの状態更新
                from_agent_state = agent_state_repository.find_by_workflow_agent(
                    db, message.workflow_id, message.from_agent
                )
                
                if from_agent_state:
                    agent_state_repository.update(db, from_agent_state.id, {
                        "last_message_sent": message_id,
                        "updated_at": datetime.now()
                    })
                    
                # 宛先エージェントの状態更新
                to_agent_state = agent_state_repository.find_by_workflow_agent(
                    db, message.workflow_id, message.to_agent
                )
                
                if to_agent_state:
                    agent_state_repository.update(db, to_agent_state.id, {
                        "new_messages": True,
                        "last_message_received": message_id,
                        "updated_at": datetime.now()
                    })
            except Exception as e:
                logger.warning(f"エージェント状態の更新中にエラーが発生: {e}")
        
        return {
            "message_id": message_id,
            "status": "sent",
            "timestamp": timestamp
        }
    
    except Exception as e:
        logger.error(f"メッセージ送信中にエラーが発生: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"メッセージ送信に失敗しました: {str(e)}"
        )

@router.get("/messages/{agent_id}", response_model=List[Dict[str, Any]])
async def get_messages(
    agent_id: str,
    workflow_id: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    特定のエージェント宛のメッセージを取得する
    """
    try:
        # エージェント宛のメッセージを検索
        filters = {"to_agent": agent_id}
        if workflow_id:
            filters["workflow_id"] = workflow_id
            
        messages = message_repository.find_all(
            db, 
            filters=filters,
            limit=limit,
            offset=offset,
            order_by={"created_at": "desc"}
        )
        
        # メッセージを整形
        formatted_messages = []
        for msg in messages:
            try:
                content = json_utils.json_deserialize(msg.content) if msg.content else {}
            except json.JSONDecodeError:
                content = {"raw_content": msg.content}
                
            formatted_messages.append({
                "id": msg.id,
                "from_agent": msg.from_agent,
                "to_agent": msg.to_agent,
                "message_type": msg.message_type,
                "content": content,
                "workflow_id": msg.workflow_id,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "status": msg.status
            })
            
        return formatted_messages
        
    except Exception as e:
        logger.error(f"メッセージ取得中にエラーが発生: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"メッセージ取得に失敗しました: {str(e)}"
        )

@router.post("/tools/execute", response_model=ToolResponse)
async def execute_tool(
    tool_request: ToolRequest,
    db: Session = Depends(get_db)
):
    """
    ツールを実行する
    """
    import time
    
    start_time = time.time()
    request_id = f"tool-{uuid.uuid4().hex[:8]}"
    
    try:
        # ツールの存在確認
        tool = registry.get_tool(tool_request.tool_name)
        if not tool:
            raise HTTPException(
                status_code=404,
                detail=f"ツール '{tool_request.tool_name}' が見つかりません"
            )
            
        # ツールの実行
        parameters = tool_request.parameters
        operation = tool_request.operation
        
        # パラメータに操作名を追加
        if "operation" not in parameters:
            parameters["operation"] = operation
            
        # ツールの非同期実行
        try:
            result = await tool.execute(parameters)
            
            # 実行時間の計算
            execution_time = time.time() - start_time
            
            # レスポンスの作成
            response = {
                "request_id": request_id,
                "tool_name": tool_request.tool_name,
                "operation": operation,
                "status": result.status,
                "result": result.data,
                "error": result.error,
                "execution_time": execution_time
            }
            
            # ツール実行ログを記録（オプション）
            if tool_request.workflow_id:
                # ここにログ記録コードを追加
                pass
                
            return response
            
        except Exception as e:
            # 実行時間の計算
            execution_time = time.time() - start_time
            
            logger.error(f"ツール実行中にエラーが発生: {e}")
            return {
                "request_id": request_id,
                "tool_name": tool_request.tool_name,
                "operation": operation,
                "status": "error",
                "result": {},
                "error": str(e),
                "execution_time": execution_time
            }
    
    except HTTPException as e:
        # FastAPIの例外はそのまま再度発生させる
        raise
        
    except Exception as e:
        logger.error(f"ツールリクエスト処理中にエラーが発生: {e}")
        
        # 実行時間の計算
        execution_time = time.time() - start_time
        
        return {
            "request_id": request_id,
            "tool_name": tool_request.tool_name,
            "operation": tool_request.operation,
            "status": "error",
            "result": {},
            "error": f"ツール実行中にエラーが発生: {str(e)}",
            "execution_time": execution_time
        } 