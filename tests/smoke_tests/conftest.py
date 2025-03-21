"""
Smokeテスト用の共通フィクスチャと設定
"""

import os
import sys
from pathlib import Path
import warnings
import asyncio
import json
from typing import Dict, Any, List, Optional, Generator
from datetime import datetime

import pytest
from loguru import logger

# テスト環境フラグを設定
os.environ["TESTING"] = "1"
os.environ["USE_MOCK_LLM"] = "True"

# プロジェクトルートをPYTHONPATHに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# プロジェクトルートパスを取得
project_root = Path(__file__).parents[2].absolute()
sys.path.append(str(project_root))

# 警告フィルターを設定
def pytest_configure(config):
    """Pytestの設定をカスタマイズ"""
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")
    warnings.filterwarnings("ignore", category=pytest.PytestDeprecationWarning)

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    テスト環境のセットアップと後片付け
    """
    # テスト用ディレクトリの作成
    os.makedirs("tests/smoke_tests/temp", exist_ok=True)
    os.makedirs("logs/agent", exist_ok=True)
    
    logger.info("疎通テスト環境をセットアップしました")
    
    yield
    
    # テスト後のクリーンアップ
    logger.info("疎通テスト環境をクリーンアップしています")

@pytest.fixture
def mock_llm():
    """
    モックLLMを提供するフィクスチャ
    """
    class MockLLM:
        def __init__(self):
            self.responses = {}
            
        def add_response(self, prompt, response):
            self.responses[prompt] = response
            
        def generate(self, prompt, **kwargs):
            return self.responses.get(prompt, "モックレスポンス")
    
    return MockLLM()

@pytest.fixture(scope="session")
def db_session():
    """テスト用データベースセッション"""
    # DataBaseSessionの設定
    from src.utils.db_manager import get_db
    
    session = next(get_db())
    yield session
    
    session.close()

# ワークフローIDを記録するフィクスチャ
@pytest.fixture
def workflow_id_recorder():
    """テスト中のワークフローIDを記録するフィクスチャ"""
    active_workflow_ids = []
    
    def _record_workflow_id(workflow_id: str) -> None:
        """ワークフローIDを記録する"""
        if workflow_id and workflow_id not in active_workflow_ids:
            active_workflow_ids.append(workflow_id)
    
    yield _record_workflow_id
    
    # テスト完了時に記録されたすべてのワークフローIDのエージェントログを保存
    for workflow_id in active_workflow_ids:
        try:
            # ヘルパー関数をローカルからインポート
            sys.path.insert(0, str(Path(__file__).parent))
            try:
                # save_agent_logs関数を使用
                from test_helpers import save_agent_logs
                save_agent_logs(workflow_id)
            except ImportError:
                print(f"save_agent_logs 関数をインポートできませんでした")
                # 直接ファイルを作成
                log_path = os.path.join(project_root, "logs", "agent", f"workflow_{workflow_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                with open(log_path, "w") as f:
                    f.write(f"ワークフローID {workflow_id} のログ情報")
        except Exception as e:
            print(f"ワークフロー {workflow_id} のログ保存中にエラー: {str(e)}")

# エージェントのログを保存するフック
@pytest.hookimpl(trylast=True)
def pytest_runtest_makereport(item, call):
    """テスト実行結果を処理するフック"""
    if call.when == "teardown":
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from datetime import datetime
            
            # テスト関数から直接ワークフローIDを取得できるか試みる
            workflow_id = None
            if hasattr(item, "workflow_id"):
                workflow_id = item.workflow_id
            
            # ワークフローIDをテスト関数の属性から取得
            if not workflow_id:
                for attr in dir(item.function):
                    if attr.startswith("workflow_id_"):
                        workflow_id = getattr(item.function, attr)
                        break
            
            if workflow_id:
                try:
                    # save_agent_logs関数を使用
                    from test_helpers import save_agent_logs
                    save_agent_logs(workflow_id)
                except ImportError:
                    # 直接ファイルを作成
                    log_path = os.path.join(project_root, "logs", "agent", f"test_result_{workflow_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                    with open(log_path, "w") as f:
                        f.write(f"テスト {item.name} の実行結果: {workflow_id}")
        except Exception as e:
            print(f"テスト後のログ保存中にエラー: {str(e)}") 