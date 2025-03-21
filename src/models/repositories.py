"""
リポジトリパターンに基づくデータアクセスレイヤー
SQLAlchemyを使用してデータベースとの対話を抽象化し、ビジネスロジックから分離します
"""

from typing import Generic, TypeVar, Type, List, Optional, Dict, Any, Union, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from loguru import logger
import uuid
import json
from src.utils import json_utils
from datetime import datetime, date, time, UTC
import logging

from src.models.db_models import AuditProcedure, SampleData, Workflow, AgentState, AuditResult, Finding, Message, AuditTrail, MessageLog, AgentDecision, HumanInterventionRequest, HumanInterventionResponse, GraphStateHistory, CheckpointRecord

# 型変数の定義（T = モデルクラス）
T = TypeVar('T')


# JSONシリアライズ用ヘルパー関数
def _serialize_json_safe(obj):
    """JSONシリアライズ可能な形式にオブジェクトを変換する"""
    if isinstance(obj, dict):
        return {k: _serialize_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_json_safe(item) for item in obj]
    elif isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    elif isinstance(obj, set):
        return list(obj)
    else:
        # その他の型はそのまま返す
        return obj

class BaseRepository(Generic[T]):
    """
    基本リポジトリクラス - 汎用的なCRUD操作を提供
    ジェネリック型を使用して任意のモデルクラスで動作する
    """
    
    def __init__(self, db: Session, model: Type[T]):
        """
        ベースリポジトリの初期化
        
        Args:
            db: データベースセッション
            model: モデルクラス
        """
        self.db = db
        self.model = model
    
    def create(self, obj_in: Dict[str, Any]) -> T:
        """
        レコード作成
        
        Args:
            obj_in: 作成するオブジェクトのデータ
            
        Returns:
            T: 作成されたレコード
        """
        try:
            # データの前処理
            db_data = self._prepare_data_for_db(obj_in)
            
            # モデルインスタンスの作成
            db_obj = self.model(**db_data)
            
            # セッションに追加
            self.db.add(db_obj)
            self.db.commit()
            
            # 作成されたオブジェクトを返す
            return db_obj
        except Exception as e:
            self.db.rollback()
            logger.error(f"レコード作成エラー: {e}")
            raise
    
    def get(self, db: Session, id: str) -> Optional[T]:
        """
        IDによるレコードの取得
        
        Args:
            db: データベースセッション
            id: 取得するレコードのID
            
        Returns:
            取得したオブジェクト、存在しない場合はNone
            
        Raises:
            OperationalError: データベース接続エラーなどの操作的な問題が発生した場合
            SQLAlchemyError: その他のSQLAlchemy関連エラーが発生した場合
        """
        try:
            result = db.query(self.model).filter(self.model.id == id).first()
            if result:
                logger.debug(f"{self.model.__name__}を取得しました: id={id}")
            else:
                logger.debug(f"{self.model.__name__}が見つかりません: id={id}")
            return result
            
        except OperationalError as e:
            error_msg = str(e).lower()
            
            # 接続エラー
            if "connection" in error_msg:
                logger.error(f"{self.model.__name__}の取得に失敗しました (id={id}): データベース接続エラー - {e}")
                raise ConnectionError(f"データベースへの接続中にエラーが発生しました: {e}")
                
            # タイムアウト
            elif "timeout" in error_msg:
                logger.error(f"{self.model.__name__}の取得に失敗しました (id={id}): タイムアウト - {e}")
                raise TimeoutError(f"データベース操作がタイムアウトしました: {e}")
                
            # その他の操作エラー
            else:
                logger.error(f"{self.model.__name__}の取得に失敗しました (id={id}): データベース操作エラー - {e}")
                raise RuntimeError(f"データベース操作中にエラーが発生しました: {e}")
                
        except SQLAlchemyError as e:
            logger.error(f"{self.model.__name__}の取得に失敗しました (id={id}): {e}")
            raise RuntimeError(f"{self.model.__name__}の取得中にエラーが発生しました: {e}")
            
        except Exception as e:
            logger.error(f"{self.model.__name__}の取得中に予期しないエラーが発生しました (id={id}): {e}")
            raise
            
    def get_by_id(self, id: str) -> Optional[T]:
        """
        IDによってレコードを取得
        
        Args:
            id: 取得するレコードのID
            
        Returns:
            見つかったレコード。存在しない場合はNone
        """
        try:
            return self.db.query(self.model).filter(self.model.id == id).first()
        except Exception as e:
            logger.error(f"{self.model.__name__}の取得に失敗: {e}")
            return None
        
    def find(self, db: Session, filters: Dict[str, Any] = None, limit: int = 100, offset: int = 0) -> List[T]:
        """
        条件によるレコードの検索
        
        Args:
            db: データベースセッション
            filters: フィルタ条件（カラム名と値のディクショナリ）
            limit: 取得する最大件数
            offset: スキップする件数
            
        Returns:
            条件に一致するオブジェクトのリスト
            
        Raises:
            OperationalError: データベース接続エラーなどの操作的な問題が発生した場合
            SQLAlchemyError: その他のSQLAlchemy関連エラーが発生した場合
        """
        try:
            query = db.query(self.model)
            
            # フィルタ条件の適用
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        query = query.filter(getattr(self.model, key) == value)
                    else:
                        logger.warning(f"{self.model.__name__}には'{key}'カラムが存在しません。このフィルタ条件は無視されます。")
            
            # 件数制限とオフセットの適用
            query = query.limit(limit).offset(offset)
            
            results = query.all()
            logger.debug(f"{self.model.__name__}の検索結果: {len(results)}件")
            return results
            
        except OperationalError as e:
            error_msg = str(e).lower()
            
            # 接続エラー
            if "connection" in error_msg:
                logger.error(f"{self.model.__name__}の検索に失敗しました: データベース接続エラー - {e}")
                raise ConnectionError(f"データベースへの接続中にエラーが発生しました: {e}")
                
            # タイムアウト
            elif "timeout" in error_msg:
                logger.error(f"{self.model.__name__}の検索に失敗しました: タイムアウト - {e}")
                raise TimeoutError(f"データベース操作がタイムアウトしました: {e}")
                
            # その他の操作エラー
            else:
                logger.error(f"{self.model.__name__}の検索に失敗しました: データベース操作エラー - {e}")
                raise RuntimeError(f"データベース操作中にエラーが発生しました: {e}")
                
        except SQLAlchemyError as e:
            logger.error(f"{self.model.__name__}の検索に失敗しました: {e}")
            raise RuntimeError(f"{self.model.__name__}の検索中にエラーが発生しました: {e}")
            
        except Exception as e:
            logger.error(f"{self.model.__name__}の検索中に予期しないエラーが発生しました: {e}")
            raise
            
    def get_by_status(self, db: Session, status: str, limit: int = 100) -> List[T]:
        """
        ステータスによるレコードの検索
        
        Args:
            db: データベースセッション
            status: 検索するステータス
            limit: 取得する最大件数
            
        Returns:
            指定されたステータスのオブジェクトのリスト
            
        Raises:
            OperationalError: データベース接続エラーなどの操作的な問題が発生した場合
            SQLAlchemyError: その他のSQLAlchemy関連エラーが発生した場合
        """
        try:
            if hasattr(self.model, "status"):
                results = db.query(self.model).filter(self.model.status == status).limit(limit).all()
                logger.debug(f"{self.model.__name__}のステータス'{status}'による検索結果: {len(results)}件")
                return results
            else:
                logger.warning(f"{self.model.__name__}にはstatusカラムがありません")
                return []
                
        except OperationalError as e:
            error_msg = str(e).lower()
            
            # 接続エラー
            if "connection" in error_msg:
                logger.error(f"{self.model.__name__}のステータス検索に失敗しました (status={status}): データベース接続エラー - {e}")
                raise ConnectionError(f"データベースへの接続中にエラーが発生しました: {e}")
                
            # タイムアウト
            elif "timeout" in error_msg:
                logger.error(f"{self.model.__name__}のステータス検索に失敗しました (status={status}): タイムアウト - {e}")
                raise TimeoutError(f"データベース操作がタイムアウトしました: {e}")
                
            # その他の操作エラー
            else:
                logger.error(f"{self.model.__name__}のステータス検索に失敗しました (status={status}): データベース操作エラー - {e}")
                raise RuntimeError(f"データベース操作中にエラーが発生しました: {e}")
                
        except SQLAlchemyError as e:
            logger.error(f"{self.model.__name__}のステータス検索に失敗しました (status={status}): {e}")
            raise RuntimeError(f"{self.model.__name__}のステータス検索中にエラーが発生しました: {e}")
            
        except Exception as e:
            logger.error(f"{self.model.__name__}のステータス検索中に予期しないエラーが発生しました (status={status}): {e}")
            raise
            
    def get_multi(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        filter_by: Dict[str, Any] = None,
        date_filters: List[Tuple[str, str, datetime]] = None,
        sort_by: str = None,
        sort_order: str = "asc"
    ) -> List[T]:
        """
        複数レコードの取得（ページネーション対応）
        
        Args:
            db: データベースセッション
            skip: スキップするレコード数
            limit: 取得するレコード数の上限
            filter_by: フィルタ条件
            date_filters: 日付フィルタのリスト [(フィールド名, 演算子, 日付値)]
                        例: [("created_at", ">=", datetime(2023, 1, 1))]
            sort_by: ソートするフィールド名
            sort_order: ソート順（"asc"または"desc"）
            
        Returns:
            取得したオブジェクトのリスト
        """
        try:
            query = db.query(self.model)
            
            # フィルタ条件がある場合は適用
            if filter_by:
                for key, value in filter_by.items():
                    if hasattr(self.model, key):
                        query = query.filter(getattr(self.model, key) == value)
            
            # 日付フィルタがある場合は適用
            if date_filters:
                for field_name, operator, date_value in date_filters:
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        if operator == ">=":
                            query = query.filter(field >= date_value)
                        elif operator == ">":
                            query = query.filter(field > date_value)
                        elif operator == "<=":
                            query = query.filter(field <= date_value)
                        elif operator == "<":
                            query = query.filter(field < date_value)
                        elif operator == "==":
                            query = query.filter(field == date_value)
            
            # ソート条件がある場合は適用
            if sort_by and hasattr(self.model, sort_by):
                sort_field = getattr(self.model, sort_by)
                if sort_order.lower() == "desc":
                    query = query.order_by(sort_field.desc())
                else:
                    query = query.order_by(sort_field.asc())
            
            return query.offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"{self.model.__name__}の複数取得に失敗しました: {e}")
            raise
    
    def update(self, db: Session, id: str, obj_in: Dict[str, Any]) -> bool:
        """
        レコードの更新
        
        Args:
            db: データベースセッション
            id: 更新するレコードのID
            obj_in: 更新するデータ
            
        Returns:
            更新が成功したかどうか
            
        Raises:
            ValueError: 更新対象が見つからない場合
            IntegrityError: 一意性制約違反や外部キー制約違反が発生した場合
            OperationalError: データベース接続エラーなどの操作的な問題が発生した場合
            SQLAlchemyError: その他のSQLAlchemy関連エラーが発生した場合
        """
        try:
            # 更新対象のオブジェクトを取得
            db_obj = db.query(self.model).filter(self.model.id == id).first()
            
            if not db_obj:
                logger.warning(f"{self.model.__name__}の更新対象が見つかりません (id={id})")
                return False
                
            # updated_atが存在する場合は更新
            if hasattr(self.model, "updated_at") and "updated_at" not in obj_in:
                obj_in["updated_at"] = datetime.now(UTC)
                
            # オブジェクトの属性を更新
            for key, value in obj_in.items():
                if hasattr(db_obj, key):
                    setattr(db_obj, key, value)
                else:
                    logger.warning(f"{self.model.__name__}には'{key}'属性が存在しません。この更新は無視されます。")
            
            # 変更をコミット
            db.commit()
            db.refresh(db_obj)
            
            logger.debug(f"{self.model.__name__}を更新しました: id={id}")
            return True
            
        except IntegrityError as e:
            db.rollback()
            error_msg = str(e).lower()
            
            # 一意性制約違反のエラーメッセージ
            if "unique constraint" in error_msg or "unique violation" in error_msg or "duplicate" in error_msg:
                logger.error(f"{self.model.__name__}の更新に失敗しました (id={id}): 一意性制約違反 - {e}")
                raise ValueError(f"{self.model.__name__}の更新に失敗しました: 一意性制約に違反するデータです")
                
            # 外部キー制約違反のエラーメッセージ
            elif "foreign key constraint" in error_msg or "foreign key violation" in error_msg:
                logger.error(f"{self.model.__name__}の更新に失敗しました (id={id}): 外部キー制約違反 - {e}")
                raise ValueError(f"{self.model.__name__}の更新に失敗しました: 参照先のレコードが存在しません")
                
            # その他の整合性エラー
            else:
                logger.error(f"{self.model.__name__}の更新に失敗しました (id={id}): データ整合性エラー - {e}")
                raise ValueError(f"{self.model.__name__}の更新に失敗しました: データ整合性エラーが発生しました")
                
        except OperationalError as e:
            db.rollback()
            error_msg = str(e).lower()
            
            # 接続エラー
            if "connection" in error_msg:
                logger.error(f"{self.model.__name__}の更新に失敗しました (id={id}): データベース接続エラー - {e}")
                raise ConnectionError(f"データベースへの接続中にエラーが発生しました: {e}")
                
            # タイムアウト
            elif "timeout" in error_msg:
                logger.error(f"{self.model.__name__}の更新に失敗しました (id={id}): タイムアウト - {e}")
                raise TimeoutError(f"データベース操作がタイムアウトしました: {e}")
                
            # その他の操作エラー
            else:
                logger.error(f"{self.model.__name__}の更新に失敗しました (id={id}): データベース操作エラー - {e}")
                raise RuntimeError(f"データベース操作中にエラーが発生しました: {e}")
                
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"{self.model.__name__}の更新に失敗しました (id={id}): {e}")
            raise RuntimeError(f"{self.model.__name__}の更新中にエラーが発生しました: {e}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"{self.model.__name__}の更新中に予期しないエラーが発生しました (id={id}): {e}")
            raise
            
    def delete(self, db: Session, id: str) -> bool:
        """
        レコードの削除
        
        Args:
            db: データベースセッション
            id: 削除するレコードのID
            
        Returns:
            削除が成功したかどうか
            
        Raises:
            ValueError: 削除対象が見つからない場合
            IntegrityError: 外部キー制約違反（他のテーブルから参照されている）が発生した場合
            OperationalError: データベース接続エラーなどの操作的な問題が発生した場合
            SQLAlchemyError: その他のSQLAlchemy関連エラーが発生した場合
        """
        try:
            # 削除対象のオブジェクトを取得
            db_obj = db.query(self.model).filter(self.model.id == id).first()
            
            if not db_obj:
                logger.warning(f"{self.model.__name__}の削除対象が見つかりません (id={id})")
                return False
                
            # オブジェクトを削除
            db.delete(db_obj)
            db.commit()
            
            logger.debug(f"{self.model.__name__}を削除しました: id={id}")
            return True
            
        except IntegrityError as e:
            db.rollback()
            error_msg = str(e).lower()
            
            # 外部キー制約違反（参照整合性違反）
            if "foreign key constraint" in error_msg or "foreign key violation" in error_msg:
                logger.error(f"{self.model.__name__}の削除に失敗しました (id={id}): 参照整合性制約違反 - {e}")
                raise ValueError(f"{self.model.__name__}の削除に失敗しました: 他のレコードから参照されています")
                
            # その他の整合性エラー
            else:
                logger.error(f"{self.model.__name__}の削除に失敗しました (id={id}): データ整合性エラー - {e}")
                raise ValueError(f"{self.model.__name__}の削除に失敗しました: データ整合性エラーが発生しました")
                
        except OperationalError as e:
            db.rollback()
            error_msg = str(e).lower()
            
            # 接続エラー
            if "connection" in error_msg:
                logger.error(f"{self.model.__name__}の削除に失敗しました (id={id}): データベース接続エラー - {e}")
                raise ConnectionError(f"データベースへの接続中にエラーが発生しました: {e}")
                
            # タイムアウト
            elif "timeout" in error_msg:
                logger.error(f"{self.model.__name__}の削除に失敗しました (id={id}): タイムアウト - {e}")
                raise TimeoutError(f"データベース操作がタイムアウトしました: {e}")
                
            # その他の操作エラー
            else:
                logger.error(f"{self.model.__name__}の削除に失敗しました (id={id}): データベース操作エラー - {e}")
                raise RuntimeError(f"データベース操作中にエラーが発生しました: {e}")
                
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"{self.model.__name__}の削除に失敗しました (id={id}): {e}")
            raise RuntimeError(f"{self.model.__name__}の削除中にエラーが発生しました: {e}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"{self.model.__name__}の削除中に予期しないエラーが発生しました (id={id}): {e}")
            raise

    def count(
        self, 
        db: Session, 
        *, 
        filter_by: Dict[str, Any] = None,
        date_filters: List[Tuple[str, str, datetime]] = None
    ) -> int:
        """
        条件に一致するレコード数をカウント
        
        Args:
            db: データベースセッション
            filter_by: フィルタ条件
            date_filters: 日付フィルタのリスト [(フィールド名, 演算子, 日付値)]
                        例: [("created_at", ">=", datetime(2023, 1, 1))]
            
        Returns:
            レコード数
        """
        try:
            query = db.query(self.model)
            
            # フィルタ条件がある場合は適用
            if filter_by:
                for key, value in filter_by.items():
                    if hasattr(self.model, key):
                        query = query.filter(getattr(self.model, key) == value)
            
            # 日付フィルタがある場合は適用
            if date_filters:
                for field_name, operator, date_value in date_filters:
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        if operator == ">=":
                            query = query.filter(field >= date_value)
                        elif operator == ">":
                            query = query.filter(field > date_value)
                        elif operator == "<=":
                            query = query.filter(field <= date_value)
                        elif operator == "<":
                            query = query.filter(field < date_value)
                        elif operator == "==":
                            query = query.filter(field == date_value)
            
            return query.count()
        except SQLAlchemyError as e:
            logger.error(f"{self.model.__name__}のカウントに失敗しました: {e}")
            raise


# 具体的なリポジトリクラス
class AuditProcedureRepository(BaseRepository[AuditProcedure]):
    """監査手続きリポジトリ"""
    
    def __init__(self, db: Session):
        super().__init__(db, AuditProcedure)
    
    def _prepare_data_for_db(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        """
        データベースに保存する前にデータを前処理します。
        リストをJSON文字列に変換します。
        
        Args:
            obj_in: 元のデータ
            
        Returns:
            前処理されたデータ
        """
        db_data = obj_in.copy()
        
        # IDが指定されていない場合は生成
        if "id" not in db_data or not db_data["id"]:
            db_data["id"] = str(uuid.uuid4())
        
        # created_atが指定されていない場合は現在時刻を設定
        if "created_at" not in db_data:
            db_data["created_at"] = datetime.now(UTC)
        
        # リストをJSON文字列に変換
        if "risk_areas" in db_data and isinstance(db_data["risk_areas"], list):
            db_data["risk_areas"] = json.dumps(db_data["risk_areas"])
        
        if "required_data_fields" in db_data and isinstance(db_data["required_data_fields"], list):
            db_data["required_data_fields"] = json.dumps(db_data["required_data_fields"])
        
        return db_data
    
    def get_by_title(self, title: str) -> Optional[AuditProcedure]:
        """タイトルで監査手続きを検索"""
        try:
            return self.db.query(self.model).filter(self.model.title == title).first()
        except SQLAlchemyError as e:
            logger.error(f"タイトルによる監査手続きの取得に失敗しました (title={title}): {e}")
            raise


class SampleDataRepository(BaseRepository[SampleData]):
    """サンプルデータリポジトリ"""
    
    def __init__(self, db: Session):
        super().__init__(db, SampleData)
    
    def _prepare_data_for_db(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        """
        データベースに保存する前にデータを前処理します。
        
        Args:
            obj_in: 元のデータ
            
        Returns:
            Dict[str, Any]: 前処理済みのデータ
        """
        db_data = obj_in.copy()
        
        # IDが指定されていない場合は生成
        if "id" not in db_data:
            db_data["id"] = str(uuid.uuid4())
        
        # リストやディクショナリをJSON文字列に変換
        if "columns" in db_data and isinstance(db_data["columns"], (list, dict)):
            db_data["columns"] = json.dumps(db_data["columns"])
        if "file_metadata" in db_data and isinstance(db_data["file_metadata"], (list, dict)):
            db_data["file_metadata"] = json.dumps(db_data["file_metadata"])
        
        # タイムスタンプフィールドは自動的に設定されるため、削除
        db_data.pop("created_at", None)
        db_data.pop("updated_at", None)
        
        return db_data
    
    def get_by_procedure_id(self, procedure_id: str) -> Optional[SampleData]:
        """
        監査手続きIDに基づいてサンプルデータを取得する
        
        Args:
            procedure_id: 監査手続きID
            
        Returns:
            サンプルデータ（存在しない場合はNone）
        """
        try:
            return self.db.query(self.model).filter(self.model.procedure_id == procedure_id).first()
        except SQLAlchemyError as e:
            logger.error(f"サンプルデータの取得中にエラーが発生しました: {e}")
            raise
    
    def get_all(
        self,
        page: int = 1,
        per_page: int = 10,
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ) -> Tuple[List[SampleData], int]:
        """
        サンプルデータの一覧を取得する
        
        Args:
            page: ページ番号（1始まり）
            per_page: 1ページあたりの件数
            sort_by: ソートするフィールド名
            sort_order: ソート順序（"asc"または"desc"）
            
        Returns:
            サンプルデータのリストと総件数のタプル
        """
        try:
            # オフセットの計算
            offset = (page - 1) * per_page
            
            # クエリの構築
            query = self.db.query(SampleData)
            
            # 総件数の取得
            total = query.count()
            
            # ソート条件の適用
            if sort_by and hasattr(SampleData, sort_by):
                sort_column = getattr(SampleData, sort_by)
                if sort_order.lower() == "desc":
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())
            else:
                # デフォルトのソート順（作成日時の降順）
                query = query.order_by(SampleData.created_at.desc())
            
            # ページネーションの適用
            samples = query.offset(offset).limit(per_page).all()
            
            return samples, total
            
        except Exception as e:
            logger.error(f"サンプルデータ一覧の取得中にエラーが発生しました: {str(e)}", exc_info=True)
            raise


class WorkflowRepository(BaseRepository[Workflow]):
    """ワークフローリポジトリクラス"""
    
    def __init__(self, db: Session):
        """リポジトリの初期化"""
        super().__init__(db, Workflow)
    
    def create(self, obj_in: Dict[str, Any]) -> Workflow:
        """ワークフローの作成

        Args:
            obj_in: 作成するオブジェクトのデータ
            
        Returns:
            Workflow: 作成されたワークフロー
        """
        return super().create(obj_in)
        
    def _prepare_data_for_db(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        """データベース用にデータを準備

        Args:
            obj_in: 元のデータ
            
        Returns:
            データベース用に処理されたデータ
        """
        data = dict(obj_in)
        
        # JSON文字列に変換
        for field in ["settings", "results", "metadata"]:
            if field in data and not isinstance(data[field], str):
                data[field] = json.dumps(data[field], ensure_ascii=False, default=_serialize_json_safe)
                
        return data
    
    def get_active_workflows(self) -> List[Workflow]:
        """アクティブなワークフローを取得

        Returns:
            アクティブなワークフローのリスト
        """
        active_statuses = ["created", "in_progress", "waiting"]
        query = self.db.query(self.model).filter(
            self.model.status.in_(active_statuses)
        )
        return query.all()

    def get_by_procedure_and_sample(
        self, procedure_id: str, sample_id: str
    ) -> Optional[Workflow]:
        """手続きIDとサンプルIDでワークフローを取得

        Args:
            procedure_id: 監査手続きID
            sample_id: サンプルデータID
            
        Returns:
            該当するワークフロー
        """
        query = self.db.query(self.model).filter(
            and_(
                self.model.audit_procedure_id == procedure_id,
                self.model.sample_data_id == sample_id
            )
        )
        return query.first()

def get_workflow_repository(db: Session) -> WorkflowRepository:
    """ワークフローリポジトリのインスタンスを取得する
    
    Args:
        db: データベースセッション
        
    Returns:
        WorkflowRepository: ワークフローリポジトリのインスタンス
    """
    return WorkflowRepository(db)

class AgentStateRepository(BaseRepository[AgentState]):
    """エージェント状態リポジトリ"""
    
    def __init__(self, db: Session):
        super().__init__(db, AgentState)
    
    def _prepare_data_for_db(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        """データベース保存用にデータを準備する"""
        result = obj_in.copy()
        
        # リストや辞書はJSON文字列に変換
        for key, value in list(result.items()):
            if isinstance(value, (dict, list)) and not isinstance(value, str):
                result[key] = json.dumps(_serialize_json_safe(value))
                
        return result
    
    def get_by_workflow_and_agent(self, workflow_id: str, agent_id: str) -> Optional[AgentState]:
        """ワークフローIDとエージェントIDで状態を検索"""
        try:
            return self.db.query(self.model).filter(
                self.model.workflow_id == workflow_id,
                self.model.agent_id == agent_id
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"エージェント状態の取得に失敗しました: {e}")
            raise

def get_agent_state_repository(db: Session) -> AgentStateRepository:
    """AgentStateRepositoryのインスタンスを取得"""
    return AgentStateRepository(db)

class AuditResultRepository(BaseRepository[AuditResult]):
    """監査結果リポジトリ"""
    
    def __init__(self, db: Session):
        super().__init__(db, AuditResult)
    
    def _prepare_data_for_db(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        """データベース保存用にデータを準備する"""
        result = obj_in.copy()
        
        # リストや辞書はJSON文字列に変換
        for key, value in list(result.items()):
            if isinstance(value, (dict, list)) and not isinstance(value, str):
                result[key] = json.dumps(_serialize_json_safe(value))
                
        return result
    
    def get_by_workflow_id(self, workflow_id: str) -> Optional[AuditResult]:
        """ワークフローIDで監査結果を検索"""
        try:
            return self.db.query(self.model).filter(self.model.workflow_id == workflow_id).first()
        except SQLAlchemyError as e:
            logger.error(f"監査結果の取得に失敗しました: {e}")
            raise

def get_audit_result_repository(db: Session) -> AuditResultRepository:
    """AuditResultRepositoryのインスタンスを取得"""
    return AuditResultRepository(db)

class FindingRepository(BaseRepository[Finding]):
    """監査発見事項リポジトリ"""
    
    def __init__(self, db: Session):
        super().__init__(db, Finding)
    
    def _prepare_data_for_db(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        """データベース保存用にデータを準備する"""
        result = obj_in.copy()
        
        # リストや辞書はJSON文字列に変換
        for key, value in list(result.items()):
            if isinstance(value, (dict, list)) and not isinstance(value, str):
                result[key] = json.dumps(_serialize_json_safe(value))
                
        return result
    
    def get_by_audit_result(self, audit_result_id: str) -> List[Finding]:
        """監査結果IDで発見事項を検索"""
        try:
            return self.db.query(self.model).filter(self.model.audit_result_id == audit_result_id).all()
        except SQLAlchemyError as e:
            logger.error(f"監査発見事項の取得に失敗しました: {e}")
            raise

def get_finding_repository(db: Session) -> FindingRepository:
    """FindingRepositoryのインスタンスを取得"""
    return FindingRepository(db)

class MessageRepository(BaseRepository[Message]):
    """メッセージリポジトリ"""
    
    def __init__(self, db: Session):
        super().__init__(db, Message)
    
    def _prepare_data_for_db(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        """データベース保存用にデータを準備する"""
        result = obj_in.copy()
        
        # リストや辞書はJSON文字列に変換
        for key, value in list(result.items()):
            if isinstance(value, (dict, list)) and not isinstance(value, str):
                result[key] = json.dumps(_serialize_json_safe(value))
                
        return result

def get_message_repository(db: Session) -> MessageRepository:
    """MessageRepositoryのインスタンスを取得"""
    return MessageRepository(db)

class AuditTrailRepository(BaseRepository[AuditTrail]):
    """監査証跡リポジトリ"""
    
    def __init__(self, db: Session):
        super().__init__(db, AuditTrail)
    
    def _prepare_data_for_db(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        """データベース保存用にデータを準備する"""
        result = obj_in.copy()
        
        # リストや辞書はJSON文字列に変換
        for key, value in list(result.items()):
            if isinstance(value, (dict, list)) and not isinstance(value, str):
                result[key] = json.dumps(_serialize_json_safe(value))
                
        return result

def get_audit_trail_repository(db: Session) -> AuditTrailRepository:
    """AuditTrailRepositoryのインスタンスを取得"""
    return AuditTrailRepository(db)

class MessageLogRepository(BaseRepository[MessageLog]):
    """メッセージログリポジトリ"""
    
    def __init__(self, db: Session):
        super().__init__(db, MessageLog)
    
    def _prepare_data_for_db(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        """データベース保存用にデータを準備する"""
        result = obj_in.copy()
        
        # リストや辞書はJSON文字列に変換
        for key, value in list(result.items()):
            if isinstance(value, (dict, list)) and not isinstance(value, str):
                result[key] = json.dumps(_serialize_json_safe(value))
                
        return result

def get_message_log_repository(db: Session) -> MessageLogRepository:
    """MessageLogRepositoryのインスタンスを取得"""
    return MessageLogRepository(db)

class AgentDecisionRepository(BaseRepository[AgentDecision]):
    """エージェント決定リポジトリ"""
    
    def __init__(self, db: Session):
        super().__init__(db, AgentDecision)
    
    def _prepare_data_for_db(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        """データベース保存用にデータを準備する"""
        result = obj_in.copy()
        
        # リストや辞書はJSON文字列に変換
        for key, value in list(result.items()):
            if isinstance(value, (dict, list)) and not isinstance(value, str):
                result[key] = json.dumps(_serialize_json_safe(value))
                
        return result

def get_agent_decision_repository(db: Session) -> AgentDecisionRepository:
    """AgentDecisionRepositoryのインスタンスを取得"""
    return AgentDecisionRepository(db)

class HumanInterventionRequestRepository(BaseRepository[HumanInterventionRequest]):
    """人間介入リクエストリポジトリ"""
    
    def __init__(self, db: Session):
        super().__init__(db, HumanInterventionRequest)
    
    def _prepare_data_for_db(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        """データベース保存用にデータを準備する"""
        result = obj_in.copy()
        
        # リストや辞書はJSON文字列に変換
        for key, value in list(result.items()):
            if isinstance(value, (dict, list)) and not isinstance(value, str):
                result[key] = json.dumps(_serialize_json_safe(value))
                
        return result

def get_human_intervention_request_repository(db: Session) -> HumanInterventionRequestRepository:
    """HumanInterventionRequestRepositoryのインスタンスを取得"""
    return HumanInterventionRequestRepository(db)

class HumanInterventionResponseRepository(BaseRepository[HumanInterventionResponse]):
    """人間介入レスポンスリポジトリ"""
    
    def __init__(self, db: Session):
        super().__init__(db, HumanInterventionResponse)
    
    def _prepare_data_for_db(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        """データベース保存用にデータを準備する"""
        result = obj_in.copy()
        
        # リストや辞書はJSON文字列に変換
        for key, value in list(result.items()):
            if isinstance(value, (dict, list)) and not isinstance(value, str):
                result[key] = json.dumps(_serialize_json_safe(value))
                
        return result

def get_human_intervention_response_repository(db: Session) -> HumanInterventionResponseRepository:
    """HumanInterventionResponseRepositoryのインスタンスを取得"""
    return HumanInterventionResponseRepository(db)

class GraphStateHistoryRepository(BaseRepository[GraphStateHistory]):
    """グラフ状態履歴リポジトリ"""
    
    def __init__(self, db: Session):
        super().__init__(db, GraphStateHistory)
    
    def _prepare_data_for_db(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        """データベース保存用にデータを準備する"""
        result = obj_in.copy()
        
        # リストや辞書はJSON文字列に変換
        for key, value in list(result.items()):
            if isinstance(value, (dict, list)) and not isinstance(value, str):
                result[key] = json.dumps(_serialize_json_safe(value))
                
        return result
    
    def get_by_workflow_id(self, workflow_id: str, limit: int = 100, offset: int = 0) -> List[GraphStateHistory]:
        """ワークフローIDによる状態履歴の取得"""
        return self.db.query(GraphStateHistory)\
            .filter(GraphStateHistory.workflow_id == workflow_id)\
            .order_by(GraphStateHistory.created_at.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
    
    def get_transitions(self, workflow_id: str) -> List[GraphStateHistory]:
        """ワークフローの状態遷移履歴を取得"""
        return self.db.query(GraphStateHistory)\
            .filter(GraphStateHistory.workflow_id == workflow_id)\
            .filter(GraphStateHistory.transition_to.isnot(None))\
            .order_by(GraphStateHistory.created_at.asc())\
            .all()

def get_graph_state_history_repository(db: Session) -> GraphStateHistoryRepository:
    """GraphStateHistoryRepositoryのインスタンスを取得"""
    return GraphStateHistoryRepository(db)

class CheckpointRecordRepository(BaseRepository[CheckpointRecord]):
    """チェックポイントレコードリポジトリ"""
    
    def __init__(self, db: Session):
        super().__init__(db, CheckpointRecord)
    
    def _prepare_data_for_db(self, obj_in: Dict[str, Any]) -> Dict[str, Any]:
        """データベース保存用にデータを準備する"""
        result = obj_in.copy()
        
        # リストや辞書はJSON文字列に変換
        for key, value in list(result.items()):
            if isinstance(value, (dict, list)) and not isinstance(value, str):
                result[key] = json.dumps(_serialize_json_safe(value))
                
        return result
    
    def get_by_workflow_id(self, workflow_id: str) -> List[CheckpointRecord]:
        """ワークフローIDによるチェックポイントの取得"""
        return self.db.query(CheckpointRecord)\
            .filter(CheckpointRecord.workflow_id == workflow_id)\
            .order_by(CheckpointRecord.created_at.desc())\
            .all()
    
    def get_latest_by_workflow_id(self, workflow_id: str) -> Optional[CheckpointRecord]:
        """ワークフローIDによる最新のチェックポイントの取得"""
        return self.db.query(CheckpointRecord)\
            .filter(CheckpointRecord.workflow_id == workflow_id)\
            .order_by(CheckpointRecord.created_at.desc())\
            .first()

def get_checkpoint_record_repository(db: Session) -> CheckpointRecordRepository:
    """CheckpointRecordRepositoryのインスタンスを取得"""
    return CheckpointRecordRepository(db) 