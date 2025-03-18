"""
エージェントマネージャーモジュール

このモジュールは、エージェントの管理と制御を行うクラスを提供します。
"""

from typing import Dict, List, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)

class AgentManager:
    """エージェントの管理と制御を行うクラス"""

    def __init__(self):
        """エージェントマネージャーを初期化します。"""
        self.agents: Dict[str, dict] = {}
        self.tasks: Dict[str, dict] = {}
        logger.info("エージェントマネージャーを初期化しました")

    def register_agent(self, agent_id: str, agent_type: str) -> bool:
        """
        新しいエージェントを登録します。

        Args:
            agent_id (str): エージェントID
            agent_type (str): エージェントタイプ

        Returns:
            bool: 登録が成功したかどうか
        """
        if agent_id in self.agents:
            logger.warning(f"エージェント {agent_id} は既に登録されています")
            return False

        self.agents[agent_id] = {
            "type": agent_type,
            "status": "idle",
            "current_task": None
        }
        logger.info(f"エージェント {agent_id} を登録しました")
        return True

    def assign_task(self, task_id: str, agent_id: str, task_data: dict) -> bool:
        """
        タスクをエージェントに割り当てます。

        Args:
            task_id (str): タスクID
            agent_id (str): エージェントID
            task_data (dict): タスクデータ

        Returns:
            bool: 割り当てが成功したかどうか
        """
        if agent_id not in self.agents:
            logger.error(f"エージェント {agent_id} が見つかりません")
            return False

        if self.agents[agent_id]["status"] != "idle":
            logger.warning(f"エージェント {agent_id} は現在ビジー状態です")
            return False

        self.tasks[task_id] = {
            "data": task_data,
            "status": "assigned",
            "assigned_agent": agent_id
        }
        self.agents[agent_id]["status"] = "busy"
        self.agents[agent_id]["current_task"] = task_id
        logger.info(f"タスク {task_id} をエージェント {agent_id} に割り当てました")
        return True

    def get_agent_status(self, agent_id: str) -> Optional[dict]:
        """
        エージェントの状態を取得します。

        Args:
            agent_id (str): エージェントID

        Returns:
            Optional[dict]: エージェントの状態情報
        """
        if agent_id not in self.agents:
            logger.error(f"エージェント {agent_id} が見つかりません")
            return None
        return self.agents[agent_id]

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """
        タスクの状態を取得します。

        Args:
            task_id (str): タスクID

        Returns:
            Optional[dict]: タスクの状態情報
        """
        if task_id not in self.tasks:
            logger.error(f"タスク {task_id} が見つかりません")
            return None
        return self.tasks[task_id]

    def update_task_status(self, task_id: str, status: str) -> bool:
        """
        タスクの状態を更新します。

        Args:
            task_id (str): タスクID
            status (str): 新しい状態

        Returns:
            bool: 更新が成功したかどうか
        """
        if task_id not in self.tasks:
            logger.error(f"タスク {task_id} が見つかりません")
            return False

        self.tasks[task_id]["status"] = status
        agent_id = self.tasks[task_id]["assigned_agent"]

        if status in ["completed", "failed"]:
            self.agents[agent_id]["status"] = "idle"
            self.agents[agent_id]["current_task"] = None

        logger.info(f"タスク {task_id} の状態を {status} に更新しました")
        return True

    def get_all_agents(self) -> List[dict]:
        """
        全てのエージェントの情報を取得します。

        Returns:
            List[dict]: エージェント情報のリスト
        """
        return [
            {"id": agent_id, **agent_data}
            for agent_id, agent_data in self.agents.items()
        ]

    def get_all_tasks(self) -> List[dict]:
        """
        全てのタスクの情報を取得します。

        Returns:
            List[dict]: タスク情報のリスト
        """
        return [
            {"id": task_id, **task_data}
            for task_id, task_data in self.tasks.items()
        ] 