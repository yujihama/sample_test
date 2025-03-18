#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
統合テスト用のベースクラス
"""

import os
import sys
import unittest
import logging
from pathlib import Path
from typing import Dict, Any, Optional, ClassVar

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# テスト設定とデータベース初期化をインポート
from tests.integration.test_config import TEST_DB_CONFIG, get_temp_db_config, TEST_WORKFLOW_STATES_DIR
from tests.integration.db_init import init_database, load_test_data, Base

# ロガーのセットアップ
from src.utils.logger import setup_logger
logger = setup_logger("integration_test")


class BaseIntegrationTest(unittest.TestCase):
    """統合テスト用のベースクラス"""
    
    # クラス変数（すべてのテストで共有）
    engine: ClassVar[Optional[sqlalchemy.engine.Engine]] = None
    Session: ClassVar[Optional[sqlalchemy.orm.session.sessionmaker]] = None
    db_config: ClassVar[Dict[str, Any]] = None
    
    @classmethod
    def setUpClass(cls):
        """テストクラスの初期化（クラス全体で1回実行）"""
        logger.info(f"{cls.__name__} テストクラスの初期化を開始")
        
        # データベース設定
        cls.db_config = cls.get_db_config()
        
        # データベース初期化
        cls.engine = init_database(cls.db_config, echo=False)
        
        # セッションメーカーの作成
        cls.Session = sessionmaker(bind=cls.engine)
        
        # テストデータの読み込み
        load_test_data(cls.engine)
        
        # ワークフロー状態ディレクトリのパッチ
        from unittest.mock import patch
        cls._workflow_states_dir_patch = patch("src.utils.workflow_state.WORKFLOW_STATES_DIR", TEST_WORKFLOW_STATES_DIR)
        cls._workflow_states_dir_patch.start()
        
        logger.info(f"{cls.__name__} テストクラスの初期化が完了")
    
    @classmethod
    def tearDownClass(cls):
        """テストクラスのクリーンアップ（クラス全体で1回実行）"""
        logger.info(f"{cls.__name__} テストクラスのクリーンアップを開始")
        
        # ワークフロー状態ディレクトリのパッチを停止
        cls._workflow_states_dir_patch.stop()
        
        # データベース接続をクローズ
        if cls.engine:
            cls.engine.dispose()
            cls.engine = None
        
        # SQLiteの場合は一時ファイルを削除
        if cls.db_config and cls.db_config.get("dialect") == "sqlite":
            db_path = cls.db_config.get("database")
            if db_path and db_path != ":memory:" and os.path.exists(db_path):
                try:
                    os.unlink(db_path)
                    logger.info(f"一時データベースファイルを削除しました: {db_path}")
                except Exception as e:
                    logger.warning(f"一時データベースファイルの削除に失敗しました: {db_path} - {e}")
        
        logger.info(f"{cls.__name__} テストクラスのクリーンアップが完了")
    
    def setUp(self):
        """各テストケースの初期化"""
        logger.info(f"{self._testMethodName} テストケースを開始")
        
        # テスト用セッションの作成
        self.session = self.Session()
    
    def tearDown(self):
        """各テストケースのクリーンアップ"""
        # セッションをクリーンアップ
        if hasattr(self, "session") and self.session:
            self.session.close()
            self.session = None
        
        logger.info(f"{self._testMethodName} テストケースが完了")
    
    @classmethod
    def get_db_config(cls) -> Dict[str, Any]:
        """
        テスト用のデータベース設定を取得
        
        デフォルトではインメモリSQLiteを使用するが、
        環境変数INTEGRATION_TEST_DB_TYPEで別の設定を選択可能:
            - memory: インメモリSQLite (デフォルト)
            - sqlite: ファイルベースSQLite
            - postgres: PostgreSQL
        """
        db_type = os.environ.get("INTEGRATION_TEST_DB_TYPE", "memory")
        
        if db_type == "sqlite":
            return get_temp_db_config()
        elif db_type == "postgres":
            from tests.integration.test_config import get_postgres_test_config
            return get_postgres_test_config()
        else:  # memory
            return TEST_DB_CONFIG
    
    def create_test_workflow(self, procedure_id: str, sample_id: str) -> str:
        """
        テスト用のワークフローを作成
        
        Args:
            procedure_id: 監査手続きID
            sample_id: サンプルデータID
            
        Returns:
            str: 作成したワークフローID
        """
        from uuid import uuid4
        from datetime import datetime
        from tests.integration.db_init import Workflow
        
        workflow_id = f"workflow-{uuid4().hex[:8]}"
        
        workflow = Workflow(
            id=workflow_id,
            name=f"テストワークフロー {workflow_id}",
            description="統合テスト用のワークフロー",
            procedure_id=procedure_id,
            sample_data_id=sample_id,
            status="created",
            current_step="initial",
            progress=0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.session.add(workflow)
        self.session.commit()
        
        logger.info(f"テストワークフローを作成しました: {workflow_id}")
        return workflow_id
    
    def get_sample_data_id(self) -> str:
        """
        テスト用のサンプルデータIDを取得
        
        Returns:
            str: サンプルデータID
        """
        from tests.integration.db_init import SampleData
        
        sample = self.session.query(SampleData).first()
        if not sample:
            raise ValueError("サンプルデータが見つかりません")
        
        return sample.id
    
    def get_procedure_id(self) -> str:
        """
        テスト用の監査手続きIDを取得
        
        Returns:
            str: 監査手続きID
        """
        from tests.integration.db_init import AuditProcedure
        
        procedure = self.session.query(AuditProcedure).first()
        if not procedure:
            raise ValueError("監査手続きが見つかりません")
        
        return procedure.id 