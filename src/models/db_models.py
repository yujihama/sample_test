"""
SQLAlchemyデータベースモデル定義

このモジュールでは、アプリケーションで使用するすべてのSQLAlchemyモデルを定義します。
これらのモデルは、データベーステーブルとオブジェクト間のマッピングを提供します。
"""

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import logging

from src.utils.db_manager import Base


def generate_uuid():
    """UUIDを生成する関数"""
    return str(uuid.uuid4())


class AuditProcedure(Base):
    """監査手続きモデル"""
    __tablename__ = "audit_procedures"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    risk_areas = Column(Text)  # JSON文字列
    required_data_fields = Column(Text)  # JSON文字列
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # リレーションシップ
    sample_data = relationship("SampleData", back_populates="procedure")
    workflows = relationship("Workflow", back_populates="procedure")


class SampleData(Base):
    """サンプルデータモデル"""
    __tablename__ = "sample_data"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer)
    file_type = Column(String)
    row_count = Column(Integer)
    column_count = Column(Integer)
    columns = Column(Text)  # JSON文字列
    procedure_id = Column(String, ForeignKey("audit_procedures.id"))
    file_metadata = Column(Text)  # JSON文字列
    upload_time = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # リレーションシップ
    procedure = relationship("AuditProcedure", back_populates="sample_data")
    workflows = relationship("Workflow", back_populates="sample_data")


class Workflow(Base):
    """ワークフローモデル"""
    __tablename__ = "workflows"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    audit_procedure_id = Column(String, ForeignKey("audit_procedures.id"), nullable=False)
    sample_data_id = Column(String, ForeignKey("sample_data.id"), nullable=False)
    status = Column(String, nullable=False)
    current_agent = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    results = Column(Text)  # JSON文字列
    error = Column(Text)
    
    # リレーションシップ
    procedure = relationship("AuditProcedure", back_populates="workflows")
    sample_data = relationship("SampleData", back_populates="workflows")
    test_plans = relationship("TestPlan", back_populates="workflow")
    test_results = relationship("TestResult", back_populates="workflow")
    evaluation_summaries = relationship("EvaluationSummary", back_populates="workflow")
    reports = relationship("Report", back_populates="workflow")
    agent_states = relationship("AgentState", back_populates="workflow")
    audit_results = relationship("AuditResult", back_populates="workflow")
    human_intervention_requests = relationship("HumanInterventionRequest", back_populates="workflow")
    
    @classmethod
    def rollback(cls, session=None):
        """
        トランザクションをロールバックするクラスメソッド
        
        このメソッドは、クラスメソッドとしてもインスタンスメソッドとして
        両方の方法で呼び出せるように設計されています。
        
        Args:
            session: ロールバックするデータベースセッション（オプション）
                    クラスメソッドとして呼び出した場合は必須
        """
        # セッションが渡された場合、そのセッションをロールバック
        if session is not None:
            session.rollback()
        else:
            # インスタンスメソッドとして呼び出された場合の処理
            # または、セッションが渡されなかった場合のフォールバック
            logging.getLogger(__name__).warning("セッションが指定されていないためロールバックを実行できません")


class TestPlan(Base):
    """テスト計画モデル"""
    __tablename__ = "test_plans"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    test_items = Column(Text, nullable=False)  # JSON文字列
    prerequisites = Column(Text)  # JSON文字列
    required_data_fields = Column(Text)  # JSON文字列
    created_at = Column(DateTime, default=datetime.now)
    
    # リレーションシップ
    workflow = relationship("Workflow", back_populates="test_plans")
    test_results = relationship("TestResult", back_populates="test_plan")


class TestResult(Base):
    """テスト結果モデル"""
    __tablename__ = "test_results"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    test_plan_id = Column(String, ForeignKey("test_plans.id"), nullable=False)
    results = Column(Text, nullable=False)  # JSON文字列
    execution_time = Column(DateTime, default=datetime.now)
    status = Column(String, nullable=False)
    error = Column(Text)
    
    # リレーションシップ
    workflow = relationship("Workflow", back_populates="test_results")
    test_plan = relationship("TestPlan", back_populates="test_results")
    evaluation_summaries = relationship("EvaluationSummary", back_populates="test_result")


