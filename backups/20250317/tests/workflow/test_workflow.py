"""
ワークフローエンドツーエンドテスト

すべてのエージェント（A, B, C, D）を連携させて実行するテスト
"""

import asyncio
import sys
import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import pytest
from unittest import mock

# プロジェクトルートを追加
project_root = Path(__file__).parents[2].absolute()
sys.path.append(str(project_root))

from src.core.config import settings
from src.utils.db_manager import init_db
from src.agents.agent_a import AgentA
from src.agents.agent_b import AgentB
from src.agents.agent_c import AgentC
from src.agents.agent_d import AgentD
from src.core.messaging import MessageBroker
from src.utils.workflow_manager import check_workflow_consistency, auto_repair_workflows
from src.models.repositories import workflow_repository
from src.tests.mock_llm_responder import mock_llm_responder


# テスト用サンプルデータパス
SAMPLE_DATA_PATH = "tests/data/test_expense.csv"

# 監査手続きテキスト
AUDIT_PROCEDURE_TEXT = """
監査手続き: 経費申請プロセスの検証

目的:
従業員の経費申請が会社のポリシーに従って適切に処理されているかを検証する。

範囲:
全従業員の経費申請データ

リスク:
1. 承認なしの経費申請
2. 上限を超える経費申請
3. 不適切なカテゴリでの申請
4. 重複申請

検証項目:
1. 全ての経費申請に適切な承認があること
2. 経費申請額が規定の上限（20,000円）を超えていないこと
3. 経費申請のカテゴリが許可されたものであること
4. 同一内容の重複申請がないこと
"""


async def setup_test_environment():
    """
    テスト環境をセットアップする
    """
    # データベースの初期化
    init_db()
    
    # サンプルデータパスの調整
    sample_data_full_path = Path(project_root) / SAMPLE_DATA_PATH
    if not sample_data_full_path.exists():
        raise FileNotFoundError(f"サンプルデータファイルが見つかりません: {sample_data_full_path}")
    
    return {
        "sample_data_path": str(sample_data_full_path),
        "procedure_text": AUDIT_PROCEDURE_TEXT
    }


async def create_agents():
    """
    テスト用のエージェントを作成する
    """
    # エージェントの初期化
    agent_a = AgentA()
    agent_b = AgentB()
    agent_c = AgentC()
    agent_d = AgentD()
    
    # コンテキストIDの生成（共通で使用）
    context_id = f"ctx-{uuid.uuid4().hex}"
    workflow_id = f"wf-{uuid.uuid4().hex}"
    
    # 各エージェントの設定
    for agent in [agent_a, agent_b, agent_c, agent_d]:
        agent.context_id = context_id
        agent.workflow_id = workflow_id
    
    agents = {
        "agent_a": agent_a,
        "agent_b": agent_b,
        "agent_c": agent_c,
        "agent_d": agent_d,
        "context_id": context_id,
        "workflow_id": workflow_id
    }
    
    return agents


async def run_agent_a(agent_a: AgentA, procedure_text: str):
    """
    エージェントAの実行（監査手続き分析）
    
    Args:
        agent_a: エージェントAのインスタンス
        procedure_text: 監査手続きのテキスト
        
    Returns:
        分析結果
    """
    # 監査手続きの分析実行
    analysis_result = await agent_a.analyze_procedure(procedure_text)
    
    # 結果の検証
    assert analysis_result, "エージェントAの分析結果がありません"
    assert "テスト項目" in analysis_result, "分析結果にテスト項目が含まれていません"
    assert len(analysis_result["テスト項目"]) > 0, "テスト項目が空です"
    
    # テスト計画の作成
    test_plan = await agent_a.create_test_plan(analysis_result)
    
    assert test_plan, "テスト計画が生成されませんでした"
    assert "test_items" in test_plan, "テスト計画にテスト項目が含まれていません"
    assert len(test_plan["test_items"]) > 0, "テスト計画のテスト項目が空です"
    
    return test_plan


