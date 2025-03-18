"""
規程情報管理API

このモジュールでは、規程情報の管理に関するAPIエンドポイントを定義します。
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from src.utils.db_manager import get_db_session
from src.services.regulation_service import RegulationService
from src.models.schema import (
    RegulationCreate, RegulationUpdate, RegulationResponse,
    RegulationSearchQuery, RegulationSearchResponse,
    RegulationDecisionReferenceCreate, RegulationDecisionReferenceResponse
)

router = APIRouter(
    prefix="/regulations",
    tags=["規程情報管理"],
    responses={404: {"description": "Not found"}},
)


def get_regulation_service(db_session: AsyncSession = Depends(get_db_session)) -> RegulationService:
    """
    規程情報サービスの依存性注入
    
    Args:
        db_session (AsyncSession, optional): データベースセッション
        
    Returns:
        RegulationService: 規程情報サービス
    """
    return RegulationService(db_session)


@router.post("", response_model=RegulationResponse)
async def create_regulation(
    regulation_data: RegulationCreate,
    actor: str = Query(..., description="作成者ID（エージェントまたはユーザー）"),
    service: RegulationService = Depends(get_regulation_service)
):
    """
    規程情報を作成する
    
    Args:
        regulation_data (RegulationCreate): 規程情報作成データ
        actor (str): 作成者ID
        service (RegulationService): 規程情報サービス
        
    Returns:
        RegulationResponse: 作成された規程情報
    """
    try:
        result = await service.create_regulation(regulation_data, actor)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"規程情報の作成中にエラーが発生しました: {str(e)}")


@router.get("/{regulation_id}", response_model=RegulationResponse)
async def get_regulation(
    regulation_id: str = Path(..., description="規程ID"),
    actor: str = Query(..., description="参照者ID（エージェントまたはユーザー）"),
    service: RegulationService = Depends(get_regulation_service)
):
    """
    規程情報を取得する
    
    Args:
        regulation_id (str): 規程ID
        actor (str): 参照者ID
        service (RegulationService): 規程情報サービス
        
    Returns:
        RegulationResponse: 規程情報
    """
    result = await service.get_regulation(regulation_id, actor)
    if not result:
        raise HTTPException(status_code=404, detail=f"規程ID '{regulation_id}' は見つかりません")
    return result


@router.get("/code/{code}", response_model=RegulationResponse)
async def get_regulation_by_code(
    code: str = Path(..., description="規程コード"),
    actor: str = Query(..., description="参照者ID（エージェントまたはユーザー）"),
    service: RegulationService = Depends(get_regulation_service)
):
    """
    コードで規程情報を取得する
    
    Args:
        code (str): 規程コード
        actor (str): 参照者ID
        service (RegulationService): 規程情報サービス
        
    Returns:
        RegulationResponse: 規程情報
    """
    result = await service.get_regulation_by_code(code, actor)
    if not result:
        raise HTTPException(status_code=404, detail=f"規程コード '{code}' は見つかりません")
    return result


@router.put("/{regulation_id}", response_model=RegulationResponse)
async def update_regulation(
    regulation_id: str = Path(..., description="規程ID"),
    update_data: RegulationUpdate = Body(..., description="更新データ"),
    actor: str = Query(..., description="更新者ID（エージェントまたはユーザー）"),
    service: RegulationService = Depends(get_regulation_service)
):
    """
    規程情報を更新する
    
    Args:
        regulation_id (str): 規程ID
        update_data (RegulationUpdate): 更新データ
        actor (str): 更新者ID
        service (RegulationService): 規程情報サービス
        
    Returns:
        RegulationResponse: 更新された規程情報
    """
    try:
        result = await service.update_regulation(regulation_id, update_data, actor)
        if not result:
            raise HTTPException(status_code=404, detail=f"規程ID '{regulation_id}' は見つかりません")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"規程情報の更新中にエラーが発生しました: {str(e)}")


@router.delete("/{regulation_id}")
async def delete_regulation(
    regulation_id: str = Path(..., description="規程ID"),
    actor: str = Query(..., description="削除者ID（エージェントまたはユーザー）"),
    service: RegulationService = Depends(get_regulation_service)
):
    """
    規程情報を削除する
    
    Args:
        regulation_id (str): 規程ID
        actor (str): 削除者ID
        service (RegulationService): 規程情報サービス
        
    Returns:
        Dict[str, Any]: 削除結果
    """
    try:
        result = await service.delete_regulation(regulation_id, actor)
        if not result:
            raise HTTPException(status_code=404, detail=f"規程ID '{regulation_id}' は見つかりません")
        return {"success": True, "message": f"規程ID '{regulation_id}' が正常に削除されました"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"規程情報の削除中にエラーが発生しました: {str(e)}")


@router.post("/search", response_model=RegulationSearchResponse)
async def search_regulations(
    search_query: RegulationSearchQuery,
    actor: str = Query(..., description="検索者ID（エージェントまたはユーザー）"),
    workflow_id: Optional[str] = Query(None, description="関連するワークフローID（任意）"),
    service: RegulationService = Depends(get_regulation_service)
):
    """
    規程情報を検索する
    
    Args:
        search_query (RegulationSearchQuery): 検索クエリ
        actor (str): 検索者ID
        workflow_id (Optional[str], optional): 関連するワークフローID
        service (RegulationService): 規程情報サービス
        
    Returns:
        RegulationSearchResponse: 検索結果
    """
    try:
        result = await service.search_regulations(search_query, actor, workflow_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"規程情報の検索中にエラーが発生しました: {str(e)}")


@router.post("/decision-references", response_model=Dict[str, Any])
async def create_decision_reference(
    reference_data: RegulationDecisionReferenceCreate,
    actor: str = Query(..., description="作成者ID（エージェントまたはユーザー）"),
    service: RegulationService = Depends(get_regulation_service)
):
    """
    規程に基づく判断参照を作成する
    
    Args:
        reference_data (RegulationDecisionReferenceCreate): 判断参照データ
        actor (str): 作成者ID
        service (RegulationService): 規程情報サービス
        
    Returns:
        Dict[str, Any]: 作成結果
    """
    try:
        result = await service.create_decision_reference(reference_data, actor)
        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("error", "判断参照の作成に失敗しました"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"判断参照の作成中にエラーが発生しました: {str(e)}")


@router.get("/workflow/{workflow_id}/decision-references", response_model=List[Dict[str, Any]])
async def get_workflow_decision_references(
    workflow_id: str = Path(..., description="ワークフローID"),
    service: RegulationService = Depends(get_regulation_service)
):
    """
    ワークフローに関連する判断参照を取得する
    
    Args:
        workflow_id (str): ワークフローID
        service (RegulationService): 規程情報サービス
        
    Returns:
        List[Dict[str, Any]]: 判断参照のリスト
    """
    try:
        result = await service.get_workflow_decision_references(workflow_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"判断参照の取得中にエラーが発生しました: {str(e)}") 