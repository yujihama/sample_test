"""
データモデルを定義するPydanticスキーマ
"""

from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import uuid


class AuditStatus(str, Enum):
    """監査ステータスの列挙型"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    HUMAN_INTERVENTION_REQUIRED = "human_intervention_required"  # 人間の介入が必要
    PAUSED = "paused"  # 一時停止（人間の応答を待機中など）


class TestResult(str, Enum):
    """テスト結果の列挙型"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


class RiskLevel(str, Enum):
    """リスクレベルの列挙型"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditProcedure(BaseModel):
    """監査手続きのデータモデル"""
    id: str = Field(..., description="監査手続きの一意識別子")
    title: str = Field(..., description="監査手続きのタイトル")
    description: str = Field(..., description="監査手続きの詳細説明")
    risk_areas: List[str] = Field(default_factory=list, description="関連するリスク領域")
    required_data_fields: List[str] = Field(default_factory=list, description="必要なデータフィールド")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")
    updated_at: Optional[datetime] = Field(None, description="更新日時")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "proc-12345",
                "title": "売掛金の回収可能性評価",
                "description": "売掛金の期日経過状況と回収可能性を評価するための手続き",
                "risk_areas": ["信用リスク", "流動性リスク"],
                "required_data_fields": ["顧客ID", "請求日", "金額", "支払い期日", "支払い状況"],
                "created_at": "2023-05-01T09:00:00",
                "updated_at": None
            }
        }
    )


class SampleData(BaseModel):
    """サンプルデータのメタ情報"""
    id: str = Field(..., description="サンプルデータの一意識別子")
    procedure_id: str = Field(..., description="関連する監査手続きのID")
    data_source: str = Field(..., description="データソース(ファイル名など)")
    data_format: str = Field(..., description="データ形式(CSV, Excel, etc)")
    sample_size: int = Field(..., description="サンプル数")
    columns: List[str] = Field(..., description="データ列名")
    uploaded_at: datetime = Field(default_factory=datetime.now, description="アップロード日時")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "sample-12345",
                "procedure_id": "proc-12345",
                "data_source": "accounts_receivable_2023.csv",
                "data_format": "CSV",
                "sample_size": 250,
                "columns": ["customer_id", "invoice_date", "amount", "due_date", "payment_status"],
                "uploaded_at": "2023-05-01T10:30:00"
            }
        }
    )


class AuditSample(BaseModel):
    """監査サンプルデータのモデル"""
    id: str = Field(..., description="監査サンプルの一意識別子")
    type: Optional[str] = Field(None, description="サンプルの種類")
    application_amount: Optional[float] = Field(None, description="申請金額")
    approved_amount: Optional[float] = Field(None, description="承認金額")
    approval_type: Optional[str] = Field(None, description="承認タイプ")
    approver: Optional[str] = Field(None, description="承認者名")
    approver_title: Optional[str] = Field(None, description="承認者役職")
    approval_date: Optional[str] = Field(None, description="承認日")
    execution_date: Optional[str] = Field(None, description="実行日")
    remarks: Optional[str] = Field(None, description="備考")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")
    updated_at: Optional[datetime] = Field(None, description="更新日時")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "sample-12345",
                "type": "budget_approval",
                "application_amount": 1000000,
                "approved_amount": 950000,
                "approval_type": "条件付承認",
                "approver": "山田太郎",
                "approver_title": "財務部長",
                "approval_date": "2023-05-15",
                "execution_date": "2023-05-20",
                "remarks": "予算の範囲内で調整",
                "created_at": "2023-05-15T10:30:00",
                "updated_at": None
            }
        }
    )


class TestPlan(BaseModel):
    """エージェントAが作成するテスト計画"""
    id: str = Field(..., description="テスト計画の一意識別子")
    procedure_id: str = Field(..., description="関連する監査手続きのID")
    sample_id: str = Field(..., description="関連するサンプルデータのID")
    test_items: List[Dict[str, Any]] = Field(..., description="テスト項目のリスト")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "plan-12345",
                "procedure_id": "proc-12345",
                "sample_id": "sample-12345",
                "test_items": [
                    {
                        "id": "item-001",
                        "name": "期日経過債権の確認",
                        "description": "支払い期日から30日以上経過している売掛金を特定する",
                        "expected_result": "期日を30日以上経過した債権が全体の10%未満であること",
                        "risk_level": "medium",
                        "validation_criteria": {
                            "type": "threshold",
                            "field": "days_overdue",
                            "operator": ">",
                            "value": 30,
                            "threshold_percentage": 10
                        }
                    },
                    {
                        "id": "item-002",
                        "name": "大口債権の確認",
                        "description": "金額が100万円を超える売掛金の回収状況を確認する",
                        "expected_result": "100万円超の債権がすべて管理記録と一致していること",
                        "risk_level": "high",
                        "validation_criteria": {
                            "type": "filter",
                            "field": "amount",
                            "operator": ">",
                            "value": 1000000
                        }
                    }
                ],
                "created_at": "2023-05-02T09:15:00"
            }
        }
    )


class TestItemResult(BaseModel):
    """個別テスト項目の結果"""
    test_item_id: str = Field(..., description="テスト項目のID")
    result: TestResult = Field(..., description="テスト結果")
    details: Optional[str] = Field(None, description="詳細情報")
    affected_rows: Optional[List[int]] = Field(None, description="影響を受けた行")
    exception_data: Optional[Dict[str, Any]] = Field(None, description="例外データ")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "test_item_id": "item-001",
                "result": "warning",
                "details": "支払い期日を30日以上経過した債権が全体の15%あります。基準値10%を超えています。",
                "affected_rows": [12, 25, 38, 45, 67],
                "exception_data": {
                    "total_overdue": 15,
                    "threshold": 10,
                    "overdue_amounts": [125000, 89000, 230000, 45000, 178000]
                }
            }
        }
    )


class TestExecutionResult(BaseModel):
    """エージェントBが実行するテスト結果"""
    id: str = Field(..., description="テスト実行の一意識別子")
    plan_id: str = Field(..., description="関連するテスト計画のID")
    execution_status: str = Field(..., description="実行ステータス")
    results: List[TestItemResult] = Field(..., description="テスト項目ごとの結果")
    summary: Dict[str, int] = Field(..., description="結果サマリー")
    executed_at: datetime = Field(default_factory=datetime.now, description="実行日時")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "exec-12345",
                "plan_id": "plan-12345",
                "execution_status": "completed",
                "results": [
                    {
                        "test_item_id": "item-001",
                        "result": "failed",
                        "details": "期日経過債権が閾値を超えています",
                        "affected_rows": 150,
                        "exception_data": {
                            "overdue_amount": 1500000,
                            "threshold": 1000000,
                            "percentage": 15
                        }
                    },
                    {
                        "test_item_id": "item-002",
                        "result": "passed",
                        "details": "回収率は許容範囲内です",
                        "affected_rows": 0,
                        "exception_data": None
                    }
                ],
                "summary": {
                    "pass": 1,
                    "fail": 0,
                    "warning": 1,
                    "error": 0,
                    "skipped": 0
                },
                "executed_at": "2023-05-03T11:25:00"
            }
        }
    )


class Finding(BaseModel):
    """監査上の発見事項"""
    id: str = Field(..., description="発見事項の一意識別子")
    execution_id: str = Field(..., description="関連するテスト実行のID")
    title: str = Field(..., description="発見事項のタイトル")
    description: str = Field(..., description="発見事項の詳細説明")
    risk_level: RiskLevel = Field(..., description="リスクレベル")
    affected_test_items: List[str] = Field(..., description="関連するテスト項目ID")
    recommendation: Optional[str] = Field(None, description="改善提案")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "finding-12345",
                "execution_id": "exec-12345",
                "title": "期日経過債権の増加傾向",
                "description": "支払い期日を30日以上経過した債権が全体の15%を占めており、前年度の8%から大幅に増加しています。",
                "risk_level": "medium",
                "affected_test_items": ["item-001"],
                "recommendation": "期日経過債権に対する管理プロセスの見直しと、早期回収の取り組みを強化することを推奨します。",
                "created_at": "2023-05-04T14:30:00"
            }
        }
    )


class AuditSummary(BaseModel):
    """エージェントCが作成する監査総括"""
    id: str = Field(..., description="監査総括の一意識別子")
    procedure_id: str = Field(..., description="関連する監査手続きのID")
    execution_id: str = Field(..., description="関連するテスト実行のID")
    findings: List[Finding] = Field(..., description="発見事項のリスト")
    conclusion: str = Field(..., description="総合的な結論")
    risk_assessment: Dict[str, int] = Field(..., description="リスク評価")
    additional_tests_required: bool = Field(False, description="追加テストの必要性")
    additional_test_areas: Optional[List[str]] = Field(None, description="追加テストが必要な領域")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "summary-12345",
                "procedure_id": "proc-12345",
                "execution_id": "exec-12345",
                "findings": [
                    {
                        "id": "finding-12345",
                        "execution_id": "exec-12345",
                        "title": "期日経過債権の増加傾向",
                        "description": "支払い期日を30日以上経過した債権が全体の15%を占めており、前年度の8%から大幅に増加しています。",
                        "risk_level": "medium",
                        "affected_test_items": ["item-001"],
                        "recommendation": "期日経過債権に対する管理プロセスの見直しと、早期回収の取り組みを強化することを推奨します。",
                        "created_at": "2023-05-04T14:30:00"
                    }
                ],
                "conclusion": "売掛金管理においてリスクの増加が見られます。特に期日経過債権の増加は、将来的なキャッシュフローや貸倒リスクに影響する可能性があります。",
                "risk_assessment": {
                    "cash_flow": 3,
                    "bad_debt": 4,
                    "financial_reporting": 2
                },
                "additional_tests_required": True,
                "additional_test_areas": ["売掛金の年齢調べ", "貸倒引当金の妥当性検証"],
                "created_at": "2023-05-05T16:45:00"
            }
        }
    )


class ReportTemplate(BaseModel):
    """監査報告書のテンプレート"""
    id: str = Field(..., description="テンプレートの一意識別子")
    name: str = Field(..., description="テンプレート名")
    sections: List[Dict[str, Any]] = Field(..., description="テンプレートのセクション構造")
    variables: Dict[str, str] = Field(..., description="テンプレート内の変数とその説明")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "template-12345",
                "name": "標準監査報告書",
                "sections": [
                    {
                        "title": "要約",
                        "required": True,
                        "content_guide": "監査の目的、範囲、結論を簡潔に記載。最大500文字。"
                    },
                    {
                        "title": "背景",
                        "required": True,
                        "content_guide": "監査対象の業務概要と監査が必要とされる背景を説明。"
                    },
                    {
                        "title": "発見事項と推奨対応",
                        "required": True,
                        "content_guide": "重要度順に発見事項を列挙し、それぞれに推奨対応を記載。"
                    },
                    {
                        "title": "結論",
                        "required": True,
                        "content_guide": "全体としての評価と次のステップの提案。"
                    },
                    {
                        "title": "付録",
                        "required": False,
                        "content_guide": "詳細なデータや分析結果。"
                    }
                ],
                "variables": {
                    "AUDIT_DATE": "監査実施日",
                    "DEPARTMENT": "監査対象部門",
                    "TEAM_MEMBERS": "監査チームメンバー",
                    "STAKEHOLDERS": "利害関係者"
                },
                "created_at": "2023-05-15T10:00:00"
            }
        }
    )


class AuditReport(BaseModel):
    """完成した監査報告書"""
    id: str = Field(..., description="報告書の一意識別子")
    procedure_id: str = Field(..., description="関連する監査手続きのID")
    summary_id: str = Field(..., description="関連する監査総括のID")
    template_id: str = Field(..., description="使用したテンプレートのID")
    content: Dict[str, Any] = Field(..., description="レポートの内容")
    variables_used: Dict[str, str] = Field(..., description="使用された変数と値")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "report-12345",
                "procedure_id": "proc-12345",
                "summary_id": "summary-12345",
                "template_id": "template-001",
                "content": {
                    "title": "売掛金の回収可能性評価 監査報告書",
                    "introduction": "本報告書は、売掛金の回収可能性評価に関する...",
                    "findings": [
                        {
                            "title": "90日以上の滞留債権",
                            "description": "全売掛金の15%が90日以上滞留しており...",
                            "risk_level": "high"
                        }
                    ],
                    "conclusion": "売掛金管理プロセスに改善の余地があります..."
                },
                "variables_used": {
                    "company_name": "サンプル株式会社",
                    "audit_date": "2023-05-15",
                    "auditor_name": "監査 太郎"
                },
                "created_at": "2023-05-15T15:30:00"
            }
        }
    )


class MessageType(str, Enum):
    """メッセージタイプを表す列挙型"""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    ERROR = "error"
    STATUS = "status"
    HUMAN_QUERY = "human_query"
    QUERY = "query"
    COMMAND = "command"


class MessagePriority(str, Enum):
    """メッセージの優先度を表す列挙型"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class AgentRole(str, Enum):
    """エージェントの役割を表す列挙型"""
    SUPERVISOR = "supervisor"
    WORKER = "worker"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"
    HUMAN = "human"