async def run_agent_b(agent_b: AgentB, test_plan: Dict[str, Any], sample_data_path: str):
    """
    エージェントBの実行（データ分析）
    
    Args:
        agent_b: エージェントBのインスタンス
        test_plan: エージェントAから受け取ったテスト計画
        sample_data_path: サンプルデータのパス
        
    Returns:
        データ分析結果
    """
    # サンプルデータの読み込み
    await agent_b.load_sample_data(sample_data_path)
    
    # テスト計画に基づくデータ分析
    analysis_result = await agent_b.analyze_data(test_plan)
    
    # 結果の検証
    assert analysis_result, "エージェントBの分析結果がありません"
    assert "分析サマリー" in analysis_result, "分析結果にサマリーがありません"
    
    # テスト実行結果の生成
    test_results = await agent_b.prepare_test_results(test_plan, analysis_result)
    
    assert test_results, "テスト結果が生成されませんでした"
    assert "execution_status" in test_results, "テスト結果に実行ステータスがありません"
    
    return test_results


async def run_agent_c(agent_c: AgentC, test_plan: Dict[str, Any], test_results: Dict[str, Any]):
    """
    エージェントCの実行（結果評価）
    
    Args:
        agent_c: エージェントCのインスタンス
        test_plan: エージェントAから受け取ったテスト計画
        test_results: エージェントBから受け取ったテスト結果
        
    Returns:
        評価結果およびサマリー
    """
    # テスト結果の評価
    evaluation = await agent_c.evaluate_test_results(test_plan, test_results)
    
    # 結果の検証
    assert evaluation, "エージェントCの評価結果がありません"
    assert "評価結果" in evaluation, "評価結果に評価サマリーがありません"
    
    # 問題点の特定と要約
    findings = await agent_c.identify_findings(test_results, evaluation)
    
    assert findings, "問題点が特定されませんでした"
    assert len(findings) > 0, "問題点のリストが空です"
    
    summary = {
        "evaluation": evaluation,
        "findings": findings
    }
    
    return summary


async def run_agent_d(agent_d: AgentD, summary: Dict[str, Any], procedure_text: str):
    """
    エージェントDの実行（レポート生成）
    
    Args:
        agent_d: エージェントDのインスタンス
        summary: エージェントCから受け取った要約情報
        procedure_text: 元の監査手続きテキスト
        
    Returns:
        最終レポート
    """
    # コンテキスト情報の設定
    context = {
        "procedure_text": procedure_text,
        "evaluation": summary["evaluation"],
        "findings": summary["findings"]
    }
    
    # 監査レポートの生成
    report = await agent_d.generate_report(context)
    
    # 結果の検証
    assert report, "エージェントDのレポートがありません"
    assert "報告タイトル" in report, "レポートにタイトルがありません"
    assert "概要" in report, "レポートに概要がありません"
    assert "主要発見事項" in report, "レポートに主要発見事項がありません"
    assert len(report["主要発見事項"]) > 0, "主要発見事項のリストが空です"
    
    # レポートの詳細化
    detailed_report = await agent_d.finalize_report(report)
    
    return detailed_report


async def test_question_handling(agents: Dict[str, Any], question: str = "この監査の主な問題点は何ですか？"):
    """
    質問応答機能のテスト
    
    Args:
        agents: 各エージェントのインスタンスを含む辞書
        question: テスト用の質問
    
    Returns:
        回答
    """
    # エージェントDへの質問実行
    agent_d = agents["agent_d"]
    
    # 質問への回答
    answer = await agent_d.answer_question(question)
    
    # 結果の検証
    assert answer, "質問への回答がありません"
    assert "回答" in answer, "回答に期待される形式ではありません"
    assert len(answer["回答"]) > 10, "回答が短すぎます"
    
    return answer


