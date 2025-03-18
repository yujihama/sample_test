"""
エージェントCのテストスクリプト
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

from src.agents.agent_c import AgentC
from src.utils.db_manager import init_db

# テスト結果のサンプルデータ
TEST_RESULTS = {
    "id": "exec-12345678",
    "plan_id": "plan-87654321",
    "execution_status": "completed",
    "results": [
        {
            "test_item_id": "test-001",
            "test_name": "承認状態のチェック",
            "result": "fail",
            "details": "テストステップ「承認者が空でないことを確認」: 1行が条件を満たしていません\nテストステップ「承認状態が「承認済」であることを確認」: 10行が条件を満たしていません\n不合格: 全ての経費申請が適切に承認されているが満たされていません",
            "affected_rows": [3, 4, 5, 6, 7, 8, 9],
            "exception_data": {
                "3": {"申請ID": "EXP004", "従業員ID": "EMP003", "日付": "2023-02-10", "金額": 8000, "カテゴリ": "交通費", "説明": "タクシー代", "承認者": None, "承認状態": "未承認"},
                "4": {"申請ID": "EXP005", "従業員ID": "EMP002", "日付": "2023-02-15", "金額": 25000, "カテゴリ": "宿泊費", "説明": "高級ホテル", "承認者": "MGR002", "承認状態": "承認済"}
            },
            "risk_addressed": "承認なしの経費申請"
        },
        {
            "test_item_id": "test-002",
            "test_name": "金額の上限チェック",
            "result": "fail",
            "details": "テストステップ「金額が20000以下であることを確認」: 3行が条件を満たしていません\n不合格: 全ての経費が上限以内が満たされていません",
            "affected_rows": [4, 8],
            "exception_data": {
                "4": {"申請ID": "EXP005", "従業員ID": "EMP002", "日付": "2023-02-15", "金額": 25000, "カテゴリ": "宿泊費", "説明": "高級ホテル", "承認者": "MGR002", "承認状態": "承認済"},
                "8": {"申請ID": "EXP009", "従業員ID": "EMP003", "日付": "2023-04-01", "金額": 30000, "カテゴリ": "宿泊費", "説明": "出張費", "承認者": "MGR002", "承認状態": "承認済"}
            },
            "risk_addressed": "上限額を超える申請"
        }
    ],
    "summary": {
        "total": 2,
        "pass": 0,
        "fail": 2,
        "warning": 0,
        "error": 0,
        "skipped": 0
    },
    "executed_at": "2025-03-15T12:34:56.789Z",
    "sample_id": "sample_test_001",
    "sample_metadata": {
        "row_count": 10,
        "column_count": 8,
        "columns": ["申請ID", "従業員ID", "日付", "金額", "カテゴリ", "説明", "承認者", "承認状態"]
    }
}

# テスト計画のサンプルデータ
TEST_PLAN = {
    "procedure_id": "proc_test_001",
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

# テスト実行関数
async def run_agent_c_test():
    print("エージェントCのテスト開始")
    
    # データベース初期化
    init_db()
    
    # エージェントCのインスタンス作成
    agent_c = AgentC()
    
    # テスト結果を処理するモックを作成
    with patch('src.utils.llm_utils.create_test_result_evaluator_prompt') as mock_evaluator:
        # モックの応答を設定
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value={
            "findings": [
                {
                    "id": "find-12345678",
                    "severity": "高",
                    "title": "未承認の経費申請が多数存在",
                    "description": "10件の経費申請のうち、承認されていない申請が7件あります。これは全体の70%に相当し、許容される閾値（5%）を大幅に超えています。",
                    "risk_impact": "高",
                    "risk_likelihood": "確実",
                    "recommendation": "経費承認プロセスの見直しと管理者への通知機能の強化が必要です。",
                    "affected_items": ["EXP004", "EXP005", "EXP006", "EXP007", "EXP008", "EXP009", "EXP010"],
                    "related_test": "test-001"
                },
                {
                    "id": "find-87654321",
                    "severity": "中",
                    "title": "上限を超える経費申請",
                    "description": "10件の経費申請のうち、上限（20,000円）を超える申請が2件あります。これは全体の20%に相当し、許容される閾値（10%）を超えています。",
                    "risk_impact": "中",
                    "risk_likelihood": "可能性あり",
                    "recommendation": "高額な経費申請には追加の承認ステップを設けるべきです。",
                    "affected_items": ["EXP005", "EXP009"],
                    "related_test": "test-002"
                }
            ],
            "conclusion": "経費申請プロセスに重大な問題が発見されました。未承認の申請が多数あり、また上限を超える申請も複数存在します。承認プロセスの改善と、高額申請に対する追加チェックの導入を推奨します。",
            "risk_assessment": {
                "overall_risk": "高",
                "financial_impact": "中",
                "regulatory_compliance": "高",
                "operational_efficiency": "中"
            },
            "additional_tests_required": True,
            "additional_test_areas": [
                "経費申請の承認者の権限検証",
                "高額経費の正当性確認"
            ]
        })
        mock_evaluator.return_value = mock_chain
        
        # テスト結果の処理テスト
        print("\n=== テスト結果の処理テスト ===")
        test_results_msg = {
            "results": TEST_RESULTS,
            "test_plan": TEST_PLAN,
            "workflow_id": "workflow_test_001"
        }
        
        # エージェントCにテスト結果を送信
        result = await agent_c.handle_test_results(test_results_msg)
        
        print(f"テスト結果処理ステータス: {result.get('status')}")
        
        if result.get('status') == 'success':
            # テスト結果の評価結果を表示
            summary = result.get('summary', {})
            
            print("\nテスト評価結果:")
            print(f"結論: {summary.get('conclusion')}")
            print(f"\n発見事項数: {len(summary.get('findings', []))}")
            
            # 発見事項の詳細を表示
            for i, finding in enumerate(summary.get('findings', []), 1):
                print(f"\n発見事項 {i}:")
                print(f"ID: {finding.get('id')}")
                print(f"タイトル: {finding.get('title')}")
                print(f"深刻度: {finding.get('severity')}")
                print(f"説明: {finding.get('description')}")
                print(f"リスク影響: {finding.get('risk_impact')}")
                print(f"推奨対応: {finding.get('recommendation')}")
            
            # リスク評価を表示
            risk = summary.get('risk_assessment', {})
            print(f"\nリスク評価:")
            print(f"全体リスク: {risk.get('overall_risk')}")
            print(f"財務的影響: {risk.get('financial_impact')}")
            print(f"規制遵守: {risk.get('regulatory_compliance')}")
            
            # 追加テスト情報を表示
            if summary.get('additional_tests_required'):
                print(f"\n追加テスト領域:")
                for area in summary.get('additional_test_areas', []):
                    print(f"- {area}")
        else:
            print(f"エラー: {result.get('error')}")
        
        # 質問処理のテスト
        print("\n=== 質問処理のテスト ===")
        question_msg = {
            "question": "テスト結果から最も深刻な問題は何ですか？",
            "from_agent": "agent-user"
        }
        
        # LLMの応答をモック
        with patch('src.agents.agent_c.get_llm') as mock_get_llm:
            mock_llm = MagicMock()
            mock_chain = MagicMock()
            mock_chain.ainvoke = AsyncMock(return_value=MagicMock(content="最も深刻な問題は未承認の経費申請が多数存在することです。これは会社の経費管理ポリシーに重大な違反であり、不正な経費申請のリスクを高めます。"))
            mock_llm.__or__.return_value = mock_chain
            mock_get_llm.return_value = mock_llm
            
            # エージェントCに質問を送信
            question_result = await agent_c.handle_question(question_msg)
            
            print(f"質問処理ステータス: {question_result.get('status')}")
            print(f"回答: {question_result.get('answer')}")
    
    print("\nエージェントCのテスト完了")

# メイン実行部分
if __name__ == "__main__":
    asyncio.run(run_agent_c_test()) 