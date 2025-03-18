"""
テストデータ生成スクリプト
内部監査サンプルデータ自動テストAIエージェントシステムの動作確認のためのテストデータを生成します。
"""

import os
import sys
import random
import datetime
from pathlib import Path
import json
from src.utils import json_utils
import uuid
from enum import Enum

# ルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.config import settings, initialize_app
from src.utils.db_manager import init_db, session_scope
from src.models.repositories import (
    AuditProcedureRepository,
    SampleDataRepository,
    WorkflowRepository,
    AgentStateRepository
)
from src.models.db_models import (
    AuditProcedure,
    SampleData,
    Workflow,
    AgentState
)

# ワークフローの状態を表す列挙型
class WorkflowStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


def create_audit_procedures():
    """監査手続きのテストデータを作成"""
    procedures = [
        {
            "title": "経費申請プロセスの監査",
            "description": "経費申請と承認プロセスの適切性を評価し、不正や誤りがないか確認する。目的：経費申請プロセスの透明性と正確性を確保する。範囲：全部門の経費申請データ（2024年1月～3月）",
            "risk_areas": ["承認漏れ", "証憑不足", "経費ポリシー違反", "二重申請"],
            "required_data_fields": ["申請ID", "申請日", "申請者", "部門", "金額", "目的", "承認者", "承認日", "ステータス", "備考"]
        },
        {
            "title": "在庫管理プロセスの監査",
            "description": "在庫管理プロセスの効率性と正確性を評価し、在庫の過不足や不正がないか確認する。目的：在庫管理の適切性と資産保全を確保する。範囲：主要倉庫の在庫データ（2024年第1四半期）",
            "risk_areas": ["在庫過剰", "在庫不足", "記録不一致", "不正アクセス"],
            "required_data_fields": ["商品ID", "商品名", "カテゴリ", "在庫数", "理論在庫", "単価", "倉庫", "最終更新日", "担当者"]
        }
    ]
    
    repo = AuditProcedureRepository()
    created_procedures = []
    
    with session_scope() as session:
        for proc in procedures:
            proc_obj = {
                "id": f"proc-{uuid.uuid4().hex[:8]}",
                "title": proc["title"],
                "description": proc["description"],
                "risk_areas": json_utils.json_serialize(proc["risk_areas"]),
                "required_data_fields": json_utils.json_serialize(proc["required_data_fields"]),
                "created_at": datetime.datetime.now(),
                "updated_at": datetime.datetime.now()
            }
            
            created = repo.create(session, proc_obj)
            # セッションが閉じられた後でも使用できるように必要な情報だけを保存
            created_procedures.append({
                "id": created.id,
                "title": created.title
            })
            print(f"監査手続きを作成しました: {created.title} (ID: {created.id})")
    
    return created_procedures


