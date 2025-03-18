#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
統合テスト用データベース初期化スクリプト
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import sqlalchemy
from sqlalchemy import create_engine, inspect, Column, String, Integer, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# テスト設定をインポート
from tests.integration.test_config import (
    TEST_DB_CONFIG,
    get_temp_db_config,
    TEST_AUDIT_PROCEDURES,
    TEST_SAMPLE_DATA,
    TEST_SAMPLE_DATA_PATH
)

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQLAlchemyのベースクラス
Base = declarative_base()


# データベースモデル定義 (src/models/db_models.pyと同一の定義)
class AuditProcedure(Base):
    """監査手続き情報を管理するモデル"""
    __tablename__ = "audit_procedure"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    procedure_text = Column(Text, nullable=False)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    sample_data = relationship("SampleData", back_populates="procedure")
    workflows = relationship("Workflow", back_populates="procedure")


class SampleData(Base):
    """サンプルデータ情報を管理するモデル"""
    __tablename__ = "sample_data"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    data_type = Column(String(100), nullable=True)
    content = Column(JSON, nullable=True)
    data_metadata = Column(JSON, nullable=True)
    procedure_id = Column(String(50), ForeignKey("audit_procedure.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    procedure = relationship("AuditProcedure", back_populates="sample_data")
    workflows = relationship("Workflow", back_populates="sample_data")


class Workflow(Base):
    """ワークフロー情報を管理するモデル"""
    __tablename__ = "workflow"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    procedure_id = Column(String(50), ForeignKey("audit_procedure.id"), nullable=True)
    sample_data_id = Column(String(50), ForeignKey("sample_data.id"), nullable=True)
    status = Column(String(50), default="created")
    current_step = Column(String(50), nullable=True)
    progress = Column(Integer, default=0)
    state_file = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    procedure = relationship("AuditProcedure", back_populates="workflows")
    sample_data = relationship("SampleData", back_populates="workflows")
    agent_states = relationship("AgentState", back_populates="workflow")
    audit_results = relationship("AuditResult", back_populates="workflow")
    final_reports = relationship("FinalReport", back_populates="workflow")


class AgentState(Base):
    """エージェント状態を管理するモデル"""
    __tablename__ = "agent_state"
    
    id = Column(String(50), primary_key=True)
    workflow_id = Column(String(50), ForeignKey("workflow.id"), nullable=False)
    agent_id = Column(String(50), nullable=False)
    agent_type = Column(String(100), nullable=False)
    status = Column(String(50), default="not_started")
    data = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    workflow = relationship("Workflow", back_populates="agent_states")


class AuditResult(Base):
    """監査結果を管理するモデル"""
    __tablename__ = "audit_result"
    
    id = Column(String(50), primary_key=True)
    workflow_id = Column(String(50), ForeignKey("workflow.id"), nullable=False)
    procedure_id = Column(String(50), ForeignKey("audit_procedure.id"), nullable=True)
    compliance_level = Column(String(50), nullable=True)
    risk_level = Column(String(50), nullable=True)
    summary = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    status = Column(String(50), default="open")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    workflow = relationship("Workflow", back_populates="audit_results")


class FinalReport(Base):
    """最終監査レポートを管理するモデル"""
    __tablename__ = "final_report"
    
    id = Column(String(50), primary_key=True)
    workflow_id = Column(String(50), ForeignKey("workflow.id"), nullable=False)
    procedure_id = Column(String(50), ForeignKey("audit_procedure.id"), nullable=True)
    title = Column(String(200), nullable=True)
    content = Column(JSON, nullable=False)
    status = Column(String(50), default="completed")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    workflow = relationship("Workflow", back_populates="final_reports")


def get_database_url(db_config: Dict[str, Any]) -> str:
    """
    データベース設定からSQLAlchemy接続URLを生成する
    
    Args:
        db_config: データベース設定辞書
        
    Returns:
        str: SQLAlchemy接続URL
    """
    dialect = db_config.get("dialect", "sqlite")
    driver = db_config.get("driver", "")
    username = db_config.get("username", "")
    password = db_config.get("password", "")
    host = db_config.get("host", "")
    port = db_config.get("port", "")
    database = db_config.get("database", ":memory:")
    query = db_config.get("query", {})
    
    # クエリパラメータ文字列の構築
    query_str = ""
    if query:
        query_str = "?" + "&".join([f"{k}={v}" for k, v in query.items()])
    
    # ドライバー部分の構築
    driver_str = f"+{driver}" if driver else ""
    
    # SQLite特有の処理
    if dialect == "sqlite":
        if database == ":memory:":
            return f"{dialect}{driver_str}:///{database}{query_str}"
        else:
            # ファイルパスの場合は絶対パスに変換
            return f"{dialect}{driver_str}:///{database}{query_str}"
    
    # 認証情報部分の構築
    auth_str = ""
    if username:
        auth_str = username
        if password:
            auth_str += f":{password}"
        auth_str += "@"
    
    # ホスト部分の構築
    host_str = ""
    if host:
        host_str = host
        if port:
            host_str += f":{port}"
    
    # その他のデータベースタイプの処理
    return f"{dialect}{driver_str}://{auth_str}{host_str}/{database}{query_str}"


def init_database(db_config: Dict[str, Any], echo: bool = False) -> sqlalchemy.engine.Engine:
    """
    データベースを初期化し、必要なテーブルを作成する
    
    Args:
        db_config: データベース設定辞書
        echo: SQLログを出力するかどうか
        
    Returns:
        sqlalchemy.engine.Engine: 初期化されたデータベースエンジン
    """
    try:
        # データベース接続URLの生成
        db_url = get_database_url(db_config)
        logger.info(f"データベース初期化: {db_url}")
        
        # エンジンの作成
        engine = create_engine(db_url, echo=echo)
        
        # 既存のテーブルを確認
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        logger.info(f"既存のテーブル: {existing_tables}")
        
        # テーブルの作成
        logger.info("テーブルを作成します...")
        Base.metadata.create_all(engine)
        
        logger.info("データベース初期化が完了しました")
        return engine
    
    except SQLAlchemyError as e:
        logger.error(f"データベース初期化中にエラーが発生しました: {e}")
        raise


def load_test_data(engine: sqlalchemy.engine.Engine) -> None:
    """
    テスト用データをデータベースに読み込む
    
    Args:
        engine: 初期化済みのデータベースエンジン
    """
    try:
        # セッションの作成
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # 監査手続きの作成
            for proc_data in TEST_AUDIT_PROCEDURES:
                # 既存の監査手続きをチェック
                existing_proc = session.query(AuditProcedure).filter(AuditProcedure.id == proc_data["id"]).first()
                if existing_proc:
                    logger.info(f"監査手続き {proc_data['id']} は既に存在します")
                    continue
                
                # 新しい監査手続きを作成
                procedure = AuditProcedure(
                    id=proc_data["id"],
                    name=proc_data["name"],
                    description=proc_data["description"],
                    procedure_text=proc_data["procedure_text"],
                    status="active",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                session.add(procedure)
            
            # サンプルデータの作成
            for sample_data in TEST_SAMPLE_DATA:
                # 既存のサンプルデータをチェック
                existing_sample = session.query(SampleData).filter(SampleData.id == sample_data["id"]).first()
                if existing_sample:
                    logger.info(f"サンプルデータ {sample_data['id']} は既に存在します")
                    continue
                
                # 新しいサンプルデータを作成
                sample = SampleData(
                    id=sample_data["id"],
                    name=sample_data["name"],
                    description=sample_data["description"],
                    data_type=sample_data["data_type"],
                    content=sample_data["content"],
                    data_metadata=sample_data["metadata"],
                    procedure_id=sample_data["procedure_id"],
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                session.add(sample)
            
            # コミット
            session.commit()
            logger.info("テストデータの読み込みが完了しました")
        
        except Exception as e:
            session.rollback()
            logger.error(f"テストデータの読み込み中にエラーが発生しました: {e}")
            raise
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"テストデータの読み込み中にエラーが発生しました: {e}")
        raise


def main():
    """スクリプトのメイン処理"""
    try:
        # デフォルトはインメモリデータベース
        db_config = TEST_DB_CONFIG
        
        # コマンドライン引数で他の設定を選択可能
        import argparse
        parser = argparse.ArgumentParser(description="テスト用データベースの初期化")
        parser.add_argument("--db-type", choices=["memory", "sqlite", "postgres"], default="memory",
                          help="使用するデータベースタイプ (memory: インメモリSQLite, sqlite: ファイルベースSQLite, postgres: PostgreSQL)")
        args = parser.parse_args()
        
        if args.db_type == "sqlite":
            db_config = get_temp_db_config()
            logger.info(f"一時ファイルSQLiteデータベースを使用: {db_config['database']}")
        elif args.db_type == "postgres":
            from tests.integration.test_config import get_postgres_test_config
            db_config = get_postgres_test_config()
            logger.info(f"PostgreSQLデータベースを使用: {db_config['database']} @ {db_config['host']}")
        
        # データベースの初期化
        engine = init_database(db_config, echo=True)
        
        # テストデータの読み込み
        load_test_data(engine)
        
        logger.info("データベース初期化処理が完了しました")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 