"""
規程情報管理サービス

このモジュールでは、規程情報の管理機能を提供するサービスクラスを定義します。
規程情報の検索、参照、適用判断のトレースなど、LangGraphノードから利用される機能を提供します。
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.regulation_repository import RegulationRepository
from src.models.schema import (
    RegulationBase, RegulationCreate, RegulationUpdate, RegulationResponse,
    RegulationSearchQuery, RegulationSearchResponse, RegulationDecisionReferenceCreate
)
from src.utils.logger import get_logger
from src.utils.regulation_utils import (
    convert_db_to_response, validate_regulation_data, extract_text_matches,
    DataValidator, ModelConverter, REGULATION_SCHEMAS
)
from src.utils.audit_decorators import audit_trail

logger = get_logger(__name__)


class RegulationService:
    """規程情報管理サービスクラス"""

    def __init__(self, db_session: AsyncSession):
        """
        コンストラクタ
        
        Args:
            db_session (AsyncSession): SQLAlchemyデータベースセッション
        """
        self.db_session = db_session
        self.repository = RegulationRepository(db_session)

    @audit_trail(action="create", details_param="regulation_data")
    async def create_regulation(self, regulation_data: RegulationCreate, actor: str) -> RegulationResponse:
        """
        規程情報を作成する
        
        Args:
            regulation_data (RegulationCreate): 規程情報作成データ
            actor (str): 作成者
            
        Returns:
            RegulationResponse: 作成された規程情報
        """
        try:
            # データの検証
            errors = validate_regulation_data(regulation_data)
            
            # JSONスキーマの検証（メタデータと構造化コンテンツ）
            if regulation_data.meta_data:
                metadata_errors = DataValidator.validate_json_schema(
                    regulation_data.meta_data, 
                    REGULATION_SCHEMAS["metadata"]
                )
                errors.extend(metadata_errors)
            
            if regulation_data.structured_content:
                content_errors = DataValidator.validate_json_schema(
                    regulation_data.structured_content,
                    REGULATION_SCHEMAS["structured_content"]
                )
                errors.extend(content_errors)
            
            if errors:
                error_msg = ", ".join(errors)
                logger.error(f"規程情報の検証に失敗しました: {error_msg}")
                raise ValueError(f"規程情報の検証に失敗しました: {error_msg}")
            
            # リポジトリを使用して規程情報を作成
            regulation = await self.repository.create_regulation(
                code=regulation_data.code,
                title=regulation_data.title,
                category=regulation_data.category,
                content=regulation_data.content,
                structured_content=regulation_data.structured_content,
                version=regulation_data.version,
                effective_date=regulation_data.effective_date,
                expiration_date=regulation_data.expiration_date,
                parent_id=regulation_data.parent_id,
                keywords=regulation_data.keywords,
                meta_data=regulation_data.meta_data
            )
            
            # レスポンスを作成して返す
            return ModelConverter.db_to_response(regulation, RegulationResponse)
        
        except Exception as e:
            logger.error(f"規程情報の作成に失敗しました: {str(e)}")
            raise

    @audit_trail(action="read")
    async def get_regulation(self, regulation_id: str, actor: str) -> Optional[RegulationResponse]:
        """
        規程情報を取得する
        
        Args:
            regulation_id (str): 規程ID
            actor (str): 参照者
            
        Returns:
            Optional[RegulationResponse]: 規程情報（存在しない場合はNone）
        """
        try:
            # リポジトリを使用して規程情報を取得
            regulation = await self.repository.get_regulation_by_id(regulation_id)
            
            if regulation:
                # レスポンスを作成して返す
                return ModelConverter.db_to_response(regulation, RegulationResponse)
            
            return None
        
        except Exception as e:
            logger.error(f"規程情報の取得に失敗しました (ID: {regulation_id}): {str(e)}")
            raise

    @audit_trail(action="read", entity_id_param="code")
    async def get_regulation_by_code(self, code: str, actor: str) -> Optional[RegulationResponse]:
        """
        コードで規程情報を取得する
        
        Args:
            code (str): 規程コード
            actor (str): 参照者
            
        Returns:
            Optional[RegulationResponse]: 規程情報（存在しない場合はNone）
        """
        try:
            # リポジトリを使用して規程情報を取得
            regulation = await self.repository.get_regulation_by_code(code)
            
            if regulation:
                # レスポンスを作成して返す
                return ModelConverter.db_to_response(regulation, RegulationResponse)
            
            return None
        
        except Exception as e:
            logger.error(f"規程情報の取得に失敗しました (コード: {code}): {str(e)}")
            raise

    @audit_trail(action="update", details_param="update_data")
    async def update_regulation(self, regulation_id: str, update_data: RegulationUpdate, actor: str) -> Optional[RegulationResponse]:
        """
        規程情報を更新する
        
        Args:
            regulation_id (str): 規程ID
            update_data (RegulationUpdate): 更新データ
            actor (str): 更新者
            
        Returns:
            Optional[RegulationResponse]: 更新された規程情報（存在しない場合はNone）
        """
        try:
            # 既存の規程情報を取得して存在確認
            existing_regulation = await self.repository.get_regulation_by_id(regulation_id)
            if not existing_regulation:
                logger.warning(f"更新対象の規程情報が見つかりません (ID: {regulation_id})")
                return None
            
            # 更新データの検証
            errors = validate_regulation_data(update_data)
            
            # JSONスキーマの検証（更新対象フィールドのみ）
            if update_data.meta_data:
                metadata_errors = DataValidator.validate_json_schema(
                    update_data.meta_data, 
                    REGULATION_SCHEMAS["metadata"]
                )
                errors.extend(metadata_errors)
            
            if update_data.structured_content:
                content_errors = DataValidator.validate_json_schema(
                    update_data.structured_content,
                    REGULATION_SCHEMAS["structured_content"]
                )
                errors.extend(content_errors)
            
            if errors:
                error_msg = ", ".join(errors)
                logger.error(f"規程情報の検証に失敗しました: {error_msg}")
                raise ValueError(f"規程情報の検証に失敗しました: {error_msg}")
            
            # 更新データを辞書に変換し、Noneでない値のみ抽出
            update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
            
            if not update_dict:
                logger.info(f"更新するデータがありません (ID: {regulation_id})")
                return ModelConverter.db_to_response(existing_regulation, RegulationResponse)
            
            # リポジトリを使用して規程情報を更新
            updated_regulation = await self.repository.update_regulation(regulation_id, update_dict)
            
            if updated_regulation:
                # レスポンスを作成して返す
                return ModelConverter.db_to_response(updated_regulation, RegulationResponse)
            
            return None
        
        except Exception as e:
            logger.error(f"規程情報の更新に失敗しました (ID: {regulation_id}): {str(e)}")
            raise

    @audit_trail(action="delete")
    async def delete_regulation(self, regulation_id: str, actor: str) -> bool:
        """
        規程情報を削除する
        
        Args:
            regulation_id (str): 規程ID
            actor (str): 削除者
            
        Returns:
            bool: 削除成功時はTrue、存在しない場合はFalse
        """
        try:
            # 既存の規程情報を取得して存在確認
            existing_regulation = await self.repository.get_regulation_by_id(regulation_id)
            if not existing_regulation:
                logger.warning(f"削除対象の規程情報が見つかりません (ID: {regulation_id})")
                return False
            
            # リポジトリを使用して規程情報を削除
            result = await self.repository.delete_regulation(regulation_id)
            
            return result
        
        except Exception as e:
            logger.error(f"規程情報の削除に失敗しました (ID: {regulation_id}): {str(e)}")
            raise

    async def search_regulations(
        self, 
        search_query: RegulationSearchQuery, 
        actor: str,
        workflow_id: Optional[str] = None
    ) -> RegulationSearchResponse:
        """
        規程情報を検索する
        
        Args:
            search_query (RegulationSearchQuery): 検索クエリ
            actor (str): 検索者
            workflow_id (Optional[str], optional): ワークフローID
            
        Returns:
            RegulationSearchResponse: 検索結果
        """
        try:
            # リポジトリを使用して規程情報を検索
            regulations = await self.repository.search_regulations(
                query=search_query.query,
                category=search_query.category,
                keywords=search_query.keywords,
                effective_date=search_query.effective_date
            )
            
            # 検索結果を処理
            result_items = []
            for regulation in regulations:
                # 応答モデルに変換
                response_item = ModelConverter.db_to_response(regulation, RegulationResponse)
                
                # 検索クエリがある場合は一致部分を抽出
                matches = []
                if search_query.query:
                    matches = extract_text_matches(search_query.query, regulation.content)
                
                # 結果アイテムを作成
                result_items.append({
                    "regulation": response_item,
                    "matches": matches
                })
                
                # ワークフローIDが指定されていれば監査証跡を記録
                if workflow_id:
                    try:
                        await self.repository.create_audit_trail(
                            regulation_id=regulation.id,
                            action_type="search",
                            user_id=actor,
                            details={
                                "search_query": search_query.dict(),
                                "workflow_id": workflow_id
                            }
                        )
                    except Exception as audit_error:
                        logger.warning(f"検索の監査証跡の記録に失敗しました: {str(audit_error)}")
            
            # 検索レスポンスを作成
            return RegulationSearchResponse(
                query=search_query.query,
                count=len(result_items),
                results=result_items
            )
            
        except Exception as e:
            logger.error(f"規程情報の検索に失敗しました: {str(e)}")
            raise

    @audit_trail(action="reference", details_param="reference_data")
    async def create_decision_reference(
        self, 
        reference_data: RegulationDecisionReferenceCreate, 
        actor: str
    ) -> Dict[str, Any]:
        """
        規程に基づく決定参照を作成する
        
        Args:
            reference_data (RegulationDecisionReferenceCreate): 参照データ
            actor (str): 作成者
            
        Returns:
            Dict[str, Any]: 作成された決定参照
        """
        try:
            # 規程情報の存在確認
            regulation = await self.repository.get_regulation_by_id(reference_data.regulation_id)
            if not regulation:
                raise ValueError(f"参照対象の規程情報が見つかりません (ID: {reference_data.regulation_id})")
            
            # 決定参照の作成
            decision_ref = await self.repository.create_decision_reference(
                regulation_id=reference_data.regulation_id,
                workflow_id=reference_data.workflow_id,
                decision_point=reference_data.decision_point,
                decision=reference_data.decision,
                user_id=actor,
                reasoning=reference_data.reasoning,
                context=reference_data.context
            )
            
            # 応答データの準備
            result = {
                "id": decision_ref.id,
                "regulation_id": decision_ref.regulation_id,
                "workflow_id": decision_ref.workflow_id,
                "decision_point": decision_ref.decision_point,
                "decision": decision_ref.decision,
                "user_id": decision_ref.user_id,
                "reasoning": decision_ref.reasoning,
                "timestamp": decision_ref.timestamp.isoformat(),
                "context": decision_ref.context
            }
            
            return result
            
        except Exception as e:
            logger.error(f"決定参照の作成に失敗しました: {str(e)}")
            raise

    async def get_workflow_decision_references(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        ワークフローに関連する決定参照を取得する
        
        Args:
            workflow_id (str): ワークフローID
            
        Returns:
            List[Dict[str, Any]]: 決定参照のリスト
        """
        try:
            # リポジトリを使用して決定参照を取得
            references = await self.repository.get_decision_references_by_workflow(workflow_id)
            
            # 応答データに変換
            result = []
            for ref in references:
                result.append({
                    "id": ref.id,
                    "regulation_id": ref.regulation_id,
                    "workflow_id": ref.workflow_id,
                    "decision_point": ref.decision_point,
                    "decision": ref.decision,
                    "user_id": ref.user_id,
                    "reasoning": ref.reasoning,
                    "timestamp": ref.timestamp.isoformat(),
                    "context": ref.context
                })
            
            return result
            
        except Exception as e:
            logger.error(f"ワークフローの決定参照取得に失敗しました (ID: {workflow_id}): {str(e)}")
            raise 