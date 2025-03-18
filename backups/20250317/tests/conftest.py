"""
pytestの設定ファイル
"""

import os
import sys
import shutil
from pathlib import Path
import asyncio
from unittest import mock
import warnings

import pytest
from loguru import logger

# テスト環境フラグを設定
os.environ["TESTING"] = "1"
os.environ["USE_MOCK_LLM"] = "True"

# プロジェクトルートをPYTHONPATHに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 設定をインポート（テスト環境フラグ設定後）
from src.core.config import settings
from src.utils.logging import setup_logging
from tests.mock_llm_responder import mock_llm_responder


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
    os.makedirs(settings.TEST_DATA_DIR, exist_ok=True)
    os.makedirs(Path(settings.TEST_DATA_DIR) / "messages", exist_ok=True)
    os.makedirs(Path(settings.TEST_DATA_DIR) / "contexts", exist_ok=True)
    
    # ロギングの設定
    setup_logging()
    
    logger.info("テスト環境をセットアップしました")
    
    yield
    
    # テスト後のクリーンアップ
    try:
        # テスト用ディレクトリの削除（オプション）
        # shutil.rmtree(settings.TEST_DATA_DIR)
        logger.info("テスト環境をクリーンアップしました")
        
        # ログハンドラーをクリーンアップ
        for handler_id in list(logger._core.handlers.keys()):
            logger.remove(handler_id)
    except Exception as e:
        logger.error(f"テスト環境のクリーンアップ中にエラーが発生しました: {e}")


@pytest.fixture
def clean_test_data():
    """
    テストデータをクリーンアップするフィクスチャ
    """
    # テスト前のクリーンアップ
    for dir_path in [
        Path(settings.TEST_DATA_DIR) / "messages",
        Path(settings.TEST_DATA_DIR) / "contexts"
    ]:
        for file_path in dir_path.glob("*.json"):
            try:
                file_path.unlink()
            except Exception as e:
                logger.warning(f"ファイル削除中にエラーが発生しました: {file_path} - {e}")
    
    yield
    
    # テスト後のクリーンアップ（オプション）
    # 同様のクリーンアップコードをここに記述


@pytest.fixture
def mock_llm():
    """
    モックLLMレスポンダーを提供するフィクスチャ
    
    Returns:
        MockLLMResponder: モックLLMレスポンダーインスタンス
    """
    # テスト前の準備
    mock_llm_responder.clear_history()
    
    yield mock_llm_responder
    
    # テスト後のクリーンアップ
    mock_llm_responder.clear_history()


@pytest.fixture
def patch_llm_client():
    """
    実際のLLMクライアントをモックに置き換えるパッチ
    
    Returns:
        MagicMock: パッチされたLLMクライアント
    """
    # パッチ対象のモジュールパス
    target = "src.core.llm.client.LLMClient.generate_completion"
    
    # パッチを適用
    with mock.patch(target) as mock_generate:
        # モックLLMレスポンダーの応答を使用
        mock_generate.side_effect = mock_llm_responder.generate_response
        yield mock_generate


@pytest.fixture(scope="session")
def event_loop_policy():
    """
    非同期テスト用のイベントループポリシーを提供
    
    Returns:
        asyncio.AbstractEventLoopPolicy: イベントループポリシー
    """
    # カスタムのイベントループポリシーを返す代わりに、
    # 単にデフォルトのポリシーを返します
    return asyncio.get_event_loop_policy()


@pytest.fixture
def workflow_db_session():
    """
    ワークフロー用のDBセッションを提供
    
    Returns:
        Session: DBセッション
    """
    from src.utils.db_manager import get_db, init_db
    
    # データベースの初期化
    init_db()
    
    # セッションを取得
    db_session = next(get_db())
    
    yield db_session
    
    # テスト後のクリーンアップ
    db_session.close()


@pytest.fixture
def db_session():
    """
    テスト用のDBセッションを提供 (workflow_db_sessionのエイリアス)
    
    Returns:
        Session: DBセッション
    """
    # workflow_db_sessionを再利用
    from src.utils.db_manager import get_db, init_db
    
    # データベースの初期化
    init_db()
    
    # セッションを取得
    db_session = next(get_db())
    
    yield db_session
    
    # テスト後のクリーンアップ
    db_session.close()


@pytest.fixture
def sample_workflow_data():
    """
    サンプルワークフローデータを提供
    
    Returns:
        dict: サンプルワークフローデータ
    """
    return {
        "workflow_id": f"wf-test-{os.urandom(4).hex()}",
        "title": "テスト監査ワークフロー",
        "procedure_id": "proc-001",
        "status": "in_progress",
        "current_agent": "agent-a",
        "context_id": f"ctx-{os.urandom(4).hex()}",
        "created_at": "2025-03-15T10:00:00",
        "updated_at": "2025-03-15T10:05:00",
        "metadata": {
            "priority": "normal",
            "initiator": "test-user",
            "category": "expense-audit"
        }
    } 