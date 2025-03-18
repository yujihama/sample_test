#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ワークフロー状態の永続化と復元、およびAgent Aノードの機能テスト
"""

import os
import sys
import uuid
import json
import logging
import unittest
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

# テスト対象のモジュールのためのパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.agent_a import AgentA, agent_a_node
from src.utils.workflow_state import (
    save_workflow_state,
    load_workflow_state,
    cleanup_old_states,
    compress_workflow_state,
    decompress_workflow_state
)
from src.utils.logger import setup_logger
from tests.workflow.mock_repositories import MockSampleDataRepository, mock_get_db

# ロガーのセットアップ
logger = setup_logger("test_workflow_state")

class TestWorkflowState(unittest.TestCase):
    """ワークフロー状態とAgent Aのテスト"""

    def setUp(self):
        """テスト環境のセットアップ"""
        # 一時ディレクトリを作成
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workflow_dir = Path(self.temp_dir.name) / "workflows"
        self.workflow_dir.mkdir(exist_ok=True)
        
        # ワークフローIDを設定
        self.workflow_id = f"test-workflow-{uuid.uuid4().hex[:8]}"
        
        # モックリポジトリの設定
        self.sample_repo = MockSampleDataRepository()
        
        # テストデータの追加
        self.sample_id = self.sample_repo.create(None, {
            "name": "テスト勘定科目データ",
            "description": "テスト用の売掛金明細データ",
            "data_source": "test_csv"
        })
        
        # 基本的なワークフロー状態を作成
        self.workflow_state = {
            "workflow_id": self.workflow_id,
            "status": "started",
            "current_step": "initial",
            "sample_data_id": self.sample_id,
            "progress": 0,
            "agents": {
                "agent_a": {
                    "status": "waiting",
                    "data": {},
                    "history": []
                },
                "agent_b": {
                    "status": "not_started",
                    "data": {},
                    "history": []
                }
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.temp_dir.cleanup()

    def test_save_and_load_workflow_state(self):
        """ワークフロー状態の保存と読み込みのテスト"""
        # パスのモックを設定
        with patch("src.utils.workflow_state.WORKFLOW_STATES_DIR", self.workflow_dir):
            # 状態を保存
            file_path = save_workflow_state(self.workflow_state)
            logger.info(f"ワークフロー状態を保存: {file_path}")
            
            # ファイルが存在するか確認
            self.assertTrue(os.path.exists(file_path))
            
            # 状態を読み込み
            loaded_state = load_workflow_state(self.workflow_id)
            logger.info(f"ワークフロー状態を読み込み: {loaded_state['workflow_id']}")
            
            # 読み込んだ状態が元の状態と一致するか確認
            self.assertEqual(loaded_state["workflow_id"], self.workflow_state["workflow_id"])
            self.assertEqual(loaded_state["status"], self.workflow_state["status"])
            self.assertEqual(loaded_state["sample_data_id"], self.workflow_state["sample_data_id"])

    def test_compress_and_decompress_workflow_state(self):
        """ワークフロー状態の圧縮と展開のテスト"""
        # 大きなデータを含む状態を作成
        large_data = {"large_array": ["item" * 1000] * 100}
        self.workflow_state["agents"]["agent_a"]["data"] = large_data
        
        # 状態を圧縮
        compressed_state = compress_workflow_state(self.workflow_state)
        logger.info(f"圧縮前のサイズ: {len(json.dumps(self.workflow_state))} バイト")
        logger.info(f"圧縮後のサイズ: {len(compressed_state)} バイト")
        
        # 圧縮されたことを確認
        self.assertLess(len(compressed_state), len(json.dumps(self.workflow_state)))
        
        # 状態を展開
        decompressed_state = decompress_workflow_state(compressed_state)
        
        # 展開後の状態が元の状態と一致するか確認
        self.assertEqual(decompressed_state["workflow_id"], self.workflow_state["workflow_id"])
        self.assertIn("large_array", decompressed_state["agents"]["agent_a"]["data"])
        self.assertEqual(
            len(decompressed_state["agents"]["agent_a"]["data"]["large_array"]),
            len(self.workflow_state["agents"]["agent_a"]["data"]["large_array"])
        )

    def test_cleanup_old_states(self):
        """古いワークフロー状態のクリーンアップテスト"""
        with patch("src.utils.workflow_state.WORKFLOW_STATES_DIR", self.workflow_dir):
            # 複数のワークフロー状態を作成
            for i in range(5):
                workflow_id = f"test-workflow-{i}"
                state = self.workflow_state.copy()
                state["workflow_id"] = workflow_id
                save_workflow_state(state)
            
            # クリーンアップを実行
            deleted_count = cleanup_old_states(max_age_days=0, max_files=3)
            logger.info(f"削除されたワークフロー状態ファイル数: {deleted_count}")
            
            # クリーンアップ後のファイル数を確認
            remaining_files = list(self.workflow_dir.glob("*.json"))
            self.assertLessEqual(len(remaining_files), 3)

    @patch("src.utils.data_analyzer.analyze_sample_data")
    @patch("src.models.repositories.SampleDataRepository")
    @patch("src.utils.db_manager.get_db", mock_get_db)
    def test_agent_a_node(self, mock_sample_repo_class, mock_analyze):
        """Agent Aノード関数のテスト"""
        # モックを設定
        mock_sample_repo = MagicMock()
        mock_sample = MagicMock()
        mock_sample.id = self.sample_id
        mock_sample.name = "テスト勘定科目データ"
        mock_sample.description = "テスト用の売掛金明細データ"
        mock_sample.data_source = "test_csv"
        mock_sample.data = {
            "accounts_receivable": [
                {"customer_id": "C001", "customer_name": "株式会社A", "balance": 5000000, "due_date": "2023-12-31"},
                {"customer_id": "C002", "customer_name": "株式会社B", "balance": 3500000, "due_date": "2023-12-15"}
            ]
        }
        
        mock_sample_repo.get.return_value = mock_sample
        mock_sample_repo_class.return_value = mock_sample_repo
        
        # 分析結果のモックを設定
        mock_analyze.return_value = {
            "summary": "テスト分析結果",
            "statistics": {
                "total_rows": 100,
                "total_amount": 1000000
            },
            "issues": [
                {"severity": "medium", "description": "テスト用の問題点"}
            ]
        }
        
        # エージェントAのノードを実行
        workflow_state = self.workflow_state.copy()
        
        # get_db関数をモック
        with patch("src.agents.agent_a.get_db", mock_get_db):
            result = agent_a_node(workflow_state)
        
        # 結果を検証
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["agents"]["agent_a"]["status"], "completed")
        self.assertIn("statistics", result["agents"]["agent_a"]["data"])
        self.assertIn("issues", result["agents"]["agent_a"]["data"])
        
        logger.info(f"Agent Aノード実行結果: {json.dumps(result['agents']['agent_a']['data'], indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    unittest.main() 