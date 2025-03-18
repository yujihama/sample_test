#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
統合テストを実行するためのスクリプト
"""

import os
import sys
import unittest
import argparse
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# テスト設定をインポート
from tests.integration.test_config import (
    TEST_DB_TYPE,
    TEST_DB_PATH,
    TEST_WORKFLOW_STATES_DIR
)

# テストモジュールをインポート
from tests.integration.test_workflow_state import TestWorkflowState
from tests.integration.test_agent_a_workflow import TestAgentAWorkflow
from tests.integration.test_agent_b_workflow import TestAgentBWorkflow
from tests.integration.test_agent_c_workflow import TestAgentCWorkflow
from tests.integration.test_agent_d_workflow import TestAgentDWorkflow

def run_tests(verbose=1, test_pattern=None):
    """
    統合テストを実行する
    
    Args:
        verbose (int): 詳細度レベル (0-2)
        test_pattern (str): 実行するテストのパターン
    """
    # テスト環境の準備
    os.makedirs(TEST_WORKFLOW_STATES_DIR, exist_ok=True)
    
    # テストスイートを作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # テストクラスをスイートに追加
    suite.addTests(loader.loadTestsFromTestCase(TestWorkflowState))
    suite.addTests(loader.loadTestsFromTestCase(TestAgentAWorkflow))
    suite.addTests(loader.loadTestsFromTestCase(TestAgentBWorkflow))
    suite.addTests(loader.loadTestsFromTestCase(TestAgentCWorkflow))
    suite.addTests(loader.loadTestsFromTestCase(TestAgentDWorkflow))
    
    # 特定のパターンが指定された場合、そのパターンに一致するテストのみを実行
    if test_pattern:
        pattern_suite = unittest.TestSuite()
        for test in suite:
            if test_pattern.lower() in test.id().lower():
                pattern_suite.addTest(test)
        suite = pattern_suite
    
    # テストランナーを作成して実行
    runner = unittest.TextTestRunner(verbosity=verbose)
    result = runner.run(suite)
    
    # 結果に基づいて終了コードを設定
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="統合テストを実行します")
    parser.add_argument("--verbose", "-v", type=int, choices=[0, 1, 2], default=1,
                        help="詳細度レベル (0: 最小限, 1: 通常, 2: 詳細)")
    parser.add_argument("--pattern", "-p", type=str, default=None,
                        help="実行するテストのパターン (例: 'agent_a')")
    parser.add_argument("--db-type", type=str, choices=["sqlite", "postgres"], default=None,
                        help=f"使用するデータベースタイプ (デフォルト: {TEST_DB_TYPE})")
    parser.add_argument("--db-path", type=str, default=None,
                        help=f"SQLiteデータベースのパス (デフォルト: {TEST_DB_PATH})")
    
    args = parser.parse_args()
    
    # 環境変数を設定
    if args.db_type:
        os.environ["INTEGRATION_TEST_DB_TYPE"] = args.db_type
    if args.db_path:
        os.environ["INTEGRATION_TEST_DB_PATH"] = args.db_path
    
    # テスト実行前の情報表示
    print(f"統合テストを実行します:")
    print(f"- データベースタイプ: {os.environ.get('INTEGRATION_TEST_DB_TYPE', TEST_DB_TYPE)}")
    if os.environ.get('INTEGRATION_TEST_DB_TYPE', TEST_DB_TYPE) == "sqlite":
        print(f"- データベースパス: {os.environ.get('INTEGRATION_TEST_DB_PATH', TEST_DB_PATH)}")
    print(f"- ワークフロー状態ディレクトリ: {TEST_WORKFLOW_STATES_DIR}")
    if args.pattern:
        print(f"- テストパターン: {args.pattern}")
    print("-" * 50)
    
    # テスト実行
    exit_code = run_tests(verbose=args.verbose, test_pattern=args.pattern)
    sys.exit(exit_code) 