class EvaluationSummary(Base):
    """評価サマリーモデル"""
    __tablename__ = "evaluation_summaries"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    test_result_id = Column(String, ForeignKey("test_results.id"), nullable=False)
    overall_result = Column(Text, nullable=False)
    test_item_evaluations = Column(Text, nullable=False)  # JSON文字列
    key_findings = Column(Text)  # JSON文字列
    risk_assessment = Column(Text)  # JSON文字列
    recommendations = Column(Text)  # JSON文字列
    created_at = Column(DateTime, default=datetime.now)
    
    # リレーションシップ
    workflow = relationship("Workflow", back_populates="evaluation_summaries")
    test_result = relationship("TestResult", back_populates="evaluation_summaries")
    reports = relationship("Report", back_populates="evaluation")


class Report(Base):
    """報告書モデル"""
    __tablename__ = "reports"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    evaluation_id = Column(String, ForeignKey("evaluation_summaries.id"), nullable=False)
    title = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # リレーションシップ
    workflow = relationship("Workflow", back_populates="reports")
    evaluation = relationship("EvaluationSummary", back_populates="reports")


class MessageLog(Base):
    """メッセージログモデル"""
    __tablename__ = "message_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    from_agent = Column(String, nullable=False)
    to_agent = Column(String, nullable=False)
    message_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    processed_at = Column(DateTime)


class AgentState(Base):
    """エージェント状態モデル"""
    __tablename__ = "agent_states"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    agent_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    progress = Column(Integer, default=0)
    current_task = Column(String)
    input_data = Column(Text)  # JSON文字列
    output_data = Column(Text)  # JSON文字列
    metadata_json = Column(Text)  # JSON文字列
    error_info = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # リレーションシップ
    workflow = relationship("Workflow", back_populates="agent_states")
    messages = relationship("Message", back_populates="agent_state")
    agent_decisions = relationship("AgentDecision", back_populates="agent_state")


class AuditResult(Base):
    """監査結果モデル"""
    __tablename__ = "audit_results"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    summary = Column(Text, nullable=False)
    details = Column(Text)  # JSON文字列
    created_at = Column(DateTime, default=datetime.now)
    
    # リレーションシップ
    workflow = relationship("Workflow", back_populates="audit_results")
    findings = relationship("Finding", back_populates="audit_result")


class Finding(Base):
    """監査発見事項モデル"""
    __tablename__ = "findings"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    audit_result_id = Column(String, ForeignKey("audit_results.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    risk_level = Column(String)
    category = Column(String)
    evidence = Column(Text)  # JSON文字列
    created_at = Column(DateTime, default=datetime.now)
    
    # リレーションシップ
    audit_result = relationship("AuditResult", back_populates="findings")


class Message(Base):
    """エージェント間メッセージモデル"""
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    agent_state_id = Column(String, ForeignKey("agent_states.id"), nullable=False)
    to_agent_id = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String, nullable=False)
    meta_data = Column(Text)  # JSON文字列
    created_at = Column(DateTime, default=datetime.now)
    delivered_at = Column(DateTime)
    
    # リレーションシップ
    agent_state = relationship("AgentState", back_populates="messages")


class AuditTrail(Base):
    """監査証跡モデル"""
    __tablename__ = "audit_trails"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String)
    agent_id = Column(String)
    action = Column(String, nullable=False)
    details = Column(Text)  # JSON文字列
    created_at = Column(DateTime, default=datetime.now)


class GraphStateHistory(Base):
    """グラフ状態履歴モデル"""
    __tablename__ = "graph_state_histories"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, nullable=False)
    context_id = Column(String, nullable=True)
    agent_id = Column(String, nullable=False)
    node_id = Column(String)
    transition_from = Column(String)
    transition_to = Column(String)
    state_snapshot = Column(Text)  # 状態のJSON文字列
    state_diff = Column(Text)  # 前回の状態との差分（JSON文字列）
    event_type = Column(String)
    event_data = Column(Text)  # イベントデータ（JSON文字列）
    created_at = Column(DateTime, default=datetime.now)
    
    # 関連するチェックポイントへの参照
    checkpoint_id = Column(String, ForeignKey("checkpoint_records.id"), nullable=True)
    checkpoint = relationship("CheckpointRecord", back_populates="state_histories")


