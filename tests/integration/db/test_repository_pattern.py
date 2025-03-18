#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
リポジトリパターンテスト

このスクリプトは、新しいリポジトリパターンの機能をテストします。
各リポジトリクラスの基本的なCRUD操作をテストし、結果をログに記録します。
"""

import sys
import os
import uuid
import json
from src.utils import json_utils
from datetime import datetime
from loguru import logger

# src ディレクトリをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

def test_audit_procedure_repository():
    """監査手続きリポジトリのテスト"""
    try:
        from src.repositories.audit_procedure_repository import audit_procedure_repository
        from src.utils.db_adapter import db_adapter
        
        # テストデータの作成
        test_id = f"test-{uuid.uuid4()}"
        test_data = {
            "id": test_id,
            "title": "テスト監査手続き",
            "description": "これはリポジトリパターンのテスト用の監査手続きです。",
            "risk_areas": json_utils.json_serialize(["財務", "コンプライアンス"]),
            "required_data_fields": json_utils.json_serialize(["id", "amount", "date"]),
        }
        
        # CREATE
        logger.info("監査手続きの作成をテスト中...")
        audit_procedure_repository.create_procedure(test_data)
        logger.debug(f"作成された監査手続き: {test_id}")
        
        # READ
        logger.info(f"監査手続きの取得をテスト中... (ID: {test_id})")
        retrieved = db_adapter.get_by_id("audit_procedures", test_id)
        if retrieved and retrieved.get("id") == test_id:
            logger.debug(f"正常に取得: {retrieved.get('title')}")
        else:
            logger.error("監査手続きの取得に失敗しました")
            return False
        
        # UPDATE
        logger.info("監査手続きの更新をテスト中...")
        update_data = {"title": "更新されたテスト監査手続き"}
        audit_procedure_repository.update_procedure(test_id, update_data)
        
        # 更新の確認
        updated = db_adapter.get_by_id("audit_procedures", test_id)
        if updated and updated.get("title") == update_data["title"]:
            logger.debug(f"正常に更新: {updated.get('title')}")
        else:
            logger.error("監査手続きの更新に失敗しました")
            return False
        
        # SEARCH - 直接SQLを使用して検索
        logger.info("監査手続きの検索をテスト中...")
        query = "SELECT * FROM audit_procedures WHERE title LIKE :keyword OR description LIKE :keyword"
        search_results = db_adapter.execute_query(query, {"keyword": "%テスト%"})
        
        if search_results and any(result.get("id") == test_id for result in search_results):
            logger.debug(f"検索結果: {len(search_results)}件")
        else:
            logger.error("監査手続きの検索に失敗しました")
            return False
        
        # DELETE
        logger.info("監査手続きの削除をテスト中...")
        deleted = audit_procedure_repository.delete_procedure(test_id)
        if deleted:
            logger.debug("正常に削除されました")
        else:
            logger.error("監査手続きの削除に失敗しました")
            return False
        
        # 削除の確認
        logger.info("削除の確認をテスト中...")
        after_delete = db_adapter.get_by_id("audit_procedures", test_id)
        if after_delete is None:
            logger.debug("削除が確認されました")
        else:
            logger.error("監査手続きの削除確認に失敗しました")
            return False
        
        logger.info("監査手続きリポジトリのテストが成功しました")
        return True
        
    except Exception as e:
        logger.error(f"監査手続きリポジトリのテスト中にエラーが発生しました: {e}")
        return False

def test_sample_data_repository():
    """サンプルデータリポジトリのテスト"""
    try:
        from src.repositories.sample_data_repository import sample_data_repository
        from src.utils.db_adapter import db_adapter
        
        # テストデータの作成
        test_id = f"test-{uuid.uuid4()}"
        test_data = {
            "id": test_id,
            "filename": "test_data.csv",
            "file_path": "/tmp/test_data.csv",
            "file_size": 1024,
            "file_type": "text/csv",
            "row_count": 100,
            "column_count": 5,
            "columns": json_utils.json_serialize(["id", "name", "amount", "date", "status"]),
            "file_metadata": json_utils.json_serialize({"encoding": "utf-8", "delimiter": ","}),
        }
        
        # CREATE
        logger.info("サンプルデータの作成をテスト中...")
        sample_data_repository.create_sample_data(test_data)
        logger.debug(f"作成されたサンプルデータ: {test_id}")
        
        # READ
        logger.info(f"サンプルデータの取得をテスト中... (ID: {test_id})")
        retrieved = db_adapter.get_by_id("sample_data", test_id)
        if retrieved and retrieved.get("id") == test_id:
            logger.debug(f"正常に取得: {retrieved.get('filename')}")
        else:
            logger.error("サンプルデータの取得に失敗しました")
            return False
        
        # UPDATE
        logger.info("サンプルデータの更新をテスト中...")
        update_data = {"filename": "updated_test_data.csv"}
        sample_data_repository.update_sample_data(test_id, update_data)
        
        # 更新の確認
        updated = db_adapter.get_by_id("sample_data", test_id)
        if updated and updated.get("filename") == update_data["filename"]:
            logger.debug(f"正常に更新: {updated.get('filename')}")
        else:
            logger.error("サンプルデータの更新に失敗しました")
            return False
        
        # SEARCH - 直接SQLを使用して検索
        logger.info("サンプルデータの検索をテスト中...")
        query = "SELECT * FROM sample_data WHERE filename LIKE :keyword"
        search_results = db_adapter.execute_query(query, {"keyword": "%test_data%"})
        
        if search_results and any(result.get("id") == test_id for result in search_results):
            logger.debug(f"検索結果: {len(search_results)}件")
        else:
            logger.error("サンプルデータの検索に失敗しました")
            return False
        
        # DELETE
        logger.info("サンプルデータの削除をテスト中...")
        deleted = sample_data_repository.delete_sample_data(test_id)
        if deleted:
            logger.debug("正常に削除されました")
        else:
            logger.error("サンプルデータの削除に失敗しました")
            return False
        
        # 削除の確認
        logger.info("削除の確認をテスト中...")
        after_delete = db_adapter.get_by_id("sample_data", test_id)
        if after_delete is None:
            logger.debug("削除が確認されました")
        else:
            logger.error("サンプルデータの削除確認に失敗しました")
            return False
        
        logger.info("サンプルデータリポジトリのテストが成功しました")
        return True
        
    except Exception as e:
        logger.error(f"サンプルデータリポジトリのテスト中にエラーが発生しました: {e}")
        return False

def test_db_adapter():
    """データベースアダプターのテスト"""
    try:
        from src.utils.db_adapter import db_adapter
        
        # テストデータの作成
        test_id = f"test-{uuid.uuid4()}"
        test_data = {
            "id": test_id,
            "title": "テスト監査手続き（アダプター経由）",
            "description": "これはデータベースアダプターのテスト用の監査手続きです。",
            "risk_areas": json_utils.json_serialize(["財務", "コンプライアンス"]),
            "required_data_fields": json_utils.json_serialize(["id", "amount", "date"]),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        # INSERT
        logger.info("アダプター経由での挿入をテスト中...")
        inserted = db_adapter.insert_or_update("audit_procedures", test_data)
        if inserted:
            logger.debug("正常に挿入されました")
        else:
            logger.error("アダプター経由での挿入に失敗しました")
            return False
        
        # GET
        logger.info("アダプター経由での取得をテスト中...")
        retrieved = db_adapter.get_by_id("audit_procedures", test_id)
        if retrieved and retrieved.get("id") == test_id:
            logger.debug(f"正常に取得: {retrieved.get('title')}")
        else:
            logger.error("アダプター経由での取得に失敗しました")
            return False
        
        # UPDATE
        logger.info("アダプター経由での更新をテスト中...")
        test_data["title"] = "更新されたテスト監査手続き（アダプター経由）"
        updated = db_adapter.insert_or_update("audit_procedures", test_data)
        if updated:
            logger.debug("正常に更新されました")
        else:
            logger.error("アダプター経由での更新に失敗しました")
            return False
        
        # 更新の確認
        updated_record = db_adapter.get_by_id("audit_procedures", test_id)
        if updated_record and updated_record.get("title") == test_data["title"]:
            logger.debug(f"更新が確認されました: {updated_record.get('title')}")
        else:
            logger.error("アダプター経由での更新確認に失敗しました")
            return False
        
        # QUERY
        logger.info("アダプター経由でのクエリをテスト中...")
        query_results = db_adapter.execute_query("SELECT * FROM audit_procedures WHERE id = :id", {"id": test_id})
        if query_results and len(query_results) > 0 and query_results[0].get("id") == test_id:
            logger.debug(f"正常にクエリ: {query_results[0].get('title')}")
        else:
            logger.error("アダプター経由でのクエリに失敗しました")
            return False
        
        # DELETE
        logger.info("アダプター経由での削除をテスト中...")
        deleted = db_adapter.delete("audit_procedures", "id = :id", {"id": test_id})
        if deleted:
            logger.debug("正常に削除されました")
        else:
            logger.error("アダプター経由での削除に失敗しました")
            return False
        
        # 削除の確認
        after_delete = db_adapter.get_by_id("audit_procedures", test_id)
        if after_delete is None:
            logger.debug("削除が確認されました")
        else:
            logger.error("アダプター経由での削除確認に失敗しました")
            return False
        
        logger.info("データベースアダプターのテストが成功しました")
        return True
        
    except Exception as e:
        logger.error(f"データベースアダプターのテスト中にエラーが発生しました: {e}")
        return False

def test_db_utils_with_repository():
    """リポジトリパターンを有効にしたdb_utilsのテスト"""
    try:
        from src.utils.db_utils import (
            enable_repository_pattern,
            execute_query,
            get_by_id,
            save_audit_procedure,
        )
        from src.utils.db_adapter import db_adapter
        
        # リポジトリパターンを有効化
        enable_repository_pattern()
        
        # テストデータの作成
        test_id = f"test-{uuid.uuid4()}"
        test_data = {
            "id": test_id,
            "title": "テスト監査手続き（db_utils経由）",
            "description": "これはリポジトリパターンを有効にしたdb_utilsのテスト用の監査手続きです。",
            "risk_areas": json_utils.json_serialize(["財務", "コンプライアンス"]),
            "required_data_fields": json_utils.json_serialize(["id", "amount", "date"]),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        # SAVE - 直接db_adapterを使用して保存
        logger.info("db_utils経由での保存をテスト中...")
        saved = db_adapter.insert_or_update("audit_procedures", test_data)
        if saved:
            logger.debug("正常に保存されました")
        else:
            logger.error("db_utils経由での保存に失敗しました")
            return False
        
        # GET
        logger.info("db_utils経由での取得をテスト中...")
        retrieved = get_by_id("audit_procedures", test_id)
        if retrieved and retrieved.get("id") == test_id:
            logger.debug(f"正常に取得: {retrieved.get('title')}")
        else:
            logger.error("db_utils経由での取得に失敗しました")
            return False
        
        # QUERY
        logger.info("db_utils経由でのクエリをテスト中...")
        query_results = execute_query("SELECT * FROM audit_procedures WHERE id = :id", {"id": test_id})
        if query_results and len(query_results) > 0 and query_results[0].get("id") == test_id:
            logger.debug(f"正常にクエリ: {query_results[0].get('title')}")
        else:
            logger.error("db_utils経由でのクエリに失敗しました")
            return False
        
        # DELETE
        logger.info("db_utils経由での削除をテスト中...")
        deleted = db_adapter.delete("audit_procedures", "id = :id", {"id": test_id})
        if deleted:
            logger.debug("正常に削除されました")
        else:
            logger.error("db_utils経由での削除に失敗しました")
            return False
        
        # 削除の確認
        after_delete = get_by_id("audit_procedures", test_id)
        if after_delete is None:
            logger.debug("削除が確認されました")
        else:
            logger.error("db_utils経由での削除確認に失敗しました")
            return False
        
        logger.info("リポジトリパターンを有効にしたdb_utilsのテストが成功しました")
        return True
        
    except Exception as e:
        logger.error(f"リポジトリパターンを有効にしたdb_utilsのテスト中にエラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    logger.info("リポジトリパターンのテストを開始します")
    
    # データベースの初期化
    logger.info("データベースを初期化中...")
    from src.utils.db_manager import init_db
    init_db()
    
    # テスト結果
    test_results = {
        "audit_procedure_repository": test_audit_procedure_repository(),
        "sample_data_repository": test_sample_data_repository(),
        "db_adapter": test_db_adapter(),
        "db_utils_with_repository": test_db_utils_with_repository()
    }
    
    # 結果の表示
    logger.info("テスト結果:")
    for test_name, result in test_results.items():
        logger.info(f"- {test_name}: {'成功' if result else '失敗'}")
    
    # 全てのテストが成功したかどうかを確認
    if all(test_results.values()):
        logger.info("全てのリポジトリパターンテストが成功しました")
        sys.exit(0)
    else:
        logger.error("一部のリポジトリパターンテストが失敗しました")
        sys.exit(1) 