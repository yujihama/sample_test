"""
データベース接続ユーティリティ
"""

import os
from typing import Dict, List, Any, Optional, Union, Tuple
import json
from datetime import datetime
import sqlite3
import pandas as pd
from loguru import logger

from src.core.config import settings


class DatabaseManager:
    """
    データベース管理クラス - SQLiteデータベースへの接続と操作を行う
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance.db_path = settings.DB_PATH
            cls._instance.connection = None
            cls._instance.initialize_db()
        return cls._instance
    
    def initialize_db(self):
        """
        データベースの初期化
        - データベースファイルが存在しない場合は作成
        - 必要なテーブルを作成
        """
        try:
            # データベースのディレクトリが存在することを確認
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # データベースに接続
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            
            # テーブルを作成
            self._create_tables()
            
            logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def _create_tables(self):
        """必要なテーブルを作成"""
        cursor = self.connection.cursor()
        
        # 監査手続きテーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_procedures (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            risk_areas TEXT,
            required_data_fields TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')
        
        # サンプルデータテーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sample_data (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            file_type TEXT,
            row_count INTEGER,
            column_count INTEGER,
            columns TEXT,
            procedure_id TEXT,
            metadata TEXT,
            upload_time TEXT NOT NULL,
            FOREIGN KEY (procedure_id) REFERENCES audit_procedures (id)
        )
        ''')
        
        # ワークフローテーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS workflows (
            id TEXT PRIMARY KEY,
            audit_procedure_id TEXT NOT NULL,
            sample_data_id TEXT NOT NULL,
            status TEXT NOT NULL,
            current_agent TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            results TEXT,
            error TEXT,
            FOREIGN KEY (audit_procedure_id) REFERENCES audit_procedures (id),
            FOREIGN KEY (sample_data_id) REFERENCES sample_data (id)
        )
        ''')
        
        # テスト計画テーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_plans (
            id TEXT PRIMARY KEY,
            workflow_id TEXT NOT NULL,
            test_items TEXT NOT NULL,
            prerequisites TEXT,
            required_data_fields TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (workflow_id) REFERENCES workflows (id)
        )
        ''')
        
        # テスト結果テーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            id TEXT PRIMARY KEY,
            workflow_id TEXT NOT NULL,
            test_plan_id TEXT NOT NULL,
            results TEXT NOT NULL,
            execution_time TEXT NOT NULL,
            status TEXT NOT NULL,
            error TEXT,
            FOREIGN KEY (workflow_id) REFERENCES workflows (id),
            FOREIGN KEY (test_plan_id) REFERENCES test_plans (id)
        )
        ''')
        
        # 評価サマリーテーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS evaluation_summaries (
            id TEXT PRIMARY KEY,
            workflow_id TEXT NOT NULL,
            test_result_id TEXT NOT NULL,
            overall_result TEXT NOT NULL,
            test_item_evaluations TEXT NOT NULL,
            key_findings TEXT,
            risk_assessment TEXT,
            recommendations TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (workflow_id) REFERENCES workflows (id),
            FOREIGN KEY (test_result_id) REFERENCES test_results (id)
        )
        ''')
        
        # 報告書テーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            workflow_id TEXT NOT NULL,
            evaluation_id TEXT NOT NULL,
            title TEXT NOT NULL,
            file_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (workflow_id) REFERENCES workflows (id),
            FOREIGN KEY (evaluation_id) REFERENCES evaluation_summaries (id)
        )
        ''')
        
        # メッセージログテーブル
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_logs (
            id TEXT PRIMARY KEY,
            from_agent TEXT NOT NULL,
            to_agent TEXT NOT NULL,
            message_type TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            processed_at TEXT
        )
        ''')
        
        self.connection.commit()
        logger.debug("Database tables created")
    
    def close(self):
        """データベース接続を閉じる"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
    def get_connection(self):
        """データベース接続を取得"""
        if not self.connection:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
        return self.connection
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        クエリを実行して結果を取得
        
        Args:
            query: SQLクエリ
            params: クエリパラメータ
            
        Returns:
            List[Dict[str, Any]]: クエリ結果
        """
        try:
            cursor = self.get_connection().cursor()
            cursor.execute(query, params)
            
            # クエリがSELECTの場合、結果を取得
            if query.strip().upper().startswith("SELECT"):
                rows = cursor.fetchall()
                results = [dict(row) for row in rows]
                return results
            else:
                self.connection.commit()
                return []
                
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            self.connection.rollback()
            raise
    
    def execute_many(self, query: str, params_list: List[tuple]) -> bool:
        """
        複数のクエリを一括実行
        
        Args:
            query: SQLクエリ
            params_list: クエリパラメータのリスト
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            cursor = self.get_connection().cursor()
            cursor.executemany(query, params_list)
            self.connection.commit()
            return True
                
        except Exception as e:
            logger.error(f"Error executing many queries: {e}")
            self.connection.rollback()
            return False
    
    def insert_or_update(self, table: str, data: Dict[str, Any], pk_field: str = "id") -> bool:
        """
        レコードの挿入または更新
        
        Args:
            table: テーブル名
            data: 挿入/更新するデータ
            pk_field: 主キーフィールド名
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            # IDが存在するか確認
            pk_value = data.get(pk_field)
            exists = False
            
            if pk_value:
                query = f"SELECT COUNT(*) as count FROM {table} WHERE {pk_field} = ?"
                result = self.execute_query(query, (pk_value,))
                exists = result and result[0]["count"] > 0
            
            cursor = self.get_connection().cursor()
            
            if exists:
                # 更新
                fields = [f"{k} = ?" for k in data.keys() if k != pk_field]
                values = [data[k] for k in data.keys() if k != pk_field]
                values.append(pk_value)  # WHERE句のパラメータ
                
                query = f"UPDATE {table} SET {', '.join(fields)} WHERE {pk_field} = ?"
                cursor.execute(query, values)
                
            else:
                # 挿入
                fields = list(data.keys())
                placeholders = ["?"] * len(fields)
                values = [data[k] for k in fields]
                
                query = f"INSERT INTO {table} ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
                cursor.execute(query, values)
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error inserting/updating record: {e}")
            self.connection.rollback()
            return False
    
    def delete(self, table: str, condition: str, params: tuple = ()) -> bool:
        """
        レコードの削除
        
        Args:
            table: テーブル名
            condition: WHERE句の条件
            params: 条件パラメータ
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            query = f"DELETE FROM {table} WHERE {condition}"
            cursor = self.get_connection().cursor()
            cursor.execute(query, params)
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error deleting record: {e}")
            self.connection.rollback()
            return False
    
    def get_by_id(self, table: str, record_id: str, id_field: str = "id") -> Optional[Dict[str, Any]]:
        """
        IDによるレコード取得
        
        Args:
            table: テーブル名
            record_id: レコードID
            id_field: IDフィールド名
            
        Returns:
            Optional[Dict[str, Any]]: レコード（存在しない場合はNone）
        """
        query = f"SELECT * FROM {table} WHERE {id_field} = ?"
        results = self.execute_query(query, (record_id,))
        
        if results:
            return results[0]
        return None
    
    def query_to_dataframe(self, query: str, params: tuple = ()) -> pd.DataFrame:
        """
        クエリ結果をDataFrameとして取得
        
        Args:
            query: SQLクエリ
            params: クエリパラメータ
            
        Returns:
            pd.DataFrame: クエリ結果のDataFrame
        """
        try:
            conn = self.get_connection()
            df = pd.read_sql_query(query, conn, params=params)
            return df
            
        except Exception as e:
            logger.error(f"Error executing query to DataFrame: {e}")
            raise
    
    def dataframe_to_table(self, df: pd.DataFrame, table_name: str, if_exists: str = "append") -> bool:
        """
        DataFrameをテーブルに保存
        
        Args:
            df: 保存するDataFrame
            table_name: テーブル名
            if_exists: 既存テーブルがある場合の動作（"fail", "replace", "append"）
            
        Returns:
            bool: 成功したかどうか
        """
        try:
            conn = self.get_connection()
            df.to_sql(table_name, conn, if_exists=if_exists, index=False)
            return True
            
        except Exception as e:
            logger.error(f"Error saving DataFrame to table: {e}")
            return False

    # 特定のテーブル用のメソッド
    
    def save_audit_procedure(self, procedure: Dict[str, Any]) -> bool:
        """
        監査手続きを保存
        
        Args:
            procedure: 保存する監査手続き情報
            
        Returns:
            bool: 成功したかどうか
        """
        # リスト型フィールドをJSON文字列に変換
        procedure_copy = procedure.copy()
        
        if "risk_areas" in procedure_copy and isinstance(procedure_copy["risk_areas"], list):
            procedure_copy["risk_areas"] = json.dumps(procedure_copy["risk_areas"])
            
        if "required_data_fields" in procedure_copy and isinstance(procedure_copy["required_data_fields"], list):
            procedure_copy["required_data_fields"] = json.dumps(procedure_copy["required_data_fields"])
        
        # タイムスタンプを設定
        if "created_at" not in procedure_copy:
            procedure_copy["created_at"] = datetime.now().isoformat()
            
        procedure_copy["updated_at"] = datetime.now().isoformat()
        
        return self.insert_or_update("audit_procedures", procedure_copy)
    
    def save_sample_data(self, sample_data: Dict[str, Any]) -> bool:
        """
        サンプルデータ情報を保存
        
        Args:
            sample_data: 保存するサンプルデータ情報
            
        Returns:
            bool: 成功したかどうか
        """
        # 辞書型/リスト型フィールドをJSON文字列に変換
        sample_copy = sample_data.copy()
        
        if "columns" in sample_copy and isinstance(sample_copy["columns"], list):
            sample_copy["columns"] = json.dumps(sample_copy["columns"])
            
        if "metadata" in sample_copy and isinstance(sample_copy["metadata"], dict):
            sample_copy["metadata"] = json.dumps(sample_copy["metadata"])
        
        # タイムスタンプを設定
        if "upload_time" not in sample_copy:
            sample_copy["upload_time"] = datetime.now().isoformat()
        
        return self.insert_or_update("sample_data", sample_copy)
    
    def save_workflow(self, workflow: Dict[str, Any]) -> bool:
        """
        ワークフロー情報を保存
        
        Args:
            workflow: 保存するワークフロー情報
            
        Returns:
            bool: 成功したかどうか
        """
        # 辞書型フィールドをJSON文字列に変換
        workflow_copy = workflow.copy()
        
        if "results" in workflow_copy and isinstance(workflow_copy["results"], dict):
            workflow_copy["results"] = json.dumps(workflow_copy["results"])
        
        # タイムスタンプを設定
        if "created_at" not in workflow_copy:
            workflow_copy["created_at"] = datetime.now().isoformat()
            
        workflow_copy["updated_at"] = datetime.now().isoformat()
        
        return self.insert_or_update("workflows", workflow_copy)
    
    def save_test_plan(self, test_plan: Dict[str, Any]) -> bool:
        """
        テスト計画を保存
        
        Args:
            test_plan: 保存するテスト計画
            
        Returns:
            bool: 成功したかどうか
        """
        # リスト型/辞書型フィールドをJSON文字列に変換
        plan_copy = test_plan.copy()
        
        if "test_items" in plan_copy and (isinstance(plan_copy["test_items"], list) or isinstance(plan_copy["test_items"], dict)):
            plan_copy["test_items"] = json.dumps(plan_copy["test_items"])
            
        if "prerequisites" in plan_copy and isinstance(plan_copy["prerequisites"], list):
            plan_copy["prerequisites"] = json.dumps(plan_copy["prerequisites"])
            
        if "required_data_fields" in plan_copy and isinstance(plan_copy["required_data_fields"], list):
            plan_copy["required_data_fields"] = json.dumps(plan_copy["required_data_fields"])
        
        # タイムスタンプを設定
        if "created_at" not in plan_copy:
            plan_copy["created_at"] = datetime.now().isoformat()
        
        return self.insert_or_update("test_plans", plan_copy)
    
    def save_test_result(self, test_result: Dict[str, Any]) -> bool:
        """
        テスト結果を保存
        
        Args:
            test_result: 保存するテスト結果
            
        Returns:
            bool: 成功したかどうか
        """
        # 辞書型フィールドをJSON文字列に変換
        result_copy = test_result.copy()
        
        if "results" in result_copy and (isinstance(result_copy["results"], list) or isinstance(result_copy["results"], dict)):
            result_copy["results"] = json.dumps(result_copy["results"])
        
        # タイムスタンプを設定
        if "execution_time" not in result_copy:
            result_copy["execution_time"] = datetime.now().isoformat()
        
        return self.insert_or_update("test_results", result_copy)
    
    def save_evaluation_summary(self, summary: Dict[str, Any]) -> bool:
        """
        評価サマリーを保存
        
        Args:
            summary: 保存する評価サマリー
            
        Returns:
            bool: 成功したかどうか
        """
        # リスト型/辞書型フィールドをJSON文字列に変換
        summary_copy = summary.copy()
        
        if "test_item_evaluations" in summary_copy and (isinstance(summary_copy["test_item_evaluations"], list) or isinstance(summary_copy["test_item_evaluations"], dict)):
            summary_copy["test_item_evaluations"] = json.dumps(summary_copy["test_item_evaluations"])
            
        if "key_findings" in summary_copy and isinstance(summary_copy["key_findings"], list):
            summary_copy["key_findings"] = json.dumps(summary_copy["key_findings"])
            
        if "risk_assessment" in summary_copy and isinstance(summary_copy["risk_assessment"], dict):
            summary_copy["risk_assessment"] = json.dumps(summary_copy["risk_assessment"])
            
        if "recommendations" in summary_copy and isinstance(summary_copy["recommendations"], list):
            summary_copy["recommendations"] = json.dumps(summary_copy["recommendations"])
        
        # タイムスタンプを設定
        if "created_at" not in summary_copy:
            summary_copy["created_at"] = datetime.now().isoformat()
        
        return self.insert_or_update("evaluation_summaries", summary_copy)
    
    def save_report(self, report: Dict[str, Any]) -> bool:
        """
        報告書情報を保存
        
        Args:
            report: 保存する報告書情報
            
        Returns:
            bool: 成功したかどうか
        """
        # タイムスタンプを設定
        report_copy = report.copy()
        
        if "created_at" not in report_copy:
            report_copy["created_at"] = datetime.now().isoformat()
        
        return self.insert_or_update("reports", report_copy)
    
    def log_message(self, message: Dict[str, Any]) -> bool:
        """
        メッセージをログに記録
        
        Args:
            message: 記録するメッセージ
            
        Returns:
            bool: 成功したかどうか
        """
        # メッセージ内容をJSON文字列に変換
        message_copy = message.copy()
        
        if "content" in message_copy and isinstance(message_copy["content"], dict):
            message_copy["content"] = json.dumps(message_copy["content"])
        
        # タイムスタンプを設定
        if "created_at" not in message_copy:
            message_copy["created_at"] = datetime.now().isoformat()
        
        return self.insert_or_update("message_logs", message_copy) 