class CheckpointRecord(Base):
    """チェックポイント記録モデル"""
    __tablename__ = "checkpoint_records"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, nullable=False)
    context_id = Column(String, nullable=True)
    agent_id = Column(String, nullable=False)
    checkpoint_type = Column(String, nullable=False)  # auto, manual, error, restore
    node_id = Column(String)
    state_reference = Column(Text)  # 状態への参照情報（JSON文字列）
    checkpoint_metadata = Column(Text)  # メタデータ（JSON文字列）
    created_at = Column(DateTime, default=datetime.now)
    restored_at = Column(DateTime, nullable=True)
    restore_count = Column(Integer, default=0)
    
    # リレーションシップ
    state_histories = relationship("GraphStateHistory", back_populates="checkpoint")


class AgentDecision(Base):
    """エージェント判断履歴モデル"""
    __tablename__ = "agent_decisions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    agent_state_id = Column(String, ForeignKey("agent_states.id"), nullable=False)
    decision_type = Column(String, nullable=False)
    context = Column(Text, nullable=False)  # JSON文字列
    reasoning = Column(Text, nullable=False)
    decision = Column(Text, nullable=False)
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.now)
    
    # リレーションシップ
    agent_state = relationship("AgentState", back_populates="agent_decisions")


class HumanInterventionRequest(Base):
    """人間介入リクエストモデル"""
    __tablename__ = "human_intervention_requests"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    requesting_agent = Column(String, nullable=False)
    intervention_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    options = Column(Text)  # JSON文字列
    context_data = Column(Text)  # JSON文字列
    priority = Column(String, default="medium")
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # リレーションシップ
    workflow = relationship("Workflow", back_populates="human_intervention_requests")
    responses = relationship("HumanInterventionResponse", back_populates="request")


class HumanInterventionResponse(Base):
    """人間介入応答モデル"""
    __tablename__ = "human_intervention_responses"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    request_id = Column(String, ForeignKey("human_intervention_requests.id"), nullable=False)
    responder = Column(String, nullable=False)
    response_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    attachment_urls = Column(Text)  # JSON文字列
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    # リレーションシップ
    request = relationship("HumanInterventionRequest", back_populates="responses")


class Regulation(Base):
    """規程情報モデル"""
    __tablename__ = "regulations"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    code = Column(String, nullable=False, unique=True)  # 規程コード
    title = Column(String, nullable=False)  # 規程タイトル
    category = Column(String, nullable=False)  # カテゴリー (例: 出張規程、予算承認規程)
    content = Column(Text, nullable=False)  # 規程本文
    structured_content = Column(Text)  # 構造化された規程内容 (JSON文字列)
    version = Column(String, nullable=False)  # バージョン情報
    effective_date = Column(DateTime, nullable=False)  # 発効日
    expiration_date = Column(DateTime, nullable=True)  # 失効日
    parent_id = Column(String, ForeignKey("regulations.id"), nullable=True)  # 親規程ID
    keywords = Column(Text)  # キーワード (JSON文字列)
    meta_data = Column(Text)  # メタデータ (JSON文字列)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # リレーションシップ
    parent = relationship("Regulation", remote_side=[id], backref="children")  # 親子関係
    audit_trails = relationship("RegulationAuditTrail", back_populates="regulation")
    decision_references = relationship("RegulationDecisionReference", back_populates="regulation")


class RegulationAuditTrail(Base):
    """規程情報監査証跡モデル"""
    __tablename__ = "regulation_audit_trails"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    regulation_id = Column(String, ForeignKey("regulations.id"), nullable=False)
    action_type = Column(String, nullable=False)  # 操作種別 (作成、更新、参照)
    user_id = Column(String, nullable=False)  # 実行者 (ユーザーID)
    details = Column(Text)  # 詳細情報 (JSON文字列)
    action_timestamp = Column(DateTime, default=datetime.now)  # 操作日時
    created_at = Column(DateTime, default=datetime.now)
    
    # リレーションシップ
    regulation = relationship("Regulation", back_populates="audit_trails")


class RegulationDecisionReference(Base):
    """規程に基づく判断参照モデル"""
    __tablename__ = "regulation_decision_references"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    regulation_id = Column(String, ForeignKey("regulations.id"), nullable=False)
    workflow_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)  # 判断したユーザーID
    decision_point = Column(String, nullable=False)  # 判断ポイント
    decision = Column(String, nullable=False)  # 判断結果
    reasoning = Column(Text)  # 判断理由
    context = Column(Text)  # 判断コンテキスト (JSON文字列)
    decision_timestamp = Column(DateTime, default=datetime.now)  # 判断日時
    created_at = Column(DateTime, default=datetime.now)
    
    # リレーションシップ
    regulation = relationship("Regulation", back_populates="decision_references") 