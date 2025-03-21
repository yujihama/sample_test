"""
エージェント初期化スクリプト

このスクリプトはエージェント管理サービスを初期化し、基本的なエージェントを登録します。
"""

import sys
import os

# srcディレクトリをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.agent_management_service import get_agent_management_service
from src.models.schema import AgentRole

def main():
    """エージェントを初期化する"""
    
    # エージェント管理サービスを取得
    agent_service = get_agent_management_service()
    
    # 現在登録されているエージェント情報を取得
    current_agents = agent_service.get_all_agents()
    agent_ids = [agent["id"] for agent in current_agents]
    
    # エージェントの登録（存在しない場合のみ）
    agents_to_register = [
        {
            "id": "agent1",
            "type": "validator",
            "role": AgentRole.SPECIALIST,  # 検証専門家
            "capabilities": ["transaction_validation", "data_integrity_check"],
            "metadata": {"version": "1.0.0", "description": "検証エージェント"}
        },
        {
            "id": "agent2",
            "type": "auditor",
            "role": AgentRole.SPECIALIST,  # 監査専門家
            "capabilities": ["compliance_check", "risk_assessment"],
            "metadata": {"version": "1.0.0", "description": "監査チェックエージェント"}
        },
        {
            "id": "agent3",
            "type": "collector",
            "role": AgentRole.WORKER,  # データ収集作業員
            "capabilities": ["evidence_collection", "data_integration"],
            "metadata": {"version": "1.0.0", "description": "証拠収集エージェント"}
        },
        {
            "id": "agent4",
            "type": "evaluator",
            "role": AgentRole.SPECIALIST,  # 評価専門家
            "capabilities": ["risk_assessment", "pattern_analysis"],
            "metadata": {"version": "1.0.0", "description": "リスク評価エージェント"}
        },
        {
            "id": "agent5",
            "type": "reporter",
            "role": AgentRole.WORKER,  # レポート作成作業員
            "capabilities": ["report_generation", "data_visualization"],
            "metadata": {"version": "1.0.0", "description": "レポート生成エージェント"}
        }
    ]
    
    for agent_info in agents_to_register:
        if agent_info["id"] not in agent_ids:
            print(f"エージェント {agent_info['id']} を登録します...")
            agent_service.register_agent(
                agent_id=agent_info["id"],
                agent_type=agent_info["type"],
                agent_role=agent_info["role"],
                capabilities=agent_info["capabilities"],
                metadata=agent_info["metadata"]
            )
            print(f"エージェント {agent_info['id']} を登録しました")
        else:
            print(f"エージェント {agent_info['id']} は既に登録されています")
    
    # 登録されたエージェント一覧を表示
    registered_agents = agent_service.get_all_agents()
    print(f"\n登録済みエージェント数: {len(registered_agents)}")
    for agent in registered_agents:
        print(f"- {agent['id']}: {agent.get('type')} ({agent.get('status')})")

if __name__ == "__main__":
    main() 