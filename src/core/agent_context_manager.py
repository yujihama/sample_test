#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
エージェント間コンテキスト共有管理モジュール

このモジュールでは、複数のエージェントのLangGraphベース状態遷移グラフ間で
コンテキスト情報を共有・管理する機能を提供します。各エージェントの状態を
監視し、必要に応じて情報を共有するブリッジとして機能します。
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Type, Set, Union, cast
from loguru import logger

from langgraph.graph import StateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver

from src.services.graph_executor import GraphExecutor
from src.agents.agent_a_graph import get_agent_a_graph, AgentAGraphState
from src.agents.agent_b_graph import get_agent_b_graph, AgentBGraphState
from src.agents.agent_c_graph import get_agent_c_graph, AgentCGraphState
from src.agents.agent_d_graph import get_agent_d_graph, AgentDGraphState

# AuditContextとAuditContextStatusのモック
class AuditContext:
    """監査コンテキストのモッククラス"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', str(uuid.uuid4()))
        self.workflow_id = kwargs.get('workflow_id', '')
        self.status = kwargs.get('status', 'ACTIVE')
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.context_data = kwargs.get('context_data', {})

class AuditContextStatus:
    """監査コンテキストステータスの列挙型モック"""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PENDING = "PENDING"

class AgentContextManager:
    """
    エージェント間コンテキスト共有マネージャー
    
    複数のエージェントのグラフ状態を管理し、エージェント間で
    コンテキスト情報を共有する機能を提供します。また、監査全体の
    コンテキストを追跡し、ユーザーに進捗状況を提供します。
    """
    
    def __init__(self, checkpoint_saver: Optional[BaseCheckpointSaver] = None):
        """
        初期化
        
        Args:
            checkpoint_saver: チェックポイント保存用のインスタンス（オプション）
        """
        self.graph_executors = {
            "agent_a": GraphExecutor(get_agent_a_graph(), checkpoint_saver),
            "agent_b": GraphExecutor(get_agent_b_graph(), checkpoint_saver),
            "agent_c": GraphExecutor(get_agent_c_graph(), checkpoint_saver),
            "agent_d": GraphExecutor(get_agent_d_graph(), checkpoint_saver)
        }
        
        # 監査コンテキスト情報の保存用辞書
        self.audit_contexts: Dict[str, Dict[str, Any]] = {}
        
        # コンテキスト情報のマッピング定義
        # 各エージェント間で共有する情報の対応関係を定義
        self.context_mappings = {
            "agent_a_to_agent_b": {
                "test_plan": "collected_info.test_plan",
                "procedure_understanding": "collected_info.procedure_understanding"
            },
            "agent_b_to_agent_c": {
                "solution": "test_results",
                "solution_evaluation": "collected_info.solution_evaluation"
            },
            "agent_c_to_agent_d": {
                "summary": "audit_summary",
                "compliance_evaluation": "collected_info.compliance_evaluation"
            },
            "agent_a_to_agent_d": {
                "procedure_understanding": "collected_info.procedure_details",
                "test_plan": "collected_info.test_plan_details"
            }
        }
        
        logger.info("AgentContextManager初期化完了")
    
    async def create_audit_context(self, audit_id: str, title: str, description: str) -> str:
        """
        新しい監査コンテキストを作成
        
        Args:
            audit_id: 監査ID
            title: 監査タイトル
            description: 監査の説明
            
        Returns:
            作成されたコンテキストID
        """
        context_id = f"ctx-{uuid.uuid4().hex[:8]}"
        
        # 監査コンテキスト情報を作成
        context_info = {
            "id": context_id,
            "audit_id": audit_id,
            "title": title,
            "description": description,
            "status": "in_progress",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "agent_states": {},
            "shared_context": {},
            "workflow_ids": {}
        }
        
        # コンテキスト情報を保存
        self.audit_contexts[context_id] = context_info
        
        logger.info(f"監査コンテキスト作成: {context_id} (監査ID: {audit_id})")
        return context_id
    
    async def get_audit_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """
        監査コンテキスト情報を取得
        
        Args:
            context_id: コンテキストID
            
        Returns:
            コンテキスト情報、存在しない場合はNone
        """
        return self.audit_contexts.get(context_id)
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """
        ネストされた辞書からパスに基づいて値を取得
        
        Args:
            data: 対象のデータ辞書
            path: ドット区切りのパス (例: "collected_info.test_plan")
            
        Returns:
            パスに対応する値、存在しない場合はNone
        """
        keys = path.split(".")
        result = data
        
        for key in keys:
            if isinstance(result, dict) and key in result:
                result = result[key]
            else:
                return None
                
        return result
    
    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """
        ネストされた辞書のパスに値を設定
        
        Args:
            data: 対象のデータ辞書
            path: ドット区切りのパス (例: "collected_info.test_plan")
            value: 設定する値
        """
        keys = path.split(".")
        current = data
        
        # 最後のキーを除いたパスを走査して必要なディクショナリを作成
        for i, key in enumerate(keys[:-1]):
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        
        # 最後のキーに値を設定
        current[keys[-1]] = value
    
    async def _share_context_between_agents(
        self, from_agent: str, to_agent: str, 
        from_state: Dict[str, Any], context_id: str
    ) -> None:
        """
        エージェント間でコンテキスト情報を共有する内部メソッド
        
        Args:
            from_agent: 共有元エージェントID
            to_agent: 共有先エージェントID
            from_state: 共有元の状態
            context_id: 監査コンテキストID
        """
        # エラーチェック
        if context_id not in self.audit_contexts:
            logger.error(f"コンテキスト {context_id} が見つかりません")
            return
        
        if from_agent == to_agent:
            logger.warning(f"同一エージェント間での共有はスキップします: {from_agent}")
            return
        
        # マッピング定義の取得
        mapping_key = f"{from_agent}_to_{to_agent}"
        if mapping_key not in self.context_mappings:
            logger.warning(f"マッピング定義が見つかりません: {mapping_key}")
            return
        
        mappings = self.context_mappings[mapping_key]
        
        # 共有情報の構築
        shared_info = {}
        for from_path, to_path in mappings.items():
            # ネストされたパスから値を取得
            value = self._get_nested_value(from_state, from_path)
            if value is not None:
                # 値を共有先のパスにマッピング
                self._set_nested_value(shared_info, to_path, value)
        
        # 共有情報が空の場合はスキップ
        if not shared_info:
            logger.debug(f"{from_agent} から {to_agent} への共有情報はありません")
            return
        
        # 共有先のワークフローIDを取得
        to_workflow_id = None
        if to_agent in self.audit_contexts[context_id]["workflow_ids"]:
            to_workflow_id = self.audit_contexts[context_id]["workflow_ids"][to_agent]
        
        # 共有先のワークフローがない場合はスキップ
        if not to_workflow_id:
            logger.warning(f"共有先ワークフロー {to_agent} が見つかりません")
            return
        
        # 共有先に情報を送信
        try:
            # 共有先のワークフロー状態を取得
            to_graph_executor = self.graph_executors[to_agent]
            
            # 共有情報をイベントとして送信
            event = {
                "event_type": "context_sharing",
                "from_agent": from_agent,
                "payload": {
                    "shared_context": shared_info
                }
            }
            
            # イベントを処理
            await to_graph_executor.process_event(to_workflow_id, event)
            
            # 共有履歴を記録
            timestamp = datetime.now().isoformat()
            history_key = f"{from_agent}_{to_agent}_{timestamp}"
            
            self.audit_contexts[context_id]["shared_context"][history_key] = {
                "from": from_agent,
                "to": to_agent,
                "data": shared_info,
                "timestamp": timestamp
            }
            
            # 監査証跡への記録
            await self._record_context_sharing(
                context_id=context_id,
                from_agent=from_agent,
                to_agent=to_agent,
                shared_data=shared_info,
                from_workflow_id=self.audit_contexts[context_id]["workflow_ids"].get(from_agent),
                to_workflow_id=to_workflow_id
            )
            
            logger.info(f"コンテキスト情報を共有しました: {from_agent} -> {to_agent}")
            
        except Exception as e:
            logger.error(f"コンテキスト共有中にエラーが発生しました: {str(e)}")
    
    async def _record_context_sharing(
        self,
        context_id: str,
        from_agent: str,
        to_agent: str,
        shared_data: Dict[str, Any],
        from_workflow_id: Optional[str] = None,
        to_workflow_id: Optional[str] = None
    ) -> None:
        """
        エージェント間のコンテキスト共有を監査証跡に記録
        
        Args:
            context_id: 監査コンテキストID
            from_agent: 共有元エージェントID
            to_agent: 共有先エージェントID
            shared_data: 共有されたデータ
            from_workflow_id: 共有元ワークフローID
            to_workflow_id: 共有先ワークフローID
        """
        try:
            # グラフ状態履歴リポジトリを取得
            from src.utils.db_manager import get_db_session
            from src.models.repositories import get_graph_state_history_repository
            
            db = next(get_db_session())
            history_repo = get_graph_state_history_repository(db)
            
            # 送信元の記録
            if from_workflow_id:
                history_repo.create(
                    workflow_id=from_workflow_id,
                    context_id=context_id,
                    agent_id=from_agent,
                    node_id="context_sharing",
                    transition_from=None,
                    transition_to=None,
                    state_snapshot=None,
                    state_diff=None,
                    event_type="context_sharing_out",
                    event_data={
                        "to_agent": to_agent,
                        "shared_data": shared_data,
                        "to_workflow_id": to_workflow_id
                    }
                )
            
            # 送信先の記録
            if to_workflow_id:
                history_repo.create(
                    workflow_id=to_workflow_id,
                    context_id=context_id,
                    agent_id=to_agent,
                    node_id="context_sharing",
                    transition_from=None,
                    transition_to=None,
                    state_snapshot=None,
                    state_diff=None,
                    event_type="context_sharing_in",
                    event_data={
                        "from_agent": from_agent,
                        "shared_data": shared_data,
                        "from_workflow_id": from_workflow_id
                    }
                )
            
            db.close()
            logger.debug(f"コンテキスト共有を記録しました: {from_agent} -> {to_agent}")
        
        except Exception as e:
            logger.warning(f"コンテキスト共有の記録中にエラー: {e}")
    
    async def start_agent_workflow(
        self, agent_id: str, context_id: str, initial_state: Dict[str, Any]
    ) -> str:
        """
        エージェントのワークフローを開始
        
        Args:
            agent_id: エージェントID
            context_id: 監査コンテキストID
            initial_state: 初期状態
            
        Returns:
            作成されたワークフローID
        """
        if agent_id not in self.graph_executors:
            raise ValueError(f"エージェント {agent_id} が見つかりません")
        
        if context_id not in self.audit_contexts:
            raise ValueError(f"監査コンテキスト {context_id} が見つかりません")
        
        # ワークフローID生成と登録
        workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        self.audit_contexts[context_id]["workflow_ids"][agent_id] = workflow_id
        
        # 初期状態にコンテキスト情報を追加
        initial_state_with_context = initial_state.copy()
        initial_state_with_context["workflow_id"] = workflow_id
        initial_state_with_context["created_at"] = datetime.now().isoformat()
        initial_state_with_context["updated_at"] = datetime.now().isoformat()
        
        # ワークフロー作成
        await self.graph_executors[agent_id].create_workflow(workflow_id, initial_state_with_context)
        
        # エージェント状態を監査コンテキストに記録
        self.audit_contexts[context_id]["agent_states"][agent_id] = {
            "workflow_id": workflow_id,
            "status": "created",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        logger.info(f"エージェント {agent_id} ワークフロー開始: {workflow_id} (コンテキスト: {context_id})")
        return workflow_id
    
    async def process_agent_event(
        self, agent_id: str, context_id: str, event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        エージェントのイベントを処理し、結果をコンテキスト間で共有
        
        Args:
            agent_id: エージェントID
            context_id: 監査コンテキストID
            event: イベントデータ
            
        Returns:
            処理結果
        """
        if agent_id not in self.graph_executors:
            raise ValueError(f"エージェント {agent_id} が見つかりません")
        
        if context_id not in self.audit_contexts:
            raise ValueError(f"監査コンテキスト {context_id} が見つかりません")
        
        # ワークフローIDを取得
        workflow_id = self.audit_contexts[context_id]["workflow_ids"].get(agent_id)
        if not workflow_id:
            raise ValueError(f"エージェント {agent_id} のワークフローが見つかりません")
        
        # イベントをエージェントに処理させる
        result = await self.graph_executors[agent_id].process_event(workflow_id, event)
        
        # 処理後の状態を取得
        state = await self.graph_executors[agent_id].get_state(workflow_id)
        
        if state:
            # エージェント状態を監査コンテキストに更新
            self.audit_contexts[context_id]["agent_states"][agent_id].update({
                "status": state.get("status", "unknown"),
                "current_step": state.get("current_step", "unknown"),
                "updated_at": datetime.now().isoformat()
            })
            
            # 他のエージェントにコンテキストを共有
            for to_agent in self.graph_executors.keys():
                if to_agent != agent_id:
                    await self._share_context_between_agents(agent_id, to_agent, state, context_id)
        
        logger.info(f"エージェント {agent_id} イベント処理完了: {workflow_id} (コンテキスト: {context_id})")
        return result
    
    async def get_agent_state(
        self, agent_id: str, context_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        エージェントの現在の状態を取得
        
        Args:
            agent_id: エージェントID
            context_id: 監査コンテキストID
            
        Returns:
            エージェントの状態、存在しない場合はNone
        """
        if agent_id not in self.graph_executors:
            raise ValueError(f"エージェント {agent_id} が見つかりません")
        
        if context_id not in self.audit_contexts:
            raise ValueError(f"監査コンテキスト {context_id} が見つかりません")
        
        # ワークフローIDを取得
        workflow_id = self.audit_contexts[context_id]["workflow_ids"].get(agent_id)
        if not workflow_id:
            return None
        
        # 状態を取得
        return await self.graph_executors[agent_id].get_state(workflow_id)
    
    async def get_agent_checkpoints(
        self, agent_id: str, context_id: str
    ) -> List[Dict[str, Any]]:
        """
        エージェントのチェックポイント一覧を取得
        
        Args:
            agent_id: エージェントID
            context_id: 監査コンテキストID
            
        Returns:
            チェックポイントのリスト
        """
        if agent_id not in self.graph_executors:
            raise ValueError(f"エージェント {agent_id} が見つかりません")
        
        if context_id not in self.audit_contexts:
            raise ValueError(f"監査コンテキスト {context_id} が見つかりません")
        
        # ワークフローIDを取得
        workflow_id = self.audit_contexts[context_id]["workflow_ids"].get(agent_id)
        if not workflow_id:
            return []
        
        # チェックポイント一覧を取得
        return await self.graph_executors[agent_id].list_checkpoints(workflow_id)
    
    async def restore_agent_checkpoint(
        self, agent_id: str, context_id: str, checkpoint_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        エージェントの状態をチェックポイントから復元
        
        Args:
            agent_id: エージェントID
            context_id: 監査コンテキストID
            checkpoint_id: チェックポイントID
            
        Returns:
            復元された状態、失敗した場合はNone
        """
        if agent_id not in self.graph_executors:
            raise ValueError(f"エージェント {agent_id} が見つかりません")
        
        if context_id not in self.audit_contexts:
            raise ValueError(f"監査コンテキスト {context_id} が見つかりません")
        
        # ワークフローIDを取得
        workflow_id = self.audit_contexts[context_id]["workflow_ids"].get(agent_id)
        if not workflow_id:
            return None
        
        # チェックポイントを復元
        restored_state = await self.graph_executors[agent_id].restore_checkpoint(workflow_id, checkpoint_id)
        
        if restored_state:
            # 復元成功時は状態を更新
            self.audit_contexts[context_id]["agent_states"][agent_id].update({
                "status": restored_state.get("status", "unknown"),
                "current_step": restored_state.get("current_step", "unknown"),
                "updated_at": datetime.now().isoformat(),
                "restored_from_checkpoint": checkpoint_id
            })
            
            logger.info(f"エージェント {agent_id} チェックポイント復元: {checkpoint_id}")
        
        return restored_state
    
    async def get_audit_status(self, context_id: str) -> Dict[str, Any]:
        """
        監査の全体状況を取得
        
        Args:
            context_id: 監査コンテキストID
            
        Returns:
            監査の状況情報
        """
        if context_id not in self.audit_contexts:
            raise ValueError(f"監査コンテキスト {context_id} が見つかりません")
        
        context = self.audit_contexts[context_id]
        result = {
            "id": context["id"],
            "audit_id": context["audit_id"],
            "title": context["title"],
            "status": context["status"],
            "created_at": context["created_at"],
            "updated_at": context["updated_at"],
            "agents": {}
        }
        
        # 各エージェントの状態を取得
        for agent_id, state_info in context["agent_states"].items():
            workflow_id = state_info["workflow_id"]
            current_state = await self.graph_executors[agent_id].get_state(workflow_id)
            
            if current_state:
                result["agents"][agent_id] = {
                    "status": current_state.get("status", "unknown"),
                    "current_step": current_state.get("current_step", "unknown"),
                    "error": current_state.get("error"),
                    "updated_at": current_state.get("updated_at", state_info["updated_at"])
                }
            else:
                result["agents"][agent_id] = state_info
        
        # 全体の状態を計算
        agent_statuses = [info.get("status", "unknown") for info in result["agents"].values()]
        
        if all(status == "completed" for status in agent_statuses):
            result["status"] = "completed"
        elif any(status == "error" for status in agent_statuses):
            result["status"] = "error"
        elif any(status == "waiting_for_info" for status in agent_statuses):
            result["status"] = "waiting_for_info"
        else:
            result["status"] = "in_progress"
        
        # 監査コンテキストの状態も更新
        self.audit_contexts[context_id]["status"] = result["status"]
        self.audit_contexts[context_id]["updated_at"] = datetime.now().isoformat()
        
        return result
    
    async def get_context_sharing_history(
        self, context_id: str, from_agent: Optional[str] = None, to_agent: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        コンテキスト共有の履歴を取得
        
        Args:
            context_id: 監査コンテキストID
            from_agent: 送信元エージェント（フィルタリング用、オプション）
            to_agent: 送信先エージェント（フィルタリング用、オプション）
            
        Returns:
            共有履歴のリスト
        """
        if context_id not in self.audit_contexts:
            raise ValueError(f"監査コンテキスト {context_id} が見つかりません")
        
        # 共有履歴を取得
        shared_context = self.audit_contexts[context_id].get("shared_context", {})
        history = list(shared_context.values())
        
        # フィルタリング
        if from_agent:
            history = [item for item in history if item["from"] == from_agent]
        
        if to_agent:
            history = [item for item in history if item["to"] == to_agent]
        
        # タイムスタンプでソート
        return sorted(history, key=lambda x: x["timestamp"])


# シングルトンインスタンスを提供する関数
_context_manager_instance = None

def get_context_manager() -> AgentContextManager:
    """エージェントコンテキストマネージャーのシングルトンインスタンスを取得"""
    global _context_manager_instance
    if _context_manager_instance is None:
        _context_manager_instance = AgentContextManager()
    return _context_manager_instance 