def create_sample_data(procedures):
    """サンプルデータのテストデータを作成"""
    # サンプルデータのファイルを保存するディレクトリを作成
    sample_dir = os.path.join(settings.DATA_DIR, "samples")
    os.makedirs(sample_dir, exist_ok=True)
    
    sample_data_list = []
    repo = SampleDataRepository()
    
    with session_scope() as session:
        for procedure in procedures:
            # 経費申請プロセスの監査用サンプルデータ
            if "経費申請" in procedure["title"]:
                # CSVファイルの内容を作成
                csv_content = """申請ID,申請日,申請者,部門,金額,目的,承認者,承認日,ステータス,備考
EXP001,2024-01-05,田中太郎,営業部,15000,取引先訪問交通費,佐藤部長,2024-01-06,承認済,
EXP002,2024-01-10,鈴木花子,マーケティング部,50000,展示会参加費,伊藤部長,2024-01-12,承認済,
EXP003,2024-01-15,佐藤健太,技術部,30000,研修参加費,加藤部長,,未承認,
EXP004,2024-01-20,高橋美咲,営業部,25000,接待費,佐藤部長,2024-01-21,承認済,領収書不足
EXP005,2024-01-25,渡辺淳,財務部,18000,書籍購入費,山本部長,2024-01-26,承認済,
EXP006,2024-02-03,伊藤誠,マーケティング部,70000,広告費,伊藤部長,,未承認,予算超過
EXP007,2024-02-08,小林雅人,技術部,12000,消耗品購入,加藤部長,2024-02-09,承認済,
EXP008,2024-02-15,松本さやか,人事部,45000,研修費,中村部長,2024-02-16,承認済,
EXP009,2024-02-20,山田太郎,営業部,30000,取引先訪問交通費,佐藤部長,2024-02-21,承認済,
EXP010,2024-02-25,中村悠太,技術部,55000,ソフトウェア購入,加藤部長,2024-02-28,承認済,
EXP011,2024-03-05,田中太郎,営業部,15000,取引先訪問交通費,佐藤部長,,未承認,
EXP012,2024-03-10,鈴木花子,マーケティング部,22000,資料印刷費,伊藤部長,2024-03-11,承認済,
EXP013,2024-03-15,高橋美咲,営業部,25000,接待費,佐藤部長,2024-03-16,承認済,領収書不足
EXP014,2024-03-20,渡辺淳,財務部,35000,書籍購入費,山本部長,,未承認,金額超過
EXP015,2024-03-25,佐藤健太,技術部,9000,消耗品購入,加藤部長,2024-03-26,承認済,"""
                
                # ファイルに保存
                file_path = os.path.join(sample_dir, "expense_data.csv")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(csv_content)
                
                # サンプルデータレコードを作成
                sample_obj = {
                    "id": f"sample-{uuid.uuid4().hex[:8]}",
                    "procedure_id": procedure["id"],
                    "filename": "expense_data.csv",
                    "file_path": file_path,
                    "content_type": "text/csv",
                    "row_count": 15,
                    "columns": json_utils.json_serialize(["申請ID", "申請日", "申請者", "部門", "金額", "目的", "承認者", "承認日", "ステータス", "備考"]),
                    "file_metadata": json_utils.json_serialize({"description": "全部門の経費申請と承認状況のサンプルデータ"}),
                    "created_at": datetime.datetime.now()
                }
                created = repo.create(session, sample_obj)
                sample_data_list.append({
                    "id": created.id,
                    "procedure_id": created.procedure_id
                })
                print(f"サンプルデータを作成しました: {created.filename} (ID: {created.id})")
            
            # 在庫管理プロセスの監査用サンプルデータ
            elif "在庫管理" in procedure["title"]:
                # CSVファイルの内容を作成
                csv_content = """商品ID,商品名,カテゴリ,在庫数,理論在庫,単価,倉庫,最終更新日,担当者
INV001,ノートPC A型,電子機器,15,15,120000,東京倉庫,2024-03-15,鈴木
INV002,デスクトップPC B型,電子機器,8,10,150000,東京倉庫,2024-03-15,鈴木
INV003,モニター C型,電子機器,23,20,35000,東京倉庫,2024-03-15,鈴木
INV004,キーボード D型,周辺機器,45,50,5000,東京倉庫,2024-03-15,田中
INV005,マウス E型,周辺機器,38,40,3000,東京倉庫,2024-03-15,田中
INV006,ハードディスク F型,ストレージ,12,15,18000,大阪倉庫,2024-03-10,佐藤
INV007,SSD G型,ストレージ,22,20,25000,大阪倉庫,2024-03-10,佐藤
INV008,メモリ H型,部品,30,30,12000,大阪倉庫,2024-03-10,佐藤
INV009,プリンター I型,電子機器,5,5,80000,大阪倉庫,2024-03-10,山田
INV010,トナー J型,消耗品,15,25,15000,大阪倉庫,2024-03-10,山田
INV011,ノートPC K型,電子機器,0,5,130000,東京倉庫,2024-03-15,鈴木
INV012,タブレット L型,電子機器,18,15,85000,東京倉庫,2024-03-15,鈴木
INV013,スマートフォン M型,電子機器,7,10,95000,大阪倉庫,2024-03-10,佐藤
INV014,ケーブル N型,周辺機器,95,90,2000,大阪倉庫,2024-03-10,佐藤
INV015,ヘッドフォン O型,周辺機器,25,25,9000,東京倉庫,2024-03-15,田中"""
                
                # ファイルに保存
                file_path = os.path.join(sample_dir, "inventory_data.csv")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(csv_content)
                
                # サンプルデータレコードを作成
                sample_obj = {
                    "id": f"sample-{uuid.uuid4().hex[:8]}",
                    "procedure_id": procedure["id"],
                    "filename": "inventory_data.csv",
                    "file_path": file_path,
                    "content_type": "text/csv",
                    "row_count": 15,
                    "columns": json_utils.json_serialize(["商品ID", "商品名", "カテゴリ", "在庫数", "理論在庫", "単価", "倉庫", "最終更新日", "担当者"]),
                    "file_metadata": json_utils.json_serialize({"description": "主要倉庫の在庫記録と実在庫のサンプルデータ"}),
                    "created_at": datetime.datetime.now()
                }
                created = repo.create(session, sample_obj)
                sample_data_list.append({
                    "id": created.id,
                    "procedure_id": created.procedure_id
                })
                print(f"サンプルデータを作成しました: {created.filename} (ID: {created.id})")
    
    return sample_data_list


