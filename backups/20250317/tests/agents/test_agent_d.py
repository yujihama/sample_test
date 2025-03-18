"""
エージェントDのテストスクリプト
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

from src.agents.agent_d import AgentD
from src.utils.db_manager import init_db

# 監査総括のサンプルデータ
AUDIT_SUMMARY = {
    "id": "summary-12345678",
    "procedure_id": "proc_test_001",
    "execution_id": "exec-87654321",
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
    ],
    "created_at": "2025-03-15T12:34:56.789Z"
}

# 監査手続きのサンプルテキスト
PROCEDURE_TEXT = """
監査手続き: 経費申請プロセスの検証

目的:
従業員の経費申請が会社のポリシーに従って適切に処理されているかを検証する。

範囲:
2023年度の全従業員経費申請

リスク:
1. 承認なしの経費申請
2. 上限を超える経費申請
3. 不適切なカテゴリでの申請
4. 重複申請

検証項目:
1. 全ての経費申請に適切な承認があること
2. 経費申請額が規定の上限（20,000円）を超えていないこと
3. 経費カテゴリが正しく選択されていること
4. 同一内容の重複申請がないこと

データ要件:
申請ID、従業員ID、日付、金額、カテゴリ、説明、承認者、承認状態
"""

# テスト実行関数
async def run_agent_d_test():
    print("エージェントDのテスト開始")
    
    # データベース初期化
    init_db()
    
    # エージェントDのインスタンス作成
    agent_d = AgentD()
    
    # 監査報告書を生成するモックを作成
    with patch('src.utils.llm_utils.create_audit_report_generator_prompt') as mock_generator:
        # モックの応答を設定
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value={
            "title": "経費申請プロセスの内部監査報告書",
            "executive_summary": "本監査では、経費申請プロセスにおいて重大な問題が発見されました。未承認の申請が多数存在し、上限を超える申請も複数確認されました。経費承認プロセスの改善と高額申請に対する追加チェックの導入が必要です。",
            "background": "本監査は、社内の経費申請プロセスが適切に運用されているかを検証するために実施されました。特に、承認プロセスと金額上限の遵守状況に焦点を当てています。",
            "findings_detail": "監査の結果、以下の重大な問題が発見されました：\n\n1. **未承認の経費申請が多数存在**: 10件の経費申請のうち、承認されていない申請が7件（70%）ありました。これは許容閾値（5%）を大幅に超えています。\n\n2. **上限を超える経費申請**: 10件の経費申請のうち、上限（20,000円）を超える申請が2件（20%）ありました。これも許容閾値（10%）を超えています。\n\nこれらの問題は、経費管理の内部統制が適切に機能していないことを示しています。",
            "recommendations": "以下の改善策を推奨します：\n\n1. **経費承認プロセスの見直し**: 承認フローを明確化し、承認漏れを防止するシステムの導入。\n\n2. **管理者への通知機能の強化**: 未承認の経費申請が一定期間残っている場合、管理者に自動通知する仕組みの実装。\n\n3. **高額経費申請の追加承認ステップ**: 一定金額を超える申請には、部門長だけでなく財務部門の承認も必要とする二重承認プロセスの導入。\n\n4. **経費ポリシーの再教育**: 全従業員に対する経費申請ポリシーの再教育と定期的なリマインダーの送信。",
            "conclusion": "経費申請プロセスには重大な欠陥があり、不正や誤用のリスクが高い状態です。推奨された改善策を早急に実施し、内部統制を強化することが必要です。また、3ヶ月後に追加監査を実施して、改善状況を確認することを推奨します。",
            "appendices": [
                "経費申請ポリシー文書",
                "サンプルデータ分析結果の詳細",
                "部門別の違反率分析"
            ]
        })
        mock_generator.return_value = mock_chain
        
        # 監査総括の処理テスト
        print("\n=== 監査総括の処理テスト ===")
        audit_summary_msg = {
            "summary": AUDIT_SUMMARY,
            "procedure_text": PROCEDURE_TEXT,
            "workflow_id": "workflow_test_001"
        }
        
        # エージェントDに監査総括を送信
        result = await agent_d.handle_audit_summary(audit_summary_msg)
        
        print(f"監査総括処理ステータス: {result.get('status')}")
        
        if result.get('status') == 'success':
            # 監査報告書の内容を表示
            report = result.get('report', {})
            
            print("\n監査報告書:")
            print(f"タイトル: {report.get('title')}")
            print(f"エグゼクティブサマリー: {report.get('executive_summary')[:100]}...")
            
            # 報告書の保存先を表示
            report_path = result.get('report_path')
            if report_path:
                print(f"\n報告書の保存先: {report_path}")
                
                # ファイルが存在するか確認
                if os.path.exists(report_path):
                    print("報告書ファイルが正常に作成されました")
                    
                    # ファイルの内容を表示（最初の数行）
                    with open(report_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()[:10]
                        print("\n報告書の冒頭:")
                        for line in lines:
                            print(line.strip())
        else:
            print(f"エラー: {result.get('error')}")
        
        # 質問処理のテスト
        print("\n=== 質問処理のテスト ===")
        question_msg = {
            "question": "監査報告書の主な推奨事項は何ですか？",
            "from_agent": "agent-user"
        }
        
        # LLMの応答をモック
        with patch('src.agents.agent_d.get_llm') as mock_get_llm:
            mock_llm = MagicMock()
            mock_chain = MagicMock()
            mock_chain.ainvoke = AsyncMock(return_value=MagicMock(content="主な推奨事項は以下の4点です：1) 経費承認プロセスの見直し、2) 管理者への通知機能の強化、3) 高額経費申請の追加承認ステップの導入、4) 経費ポリシーの再教育です。特に承認プロセスの改善が最も重要です。"))
            mock_llm.__or__.return_value = mock_chain
            mock_get_llm.return_value = mock_llm
            
            # エージェントDに質問を送信
            question_result = await agent_d.handle_question(question_msg)
            
            print(f"質問処理ステータス: {question_result.get('status')}")
            print(f"回答: {question_result.get('answer')}")
    
    print("\nエージェントDのテスト完了")

# メイン実行部分
if __name__ == "__main__":
    asyncio.run(run_agent_d_test()) 