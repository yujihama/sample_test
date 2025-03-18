"""
監査手続きリポジトリ

AuditProcedureモデルに対するデータアクセス操作を提供します。
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import or_

from src.models.db_models import AuditProcedure
from src.repositories.base_repository import SQLAlchemyRepository
from src.utils.db_manager import get_db_session


class AuditProcedureRepository(SQLAlchemyRepository):
    """
    監査手続きリポジトリクラス
    
    AuditProcedureモデルに対する基本的なCRUD操作と、
    監査手続き固有の検索・操作機能を提供します。
    """
    
    def __init__(self):
        """コンストラクタ"""
        db_session = get_db_session()
        super().__init__(db_session, AuditProcedure)
    
    def search_by_keyword(self, keyword: str) -> List[AuditProcedure]:
        """
        キーワードによる監査手続きの検索
        
        タイトルまたは説明にキーワードを含む監査手続きを検索します。
        
        Args:
            keyword: 検索キーワード
            
        Returns:
            List[AuditProcedure]: 検索結果のリスト
        """
        search_term = f"%{keyword}%"
        with self.session_scope() as session:
            return session.query(AuditProcedure).filter(
                or_(
                    AuditProcedure.title.ilike(search_term),
                    AuditProcedure.description.ilike(search_term)
                )
            ).all()
    
    def get_by_risk_area(self, risk_area: str) -> List[AuditProcedure]:
        """
        リスク領域による監査手続きの検索
        
        特定のリスク領域に関連する監査手続きを検索します。
        
        Args:
            risk_area: リスク領域
            
        Returns:
            List[AuditProcedure]: 検索結果のリスト
        """
        search_term = f"%\"{risk_area}\"%"  # JSON配列内の文字列を検索
        with self.session_scope() as session:
            return session.query(AuditProcedure).filter(
                AuditProcedure.risk_areas.ilike(search_term)
            ).all()
    
    def create_procedure(self, procedure_data: Dict[str, Any]) -> AuditProcedure:
        """
        監査手続きの作成
        
        Args:
            procedure_data: 監査手続きデータ
            
        Returns:
            AuditProcedure: 作成された監査手続き
        """
        return self.create(procedure_data)
    
    def update_procedure(self, procedure_id: str, procedure_data: Dict[str, Any]) -> Optional[AuditProcedure]:
        """
        監査手続きの更新
        
        Args:
            procedure_id: 更新する監査手続きのID
            procedure_data: 更新データ
            
        Returns:
            Optional[AuditProcedure]: 更新された監査手続き（存在しない場合はNone）
        """
        return self.update(procedure_id, procedure_data)
    
    def delete_procedure(self, procedure_id: str) -> bool:
        """
        監査手続きの削除
        
        Args:
            procedure_id: 削除する監査手続きのID
            
        Returns:
            bool: 削除が成功したかどうか
        """
        return self.delete(procedure_id)


# シングルトンインスタンス
audit_procedure_repository = AuditProcedureRepository() 