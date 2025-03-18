#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
データベース接続疎通テスト

このスクリプトは、データベース接続機能が基本的に動作しているかを確認する疎通テストです。
実際の詳細な機能テストではなく、システムの基本的な機能が動作しているかを迅速に確認することが目的です。
"""

import os
import sys
import pytest
from sqlalchemy import text

# src ディレクトリをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

class TestDatabaseConnection:
    """データベース接続の疎通テスト"""

    def test_db_connection_available(self):
        """データベース接続が利用可能かをテストする"""
        try:
            from src.utils.db_manager import get_db
            
            # データベースセッションの取得
            db_gen = get_db()
            db = next(db_gen)
            
            # 基本的なクエリを実行
            result = db.execute(text("SELECT 1 AS test")).fetchone()
            
            # セッションを閉じる
            try:
                next(db_gen)
            except StopIteration:
                pass
                
            assert result[0] == 1, "データベースクエリの結果が期待値と一致しません"
            
        except Exception as e:
            pytest.fail(f"データベース接続でエラーが発生しました: {str(e)}")

    def test_main_tables_exist(self):
        """主要なテーブルが存在するかをテストする"""
        try:
            from src.utils.db_manager import get_db
            
            # データベースセッションの取得
            db_gen = get_db()
            db = next(db_gen)
            
            # テーブル一覧を取得
            tables = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
            tables_list = [table[0] for table in tables] if tables else []
            
            # 主要なテーブルのリスト（プロジェクトに合わせて調整）
            required_tables = [
                'workflows', 
                'audit_procedures', 
                'audit_results',
                'agent_states'
            ]
            
            # 主要なテーブルが存在するか確認
            for table in required_tables:
                assert table in tables_list, f"必須テーブル '{table}' が存在しません"
            
            # セッションを閉じる
            try:
                next(db_gen)
            except StopIteration:
                pass
                
        except Exception as e:
            pytest.fail(f"テーブル確認でエラーが発生しました: {str(e)}")

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 