"""
内部監査サンプルデータ自動テストAIエージェントシステム
アプリケーション起動スクリプト
"""

import os
import sys
from src.api.main import app
from src.core.config import settings, initialize_app
from loguru import logger

# ツール初期化処理を追加
from src.scripts.init_tools import init_tools

# アプリケーションを初期化
initialize_app()

# ツールを初期化
def initialize_tools():
    """ツールの初期化"""
    try:
        logger.info("補助ツールを初期化しています...")
        result = init_tools(verbose=(settings.LOG_LEVEL.upper() == "DEBUG"))
        
        if result["status"] == "success":
            logger.info(f"ツール初期化完了 - 利用可能なツール数: {len(result['available_tools'])}")
            return True
        else:
            logger.error(f"ツール初期化エラー: {result.get('message', '不明なエラー')}")
            return False
    
    except Exception as e:
        logger.error(f"ツール初期化中に例外が発生: {e}")
        return False

# ツール初期化を実行
initialize_tools()

def start_server():
    """
    アプリケーションサーバーを起動します。
    """
    import uvicorn
    
    logger.info(f"サーバーを起動しています: {settings.APP_HOST}:{settings.APP_PORT}")
    uvicorn.run(
        "src.api.main:app", 
        host=settings.APP_HOST, 
        port=settings.APP_PORT,
        reload=settings.APP_ENV == "development",
        log_level=settings.LOG_LEVEL.lower()
    )

if __name__ == "__main__":
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} を起動しています")
    start_server()
