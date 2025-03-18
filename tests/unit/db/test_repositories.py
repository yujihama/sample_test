"""
リポジトリクラスのテスト

データアクセスレイヤーの動作確認のためのテスト
"""

import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
import json
from uuid import uuid4
from sqlalchemy import text

# テスト環境設定
os.environ["ENV"] = "test"
os.environ["SKIP_MIGRATIONS"] = "1"

# プロジェクトルートを追加
project_root = Path(__file__).parents[2].absolute()
sys.path.append(str(project_root))

from src.utils.db_manager import engine, session_scope, init_db
from src.models.db_models import Base, AuditProcedure, Workflow, AgentState
from src.models.repositories import (
    audit_procedure_repository,
    workflow_repository,
    agent_state_repository,
    sample_data_repository,
    audit_result_repository,
)


class TestRepositories(unittest.TestCase):
    """リポジトリクラスのテスト"""
    
    @classmethod
    def setUpClass(cls):
        """テストクラスのセットアップ"""
        # テスト用のDBスキーマを初期化
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    
    @classmethod
    def tearDownClass(cls):
        """テストクラスのクリーンアップ"""
        Base.metadata.drop_all(bind=engine)
    
    def setUp(self):
        """各テストのセットアップ"""
        # テストごとにデータをクリア
        self.clean_tables()
    
    def clean_tables(self):
        """テーブルのデータをクリア"""
        with session_scope() as session:
            for table in reversed(Base.metadata.sorted_tables):
                # SQLAlchemy 2.0でのテキストSQL実行方法
                session.execute(text(f"DELETE FROM {table.name}"))
    
    def test_audit_procedure_repository(self):
        """監査手続きリポジトリのテスト"""
        # 監査手続きの作成
        procedure_data = {
            "title": "テスト監査手続き",
            "description": "これはテスト用の監査手続きです",
            "risk_areas": ["財務", "コンプライアンス"],
            "required_data_fields": ["申請日", "金額", "承認者"]
        }
        
        with session_scope() as session:
            # 作成
            created_procedure = audit_procedure_repository.create(session, procedure_data)
            self.assertIsNotNone(created_procedure.id)
            self.assertEqual(created_procedure.title, "テスト監査手続き")
            
            # 取得
            fetched_procedure = audit_procedure_repository.get(session, created_procedure.id)
            self.assertEqual(fetched_procedure.title, created_procedure.title)
            
            # タイトルで取得
            by_title = audit_procedure_repository.get_by_title(session, "テスト監査手続き")
            self.assertEqual(by_title.id, created_procedure.id)
            
            # 更新
            updated_data = {"description": "更新された説明"}
            updated_procedure = audit_procedure_repository.update(
                session, db_obj=fetched_procedure, obj_in=updated_data
            )
            self.assertEqual(updated_procedure.description, "更新された説明")
            
            # 複数取得
            procedures = audit_procedure_repository.get_multi(session)
            self.assertEqual(len(procedures), 1)
    
    def test_agent_state_repository(self):
        """エージェント状態リポジトリのテスト"""
        agent_id = "agent-test"
        
        # テストデータ
        test_id = str(uuid4())
        test_date = datetime.now(timezone.utc).isoformat()
        test_values = [1, 2, 3, 4, 5]
        
        # ステートデータの作成
        state_data = {
            "status": "running",
            "progress": 50,
            "context": {
                "test_id": test_id,
                "test_date": test_date,
                "test_values": test_values
            }
        }
        
        with session_scope() as session:
            # エージェント状態の保存
            created_state = agent_state_repository.save_agent_state(session, agent_id, state_data)
            self.assertIsNotNone(created_state.id)
            self.assertEqual(created_state.agent_id, agent_id)
            self.assertEqual(created_state.status, "running")
            self.assertEqual(created_state.progress, 50)
            
            # 状態の取得
            fetched_state = agent_state_repository.get_by_agent_id(session, agent_id)
            self.assertEqual(fetched_state.id, created_state.id)
            
            # コンテキストの検証
            self.assertIsNotNone(fetched_state.context)
            self.assertIn("test_id", fetched_state.context)
            self.assertEqual(fetched_state.context["test_id"], test_id)
            self.assertEqual(len(fetched_state.context["test_values"]), 5)
            
            # 状態の更新
            updated_data = {
                "status": "completed",
                "progress": 100,
                "context": {
                    "result": "成功",
                    "execution_time": 1.23
                }
            }
            
            updated_state = agent_state_repository.save_agent_state(session, agent_id, updated_data)
            self.assertEqual(updated_state.status, "completed")
            self.assertEqual(updated_state.progress, 100)
            self.assertIn("result", updated_state.context)
            self.assertEqual(updated_state.context["result"], "成功")
    
    def test_workflow_repository(self):
        """ワークフローリポジトリのテスト"""
        # 監査手続きの作成とワークフローの作成を同じセッション内で行う
        with session_scope() as session:
            # 事前条件として監査手続きを作成
            procedure_data = {
                "title": "テストワークフロー手続き",
                "description": "これはテスト用です",
                "risk_areas": ["テスト領域"]
            }
            procedure = audit_procedure_repository.create(session, procedure_data)
            
            # ワークフローの作成
            workflow_data = {
                "procedure_id": procedure.id,
                "status": "in_progress",
                "current_agent": "agent-a",
                "progress": 25
            }
            
            # 作成
            created_workflow = workflow_repository.create(session, workflow_data)
            self.assertIsNotNone(created_workflow.id)
            self.assertEqual(created_workflow.status, "in_progress")
            
            # IDで取得
            fetched_workflow = workflow_repository.get(session, created_workflow.id)
            self.assertEqual(fetched_workflow.procedure_id, procedure.id)
            
            # 進行中のワークフローを取得
            active_workflows = workflow_repository.get_active_workflows(session)
            self.assertEqual(len(active_workflows), 1)
            
            # 更新
            updated_data = {"status": "completed", "progress": 100}
            updated_workflow = workflow_repository.update(
                session, db_obj=fetched_workflow, obj_in=updated_data
            )
            self.assertEqual(updated_workflow.status, "completed")
            self.assertEqual(updated_workflow.progress, 100)
            
            # 再度進行中のワークフローを取得（完了したのでゼロになるはず）
            active_workflows = workflow_repository.get_active_workflows(session)
            self.assertEqual(len(active_workflows), 0)


if __name__ == "__main__":
    unittest.main() 