class AgentStatus(str, Enum):
    """エージェントの状態を表す列挙型"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class WorkflowStatus(str, Enum):
    """ワークフローの状態を表す列挙型"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    """タスクの状態を表す列挙型"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class AgentBase(BaseModel):
    """エージェントの基本情報を表すモデル"""
    agent_id: str
    name: str
    description: Optional[str] = None
    capabilities: List[str] = []
    status: AgentStatus = AgentStatus.IDLE
    metadata: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class AgentCreate(AgentBase):
    """エージェント作成時のリクエストモデル"""
    pass


class Agent(AgentBase):
    """エージェントの完全な情報を表すモデル"""
    created_at: str
    updated_at: str


class WorkflowBase(BaseModel):
    """ワークフローの基本情報を表すモデル"""
    workflow_id: str
    name: str
    description: Optional[str] = None
    agent_ids: List[str]
    status: WorkflowStatus = WorkflowStatus.PENDING
    metadata: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class WorkflowCreate(WorkflowBase):
    """ワークフロー作成時のリクエストモデル"""
    pass


class Workflow(WorkflowBase):
    """ワークフローの完全な情報を表すモデル"""
    created_at: str
    updated_at: str


class TaskBase(BaseModel):
    """タスクの基本情報を表すモデル"""
    task_id: str
    difficulty: int = Field(ge=1, le=10, description="タスクの難易度（1-10）")
    description: str
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent_id: Optional[str] = None
    metadata: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class TaskCreate(TaskBase):
    """タスク作成時のリクエストモデル"""
    pass


