#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
データベース接続テストスクリプト

このスクリプトは、db_manager.pyとdb_utils.pyの両方のデータベース接続機能をテストします。
各モジュールが正しく接続できるかどうかを確認し、結果をログに記録します。
"""

import sys
import os
from loguru import logger
from sqlalchemy import text

# src ディレクトリをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# テスト結果を格納する変数
test_results = {
    'db_manager': False,
    'db_utils': False
}

def test_db_manager():
    """
    db_manager.pyのデータベース接続をテストする
    """
    try:
        from src.utils.db_manager import get_db, init_db, execute_sql
        
        # データベースの初期化
        init_db()
        
        # セッションを取得してテストクエリを実行
        db_gen = get_db()
        db = next(db_gen)
        
        # テーブル一覧を取得
        tables = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
        tables_list = [table[0] for table in tables] if tables else []
        
        logger.debug(f"定義されているテーブル: {tables_list}")
        
        # 簡単なクエリを実行
        result = db.execute(text("SELECT 1 AS test")).fetchone()
        
        # セッションを閉じる
        try:
            next(db_gen)
        except StopIteration:
            pass
        
        if result and result[0] == 1:
            logger.info("db_managerのテストが成功しました")
            test_results['db_manager'] = True
            return True
        else:
            logger.error("db_managerのテストが失敗しました: 予期しない結果")
            return False
            
    except Exception as e:
        logger.error(f"db_managerのテスト中にエラーが発生しました: {e}")
        return False

def test_db_utils():
    """
    db_utils.pyのデータベース接続をテストする
    """
    try:
        from src.utils.db_utils import execute_query, initialize_database
        
        # データベースの初期化
        initialize_database()
        
        # 簡単なクエリを実行
        result = execute_query("SELECT 1 AS test")
        
        if result and isinstance(result, list) and len(result) > 0:
            # 結果の形式に応じて確認
            if isinstance(result[0], dict) and 'test' in result[0] and result[0]['test'] == 1:
                logger.info("db_utilsのテストが成功しました")
                test_results['db_utils'] = True
                return True
            else:
                logger.error(f"db_utilsのテストが失敗しました: 予期しない結果形式 {result}")
                return False
        else:
            logger.error(f"db_utilsのテストが失敗しました: 結果が空または無効 {result}")
            return False
            
    except Exception as e:
        logger.error(f"db_utilsのテスト中にエラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    logger.info("データベース接続テストを開始します")
    
    # db_managerのテスト
    db_manager_result = test_db_manager()
    
    # db_utilsのテスト
    db_utils_result = test_db_utils()
    
    # 結果のサマリーを表示
    logger.info(f"テスト結果サマリー: db_manager={test_results['db_manager']}, db_utils={test_results['db_utils']}")
    
    # 全てのテストが成功したかどうかを確認
    if all(test_results.values()):
        logger.info("全てのテストが成功しました")
        sys.exit(0)
    else:
        logger.error("一部のテストが失敗しました")
        sys.exit(1) 