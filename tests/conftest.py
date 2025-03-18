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
os.environ["TESTING"] = "True"
os.environ["USE_MOCK_LLM"] = "True"

# プロジェクトルートをPYTHONPATHに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 設定をインポート（テスト環境フラグ設定後）
from src.core.config import settings
from src.utils.logging import setup_logging
from src.utils.db_manager import init_db, engine
from tests.utils.mocks.mock_llm_responder import mock_llm_responder


# 警告フィルターを設定
def pytest_configure(config):
    """Pytestの設定をカスタマイズ"""
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")
    warnings.filterwarnings("ignore", category=pytest.PytestDeprecationWarning)


@pytest.fixture(scope="session", autouse=True)
async def setup_test_environment():
    """
    テスト環境のセットアップ
    - テスト環境フラグを設定
    - テストデータディレクトリを作成
    - データベースを初期化
    - ログ設定
    """
    # テスト環境フラグを設定
    os.environ["TESTING"] = "True"
    
    # テストデータディレクトリを作成
    test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
    os.makedirs(test_data_dir, exist_ok=True)
    
    # ログ設定
    setup_logging()
    
    # データベースファイルを削除（存在する場合）
    db_path = settings.DATABASE_URL.replace('sqlite:///', '')
    if os.path.exists(db_path):
        try:
            # データベース接続を閉じる
            engine.dispose()
            os.remove(db_path)
            logger.info(f"既存のデータベースファイルを削除しました: {db_path}")
        except Exception as e:
            logger.error(f"データベースファイルの削除中にエラーが発生しました: {e}")
            raise
    
    # データベースを初期化
    try:
        # データベースディレクトリを作成
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # データベースを初期化
        init_db()
        logger.info("データベースを初期化しました")
        
        # データベースが正しく作成されたか確認
        if not os.path.exists(db_path):
            raise Exception("データベースファイルが作成されませんでした")
        
    except Exception as e:
        logger.error(f"データベース初期化中にエラーが発生しました: {e}")
        raise
    
    yield
    
    # クリーンアップ
    try:
        # データベース接続を閉じる
        engine.dispose()
        
        # データベースファイルを削除
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info("データベースファイルを削除しました")
        
        # テストデータディレクトリを削除
        if os.path.exists(test_data_dir):
            shutil.rmtree(test_data_dir)
            logger.info("テストデータディレクトリを削除しました")
    except Exception as e:
        logger.error(f"クリーンアップ中にエラーが発生しました: {e}")
        raise


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
        if dir_path.exists():
            for file_path in dir_path.glob("*.json"):
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.error(f"テストデータファイルの削除中にエラーが発生しました: {file_path}, エラー: {e}")
    
    yield


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
def test_db_session():
    """
    テスト用のDBセッションを提供 (db_sessionのエイリアス)
    規程情報リポジトリテスト用に特別に定義
    
    Returns:
        Session: DBセッション
    """
    # db_sessionを再利用
    import os
    from pathlib import Path
    from src.core.config import settings
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.utils.db_manager import Base, init_db
    
    # テスト環境を明示的に設定
    os.environ["TESTING"] = "True"
    
    # テストデータベースのパスを確認
    db_path = Path(settings.TEST_DATA_DIR) / "test.db"
    
    # データベースファイルが存在する場合は削除
    if db_path.exists():
        try:
            db_path.unlink()
            logger.info(f"既存のテストデータベースを削除しました: {db_path}")
        except Exception as e:
            logger.warning(f"テストデータベースの削除に失敗しました: {e}")
    
    # テスト用のデータベースURLを設定
    test_db_url = f"sqlite:///{db_path}"
    logger.info(f"テストデータベースURL: {test_db_url}")
    
    # テスト用のエンジンを作成
    test_engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False}
    )
    
    # テスト用のセッションを作成
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    # テーブルを作成
    Base.metadata.create_all(bind=test_engine)
    logger.info(f"テストデータベーステーブルを作成しました: {test_db_url}")
    
    # セッションを取得
    db_session = TestSessionLocal()
    
    # テスト用のセッションを提供
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