@pytest.mark.asyncio
async def test_workflow_execution(patch_llm_client, mock_llm, workflow_db_session):
    """
    ワークフロー全体のテスト実行
    
    Args:
        patch_llm_client: LLMクライアントのパッチ
        mock_llm: モックLLMレスポンダー
        workflow_db_session: DBセッション
    """
    # テスト環境のセットアップ
    env = await setup_test_environment()
    
    # エージェントの作成
    agents = await create_agents()
    
    try:
        # ワークフローをデータベースに登録
        workflow_data = {
            "id": agents["workflow_id"],
            "title": "経費申請プロセステスト",
            "status": "in_progress",
            "current_agent": "agent-a",
            "context_id": agents["context_id"],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "metadata": {
                "procedure_text": AUDIT_PROCEDURE_TEXT,
                "sample_data_path": env["sample_data_path"]
            }
        }
        
        workflow_repository.create(workflow_db_session, workflow_data)
        
        # エージェントAの実行
        test_plan = await run_agent_a(agents["agent_a"], env["procedure_text"])
        
        # ワークフロー状態の更新
        workflow_repository.update_status(
            workflow_db_session, 
            agents["workflow_id"], 
            "in_progress", 
            "agent-b"
        )
        
        # エージェントBの実行
        test_results = await run_agent_b(agents["agent_b"], test_plan, env["sample_data_path"])
        
        # ワークフロー状態の更新
        workflow_repository.update_status(
            workflow_db_session, 
            agents["workflow_id"], 
            "in_progress", 
            "agent-c"
        )
        
        # エージェントCの実行
        summary = await run_agent_c(agents["agent_c"], test_plan, test_results)
        
        # ワークフロー状態の更新
        workflow_repository.update_status(
            workflow_db_session, 
            agents["workflow_id"], 
            "in_progress", 
            "agent-d"
        )
        
        # エージェントDの実行
        report = await run_agent_d(agents["agent_d"], summary, env["procedure_text"])
        
        # ワークフロー状態の更新
        workflow_repository.update_status(
            workflow_db_session, 
            agents["workflow_id"], 
            "completed", 
            None
        )
        
        # 質問応答テスト
        answer = await test_question_handling(agents)
        
        # ワークフロー整合性チェック
        inconsistencies = check_workflow_consistency(workflow_db_session, agents["workflow_id"])
        assert len(inconsistencies) == 0, f"ワークフローに整合性の問題があります: {inconsistencies}"
        
        # モックLLMの使用確認
        history = mock_llm.get_request_history()
        assert len(history) > 0, "モックLLMが使用されていません"
        
        # 各段階の結果出力
        print("\n========== テスト実行結果 ==========")
        print(f"テスト計画: {len(test_plan['test_items'])}項目のテストを計画")
        print(f"テスト結果: ステータス '{test_results['execution_status']}'")
        print(f"問題点の数: {len(summary['findings'])}")
        print(f"レポートタイトル: {report['報告タイトル']}")
        print(f"質問への回答: {answer['回答'][:50]}...")
        print("====================================\n")
        
    except Exception as e:
        # エラー発生時の情報出力
        print(f"テスト実行中にエラーが発生しました: {str(e)}")
        # ワークフロー整合性チェック実行
        inconsistencies = check_workflow_consistency(workflow_db_session, agents["workflow_id"])
        if inconsistencies:
            print(f"ワークフロー整合性の問題: {inconsistencies}")
            # 自動修復を試行
            fixed, repairs = auto_repair_workflows(
                workflow_db_session, 
                workflow_id=agents["workflow_id"],
                dry_run=False
            )
            print(f"自動修復結果: {fixed}件修復, {repairs}")
        raise
    
    # 最終確認
    assert report["結論"], "最終レポートに結論がありません"


if __name__ == "__main__":
    # スクリプトとして実行された場合はイベントループを使って実行
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_workflow_execution(None, mock_llm_responder, None))
    loop.close() 