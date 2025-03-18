"""
エージェントAのテストスクリプト
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

from src.agents.agent_a import AgentA
from src.utils.db_manager import init_db
from src.utils.llm_utils import LLMProcessor

# テスト用監査手続きテキスト
TEST_PROCEDURE_TEXT = """
内部監査手続き: 経費申請の適正性監査

目的:
従業員の経費申請プロセスが会社のポリシーに準拠しているか検証し、不正や誤りを特定する。

範囲:
2023年1月1日から2023年12月31日までの全従業員の経費申請を対象とする。

リスク領域:
1. 承認なしの経費申請
2. 上限額を超える申請
3. 重複申請
4. 不適切な経費カテゴリ
5. 必要な証憑書類の欠如

検証ポイント:
1. 全ての経費申請に適切な承認者の承認があるか
2. 経費カテゴリごとの上限金額を超えていないか
3. 同一の経費が複数回申請されていないか
4. 各経費申請に必要な証憑が添付されているか
5. 経費申請と証憑の金額が一致しているか

必要データ:
1. 経費申請データ（申請ID、従業員ID、日付、金額、カテゴリ、説明、承認者、承認状態）
2. 証憑データ（証憑ID、申請ID、金額、日付）
3. 経費カテゴリマスタ（カテゴリID、名称、上限金額）
"""

# モック応答
MOCK_PROCEDURE_UNDERSTANDING = {
    "title": "経費申請の適正性監査",
    "description": "従業員の経費申請プロセスが会社のポリシーに準拠しているか検証し、不正や誤りを特定する監査手続き",
    "objectives": [
        "経費申請プロセスの適正性確認",
        "不正や誤りの特定",
        "ポリシー遵守の確認"
    ],
    "scope": "2023年1月1日から2023年12月31日までの全従業員の経費申請",
    "key_risks": [
        "承認なしの経費申請",
        "上限額を超える申請",
        "重複申請",
        "不適切な経費カテゴリ",
        "必要な証憑書類の欠如"
    ],
    "verification_points": [
        "全ての経費申請に適切な承認者の承認があるか",
        "経費カテゴリごとの上限金額を超えていないか",
        "同一の経費が複数回申請されていないか",
        "各経費申請に必要な証憑が添付されているか",
        "経費申請と証憑の金額が一致しているか"
    ],
    "required_data_fields": [
        "経費申請データ（申請ID、従業員ID、日付、金額、カテゴリ、説明、承認者、承認状態）",
        "証憑データ（証憑ID、申請ID、金額、日付）",
        "経費カテゴリマスタ（カテゴリID、名称、上限金額）"
    ],
    "test_approach": "サンプリング検査とデータ分析を組み合わせて実施"
}

MOCK_TEST_PLAN = {
    "test_items": [
        {
            "id": "item-001",
            "name": "経費申請の承認状況テスト",
            "description": "全ての経費申請に適切な承認者の承認があるかを検証",
            "objective": "承認プロセスの適正性確認",
            "risk_addressed": "承認なしの経費申請",
            "test_steps": [
                "全ての経費申請レコードを抽出",
                "承認者が空白または未承認状態のレコードを特定",
                "会社ポリシーに基づく承認要件との整合性を確認"
            ],
            "expected_results": "全ての経費申請が適切に承認されている",
            "pass_criteria": "未承認または承認者の無い申請が全体の5%未満"
        },
        {
            "id": "item-002",
            "name": "経費金額上限テスト",
            "description": "カテゴリごとの上限金額を超える申請がないかを検証",
            "objective": "経費金額の適正性確認",
            "risk_addressed": "上限額を超える申請",
            "test_steps": [
                "カテゴリごとの上限金額を確認",
                "各経費申請をカテゴリごとに集計",
                "上限を超える申請を特定"
            ],
            "expected_results": "経費はカテゴリごとの上限を超えていない",
            "pass_criteria": "上限超過申請が全体の3%未満"
        }
    ],
    "additional_notes": "検出された例外については、個別に調査を実施すること"
}

# モックLLMProcessor
class MockLLMProcessor:
    async def process_json_prompt(self, prompt_id, input_vars):
        if prompt_id == "audit_procedure_understanding":
            return MOCK_PROCEDURE_UNDERSTANDING
        elif prompt_id == "test_plan_generation":
            return MOCK_TEST_PLAN
        else:
            return {"error": "Unknown prompt"}

# テスト実行関数
async def run_agent_a_test():
    print("エージェントAのテスト開始")
    
    # データベース初期化
    init_db()
    
    # エージェントAのインスタンス作成
    agent_a = AgentA()
    
    # 監査手続き解析のテスト
    print("\n=== 監査手続き解析のテスト ===")
    
    # モックの応答を直接使用
    understanding = MOCK_PROCEDURE_UNDERSTANDING
    print("監査手続き解析結果:")
    pprint(understanding)
    
    # サンプルCSVファイルの作成（テスト用）
    test_data_dir = Path(project_root) / "tests" / "data"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    sample_file_path = test_data_dir / "test_expense.csv"
    
    # テスト用CSVファイルがなければ作成
    if not sample_file_path.exists():
        with open(sample_file_path, "w", encoding="utf-8") as f:
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
        print(f"テスト用CSVファイルを作成しました: {sample_file_path}")
    
    # サンプルデータの登録（テスト用にサンプルデータレコードを作成）
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
                "filename": sample_file_path.name,
                "file_path": str(sample_file_path),
                "content_type": "text/csv",
                "file_metadata": {"original_filename": sample_file_path.name}
            })
            print(f"テスト用サンプルデータを作成しました: {sample_id}")
        else:
            print(f"テスト用サンプルデータが既に存在します: {sample_id}")
            sample = existing_sample
    
        # サンプルデータ解析のテスト
        print("\n=== サンプルデータ解析のテスト ===")
        sample_analysis = await agent_a.analyze_sample_data(sample_id)
        
        if "error" in sample_analysis:
            print(f"エラー: {sample_analysis['error']}")
        else:
            print("サンプルデータ解析結果:")
            print(f"行数: {sample_analysis.get('row_count')}")
            print(f"列数: {sample_analysis.get('column_count')}")
            print(f"データ品質: {sample_analysis.get('data_quality', {}).get('overall_quality')}")
            
            if "data_quality" in sample_analysis and "issues" in sample_analysis["data_quality"]:
                print("\nデータ品質の問題:")
                for issue in sample_analysis["data_quality"]["issues"]:
                    print(f"- {issue.get('description')} (重要度: {issue.get('severity')})")
    
        # テスト計画生成のテスト
        print("\n=== テスト計画生成のテスト ===")
        
        # モックの応答を直接使用
        test_plan = MOCK_TEST_PLAN
        print("テスト計画生成結果:")
        print(f"テスト項目数: {len(test_plan.get('test_items', []))}")
        
        if "test_items" in test_plan and len(test_plan["test_items"]) > 0:
            print("\n最初のテスト項目:")
            first_item = test_plan["test_items"][0]
            print(f"ID: {first_item.get('id')}")
            print(f"名称: {first_item.get('name')}")
            print(f"説明: {first_item.get('description')}")
    
    except Exception as e:
        print(f"テスト実行中にエラーが発生しました: {e}")
    
    print("\nエージェントAのテスト完了")

# メイン実行部分
if __name__ == "__main__":
    asyncio.run(run_agent_a_test()) 