class Task(TaskBase):
    """タスクの完全な情報を表すモデル"""
    created_at: str
    updated_at: str
    completion_time: Optional[str] = None
    error_message: Optional[str] = None
    human_feedback: Optional[str] = None


class SearchResponse(BaseModel):
    """検索結果を表すモデル"""
    total: int = Field(..., description="総検索ヒット数")
    regulations: List[str] = Field(..., description="検索結果規程リスト")
    matches: Optional[List[Dict[str, Any]]] = Field(None, description="マッチした部分の詳細情報")


class AgentMessage(BaseModel):
    """エージェント間のメッセージを表すモデル"""
    message_id: str = Field(..., description="メッセージの一意識別子")
    sender_id: str = Field(..., description="送信者のエージェントID")
    receiver_id: Optional[str] = Field(None, description="受信者のエージェントID")
    message_type: MessageType = Field(..., description="メッセージのタイプ")
    priority: MessagePriority = Field(default=MessagePriority.NORMAL, description="メッセージの優先度")
    content: Dict[str, Any] = Field(..., description="メッセージの内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="追加のメタデータ")
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")
    processed_at: Optional[datetime] = Field(None, description="処理完了日時")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message_id": "msg-12345",
                "sender_id": "agent-001",
                "receiver_id": "agent-002",
                "message_type": "task_request",
                "priority": "normal",
                "content": {
                    "task_id": "task-789",
                    "action": "analyze_data",
                    "parameters": {
                        "dataset_id": "data-456",
                        "analysis_type": "anomaly_detection"
                    }
                },
                "metadata": {
                    "workflow_id": "workflow-123",
                    "step_number": 2
                },
                "created_at": "2023-05-10T15:30:00",
                "processed_at": None
            }
        }
    )
