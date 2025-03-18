"""
疎通テスト用のpytest設定ファイル
"""

import os
import sys
from pathlib import Path
import warnings

import pytest
from loguru import logger

# テスト環境フラグを設定
os.environ["TESTING"] = "1"
os.environ["USE_MOCK_LLM"] = "True"

# プロジェクトルートをPYTHONPATHに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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

@pytest.fixture
def db_session():
    """
    テスト用のデータベースセッションを提供するフィクスチャ
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # インメモリSQLiteデータベースを使用
    engine = create_engine("sqlite:///:memory:")
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close() 