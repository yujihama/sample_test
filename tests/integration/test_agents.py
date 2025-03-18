"""
テスト用エージェントクラス

このモジュールには、テスト用のエージェントクラス実装が含まれています。
これらのクラスはテスト環境でのエージェント間通信とワークフローのテストに使用されます。
"""

import json
import logging
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime
from pathlib import Path

from src.core.agent import AgentBase
from src.core.messaging import MessageClient

class AgentLogger:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.logger = logging.getLogger(f"agent.{agent_id}")
        self.logger.setLevel(logging.DEBUG)
        
        # ログディレクトリの作成
        log_dir = Path("logs/agents")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # ファイルハンドラの設定
        file_handler = logging.FileHandler(
            log_dir / f"{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # フォーマッタの設定
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            '%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def log_message(self, message: Dict[str, Any], direction: str = "received"):
        """メッセージのログを記録"""
        message_type = message.get("type", "unknown")
        content = message.get("content", {})
        self.logger.info(
            f"Message {direction}: type={message_type} | "
            f"content={json.dumps(content, ensure_ascii=False)}"
        )
    
    def log_state_change(self, state_type: str, details: Dict[str, Any]):
        """状態変更のログを記録"""
        self.logger.info(
            f"State change: {state_type} | "
            f"details={json.dumps(details, ensure_ascii=False)}"
        )
    
    def log_error(self, error_type: str, details: Dict[str, Any], exc_info=None):
        """エラーのログを記録"""
        self.logger.error(
            f"Error occurred: {error_type} | "
            f"details={json.dumps(details, ensure_ascii=False)}",
            exc_info=exc_info
        )
    
    def log_action(self, action_type: str, details: Dict[str, Any]):
        """アクションのログを記録"""
        self.logger.info(
            f"Action performed: {action_type} | "
            f"details={json.dumps(details, ensure_ascii=False)}"
        )

class AgentRole(Enum):
    SUPERVISOR = "supervisor"
    WORKER = "worker"
    HUMAN = "human"

class TestAgentA(AgentBase):
    def __init__(self):
        message_client = MessageClient("test_agent_a")
        super().__init__("test_agent_a", message_client)
        self.role = AgentRole.SUPERVISOR
        self.pending_tasks: List[Dict[str, Any]] = []
        self.human_queries: List[Dict[str, Any]] = []
        self.logger = AgentLogger("test_agent_a")

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.log_message(message, "received")
        
        try:
            message_type = message.get("type", "unknown")
            message_content = message.get("content", {})
            
            if message_type == "task_request":
                # タスクの評価と割り当て
                task_difficulty = message_content.get("difficulty", 0)
                requires_approval = message_content.get("requires_approval", False)
                task_priority = message_content.get("priority", "normal")
                task_category = message_content.get("category", "default")
                
                self.logger.log_action("task_evaluation", {
                    "task_id": message_content.get("task_id"),
                    "difficulty": task_difficulty,
                    "requires_approval": requires_approval
                })
                
                # 難易度が高いまたは承認が必要なタスクは人間に問い合わせ
                if task_difficulty > 7 or requires_approval:
                    query = {
                        "type": "human_query",
                        "content": {
                            "task_id": message_content.get("task_id"),
                            "question": "難易度の高いタスクの承認が必要です"
                        }
                    }
                    self.human_queries.append(query)
                    self.logger.log_action("human_query_created", {
                        "task_id": message_content.get("task_id"),
                        "query": query
                    })
                    
                    response = {"response": "human_query_created"}
                    self.logger.log_message(response, "sent")
                    return response
                
                # カテゴリに基づいてタスクをルーティング
                if task_category == "analysis":
                    self.logger.log_action("task_routing", {
                        "task_id": message_content.get("task_id"),
                        "category": task_category,
                        "target_agent": "agent_b"
                    })
                    
                    response = {
                        "response": "task_routed",
                        "route_to": "agent_b",
                        "task_id": message_content.get("task_id")
                    }
                    self.logger.log_message(response, "sent")
                    return response
                
                # 通常タスクは受け入れ
                # タスクを追加
                task_message = {"type": message_type, "content": message_content}
                self.pending_tasks.append(task_message)
                self.logger.log_state_change("task_added", {
                    "task_id": message_content.get("task_id"),
                    "pending_tasks_count": len(self.pending_tasks)
                })
                
                # 優先度に基づいてタスクを並べ替え
                priorities = [task["content"].get("priority", "normal") for task in self.pending_tasks]
                self.logger.log_action("tasks_prioritized", {
                    "priorities": priorities
                })
                
                # 優先度が "high" の場合は、優先処理を行う
                if task_priority == "high":
                    response = {
                        "response": "task_accepted", 
                        "task_id": message_content.get("task_id"),
                        "priority_handled": True
                    }
                else:
                    response = {
                        "response": "task_accepted", 
                        "task_id": message_content.get("task_id")
                    }
                
                self.logger.log_message(response, "sent")
                return response

            elif message_type == "human_response":
                # 人間からの応答を処理
                task_id = message_content.get("task_id")
                approved = message_content.get("approved", False)
                
                self.logger.log_action("human_response_received", {
                    "task_id": task_id,
                    "approved": approved
                })
                
                if approved:
                    # 承認された場合、タスクを処理
                    response = {"response": "task_approved", "task_id": task_id}
                    self.logger.log_message(response, "sent")
                    return response
                else:
                    # 拒否された場合
                    response = {"response": "task_rejected", "task_id": task_id}
                    self.logger.log_message(response, "sent")
                    return response

            elif message_type == "task_completion":
                # タスク完了処理
                task_id = message_content.get("task_id")
                self.logger.log_action("task_completion_received", {
                    "task_id": task_id
                })
                
                # タスクの状態を更新
                for i, task in enumerate(self.pending_tasks):
                    if task["content"].get("task_id") == task_id:
                        self.pending_tasks.pop(i)
                        self.logger.log_state_change("task_removed", {
                            "task_id": task_id,
                            "pending_tasks_count": len(self.pending_tasks)
                        })
                        break
                
                response = {"response": "completion_acknowledged", "task_id": task_id}
                self.logger.log_message(response, "sent")
                return response
                
            elif message_type == "complex_task":
                # 複雑なタスクの委任処理
                task_id = message_content.get("task_id")
                requires_delegation = message_content.get("requires_delegation", False)
                
                self.logger.log_action("complex_task_received", {
                    "task_id": task_id,
                    "requires_delegation": requires_delegation
                })
                
                if requires_delegation:
                    # サブタスクを作成
                    subtask = {
                        "parent_task_id": task_id,
                        "subtask_id": f"subtask_001",
                        "description": "サブタスク処理"
                    }
                    
                    self.logger.log_action("subtask_created", {
                        "parent_task_id": task_id,
                        "subtask_id": subtask["subtask_id"]
                    })
                    
                    response = {
                        "response": "task_delegated",
                        "parent_task_id": task_id,
                        "subtasks": [subtask]
                    }
                    self.logger.log_message(response, "sent")
                    return response
                
                # 委任が不要な場合は通常処理
                response = {"response": "task_accepted", "task_id": task_id}
                self.logger.log_message(response, "sent")
                return response
                
            elif message_type == "subtask_completion":
                # サブタスク完了の処理
                parent_task_id = message_content.get("parent_task_id")
                subtask_id = message_content.get("subtask_id")
                result = message_content.get("result")
                
                self.logger.log_action("subtask_completion_received", {
                    "parent_task_id": parent_task_id,
                    "subtask_id": subtask_id,
                    "result": result
                })
                
                # 最終結果の統合
                response = {
                    "response": "task_integration_complete",
                    "parent_task_id": parent_task_id,
                    "result": "タスク処理が完了しました"
                }
                self.logger.log_message(response, "sent")
                return response
                
            elif message_type == "decision_task":
                # 意思決定タスクの処理
                task_id = message_content.get("task_id")
                requires_collaboration = message_content.get("requires_collaboration", False)
                
                self.logger.log_action("decision_task_received", {
                    "task_id": task_id,
                    "requires_collaboration": requires_collaboration
                })
                
                if requires_collaboration:
                    # 協調プロセスを開始
                    self.logger.log_action("collaboration_initiated", {
                        "task_id": task_id,
                        "collaboration_type": "risk_assessment"
                    })
                    
                    response = {
                        "response": "collaboration_initiated",
                        "task_id": task_id,
                        "next_step": "risk_assessment"
                    }
                    self.logger.log_message(response, "sent")
                    return response
                
                # 通常の決定プロセス
                response = {"response": "decision_made", "task_id": task_id}
                self.logger.log_message(response, "sent")
                return response
                
            elif message_type == "analysis_result":
                # 分析結果の処理と最終決定
                task_id = message_content.get("task_id")
                result = message_content.get("result", {})
                
                self.logger.log_action("analysis_result_received", {
                    "task_id": task_id,
                    "result": result
                })
                
                # 結果に基づいて決定
                risk_level = result.get("risk_level", "unknown")
                recommendations = result.get("recommendations", [])
                
                self.logger.log_action("decision_making", {
                    "task_id": task_id,
                    "risk_level": risk_level,
                    "recommendations_count": len(recommendations)
                })
                
                # 最終決定
                response = {
                    "response": "decision_made",
                    "task_id": task_id,
                    "decision": "proceed" if risk_level != "high" else "escalate",
                    "justification": f"リスクレベル{risk_level}に基づく判断"
                }
                self.logger.log_message(response, "sent")
                return response

            else:
                # 未知のメッセージタイプ
                self.logger.log_error("unknown_message_type", {
                    "message_type": message_type
                })
                response = {"response": "unknown_message_type", "error": f"Unknown message type: {message_type}"}
                self.logger.log_message(response, "sent")
                return response

        except Exception as e:
            self.logger.log_error("process_error", {
                "message_type": message_type,
                "error": str(e)
            }, exc_info=e)
            response = {"response": "error", "error": str(e)}
            self.logger.log_message(response, "sent")
            return response

    async def initialize(self):
        """初期化処理"""
        self.logger.log_action("initialization", {"agent_id": "test_agent_a"})
        return True

    async def cleanup(self):
        """クリーンアップ処理"""
        self.logger.log_action("cleanup", {"agent_id": "test_agent_a"})
        return True

class TestAgentB(AgentBase):
    def __init__(self):
        message_client = MessageClient("test_agent_b")
        super().__init__("test_agent_b", message_client)
        self.role = AgentRole.WORKER
        self.assigned_tasks: List[Dict[str, Any]] = []
        self.current_task: Optional[Dict[str, Any]] = None
        self.logger = AgentLogger("test_agent_b")

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.log_message(message, "received")
        
        try:
            message_type = message.get("type", "unknown")
            message_content = message.get("content", {})
            
            if message_type == "task_assignment":
                # タスクの受け入れと実行
                task = message_content.get("task")
                if task:
                    task_id = task.get("task_id")
                    
                    # エラートリガーの確認
                    if task.get("error_trigger", False):
                        self.logger.log_action("error_detected", {
                            "task_id": task_id,
                            "reason": "error_trigger_detected"
                        })
                        
                        response = {
                            "response": "error_handled",
                            "error_details": {
                                "task_id": task_id,
                                "error_type": "triggered_error",
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                        
                        self.logger.log_message(response, "sent")
                        return response
                    
                    # 通常のタスク処理
                    self.logger.log_action("task_assignment_received", {
                        "task_id": task_id,
                        "error_count": 0,
                        "retry_attempts": 0
                    })
                    
                    # 既存のタスク処理ロジック...
                    self.assigned_tasks.append(task)
                    self.current_task = task
                    self.logger.log_state_change("task_accepted", {
                        "task_id": task_id,
                        "active_tasks_count": len(self.assigned_tasks)
                    })
                    response = {"response": "task_accepted", "task_id": task_id}
                    self.logger.log_message(response, "sent")
                    return response

                self.logger.log_error("invalid_task", {"content": message_content})
                response = {"response": "invalid_task"}
                self.logger.log_message(response, "sent")
                return response

            elif message_type == "routed_task":
                # ルーティングされたタスクの処理
                task_id = message_content.get("task_id")
                category = message_content.get("category")
                source_agent = message_content.get("source_agent")
                
                self.logger.log_action("routed_task_received", {
                    "task_id": task_id,
                    "category": category,
                    "source_agent": source_agent
                })
                
                # タスクをアサイン
                task = {
                    "task_id": task_id,
                    "category": category,
                    "source_agent": source_agent
                }
                self.assigned_tasks.append(task)
                self.current_task = task
                
                self.logger.log_state_change("routed_task_accepted", {
                    "task_id": task_id,
                    "category": category,
                    "assigned_tasks_count": len(self.assigned_tasks)
                })
                
                response = {
                    "response": "routed_task_accepted",
                    "task_id": task_id
                }
                self.logger.log_message(response, "sent")
                return response

            elif message_type == "delegated_subtask":
                # 委任されたサブタスクの処理
                parent_task_id = message_content.get("parent_task_id")
                subtask_id = message_content.get("subtask_id")
                description = message_content.get("description")
                
                self.logger.log_action("delegated_subtask_received", {
                    "parent_task_id": parent_task_id,
                    "subtask_id": subtask_id,
                    "description": description
                })
                
                # サブタスクを処理
                self.logger.log_action("processing_subtask", {
                    "subtask_id": subtask_id
                })
                
                # 処理完了
                response = {
                    "response": "subtask_completed",
                    "parent_task_id": parent_task_id,
                    "subtask_id": subtask_id,
                    "result": "サブタスク処理が完了しました"
                }
                self.logger.log_message(response, "sent")
                return response

            elif message_type == "error_prone_task":
                # エラーが発生しやすいタスクの処理
                task_id = message_content.get("task_id")
                error_probability = message_content.get("error_probability", 0)
                description = message_content.get("description")
                
                self.logger.log_action("error_prone_task_received", {
                    "task_id": task_id,
                    "error_probability": error_probability,
                    "description": description
                })
                
                # エラー検出
                self.logger.log_action("error_detected", {
                    "task_id": task_id,
                    "reason": "high_error_probability",
                    "error_probability": error_probability
                })
                
                response = {
                    "response": "error_detected",
                    "task_id": task_id,
                    "error_details": {
                        "type": "high_error_probability",
                        "probability": error_probability
                    }
                }
                self.logger.log_message(response, "sent")
                return response
                
            elif message_type == "error_correction":
                # エラー修正の適用
                task_id = message_content.get("task_id")
                correction_strategy = message_content.get("correction_strategy")
                params = message_content.get("params", {})
                
                self.logger.log_action("error_correction_received", {
                    "task_id": task_id,
                    "correction_strategy": correction_strategy,
                    "params": params
                })
                
                # 修正を適用
                self.logger.log_action("correction_applied", {
                    "task_id": task_id,
                    "strategy": correction_strategy
                })
                
                response = {
                    "response": "correction_applied",
                    "task_id": task_id,
                    "applied_strategy": correction_strategy
                }
                self.logger.log_message(response, "sent")
                return response
                
            elif message_type == "rerun_task":
                # 修正後のタスク再実行
                task_id = message_content.get("task_id")
                description = message_content.get("description")
                
                self.logger.log_action("task_rerun", {
                    "task_id": task_id,
                    "description": description
                })
                
                # 成功
                self.logger.log_action("task_completed_after_correction", {
                    "task_id": task_id
                })
                
                response = {
                    "response": "task_completed_after_correction",
                    "task_id": task_id,
                    "result": "タスクが修正後に正常に完了しました"
                }
                self.logger.log_message(response, "sent")
                return response

            elif message_type == "analysis_request":
                # 分析リクエストの処理
                task_id = message_content.get("task_id")
                analysis_type = message_content.get("analysis_type")
                data = message_content.get("data", {})
                
                self.logger.log_action("analysis_request_received", {
                    "task_id": task_id,
                    "analysis_type": analysis_type,
                    "data": data
                })
                
                # 分析を実行
                self.logger.log_action("analysis_performed", {
                    "task_id": task_id,
                    "analysis_type": analysis_type
                })
                
                # 分析結果
                response = {
                    "response": "analysis_complete",
                    "task_id": task_id,
                    "analysis_type": analysis_type,
                    "result": {
                        "risk_level": "medium",
                        "confidence": 0.75,
                        "factors_analyzed": data.get("risk_factors", [])
                    }
                }
                self.logger.log_message(response, "sent")
                return response

            elif message_type == "status_check":
                # 状態報告
                self.logger.log_action("status_check", {
                    "active_tasks_count": len(self.assigned_tasks)
                })
                response = {
                    "response": "status_report",
                    "status": "ready",
                    "active_tasks": len(self.assigned_tasks),
                    "completed_tasks": [],
                    "assigned_tasks": [task.get("task_id") for task in self.assigned_tasks]
                }
                self.logger.log_message(response, "sent")
                return response

            else:
                # 未知のメッセージタイプ
                self.logger.log_error("unknown_message_type", {
                    "message_type": message_type
                })
                response = {"response": "unknown_message_type", "error": f"Unknown message type: {message_type}"}
                self.logger.log_message(response, "sent")
                return response

        except Exception as e:
            self.logger.log_error("process_error", {
                "message_type": message_type,
                "error": str(e)
            }, exc_info=e)
            response = {"response": "error", "error": str(e)}
            self.logger.log_message(response, "sent")
            return response

    async def initialize(self):
        """初期化処理"""
        self.logger.log_action("initialization", {"agent_id": "test_agent_b"})
        return True

    async def cleanup(self):
        """クリーンアップ処理"""
        self.logger.log_action("cleanup", {"agent_id": "test_agent_b"})
        return True 