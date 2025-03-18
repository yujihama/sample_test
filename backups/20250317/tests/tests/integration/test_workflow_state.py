#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ワークフロー状態管理機能の統合テスト
"""

import os
import json
import unittest
import logging
import tempfile
from pathlib import Path
import sys
import uuid
import gzip
import shutil
import time

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# テスト対象のモジュールをインポート
from src.utils.workflow_state import (
    save_workflow_state,
    load_workflow_state,
    cleanup_old_states
)

# テストベースクラスをインポート
from tests.integration.test_base import BaseIntegrationTest

# ロガーのセットアップ
from src.utils.logger import setup_logger
logger = setup_logger("test_workflow_state")


class TestWorkflowState(BaseIntegrationTest):
    """ワークフロー状態管理機能の統合テスト"""
    
    def setUp(self):
        """各テストケースの初期化"""
        super().setUp()
        
        # テスト用のワークフロー状態が保存されるディレクトリを作成
        from tests.integration.test_config import TEST_WORKFLOW_STATES_DIR
        os.makedirs(TEST_WORKFLOW_STATES_DIR, exist_ok=True)
        
        # テスト前にディレクトリをクリーンアップ
        for file_path in Path(TEST_WORKFLOW_STATES_DIR).glob("test-*.json*"):
            try:
                file_path.unlink()
            except Exception as e:
                logger.warning(f"ファイルの削除に失敗しました: {file_path} - {e}")
    
    def test_save_and_load_workflow_state(self):
        """ワークフロー状態の保存と読み込みをテスト"""
        # テスト用のワークフロー状態を作成
        workflow_id = f"test-{uuid.uuid4()}"
        workflow_state = {
            "workflow_id": workflow_id,
            "status": "in_progress",
            "current_agent": "agent_a",
            "procedure_id": "proc-001",
            "procedure_text": "売掛金の残高確認を行い、差異を分析する",
            "sample_id": "sample-001",
            "outputs": {},
            "updated_at": "2025-03-16T12:00:00"
        }
        
        # ワークフロー状態を保存
        state_path = save_workflow_state(workflow_state)
        logger.info(f"ワークフロー状態を保存しました: {state_path}")
        
        # 保存されたファイルが存在することを確認
        self.assertTrue(os.path.exists(state_path))
        
        # ワークフロー状態を読み込み
        loaded_state = load_workflow_state(workflow_id)
        logger.info(f"ワークフロー状態を読み込みました: {loaded_state}")
        
        # 読み込んだ状態が元の状態と一致することを確認
        self.assertEqual(loaded_state["workflow_id"], workflow_state["workflow_id"])
        self.assertEqual(loaded_state["status"], workflow_state["status"])
        self.assertEqual(loaded_state["current_agent"], workflow_state["current_agent"])
        self.assertEqual(loaded_state["procedure_id"], workflow_state["procedure_id"])
        self.assertEqual(loaded_state["procedure_text"], workflow_state["procedure_text"])
        self.assertEqual(loaded_state["sample_id"], workflow_state["sample_id"])
    
    def test_workflow_state_compression(self):
        """ワークフロー状態の圧縮と解凍をテスト"""
        # テスト用の大きなワークフロー状態を作成
        workflow_id = f"test-compress-{uuid.uuid4()}"
        
        # 大きなデータを生成（圧縮閾値を超えるサイズ）
        large_data = {f"key_{i}": "x" * 10000 for i in range(100)}
        
        workflow_state = {
            "workflow_id": workflow_id,
            "status": "in_progress",
            "current_agent": "agent_a",
            "procedure_id": "proc-001",
            "procedure_text": "売掛金の残高確認を行い、差異を分析する",
            "sample_id": "sample-001",
            "outputs": {},
            "large_data": large_data,
            "updated_at": "2025-03-16T12:00:00"
        }
        
        # ワークフロー状態を保存（自動的に圧縮される）
        state_path = save_workflow_state(workflow_state)
        logger.info(f"ワークフロー状態を保存しました: {state_path}")
        
        # 保存されたファイルが存在することを確認
        self.assertTrue(os.path.exists(state_path))
        
        # ファイルが圧縮されているかどうかを確認
        # 注意: 実装によっては圧縮されない場合もあるため、ファイル拡張子ではなくファイルサイズで判断
        file_size = os.path.getsize(state_path)
        json_size = len(json.dumps(workflow_state).encode('utf-8'))
        logger.info(f"ファイルサイズ: {file_size}, JSONサイズ: {json_size}")
        self.assertLess(file_size, json_size, "ファイルが圧縮されていません")
        
        # ワークフロー状態を読み込み
        loaded_state = load_workflow_state(workflow_id)
        logger.info(f"ワークフロー状態を読み込みました")
        
        # 読み込んだ状態が元の状態と一致することを確認
        self.assertEqual(loaded_state["workflow_id"], workflow_state["workflow_id"])
        self.assertEqual(loaded_state["status"], workflow_state["status"])
        self.assertEqual(loaded_state["current_agent"], workflow_state["current_agent"])
        self.assertEqual(loaded_state["large_data"], workflow_state["large_data"])
    
    def test_cleanup_old_states(self):
        """古いワークフロー状態のクリーンアップをテスト"""
        base_name = "test-cleanup"
        
        # テスト前にすべてのテストファイルを削除して初期状態をクリーンにする
        from tests.integration.test_config import TEST_WORKFLOW_STATES_DIR
        for file_path in Path(TEST_WORKFLOW_STATES_DIR).glob(f"{base_name}-*.json*"):
            try:
                file_path.unlink()
            except Exception as e:
                logger.warning(f"ファイルの削除に失敗しました: {file_path} - {e}")
        
        # テスト用のワークフロー状態ファイルを作成
        for i in range(15):
            workflow_id = f"{base_name}-{i}"
            workflow_state = {
                "workflow_id": workflow_id,
                "status": "in_progress",
                "current_agent": "agent_a",
                "procedure_id": "proc-001",
                "procedure_text": "売掛金の残高確認を行い、差異を分析する",
                "sample_id": "sample-001",
                "outputs": {},
                "updated_at": f"2025-03-16T{12+i:02d}:00:00"  # 時間を変えて作成
            }
            
            # ワークフロー状態を保存
            state_path = save_workflow_state(workflow_state)
            logger.info(f"ワークフロー状態を保存しました: {state_path}")
            
            # 少し待機して、ファイルの作成時間に差をつける
            time.sleep(0.1)
        
        # 現在のファイル数を確認
        all_files_before = list(Path(TEST_WORKFLOW_STATES_DIR).glob(f"{base_name}-*.json*"))
        self.assertEqual(len(all_files_before), 15, "作成されたファイル数が15ではありません")
        
        # ファイルの更新時間を明示的に設定（インデックスが小さいほど古い）
        now = time.time()
        for i in range(15):
            file_path = Path(TEST_WORKFLOW_STATES_DIR) / f"{base_name}-{i}.json"
            # インデックスが小さいほど古いタイムスタンプを設定
            # 1時間単位で古くなるように設定
            os.utime(file_path, (now, now - (15 - i) * 3600))
        
        # クリーンアップ前にワークフロー状態ディレクトリのパスを保存
        original_states_dir = os.environ.get("WORKFLOW_STATES_DIR", None)
        
        try:
            # テスト用のディレクトリを環境変数にセット
            os.environ["WORKFLOW_STATES_DIR"] = str(TEST_WORKFLOW_STATES_DIR)
            
            # クリーンアップを実行（最新の8個を残す）
            max_files = 8
            deleted_count = cleanup_old_states(
                max_files=max_files,
                max_age_days=0  # 日数制限は使用しない
            )
            
            # 削除されたファイル数を確認
            self.assertEqual(deleted_count, 15 - max_files, f"削除されたファイル数が正しくありません。期待: {15 - max_files}, 実際: {deleted_count}")
            
            # 残っているファイルを確認
            remaining_files = list(Path(TEST_WORKFLOW_STATES_DIR).glob(f"{base_name}-*.json*"))
            remaining_file_names = [file_path.name for file_path in remaining_files]
            logger.info(f"残っているファイル: {remaining_file_names}")
            
            # 残っているファイル数を確認
            self.assertEqual(len(remaining_files), max_files, f"残っているファイル数が{max_files}ではありません。実際: {len(remaining_files)}, ファイル: {remaining_file_names}")
            
            # 最新のファイルが残っていることを確認
            # 作成時間が新しい（インデックスが大きい）ファイルが残っているはず
            expected_remaining = [f"{base_name}-{i}.json" for i in range(7, 15)]
            for file_name in expected_remaining:
                file_path = Path(TEST_WORKFLOW_STATES_DIR) / file_name
                self.assertTrue(file_path.exists(), f"ファイル {file_name} が見つかりません")
            
            # 古いファイルが削除されていることを確認
            expected_deleted = [f"{base_name}-{i}.json" for i in range(0, 7)]
            for file_name in expected_deleted:
                file_path = Path(TEST_WORKFLOW_STATES_DIR) / file_name
                self.assertFalse(file_path.exists(), f"ファイル {file_name} が削除されていません")
        
        finally:
            # 環境変数を元に戻す
            if original_states_dir:
                os.environ["WORKFLOW_STATES_DIR"] = original_states_dir
            else:
                os.environ.pop("WORKFLOW_STATES_DIR", None)


if __name__ == "__main__":
    unittest.main() 