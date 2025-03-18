"""
テストデータベースにインデックスを作成するスクリプト
"""

from sqlalchemy import create_engine, text

def create_indexes():
    """テストデータベースにインデックスを作成"""
    engine = create_engine('sqlite:///test_db.db')
    
    with engine.begin() as conn:
        # workflows テーブルのインデックス
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_workflows_procedure_id ON workflows (procedure_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_workflows_sample_id ON workflows (sample_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_workflows_status ON workflows (status)"))
        
        # agent_states テーブルのインデックス
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_agent_states_agent_id ON agent_states (agent_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_agent_states_workflow_id ON agent_states (workflow_id)"))
        
        # audit_results テーブルのインデックス
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_results_workflow_id ON audit_results (workflow_id)"))
        
        # sample_data テーブルのインデックス
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_sample_data_procedure_id ON sample_data (procedure_id)"))
        
        # findings テーブルのインデックス
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_findings_result_id ON findings (result_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_findings_risk_level ON findings (risk_level)"))
        
        # messages テーブルのインデックス
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_messages_from_agent ON messages (from_agent)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_messages_to_agent ON messages (to_agent)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_messages_is_processed ON messages (is_processed)"))
        
        # audit_procedures テーブルのインデックス
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_audit_procedures_title ON audit_procedures (title)"))
    
    print("インデックスが正常に作成されました。")

if __name__ == "__main__":
    create_indexes() 