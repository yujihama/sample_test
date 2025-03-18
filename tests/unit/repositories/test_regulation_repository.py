"""
規程情報リポジトリの単体テスト
"""

import pytest
import json
from datetime import datetime, timedelta
from uuid import uuid4

from src.repositories.regulation_repository import RegulationRepository
from src.models.db_models import Regulation, RegulationAuditTrail, RegulationDecisionReference


class TestRegulationRepository:
    """規程情報リポジトリのテストクラス"""

    @pytest.mark.asyncio
    async def test_create_regulation(self, test_db_session):
        """規程情報作成のテスト"""
        # テスト用のデータ準備
        repository = RegulationRepository(test_db_session)
        code = f"REG-{uuid4().hex[:8]}"
        title = "テスト規程"
        category = "出張規程"
        content = "これはテスト用の規程内容です。"
        structured_content = {"sections": [{"title": "第1条", "content": "目的"}]}
        version = "1.0"
        effective_date = datetime.now()
        keywords = ["テスト", "規程"]
        
        # 実行
        result = await repository.create_regulation(
            code=code,
            title=title,
            category=category,
            content=content,
            structured_content=structured_content,
            version=version,
            effective_date=effective_date,
            keywords=keywords
        )
        
        # 検証
        assert result is not None
        assert result.id is not None
        assert result.code == code
        assert result.title == title
        assert result.category == category
        assert result.content == content
        assert json.loads(result.structured_content) == structured_content
        assert result.version == version
        assert result.effective_date == effective_date
        assert json.loads(result.keywords) == keywords

    @pytest.mark.asyncio
    async def test_get_regulation_by_id(self, test_db_session):
        """IDによる規程情報取得のテスト"""
        # テスト用のデータ準備
        repository = RegulationRepository(test_db_session)
        code = f"REG-{uuid4().hex[:8]}"
        regulation = await repository.create_regulation(
            code=code,
            title="取得テスト規程",
            category="テスト用",
            content="取得テスト用の規程内容",
            version="1.0",
            effective_date=datetime.now()
        )
        
        # 実行
        result = await repository.get_regulation_by_id(regulation.id)
        
        # 検証
        assert result is not None
        assert result.id == regulation.id
        assert result.code == code
        assert result.title == "取得テスト規程"

    @pytest.mark.asyncio
    async def test_get_regulation_by_code(self, test_db_session):
        """コードによる規程情報取得のテスト"""
        # テスト用のデータ準備
        repository = RegulationRepository(test_db_session)
        code = f"REG-CODE-{uuid4().hex[:8]}"
        await repository.create_regulation(
            code=code,
            title="コード取得テスト規程",
            category="テスト用",
            content="コード取得テスト用の規程内容",
            version="1.0",
            effective_date=datetime.now()
        )
        
        # 実行
        result = await repository.get_regulation_by_code(code)
        
        # 検証
        assert result is not None
        assert result.code == code
        assert result.title == "コード取得テスト規程"

    @pytest.mark.asyncio
    async def test_update_regulation(self, test_db_session):
        """規程情報更新のテスト"""
        # テスト用のデータ準備
        repository = RegulationRepository(test_db_session)
        code = f"REG-UPDATE-{uuid4().hex[:8]}"
        regulation = await repository.create_regulation(
            code=code,
            title="更新前タイトル",
            category="テスト用",
            content="更新前の規程内容",
            version="1.0",
            effective_date=datetime.now()
        )
        
        # 更新データ
        new_title = "更新後タイトル"
        new_content = "更新後の規程内容"
        new_version = "1.1"
        new_structured_content = {"updated": True}
        
        # 実行
        result = await repository.update_regulation(
            regulation_id=regulation.id,
            title=new_title,
            content=new_content,
            version=new_version,
            structured_content=new_structured_content
        )
        
        # 検証
        assert result is not None
        assert result.id == regulation.id
        assert result.code == code  # 変更なし
        assert result.title == new_title
        assert result.content == new_content
        assert result.version == new_version
        assert json.loads(result.structured_content) == new_structured_content

    @pytest.mark.asyncio
    async def test_delete_regulation(self, test_db_session):
        """規程情報削除のテスト"""
        # テスト用のデータ準備
        repository = RegulationRepository(test_db_session)
        code = f"REG-DELETE-{uuid4().hex[:8]}"
        regulation = await repository.create_regulation(
            code=code,
            title="削除テスト規程",
            category="テスト用",
            content="削除テスト用の規程内容",
            version="1.0",
            effective_date=datetime.now()
        )
        
        # 実行
        result = await repository.delete_regulation(regulation.id)
        
        # 検証
        assert result is True
        
        # 削除後に取得を試みる
        deleted_check = await repository.get_regulation_by_id(regulation.id)
        assert deleted_check is None

    @pytest.mark.asyncio
    async def test_get_regulations(self, test_db_session):
        """規程情報検索のテスト"""
        # テスト用のデータ準備
        repository = RegulationRepository(test_db_session)
        
        # 複数の規程を作成
        test_prefix = f"SEARCH-{uuid4().hex[:6]}"
        
        await repository.create_regulation(
            code=f"{test_prefix}-A",
            title="検索A規程",
            category="出張規程",
            content="出張費の精算に関する規程",
            version="1.0",
            effective_date=datetime.now() - timedelta(days=30),
            keywords=["出張", "精算"]
        )
        
        await repository.create_regulation(
            code=f"{test_prefix}-B",
            title="検索B規程",
            category="購買規程",
            content="購買プロセスと承認ワークフローの規程",
            version="1.0",
            effective_date=datetime.now() - timedelta(days=15),
            keywords=["購買", "承認"]
        )
        
        # カテゴリによる検索
        results1 = await repository.get_regulations(category="出張規程")
        assert len(results1) >= 1
        assert any(r.code == f"{test_prefix}-A" for r in results1)
        
        # キーワードによる検索
        results2 = await repository.get_regulations(keywords=["購買"])
        assert len(results2) >= 1
        assert any(r.code == f"{test_prefix}-B" for r in results2)
        
        # 日付による検索
        results3 = await repository.get_regulations(effective_date=datetime.now())
        assert len(results3) >= 2
        assert any(r.code == f"{test_prefix}-A" for r in results3)
        assert any(r.code == f"{test_prefix}-B" for r in results3)

    @pytest.mark.asyncio
    async def test_create_audit_trail(self, test_db_session):
        """規程情報監査証跡作成のテスト"""
        # テスト用のデータ準備
        repository = RegulationRepository(test_db_session)
        code = f"REG-AUDIT-{uuid4().hex[:8]}"
        regulation = await repository.create_regulation(
            code=code,
            title="監査証跡テスト規程",
            category="テスト用",
            content="監査証跡テスト用の規程内容",
            version="1.0",
            effective_date=datetime.now()
        )
        
        # 監査証跡を作成
        details = {"action_details": "テスト操作", "data": {"test": True}}
        audit_trail = await repository.create_audit_trail(
            regulation_id=regulation.id,
            action_type="read",
            user_id="test_user",
            details=details
        )
        
        # 検証
        assert audit_trail is not None
        assert audit_trail.regulation_id == regulation.id
        assert audit_trail.action_type == "read"
        assert audit_trail.user_id == "test_user"
        assert json.loads(audit_trail.details) == details
        
        # 監査証跡の取得をテスト
        audit_trails = await repository.get_audit_trails(regulation_id=regulation.id)
        assert len(audit_trails) >= 1
        assert audit_trails[0].regulation_id == regulation.id

    @pytest.mark.asyncio
    async def test_create_decision_reference(self, test_db_session):
        """規程判断参照作成のテスト"""
        # テスト用のデータ準備
        repository = RegulationRepository(test_db_session)
        code = f"REG-DECISION-{uuid4().hex[:8]}"
        regulation = await repository.create_regulation(
            code=code,
            title="判断参照テスト規程",
            category="テスト用",
            content="判断参照テスト用の規程内容",
            version="1.0",
            effective_date=datetime.now()
        )
        
        # 判断参照を作成
        workflow_id = f"workflow-{uuid4().hex[:8]}"
        decision_point = "申請承認"
        decision = "承認"
        context = {"申請者": "テストユーザー", "申請内容": "出張費用"}
        
        decision_ref = await repository.create_decision_reference(
            regulation_id=regulation.id,
            workflow_id=workflow_id,
            decision_point=decision_point,
            decision=decision,
            user_id="test_user",
            reasoning="規程に準拠しているため承認",
            context=context
        )
        
        # 検証
        assert decision_ref is not None
        assert decision_ref.regulation_id == regulation.id
        assert decision_ref.workflow_id == workflow_id
        assert decision_ref.decision_point == decision_point
        assert decision_ref.decision == decision
        assert decision_ref.user_id == "test_user"
        assert decision_ref.reasoning == "規程に準拠しているため承認"
        assert json.loads(decision_ref.context) == context
        
        # ワークフローIDによる取得をテスト
        refs = await repository.get_decision_references_by_workflow(workflow_id)
        assert len(refs) >= 1
        assert refs[0].workflow_id == workflow_id
        
        # 検索条件による取得をテスト
        search_refs = await repository.get_decision_references(
            regulation_id=regulation.id,
            decision_point=decision_point
        )
        assert len(search_refs) >= 1
        assert search_refs[0].regulation_id == regulation.id
        assert search_refs[0].decision_point == decision_point

    @pytest.mark.asyncio
    async def test_get_decision_references_by_workflow(self, test_db_session):
        """ワークフローによる判断参照取得のテスト"""
        # テスト用のデータ準備
        repository = RegulationRepository(test_db_session)
        workflow_id = f"test_workflow_{uuid4().hex[:8]}"
        
        # 規程を作成
        regulation = await repository.create_regulation(
            code=f"REG-WORKFLOW-{uuid4().hex[:8]}",
            title="ワークフロー参照テスト規程",
            category="テスト用",
            content="ワークフロー参照テスト用の規程内容",
            version="1.0",
            effective_date=datetime.now()
        )
        
        # 複数の判断参照を作成
        await repository.create_decision_reference(
            regulation_id=regulation.id,
            workflow_id=workflow_id,
            decision_point="申請確認",
            decision="確認済み",
            user_id="user_1",
            reasoning="内容を確認",
            context={"step": "確認"}
        )
        
        await repository.create_decision_reference(
            regulation_id=regulation.id,
            workflow_id=workflow_id,
            decision_point="最終承認",
            decision="承認",
            user_id="user_2",
            reasoning="問題なし",
            context={"step": "承認"}
        )
        
        # 別ワークフローの参照も作成
        await repository.create_decision_reference(
            regulation_id=regulation.id,
            workflow_id="another_workflow",
            decision_point="別ワークフロー",
            decision="別決定",
            user_id="user_3",
            context={"test": "another"}
        )
        
        # 実行
        results = await repository.get_decision_references_by_workflow(workflow_id)
        
        # 検証
        assert results is not None
        assert len(results) == 2
        assert all(r.workflow_id == workflow_id for r in results)
        
        # 決定ポイントの検証
        decision_points = [r.decision_point for r in results]
        assert "申請確認" in decision_points
        assert "最終承認" in decision_points 