import argparse
import asyncio
import os
import logging
from src.core.workflow import execute_workflow, create_audit_workflow, load_workflow_state

# 簡易ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """ワークフローのテスト実行"""
    parser = argparse.ArgumentParser(description='テスト監査ワークフロー実行')
    parser.add_argument('--workflow_id', type=str, help='実行するワークフローID')
    parser.add_argument('--sample_id', type=str, default='test-sample-id', help='サンプルデータID')
    
    args = parser.parse_args()
    
    if args.workflow_id:
        # 既存のワークフローを実行
        workflow_id = args.workflow_id
        print(f"Executing existing workflow: {workflow_id}")
        
        # ワークフロー状態を読み込み
        workflow_state = await load_workflow_state(workflow_id)
        
        if not workflow_state:
            print(f"Could not find workflow with ID: {workflow_id}")
            return
    else:
        # 新しいワークフローを作成
        workflow_id = f"test-{os.urandom(4).hex()}"
        print(f"Creating new workflow with ID: {workflow_id}")
        
        # テスト用の監査手続き
        procedure = {
            "id": "test-procedure-id",
            "text": "テスト監査手続き",
            "type": "standard"
        }
        
        # テスト用のサンプルデータ
        sample_id = args.sample_id
        
        # 監査ワークフロー作成API呼び出し
        creation_result = await create_audit_workflow(
            procedure_id=procedure["id"],
            procedure_text=procedure["text"],
            sample_id=sample_id,  # サンプルIDを明示的に渡す
            data_source="test"
        )
        
        if creation_result["status"] == "success":
            workflow_id = creation_result["workflow_id"]
            print(f"Workflow created: {workflow_id}")
            
            # ワークフロー状態を読み込み
            workflow_state = await load_workflow_state(workflow_id)
            
            if not workflow_state:
                print(f"Could not load state for workflow with ID: {workflow_id}")
                return
        else:
            print(f"Failed to create workflow: {creation_result.get('error')}")
            return
    
    print("Executing workflow...")
    
    # ワークフロー実行
    try:
        # ワークフロー状態を渡してワークフローを実行
        result = await execute_workflow(workflow_state)
        print(f"Workflow execution result: {result['status']}")
        
        if result["status"] == "error":
            print(f"Error: {result.get('error')}")
            
    except Exception as e:
        print(f"Error executing workflow: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 