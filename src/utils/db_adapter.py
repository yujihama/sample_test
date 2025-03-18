"""
データベースアダプター

このモジュールは、既存のdb_utils.pyおよびdb_manager.pyモジュールから
新しいリポジトリパターンへの移行を支援するアダプタークラスを提供します。
"""

import json
from src.utils import json_utils
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from loguru import logger
import re

from src.utils.db_manager import get_db, execute_sql
from src.repositories.audit_procedure_repository import audit_procedure_repository
from src.repositories.sample_data_repository import sample_data_repository
from src.repositories.workflow_repository import workflow_repository
from src.repositories.test_plan_repository import test_plan_repository
from src.repositories.test_result_repository import test_result_repository
from sqlalchemy.sql import text

# 互換性のためのインポート
from src.utils.backup_manager import backup_database as backup_db_func
from sqlalchemy import create_engine, inspect
from src.models.db_models import Base
from src.core.config import settings

class DatabaseAdapter:
    """
    データベースアダプタークラス
    
    既存のコードがdb_utils.pyの関数を使用している場合、
    このクラスを通じて同等の機能を新しいリポジトリパターンで実現できます。
    """
    
    @staticmethod
    def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        SQLクエリを実行する
        
        Args:
            query: SQLクエリ文字列
            params: クエリパラメータ
            
        Returns:
            List[Dict[str, Any]]: クエリ結果
        """
        try:
            # SQLAlchemyのテキストクエリを使用
            result = execute_sql(query, params)
            
            # 結果を辞書のリストに変換
            result_list = []
            for row in result:
                row_dict = {}
                for key in row._mapping.keys():
                    row_dict[key] = row._mapping[key]
                result_list.append(row_dict)
            
            return result_list
            
        except Exception as e:
            logger.error(f"クエリ実行エラー: {e}")
            raise
    
    @staticmethod
    def insert_or_update(table: str, data: dict) -> bool:
        """
        指定されたテーブルにデータを挿入または更新します。
        
        Args:
            table: テーブル名
            data: 挿入または更新するデータの辞書
            
        Returns:
            bool: 操作が成功した場合はTrue、失敗した場合はFalse
        """
        try:
            # データのIDを取得
            record_id = data.get("id")
            if not record_id:
                logger.error("データにIDが含まれていません")
                return False
                
            # 既存のレコードを確認
            existing_record = DatabaseAdapter.get_by_id(table, record_id)
            
            # SQLクエリを構築
            if existing_record:
                # 更新の場合
                set_clauses = []
                params = {}
                
                for key, value in data.items():
                    if key != "id":  # IDは更新しない
                        set_clauses.append(f"{key} = :{key}")
                        params[key] = value
                
                params["id"] = record_id
                query = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE id = :id"
            else:
                # 挿入の場合
                columns = list(data.keys())
                placeholders = [f":{col}" for col in columns]
                
                query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                params = data
            
            # クエリ実行
            db_gen = get_db()
            session = next(db_gen)
            try:
                session.execute(text(query), params)
                session.commit()
                logger.debug(f"レコードが正常に{'更新' if existing_record else '挿入'}されました: {table}, ID={record_id}")
                return True
            finally:
                try:
                    next(db_gen)  # セッションを閉じる
                except StopIteration:
                    pass
                
        except Exception as e:
            logger.error(f"レコード保存エラー: {e}")
            return False
    
    @staticmethod
    def get_by_id(table: str, record_id: str, id_field: str = "id") -> Optional[Dict[str, Any]]:
        """
        指定されたIDでレコードを取得
        
        Args:
            table: テーブル名
            record_id: レコードID
            id_field: ID列の名前（デフォルト: "id"）
            
        Returns:
            レコード（辞書形式）または None
        """
        try:
            # SQLで直接実行
            query = f"SELECT * FROM {table} WHERE {id_field} = :record_id"
            logger.debug(f"get_by_id: テーブル={table}, ID={record_id}, クエリ={query}")
            
            # クエリ実行
            db_gen = get_db()
            session = next(db_gen)
            try:
                result = session.execute(text(query), {"record_id": record_id})
                row = result.fetchone()
                
                if row:
                    # 行を辞書に変換
                    result_dict = {}
                    for key in row._mapping.keys():
                        result_dict[key] = row._mapping[key]
                    logger.debug(f"get_by_id: レコードが見つかりました: {result_dict.get('id')}")
                    return result_dict
                
                logger.debug(f"get_by_id: レコードが見つかりませんでした: テーブル={table}, ID={record_id}")
                return None
            finally:
                try:
                    next(db_gen)  # セッションを閉じる
                except StopIteration:
                    pass
                
        except Exception as e:
            logger.error(f"レコード取得エラー: {e}")
            return None
    
    @staticmethod
    def delete(table: str, condition: str, params: Union[tuple, dict] = ()) -> bool:
        """
        レコードの削除
        
        Args:
            table: テーブル名
            condition: WHERE句の条件
            params: 条件パラメータ（タプルまたは辞書）
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            # 単純なID条件の場合はリポジトリを使用
            if condition.startswith("id = ") and isinstance(params, dict) and "id" in params:
                record_id = params["id"]
                
                if table == "audit_procedures":
                    return audit_procedure_repository.delete_procedure(record_id)
                    
                elif table == "sample_data":
                    return sample_data_repository.delete_sample_data(record_id)
                    
                elif table == "workflows":
                    return workflow_repository.delete_workflow(record_id)
                    
                elif table == "test_plans":
                    return test_plan_repository.delete_test_plan(record_id)
                    
                elif table == "test_results":
                    return test_result_repository.delete_test_result(record_id)
            
            # 未対応のテーブルまたは複雑な条件はSQLで直接実行
            query = f"DELETE FROM {table} WHERE {condition}"
            
            # クエリ実行
            db_gen = get_db()
            session = next(db_gen)
            try:
                session.execute(text(query), params if isinstance(params, dict) else {})
                session.commit()
                logger.debug(f"レコードが正常に削除されました: {table}, 条件={condition}")
                return True
            finally:
                try:
                    next(db_gen)  # セッションを閉じる
                except StopIteration:
                    pass
                
        except Exception as e:
            logger.error(f"レコード削除エラー: {e}")
            return False

    # 便利なヘルパーメソッド
    
    @staticmethod
    def save_audit_procedure(procedure: Dict[str, Any]) -> bool:
        """
        監査手続きを保存
        
        Args:
            procedure: 保存する監査手続き情報
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            procedure_copy = procedure.copy()
            
            # JSONフィールドの前処理
            for field in ["risk_areas", "required_data_fields"]:
                if field in procedure_copy and not isinstance(procedure_copy[field], str):
                    procedure_copy[field] = json_utils.json_serialize(procedure_copy[field])
            
            # タイムスタンプを設定
            if "created_at" not in procedure_copy:
                procedure_copy["created_at"] = datetime.now()
                
            procedure_copy["updated_at"] = datetime.now()
            
            # IDがある場合は更新、ない場合は作成
            if "id" in procedure_copy and procedure_copy["id"]:
                audit_procedure_repository.update_procedure(procedure_copy["id"], procedure_copy)
            else:
                audit_procedure_repository.create_procedure(procedure_copy)
                
            return True
                
        except Exception as e:
            logger.error(f"監査手続き保存エラー: {e}")
            return False
    
    @staticmethod
    def save_sample_data(sample_data: Dict[str, Any]) -> bool:
        """
        サンプルデータ情報を保存
        
        Args:
            sample_data: 保存するサンプルデータ情報
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            sample_copy = sample_data.copy()
            
            # JSONフィールドの前処理
            for field in ["columns", "file_metadata"]:
                if field in sample_copy and not isinstance(sample_copy[field], str):
                    sample_copy[field] = json_utils.json_serialize(sample_copy[field])
            
            # タイムスタンプを設定
            if "upload_time" not in sample_copy:
                sample_copy["upload_time"] = datetime.now()
            
            # IDがある場合は更新、ない場合は作成
            if "id" in sample_copy and sample_copy["id"]:
                sample_data_repository.update_sample_data(sample_copy["id"], sample_copy)
            else:
                sample_data_repository.create_sample_data(sample_copy)
                
            return True
                
        except Exception as e:
            logger.error(f"サンプルデータ保存エラー: {e}")
            return False
    
    @staticmethod
    def save_workflow(workflow: Dict[str, Any]) -> bool:
        """
        ワークフローを保存
        
        Args:
            workflow: 保存するワークフロー情報
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            workflow_copy = workflow.copy()
            
            # JSONフィールドの前処理
            if "results" in workflow_copy and not isinstance(workflow_copy["results"], str):
                workflow_copy["results"] = json_utils.json_serialize(workflow_copy["results"])
            
            # タイムスタンプを設定
            if "created_at" not in workflow_copy:
                workflow_copy["created_at"] = datetime.now()
                
            workflow_copy["updated_at"] = datetime.now()
            
            # IDがある場合は更新、ない場合は作成
            if "id" in workflow_copy and workflow_copy["id"]:
                workflow_repository.update_workflow(workflow_copy["id"], workflow_copy)
            else:
                workflow_repository.create_workflow(workflow_copy)
                
            return True
                
        except Exception as e:
            logger.error(f"ワークフロー保存エラー: {e}")
            return False

    # db_migration.py 互換性関数
    
    @staticmethod
    def backup_database():
        """
        データベースのバックアップ作成 (db_migration.py互換)
        """
        from src.utils.backup_manager import backup_database_legacy
        return backup_database_legacy()
    
    @staticmethod
    def get_db_engine():
        """
        データベースエンジンを取得 (db_migration.py互換)
        """
        db_url = settings.DATABASE_URL
        return create_engine(db_url)
    
    @staticmethod
    def create_database():
        """
        新しいデータベースを作成 (db_migration.py互換)
        """
        try:
            engine = DatabaseAdapter.get_db_engine()
            Base.metadata.create_all(engine)
            return True
        except Exception as e:
            logger.error(f"データベーススキーマの作成中にエラーが発生しました: {e}")
            return False
    
    @staticmethod
    def migrate_database():
        """
        既存のデータベースをマイグレーション (db_migration.py互換)
        """
        try:
            engine = DatabaseAdapter.get_db_engine()
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
            
            logger.info(f"既存のテーブル: {existing_tables}")
            
            # 新しいテーブルの作成とカラムの追加のみを行う
            Base.metadata.create_all(engine)
            logger.info("データベースマイグレーションが正常に完了しました")
            
            return True
        except Exception as e:
            logger.error(f"データベースマイグレーション中にエラーが発生しました: {e}")
            return False
    
    @staticmethod
    def perform_migration():
        """
        マイグレーションプロセスを実行 (db_migration.py互換)
        """
        logger.info("データベースマイグレーションを開始します...")
        
        # バックアップを作成
        backup_result = DatabaseAdapter.backup_database()
        if not backup_result:
            logger.warning("バックアップが作成されませんでした。既存のデータベースファイルが存在しない可能性があります。")
        
        # マイグレーションを実行
        migration_result = DatabaseAdapter.migrate_database()
        
        if migration_result:
            logger.info("マイグレーションが正常に完了しました。")
        else:
            logger.error("マイグレーションに失敗しました。")
        
        return migration_result

# シングルトンインスタンス
db_adapter = DatabaseAdapter() 