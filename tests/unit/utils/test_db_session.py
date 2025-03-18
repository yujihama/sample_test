#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
データベースセッション管理のテスト
"""

import os
import sys
import pytest
from sqlalchemy.orm import Session
from sqlalchemy import text

# src ディレクトリをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# 必要なモジュールのインポート
from src.utils.db_manager import get_db, get_db_context, with_db_session


class TestDbSession:
    """データベースセッション管理テスト"""

    def test_get_db(self):
        """get_db関数が正しくセッションを返すかテスト"""
        db = get_db()
        try:
            # db が Session インスタンスであることを確認
            assert isinstance(db, Session), "get_db()がSessionインスタンスを返していません"
            
            # 簡単なクエリを実行して動作確認
            result = db.execute(text("SELECT 1")).scalar()
            assert result == 1, "セッションでの基本的なクエリが失敗しました"
        finally:
            db.close()

    def test_get_db_context(self):
        """get_db_context関数が正しく動作するかテスト"""
        with get_db_context() as db:
            # db が Session インスタンスであることを確認
            assert isinstance(db, Session), "get_db_context()がSessionインスタンスを返していません"
            
            # 簡単なクエリを実行して動作確認
            result = db.execute(text("SELECT 1")).scalar()
            assert result == 1, "コンテキストマネージャでのクエリが失敗しました"
        
        # コンテキスト終了後は自動的にクローズされているはず

    def test_with_db_session_decorator(self):
        """with_db_sessionデコレータが正しく動作するかテスト"""
        # テスト用の関数を定義
        @with_db_session
        def test_function(db, test_value):
            assert isinstance(db, Session), "デコレータから受け取ったdbがSessionインスタンスではありません"
            result = db.execute(text("SELECT :val"), {"val": test_value}).scalar()
            return result
        
        # 関数を呼び出してテスト
        result = test_function(42)
        assert result == 42, "デコレータを使用した関数が正しく動作していません"


if __name__ == "__main__":
    pytest.main(["-v", __file__]) 