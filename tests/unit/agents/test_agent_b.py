"""
エージェントBのテストスクリプト
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from pprint import pprint
from unittest.mock import patch, AsyncMock, MagicMock

# プロジェクトルートを追加
project_root = Path(__file__).parents[2].absolute()
sys.path.append(str(project_root))

from src.agents.agent_b import AgentB
from src.agents.agent_a import AgentA
from src.utils.db_manager import init_db
from src.utils.data_utils import load_sample_data

# テスト用サンプルデータファイルのパス
TEST_DATA_PATH = Path(project_root) / "tests" / "data" / "test_expense.csv"

# テスト用テストプラン
TEST_PLAN = {
    "test_items": [
        {
            "id": "test-001",
            "name": "承認状態のチェック",
            "description": "全ての経費申請に承認者が設定されていることを確認",
            "objective": "未承認の申請を検出",
            "risk_addressed": "承認なしの経費申請",
            "test_steps": [
                "承認者が空でないことを確認",
                "承認状態が「承認済」であることを確認"
            ],
            "expected_results": "全ての経費申請が適切に承認されている",
            "pass_criteria": "未承認または承認者の無い申請が全体の5%未満"
        },
        {
            "id": "test-002",
            "name": "金額の上限チェック",
            "description": "経費の金額が上限（20000円）を超えていないことを確認",
            "objective": "高額な経費申請を検出",
            "risk_addressed": "上限額を超える申請",
            "test_steps": [
                "金額が20000以下であることを確認"
            ],
            "expected_results": "全ての経費が上限以内",
            "pass_criteria": "上限超過が全体の10%未満"
        }
    ],
    "additional_notes": "テスト用サンプルデータの検証"
}

# サンプルCSVファイルの作成（テスト用）
def create_test_data_file():
    # テスト用ディレクトリを作成
    test_data_dir = Path(project_root) / "tests" / "data"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # テスト用CSVファイルが既に存在する場合はスキップ
    if TEST_DATA_PATH.exists():
        print(f"テスト用CSVファイルが既に存在します: {TEST_DATA_PATH}")
        return
    
    # テスト用CSVファイルを作成
    with open(TEST_DATA_PATH, "w", encoding="utf-8") as f:
        f.write("申請ID,従業員ID,日付,金額,カテゴリ,説明,承認者,承認状態\n")
        f.write("EXP001,EMP001,2023-01-15,5000,交通費,タクシー代,MGR001,承認済\n")
        f.write("EXP002,EMP002,2023-01-20,12000,宿泊費,ホテル代,MGR002,承認済\n")
        f.write("EXP003,EMP001,2023-02-01,3000,食費,接待費,MGR001,承認済\n")
        f.write("EXP004,EMP003,2023-02-10,8000,交通費,タクシー代,,未承認\n")
        f.write("EXP005,EMP002,2023-02-15,25000,宿泊費,高級ホテル,MGR002,承認済\n")
        f.write("EXP006,EMP004,2023-03-01,5000,食費,接待費,MGR003,承認済\n")
        f.write("EXP007,EMP001,2023-03-10,5000,交通費,タクシー代,MGR001,承認済\n")
        f.write("EXP008,EMP005,2023-03-15,15000,その他,備品購入,MGR004,承認済\n")
        f.write("EXP009,EMP003,2023-04-01,30000,宿泊費,出張費,MGR002,承認済\n")
        f.write("EXP010,EMP002,2023-04-10,,食費,接待費,MGR001,承認済\n")
    
    print(f"テスト用CSVファイルを作成しました: {TEST_DATA_PATH}")

# テスト実行関数
async def run_agent_b_test():
    print("エージェントBのテスト開始")
    
    # テスト用データファイルの作成
    create_test_data_file()
    
    # データベース初期化
    init_db()
    
    # エージェントBのインスタンス作成
    agent_b = AgentB()
    
    # サンプルデータの登録（データベースに登録されているか確認）
    try:
        from src.models.repositories import SampleDataRepository
        from src.utils.db_manager import get_db
        
        db = next(get_db())
        sample_repo = SampleDataRepository()
        
        sample_id = "sample_test_001"
        existing_sample = sample_repo.get(db, sample_id)
        
        if not existing_sample:
            sample = sample_repo.create(db, {
                "id": sample_id,
                "procedure_id": "proc_test_001",
                "filename": TEST_DATA_PATH.name,
                "file_path": str(TEST_DATA_PATH),
                "content_type": "text/csv",
                "file_metadata": {"original_filename": TEST_DATA_PATH.name}
            })
            print(f"テスト用サンプルデータを作成しました: {sample_id}")
        else:
            print(f"テスト用サンプルデータが既に存在します: {sample_id}")
            sample = existing_sample
    except Exception as e:
        print(f"サンプルデータの登録中にエラー: {e}")
        sample_id = "sample_test_001"  # エラーが発生してもテストは続行
    
    # テスト計画の処理テスト
    print("\n=== テスト計画の処理テスト ===")
    test_plan_result = await agent_b.handle_test_plan({
        "test_plan": TEST_PLAN,
        "procedure_id": "proc_test_001",
        "sample_id": sample_id,
        "workflow_id": "workflow_test_001"
    })
    
    print(f"テスト計画処理結果: {test_plan_result.get('status')}")
    print(f"メッセージ: {test_plan_result.get('message')}")
    print(f"テスト計画ID: {test_plan_result.get('test_plan_id')}")
    
    if test_plan_result.get('status') != 'success':
        print(f"エラー: {test_plan_result.get('error')}")
        return
    
    # テスト実行テスト
    print("\n=== テスト実行テスト ===")
    execution_result = await agent_b.handle_execute_test({
        "sample_path": str(TEST_DATA_PATH),
        "sample_id": sample_id
    })
    
    print(f"テスト実行結果: {execution_result.get('status')}")
    
    if execution_result.get('status') == 'success':
        print(f"メッセージ: {execution_result.get('message')}")
        
        # テスト結果の詳細を表示
        if 'test_results' in execution_result:
            results = execution_result['test_results']
            summary = results.get('summary', {})
            
            print(f"\nテスト結果サマリー:")
            print(f"合格: {summary.get('pass', 0)}")
            print(f"失敗: {summary.get('fail', 0)}")
            print(f"エラー: {summary.get('error', 0)}")
            print(f"スキップ: {summary.get('skipped', 0)}")
            
            print(f"\n各テスト項目の結果:")
            for i, result in enumerate(results.get('results', []), 1):
                print(f"\nテスト項目 {i}:")
                print(f"ID: {result.get('test_item_id')}")
                print(f"名前: {result.get('test_name')}")
                print(f"結果: {result.get('result')}")
                print(f"詳細: {result.get('details')}")
                print(f"影響行数: {len(result.get('affected_rows', []))}")
    else:
        print(f"エラー: {execution_result.get('error')}")
    
    print("\nエージェントBのテスト完了")

# メイン実行部分
if __name__ == "__main__":
    asyncio.run(run_agent_b_test()) 