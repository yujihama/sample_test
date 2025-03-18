"""
規程情報リポジトリ

このモジュールでは、規程情報へのデータアクセスを提供するリポジトリクラスを定義します。
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func, desc
from sqlalchemy.orm import joinedload, Session

from src.models.db_models import Regulation, RegulationAuditTrail, RegulationDecisionReference
from src.utils.logger import setup_logger
from src.utils.regulation_utils import serialize_json, deserialize_json

logger = setup_logger(__name__)


class RegulationRepository:
    """規程情報リポジトリクラス"""

    def __init__(self, db_session):
        """
        コンストラクタ
        
        Args:
            db_session: SQLAlchemyデータベースセッション（AsyncSessionまたはSession）
        """
        self.db_session = db_session
        # 同期セッションと非同期セッションを判定
        self.is_async = isinstance(db_session, AsyncSession)

    async def create_regulation(self, 
                              code: str,
                              title: str,
                              category: str,
                              content: str,
                              version: str,
                              effective_date: datetime,
                              structured_content: Optional[Dict[str, Any]] = None,
                              expiration_date: Optional[datetime] = None,
                              parent_id: Optional[str] = None,
                              keywords: Optional[List[str]] = None,
                              metadata: Optional[Dict[str, Any]] = None) -> Regulation:
        """
        規程情報を作成する
        
        Args:
            code (str): 規程コード
            title (str): 規程タイトル
            category (str): カテゴリー
            content (str): 規程本文
            version (str): バージョン
            effective_date (datetime): 発効日
            structured_content (Optional[Dict[str, Any]], optional): 構造化規程内容
            expiration_date (Optional[datetime], optional): 失効日
            parent_id (Optional[str], optional): 親規程ID
            keywords (Optional[List[str]], optional): キーワード
            metadata (Optional[Dict[str, Any]], optional): メタデータ
            
        Returns:
            Regulation: 作成された規程情報
        """
        try:
            # JSONフィールドの処理（共通ユーティリティを使用）
            structured_content_str = serialize_json(structured_content)
            keywords_str = serialize_json(keywords)
            metadata_str = serialize_json(metadata)
            
            # 規程情報の作成
            regulation = Regulation(
                code=code,
                title=title,
                category=category,
                content=content,
                structured_content=structured_content_str,
                version=version,
                effective_date=effective_date,
                expiration_date=expiration_date,
                parent_id=parent_id,
                keywords=keywords_str,
                metadata=metadata_str
            )
            
            self.db_session.add(regulation)
            
            if self.is_async:
                await self.db_session.flush()
                await self.db_session.commit()
            else:
                self.db_session.flush()
                self.db_session.commit()
            
            return regulation
        
        except Exception as e:
            if self.is_async:
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            logger.error(f"規程情報の作成に失敗しました: {str(e)}")
            raise

    async def get_regulation_by_id(self, regulation_id: str) -> Optional[Regulation]:
        """
        IDによる規程情報の取得
        
        Args:
            regulation_id (str): 規程情報ID
            
        Returns:
            Optional[Regulation]: 規程情報（存在しない場合はNone）
        """
        try:
            query = select(Regulation).where(Regulation.id == regulation_id)
            
            if self.is_async:
                result = await self.db_session.execute(query)
                regulation = result.scalars().first()
            else:
                result = self.db_session.execute(query)
                regulation = result.scalars().first()
            
            return regulation
            
        except Exception as e:
            logger.error(f"規程情報の取得に失敗しました: {str(e)}")
            raise

    async def get_regulation_by_code(self, code: str) -> Optional[Regulation]:
        """
        コードによる規程情報の取得
        
        Args:
            code (str): 規程コード
            
        Returns:
            Optional[Regulation]: 規程情報（存在しない場合はNone）
        """
        try:
            query = select(Regulation).where(Regulation.code == code)
            
            if self.is_async:
                result = await self.db_session.execute(query)
                regulation = result.scalars().first()
            else:
                result = self.db_session.execute(query)
                regulation = result.scalars().first()
            
            return regulation
            
        except Exception as e:
            logger.error(f"コードによる規程情報の取得に失敗しました: {str(e)}")
            raise

    async def update_regulation(self, regulation_id: str, update_dict: Dict[str, Any]) -> Optional[Regulation]:
        """
        規程情報を更新する
        
        Args:
            regulation_id (str): 規程情報ID
            update_dict (Dict[str, Any]): 更新データの辞書
            
        Returns:
            Optional[Regulation]: 更新された規程情報（存在しない場合はNone）
        """
        try:
            # 更新対象の規程情報の存在確認
            regulation = await self.get_regulation_by_id(regulation_id)
            if not regulation:
                logger.warning(f"更新対象の規程情報が存在しません: {regulation_id}")
                return None
            
            # JSONフィールドの特別処理
            json_fields = {
                "structured_content": "structured_content",
                "keywords": "keywords",
                "metadata": "metadata"
            }
            
            db_update_data = {}
            
            # 通常のフィールドとJSONフィールドを分けて処理
            for key, value in update_dict.items():
                if key in json_fields:
                    # JSONフィールドの処理
                    db_key = json_fields[key]
                    db_update_data[db_key] = serialize_json(value)
                else:
                    # 通常フィールドの処理
                    db_update_data[key] = value
            
            if not db_update_data:
                logger.info(f"更新項目がありません: {regulation_id}")
                return regulation
            
            # 更新の実行
            query = update(Regulation).where(Regulation.id == regulation_id).values(**db_update_data)
            
            if self.is_async:
                await self.db_session.execute(query)
                await self.db_session.commit()
            else:
                self.db_session.execute(query)
                self.db_session.commit()
            
            # 更新後の規程情報を取得して返す
            return await self.get_regulation_by_id(regulation_id)
            
        except Exception as e:
            if self.is_async:
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            logger.error(f"規程情報の更新に失敗しました: {str(e)}")
            raise

    async def delete_regulation(self, regulation_id: str) -> bool:
        """
        規程情報の削除
        
        Args:
            regulation_id (str): 規程情報ID
            
        Returns:
            bool: 削除成功時はTrue、対象が存在しない場合はFalse
        """
        try:
            # 削除対象の規程情報の存在確認
            regulation = await self.get_regulation_by_id(regulation_id)
            if not regulation:
                logger.warning(f"削除対象の規程情報が存在しません: {regulation_id}")
                return False
            
            # 削除の実行
            query = delete(Regulation).where(Regulation.id == regulation_id)
            
            if self.is_async:
                await self.db_session.execute(query)
                await self.db_session.commit()
            else:
                self.db_session.execute(query)
                self.db_session.commit()
            
            return True
            
        except Exception as e:
            if self.is_async:
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            logger.error(f"規程情報の削除に失敗しました: {str(e)}")
            raise

    async def _delete_related_records(self, regulation_id: str) -> None:
        """
        規程情報に関連するレコード（監査証跡、判断参照）を削除する内部メソッド
        
        Args:
            regulation_id (str): 規程情報ID
        """
        try:
            # 監査証跡の削除
            audit_query = delete(RegulationAuditTrail).where(
                RegulationAuditTrail.regulation_id == regulation_id
            )
            
            # 判断参照の削除
            ref_query = delete(RegulationDecisionReference).where(
                RegulationDecisionReference.regulation_id == regulation_id
            )
            
            if self.is_async:
                await self.db_session.execute(audit_query)
                await self.db_session.execute(ref_query)
            else:
                self.db_session.execute(audit_query)
                self.db_session.execute(ref_query)
            
        except Exception as e:
            logger.error(f"規程情報関連レコードの削除に失敗しました: {str(e)}")
            raise

    async def search_regulations(self, 
                              query: Optional[str] = None,
                              category: Optional[str] = None,
                              keywords: Optional[List[str]] = None,
                              effective_date: Optional[datetime] = None) -> List[Regulation]:
        """
        規程情報を検索する
        
        Args:
            query (Optional[str], optional): 検索クエリ
            category (Optional[str], optional): カテゴリーフィルタ
            keywords (Optional[List[str]], optional): キーワードフィルタ
            effective_date (Optional[datetime], optional): 有効な規程を指定日で絞り込み
            
        Returns:
            List[Regulation]: 検索結果の規程情報リスト
        """
        try:
            # 基本クエリ
            base_query = select(Regulation)
            
            # 条件の追加
            conditions = []
            
            if query:
                # タイトルと内容で検索
                conditions.append(
                    or_(
                        Regulation.title.ilike(f"%{query}%"),
                        Regulation.content.ilike(f"%{query}%"),
                        Regulation.code.ilike(f"%{query}%")
                    )
                )
            
            if category:
                conditions.append(Regulation.category == category)
            
            if effective_date:
                conditions.append(
                    and_(
                        Regulation.effective_date <= effective_date,
                        or_(
                            Regulation.expiration_date.is_(None),
                            Regulation.expiration_date >= effective_date
                        )
                    )
                )
                
            if keywords:
                # キーワード検索（JSONフィールドの部分一致）
                keyword_conditions = []
                for keyword in keywords:
                    keyword_conditions.append(Regulation.keywords.ilike(f"%{keyword}%"))
                
                if keyword_conditions:
                    conditions.append(or_(*keyword_conditions))
            
            # 条件の適用
            if conditions:
                base_query = base_query.where(and_(*conditions))
            
            # 実行
            result = await self.db_session.execute(base_query)
            return result.scalars().all()
        
        except Exception as e:
            logger.error(f"規程情報の検索に失敗しました: {str(e)}")
            raise

    async def create_audit_trail(self, 
                               regulation_id: str, 
                               action_type: str,
                               user_id: str,
                               details: Optional[Dict[str, Any]] = None) -> RegulationAuditTrail:
        """
        監査証跡を作成する
        
        Args:
            regulation_id (str): 規程情報ID
            action_type (str): アクションタイプ（create, read, update, delete等）
            user_id (str): ユーザーID
            details (Optional[Dict[str, Any]], optional): 詳細情報（JSON形式）
            
        Returns:
            RegulationAuditTrail: 作成された監査証跡
        """
        try:
            # 詳細情報のシリアライズ
            details_str = serialize_json(details)
            
            # 監査証跡の作成
            audit_trail = RegulationAuditTrail(
                regulation_id=regulation_id,
                action_type=action_type,
                user_id=user_id,
                timestamp=datetime.now(),
                details=details_str
            )
            
            self.db_session.add(audit_trail)
            
            if self.is_async:
                await self.db_session.flush()
                await self.db_session.commit()
            else:
                self.db_session.flush()
                self.db_session.commit()
            
            return audit_trail
            
        except Exception as e:
            if self.is_async:
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            logger.error(f"監査証跡の作成に失敗しました: {str(e)}")
            raise

    async def get_audit_trails(self, 
                            regulation_id: Optional[str] = None,
                            action_type: Optional[str] = None,
                            user_id: Optional[str] = None,
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None,
                            limit: int = 100,
                            offset: int = 0) -> List[RegulationAuditTrail]:
        """
        監査証跡の検索
        
        Args:
            regulation_id (Optional[str], optional): 規程情報IDによるフィルタ
            action_type (Optional[str], optional): アクションタイプによるフィルタ
            user_id (Optional[str], optional): ユーザーIDによるフィルタ
            start_date (Optional[datetime], optional): 開始日時によるフィルタ
            end_date (Optional[datetime], optional): 終了日時によるフィルタ
            limit (int, optional): 取得件数. デフォルト 100.
            offset (int, optional): オフセット. デフォルト 0.
            
        Returns:
            List[RegulationAuditTrail]: 監査証跡リスト
        """
        try:
            query = select(RegulationAuditTrail)
            
            # フィルタ条件の適用
            if regulation_id:
                query = query.where(RegulationAuditTrail.regulation_id == regulation_id)
            if action_type:
                query = query.where(RegulationAuditTrail.action_type == action_type)
            if user_id:
                query = query.where(RegulationAuditTrail.user_id == user_id)
            if start_date:
                query = query.where(RegulationAuditTrail.timestamp >= start_date)
            if end_date:
                query = query.where(RegulationAuditTrail.timestamp <= end_date)
            
            # ページネーション
            query = query.order_by(desc(RegulationAuditTrail.timestamp))
            query = query.limit(limit).offset(offset)
            
            if self.is_async:
                result = await self.db_session.execute(query)
                audit_trails = result.scalars().all()
            else:
                result = self.db_session.execute(query)
                audit_trails = result.scalars().all()
            
            return audit_trails
            
        except Exception as e:
            logger.error(f"監査証跡の検索に失敗しました: {str(e)}")
            raise

    async def create_decision_reference(self,
                                     regulation_id: str,
                                     workflow_id: str,
                                     decision_point: str,
                                     decision: str,
                                     user_id: str,
                                     reasoning: Optional[str] = None,
                                     context: Optional[Dict[str, Any]] = None) -> RegulationDecisionReference:
        """
        決定参照を作成する
        
        Args:
            regulation_id (str): 規程情報ID
            workflow_id (str): ワークフローID
            decision_point (str): 決定ポイント
            decision (str): 決定内容
            user_id (str): ユーザーID
            reasoning (Optional[str], optional): 決定理由
            context (Optional[Dict[str, Any]], optional): コンテキスト情報
            
        Returns:
            RegulationDecisionReference: 作成された決定参照
        """
        try:
            # コンテキスト情報のシリアライズ
            context_str = serialize_json(context)
            
            # 決定参照の作成
            decision_reference = RegulationDecisionReference(
                regulation_id=regulation_id,
                workflow_id=workflow_id,
                decision_point=decision_point,
                decision=decision,
                user_id=user_id,
                reasoning=reasoning,
                timestamp=datetime.now(),
                context=context_str
            )
            
            self.db_session.add(decision_reference)
            
            if self.is_async:
                await self.db_session.flush()
                await self.db_session.commit()
            else:
                self.db_session.flush()
                self.db_session.commit()
            
            return decision_reference
            
        except Exception as e:
            if self.is_async:
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
            logger.error(f"決定参照の作成に失敗しました: {str(e)}")
            raise

    async def get_decision_references(self,
                                   regulation_id: Optional[str] = None,
                                   workflow_id: Optional[str] = None,
                                   decision_point: Optional[str] = None,
                                   user_id: Optional[str] = None,
                                   start_date: Optional[datetime] = None,
                                   end_date: Optional[datetime] = None,
                                   limit: int = 100,
                                   offset: int = 0) -> List[RegulationDecisionReference]:
        """
        判断参照の検索
        
        Args:
            regulation_id (Optional[str], optional): 規程情報IDによるフィルタ
            workflow_id (Optional[str], optional): ワークフローIDによるフィルタ
            decision_point (Optional[str], optional): 判断ポイントによるフィルタ
            user_id (Optional[str], optional): ユーザーIDによるフィルタ
            start_date (Optional[datetime], optional): 開始日時によるフィルタ
            end_date (Optional[datetime], optional): 終了日時によるフィルタ
            limit (int, optional): 取得件数. デフォルト 100.
            offset (int, optional): オフセット. デフォルト 0.
            
        Returns:
            List[RegulationDecisionReference]: 判断参照リスト
        """
        try:
            query = select(RegulationDecisionReference)
            
            # フィルタ条件の適用
            if regulation_id:
                query = query.where(RegulationDecisionReference.regulation_id == regulation_id)
            if workflow_id:
                query = query.where(RegulationDecisionReference.workflow_id == workflow_id)
            if decision_point:
                query = query.where(RegulationDecisionReference.decision_point == decision_point)
            if user_id:
                query = query.where(RegulationDecisionReference.user_id == user_id)
            if start_date:
                query = query.where(RegulationDecisionReference.timestamp >= start_date)
            if end_date:
                query = query.where(RegulationDecisionReference.timestamp <= end_date)
            
            # ページネーション
            query = query.order_by(desc(RegulationDecisionReference.timestamp))
            query = query.limit(limit).offset(offset)
            
            if self.is_async:
                result = await self.db_session.execute(query)
                decision_refs = result.scalars().all()
            else:
                result = self.db_session.execute(query)
                decision_refs = result.scalars().all()
            
            return decision_refs
            
        except Exception as e:
            logger.error(f"判断参照の検索に失敗しました: {str(e)}")
            raise

    async def get_decision_references_by_workflow(self, workflow_id: str) -> List[RegulationDecisionReference]:
        """
        ワークフローIDによる判断参照の取得
        
        Args:
            workflow_id (str): ワークフローID
            
        Returns:
            List[RegulationDecisionReference]: 判断参照リスト
        """
        try:
            return await self.get_decision_references(workflow_id=workflow_id)
            
        except Exception as e:
            logger.error(f"ワークフローIDによる判断参照の取得に失敗しました: {str(e)}")
            raise

    async def get_regulations(self, 
                            category: Optional[str] = None,
                            keywords: Optional[List[str]] = None,
                            effective_date: Optional[datetime] = None,
                            limit: int = 100,
                            offset: int = 0) -> List[Regulation]:
        """
        規程情報の検索
        
        Args:
            category (Optional[str], optional): カテゴリによるフィルタ
            keywords (Optional[List[str]], optional): キーワードによるフィルタ
            effective_date (Optional[datetime], optional): 有効日によるフィルタ
            limit (int, optional): 取得件数. デフォルト 100.
            offset (int, optional): オフセット. デフォルト 0.
            
        Returns:
            List[Regulation]: 規程情報リスト
        """
        try:
            query = select(Regulation)
            
            # フィルタ条件の適用
            if category:
                query = query.where(Regulation.category == category)
            
            if effective_date:
                query = query.where(
                    (Regulation.effective_date <= effective_date) & 
                    (or_(
                        Regulation.expiration_date.is_(None),
                        Regulation.expiration_date >= effective_date
                    ))
                )
            
            # ページネーション
            query = query.order_by(desc(Regulation.effective_date))
            query = query.limit(limit).offset(offset)
            
            if self.is_async:
                result = await self.db_session.execute(query)
                regulations = result.scalars().all()
            else:
                result = self.db_session.execute(query)
                regulations = result.scalars().all()
            
            # キーワードフィルタリング（データベースでJSONフィルタリングが難しい場合、メモリ上で実行）
            if keywords:
                filtered_regulations = []
                for regulation in regulations:
                    reg_keywords = json.loads(regulation.keywords) if regulation.keywords else []
                    if any(kw in reg_keywords for kw in keywords):
                        filtered_regulations.append(regulation)
                return filtered_regulations
            
            return regulations
            
        except Exception as e:
            logger.error(f"規程情報の検索に失敗しました: {str(e)}")
            raise 