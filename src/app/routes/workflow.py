import time
import traceback
from fastapi import HTTPException
from src.api.models import WorkflowResponse, ExecuteWorkflowRequest
from src.utils import json_utils
from src.core import workflow as core_workflow

@router.post("/execute", response_model=WorkflowResponse)
async def execute_workflow(request: ExecuteWorkflowRequest) -> WorkflowResponse:
    """指定されたワークフローを実行します
    
    Args:
        request: ワークフロー実行リクエスト
        
    Returns:
        ワークフローの実行結果
    """
    try:
        logger.info(f"ワークフロー実行リクエストを受信: workflow_id={request.workflow_id}")
        
        # ワークフローの存在確認
        workflow = await get_workflow_by_id(request.workflow_id)
        if not workflow:
            logger.error(f"ワークフローが見つかりません: {request.workflow_id}")
            raise HTTPException(
                status_code=404,
                detail=f"ワークフローが見つかりません: {request.workflow_id}"
            )
        
        # リクエストパラメータを追加したワークフロー状態を作成
        workflow_state = workflow.to_dict()
        
        # リクエストからのパラメータがあれば追加（オプショナル）
        if request.parameters:
            logger.info(f"パラメータをワークフロー状態に追加: {request.parameters}")
            workflow_state.update(request.parameters)
        
        # ログ出力を強化
        logger.info(f"ワークフロー実行を開始します: {json_utils.json_serialize(workflow_state)}")
        
        # ワークフロー実行の開始時間を記録
        start_time = time.time()
        
        try:
            # ワークフロー実行
            updated_state = await core_workflow.execute_workflow(workflow_state)
            
            # 実行時間を計算
            execution_time = time.time() - start_time
            logger.info(f"ワークフロー実行が完了しました。実行時間: {execution_time:.2f}秒")
            
            # 実行結果を詳細にログ出力
            status = updated_state.get("status", "unknown")
            error = updated_state.get("error", None)
            
            if status == "error":
                logger.error(f"ワークフロー実行エラー: {error}")
                logger.error(f"エラー詳細: {json_utils.json_serialize(updated_state.get('error_details', {}))}")
            else:
                logger.info(f"ワークフロー実行成功: status={status}")
            
            # レスポンスの構築
            return WorkflowResponse(
                workflow_id=updated_state.get("workflow_id"),
                status=status,
                message="ワークフロー実行が完了しました",
                result=updated_state,
                execution_time=execution_time
            )
            
        except Exception as e:
            # 実行時間を計算
            execution_time = time.time() - start_time
            logger.error(f"ワークフロー実行中に例外が発生: {str(e)}")
            logger.error(traceback.format_exc())
            
            # エラーレスポンスの構築
            return WorkflowResponse(
                workflow_id=request.workflow_id,
                status="error",
                message=f"ワークフロー実行中にエラーが発生しました: {str(e)}",
                result={"error": str(e), "error_trace": traceback.format_exc()},
                execution_time=execution_time
            )
    
    except HTTPException as e:
        # FastAPIの例外はそのまま再送出
        raise e
    except Exception as e:
        # その他の例外
        logger.error(f"ワークフロー実行リクエスト処理中に予期しないエラーが発生: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"ワークフロー実行リクエスト処理中にエラーが発生しました: {str(e)}"
        ) 