#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ワークフロー初期化疎通テスト

このスクリプトは、ワークフローの初期化処理が基本的に機能するかを確認する疎通テストです。
詳細な機能テストではなく、ワークフロー関連の基本的なコンポーネントが動作することを確認します。
"""

import os
import sys
import pytest
from datetime import datetime

# src ディレクトリをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 前提条件のスキップフラグ
skip_tests = False
reason = ""

# 必要なモジュールのインポート
try:
    from src.core.workflow import create_workflow_state
    from src.utils.db_manager import get_db
    from sqlalchemy import text
except ImportError as e:
    skip_tests = True
    reason = f"必要なモジュールのインポートに失敗しました: {e}"

class TestWorkflowInit:
    """ワークフロー初期化の疎通テスト"""

    def setup_method(self):
        """各テストの前に実行されるセットアップ"""
        if skip_tests:
            pytest.skip(reason)
    
    def test_create_workflow_state(self):
        """ワークフロー状態の作成機能をテスト"""
        try:
            # 最小限のパラメータでワークフロー状態を作成
            procedure_id = "test-proc-001"
            procedure_text = "テスト用監査手続き"
            sample_id = "test-sample-001"
            data_source = "test_db"
            
            # ワークフロー状態の作成
            workflow_state = create_workflow_state(
                procedure_id=procedure_id,
                procedure_text=procedure_text,
                sample_id=sample_id,
                data_source=data_source
            )
            
            # 基本的なプロパティの確認
            assert "procedure_id" in workflow_state, "ワークフロー状態にprocedure_idがありません"
            assert workflow_state["procedure_id"] == procedure_id, "procedure_idが正しく設定されていません"
            assert "procedure_text" in workflow_state, "ワークフロー状態にprocedure_textがありません"
            assert "sample_id" in workflow_state, "ワークフロー状態にsample_idがありません"
            assert "data_source" in workflow_state, "ワークフロー状態にdata_sourceがありません"
            assert "workflow_id" in workflow_state, "ワークフロー状態にworkflow_idがありません"
            assert "status" in workflow_state, "ワークフロー状態にstatusがありません"
            assert workflow_state["status"] == "initialized", "ステータスが'initialized'ではありません"
            
        except Exception as e:
            pytest.fail(f"ワークフロー状態の作成でエラーが発生しました: {str(e)}")
    
    def test_workflow_table_exists(self):
        """ワークフローテーブルが存在するかテスト"""
        try:
            # データベースセッションの取得
            db_gen = get_db()
            db = next(db_gen)
            
            # テーブル一覧を取得
            tables = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
            tables_list = [table[0] for table in tables] if tables else []
            
            # ワークフローテーブルが存在するか確認
            assert "workflows" in tables_list, "ワークフローテーブルが存在しません"
            
            # カラム一覧を取得
            columns = db.execute(text("PRAGMA table_info(workflows)")).fetchall()
            column_names = [col[1] for col in columns] if columns else []
            
            # 必須カラムが存在するか確認
            assert "id" in column_names, "workflowsテーブルにidカラムがありません"
            assert "status" in column_names, "workflowsテーブルにstatusカラムがありません"
            assert "current_agent" in column_names, "workflowsテーブルにcurrent_agentカラムがありません"
            
            # セッションを閉じる
            try:
                next(db_gen)
            except StopIteration:
                pass
                
        except Exception as e:
            pytest.fail(f"ワークフローテーブルの確認でエラーが発生しました: {str(e)}")

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 