def create_workflows(procedures, sample_data_list):
    """ワークフローのテストデータを作成"""
    workflow_repo = WorkflowRepository()
    agent_state_repo = AgentStateRepository()
    created_workflows = []
    
    # 監査手続きとサンプルデータを関連付ける
    procedure_samples = {}
    for sample in sample_data_list:
        if sample["procedure_id"] not in procedure_samples:
            procedure_samples[sample["procedure_id"]] = []
        procedure_samples[sample["procedure_id"]].append(sample)
    
    with session_scope() as session:
        for procedure in procedures:
            if procedure["id"] in procedure_samples:
                for sample in procedure_samples[procedure["id"]]:
                    # ワークフローを作成
                    status = random.choice([
                        WorkflowStatus.NOT_STARTED,
                        WorkflowStatus.IN_PROGRESS,
                        WorkflowStatus.COMPLETED,
                        WorkflowStatus.FAILED
                    ])
                    
                    completed_at = datetime.datetime.now() if status == WorkflowStatus.COMPLETED else None
                    
                    workflow_obj = {
                        "id": f"workflow-{uuid.uuid4().hex[:8]}",
                        "audit_procedure_id": procedure["id"],
                        "sample_data_id": sample["id"],
                        "status": status.value,
                        "current_agent": None,
                        "progress": random.randint(0, 100),
                        "started_at": datetime.datetime.now(),
                        "updated_at": datetime.datetime.now(),
                        "completed_at": completed_at
                    }
                    
                    created_workflow = workflow_repo.create(session, workflow_obj)
                    created_workflows.append({
                        "id": created_workflow.id,
                        "procedure_id": created_workflow.audit_procedure_id,
                        "sample_id": created_workflow.sample_data_id
                    })
                    print(f"ワークフローを作成しました: {created_workflow.id} (手続き: {procedure['title']})")
                    
                    # エージェント状態を作成
                    for agent_id in [settings.AGENT_A_ID, settings.AGENT_B_ID, settings.AGENT_C_ID, settings.AGENT_D_ID]:
                        agent_status = "initialized" if status != WorkflowStatus.NOT_STARTED else "pending"
                        progress = random.randint(0, 100) if status == WorkflowStatus.IN_PROGRESS else 0
                        started_at = datetime.datetime.now() if status != WorkflowStatus.NOT_STARTED else None
                        completed_at = datetime.datetime.now() if status == WorkflowStatus.COMPLETED else None
                        
                        agent_state_obj = {
                            "id": f"state-{uuid.uuid4().hex[:8]}",
                            "workflow_id": created_workflow.id,
                            "agent_id": agent_id,
                            "status": agent_status,
                            "progress": progress,
                            "context": json_utils.json_serialize({"initialized": True}),
                            "started_at": started_at,
                            "updated_at": datetime.datetime.now(),
                            "completed_at": completed_at
                        }
                        
                        agent_state_repo.create(session, agent_state_obj)
                        print(f"エージェント状態を作成しました: {agent_id} (ワークフロー: {created_workflow.id})")
    
    return created_workflows


def main():
    """メイン関数"""
    print("テストデータ生成を開始します...")
    
    # アプリケーションの初期化
    initialize_app()
    
    # データベースの初期化
    init_db()
    
    # テストデータの作成
    print("\n=== 監査手続きの作成 ===")
    procedures = create_audit_procedures()
    
    print("\n=== サンプルデータの作成 ===")
    sample_data_list = create_sample_data(procedures)
    
    print("\n=== ワークフローの作成 ===")
    workflows = create_workflows(procedures, sample_data_list)
    
    print("\nテストデータ生成が完了しました！")
    print(f"監査手続き: {len(procedures)}件")
    print(f"サンプルデータ: {len(sample_data_list)}件")
    print(f"ワークフロー: {len(workflows)}件")


if __name__ == "__main__":
    main() 