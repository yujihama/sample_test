"""
テスト用ユーティリティ関数

このモジュールには、テストで使用するユーティリティ関数が含まれています。
特にテストデータの作成とテスト環境のセットアップ機能を提供します。
"""

import uuid
import logging
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ルートディレクトリへのパスを設定
import os
import sys
current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(current_dir)

from src.models.db_models import AuditProcedure, SampleData, Workflow
from src.core.config import settings

logger = logging.getLogger(__name__)

def create_test_workflow(db: Session) -> Workflow:
    """
    テスト用のワークフローを作成する
    
    Args:
        db: データベースセッション
        
    Returns:
        作成されたワークフローオブジェクト
    """
    try:
        # 監査手続きの作成
        procedure = AuditProcedure(
            id=f"proc-test-{uuid.uuid4().hex[:8]}",
            title="テスト用監査手続き",
            description="テスト用の監査手続きです",
            risk_areas=["test"],
            required_data_fields=["test_field"]
        )
        db.add(procedure)
        
        # サンプルデータの作成
        sample = SampleData(
            id=f"sample-test-{uuid.uuid4().hex[:8]}",
            procedure_id=procedure.id,
            filename="test.csv",
            file_path="/path/to/test.csv",
            content_type="text/csv",
            row_count=10,
            columns=["col1", "col2"]
        )
        db.add(sample)
        
        # ワークフローの作成
        workflow = Workflow(
            id=f"flow-test-{uuid.uuid4().hex[:8]}",
            audit_procedure_id=procedure.id,
            sample_data_id=sample.id,
            status="in_progress"
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        
        logger.info(f"テスト用ワークフローを作成しました: {workflow.id}")
        return workflow
    except Exception as e:
        db.rollback()
        logger.error(f"テスト用ワークフロー作成中にエラーが発生しました: {e}")
        raise

def setup_test_environment(db: Session = None):
    """
    テスト環境をセットアップする
    
    Args:
        db: オプションのデータベースセッション。指定されていない場合は新しいセッションを作成
        
    Returns:
        テスト環境の設定情報を含む辞書
    """
    session_created = False
    if db is None:
        # テスト用のデータベース接続を作成
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        session_created = True
    
    try:
        # テスト用のワークフローを作成
        workflow = create_test_workflow(db)
        
        return {
            "db": db,
            "workflow_id": workflow.id,
            "procedure_id": workflow.audit_procedure_id,
            "sample_id": workflow.sample_data_id,
            "session_created": session_created
        }
    except Exception as e:
        logger.error(f"テスト環境のセットアップに失敗しました: {e}")
        if session_created:
            db.close()
        raise 