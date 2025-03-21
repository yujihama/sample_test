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
from src.core.agent_management_service import get_agent_management_service
from src.models.schema import AgentRole

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

# エージェントを初期化
def initialize_agents():
    """エージェントの初期化"""
    try:
        logger.info("エージェントを初期化しています...")
        agent_service = get_agent_management_service()
        
        # 現在登録されているエージェント情報を取得
        current_agents = agent_service.get_all_agents()
        agent_ids = [agent["id"] for agent in current_agents]
        
        # 基本エージェントのリスト
        agents_to_register = [
            {
                "id": "agent1",
                "type": "validator",
                "role": AgentRole.SPECIALIST,
                "capabilities": ["transaction_validation", "data_integrity_check"],
                "metadata": {"version": "1.0.0", "description": "検証エージェント"}
            },
            {
                "id": "agent2",
                "type": "auditor",
                "role": AgentRole.SPECIALIST,
                "capabilities": ["compliance_check", "risk_assessment"],
                "metadata": {"version": "1.0.0", "description": "監査チェックエージェント"}
            },
            {
                "id": "agent3",
                "type": "collector",
                "role": AgentRole.WORKER,
                "capabilities": ["evidence_collection", "data_integration"],
                "metadata": {"version": "1.0.0", "description": "証拠収集エージェント"}
            },
            {
                "id": "agent4",
                "type": "evaluator",
                "role": AgentRole.SPECIALIST,
                "capabilities": ["risk_assessment", "pattern_analysis"],
                "metadata": {"version": "1.0.0", "description": "リスク評価エージェント"}
            },
            {
                "id": "agent5",
                "type": "reporter",
                "role": AgentRole.WORKER,
                "capabilities": ["report_generation", "data_visualization"],
                "metadata": {"version": "1.0.0", "description": "レポート生成エージェント"}
            }
        ]
        
        # エージェントの登録
        registered_count = 0
        for agent_info in agents_to_register:
            if agent_info["id"] not in agent_ids:
                agent_service.register_agent(
                    agent_id=agent_info["id"],
                    agent_type=agent_info["type"],
                    agent_role=agent_info["role"],
                    capabilities=agent_info["capabilities"],
                    metadata=agent_info["metadata"]
                )
                registered_count += 1
        
        logger.info(f"エージェント初期化完了 - 新規登録: {registered_count}, 合計: {len(agent_service.get_all_agents())}")
        return True
    
    except Exception as e:
        logger.error(f"エージェント初期化中に例外が発生: {e}")
        return False

# ツール初期化を実行
initialize_tools()

# エージェント初期化を実行
initialize_agents()

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
