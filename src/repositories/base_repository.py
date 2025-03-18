"""
リポジトリ基底クラス

このモジュールでは、データアクセスレイヤーを抽象化するための基底リポジトリクラスを定義します。
抽象基底クラスを使用して型安全なリポジトリインターフェースを提供し、依存性の逆転と
単一責任の原則を実現します。また、Unit of Workパターンをサポートしています。
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Type, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Session
from sqlalchemy import update, delete

from src.models.db_models import Base
from src.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T', bound=Base)
ID = TypeVar('ID')


class Repository(Generic[T, ID], ABC):
    """
    リポジトリ基底クラス
    
    データアクセスのための抽象インターフェースを提供します。
    T: エンティティの型
    ID: エンティティIDの型
    """
    
    @abstractmethod
    async def find_by_id(self, id: ID) -> Optional[T]:
        """
        IDでエンティティを検索する
        
        Args:
            id: エンティティID
            
        Returns:
            Optional[T]: 見つかったエンティティ、または None
        """
        pass
    
    @abstractmethod
    async def find_all(self) -> List[T]:
        """
        すべてのエンティティを取得する
        
        Returns:
            List[T]: エンティティのリスト
        """
        pass
    
    @abstractmethod
    async def save(self, entity: T) -> T:
        """
        エンティティを保存する
        
        Args:
            entity: 保存するエンティティ
            
        Returns:
            T: 保存されたエンティティ
        """
        pass
    
    @abstractmethod
    async def delete(self, id: ID) -> bool:
        """
        IDでエンティティを削除する
        
        Args:
            id: 削除するエンティティのID
            
        Returns:
            bool: 削除が成功したかどうか
        """
        pass
    
    @abstractmethod
    async def update(self, id: ID, data: Dict[str, Any]) -> Optional[T]:
        """
        IDでエンティティを更新する
        
        Args:
            id: 更新するエンティティのID
            data: 更新データ
            
        Returns:
            Optional[T]: 更新されたエンティティ
        """
        pass


class SQLAlchemyRepository(Repository[T, ID]):
    """
    SQLAlchemyを使用したリポジトリ実装
    """
    
    def __init__(self, db_session: Union[AsyncSession, Session], model_class: Type[T]):
        """
        コンストラクタ
        
        Args:
            db_session: データベースセッション
            model_class: エンティティクラス
        """
        self.db_session = db_session
        self.model_class = model_class
        self.is_async = isinstance(db_session, AsyncSession)
    
    async def find_by_id(self, id: ID) -> Optional[T]:
        """
        IDでエンティティを検索する
        
        Args:
            id: エンティティID
            
        Returns:
            Optional[T]: 見つかったエンティティ、または None
        """
        if self.is_async:
            stmt = select(self.model_class).where(self.model_class.id == id)
            result = await self.db_session.execute(stmt)
            return result.scalars().first()
        else:
            stmt = select(self.model_class).where(self.model_class.id == id)
            result = self.db_session.execute(stmt)
            return result.scalars().first()
    
    async def find_all(self) -> List[T]:
        """
        すべてのエンティティを取得する
        
        Returns:
            List[T]: エンティティのリスト
        """
        if self.is_async:
            stmt = select(self.model_class)
            result = await self.db_session.execute(stmt)
            return list(result.scalars().all())
        else:
            stmt = select(self.model_class)
            result = self.db_session.execute(stmt)
            return list(result.scalars().all())
    
    async def save(self, entity: T) -> T:
        """
        エンティティを保存する
        
        Args:
            entity: 保存するエンティティ
            
        Returns:
            T: 保存されたエンティティ
        """
        try:
            self.db_session.add(entity)
            
            if self.is_async:
                await self.db_session.flush()
                await self.db_session.commit()
            else:
                self.db_session.flush()
                self.db_session.commit()
                
            return entity
            
        except Exception as e:
            if self.is_async:
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
                
            logger.error(f"エンティティの保存に失敗しました: {e}")
            raise
    
    async def delete(self, id: ID) -> bool:
        """
        IDでエンティティを削除する
        
        Args:
            id: 削除するエンティティのID
            
        Returns:
            bool: 削除が成功したかどうか
        """
        try:
            stmt = delete(self.model_class).where(self.model_class.id == id)
            
            if self.is_async:
                result = await self.db_session.execute(stmt)
                await self.db_session.commit()
            else:
                result = self.db_session.execute(stmt)
                self.db_session.commit()
                
            return result.rowcount > 0
            
        except Exception as e:
            if self.is_async:
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
                
            logger.error(f"エンティティの削除に失敗しました: {e}")
            raise
    
    async def update(self, id: ID, data: Dict[str, Any]) -> Optional[T]:
        """
        IDでエンティティを更新する
        
        Args:
            id: 更新するエンティティのID
            data: 更新データ
            
        Returns:
            Optional[T]: 更新されたエンティティ
        """
        try:
            # 更新対象のエンティティが存在するか確認
            entity = await self.find_by_id(id)
            if not entity:
                return None
                
            # 更新の実行
            stmt = update(self.model_class).where(self.model_class.id == id).values(**data)
            
            if self.is_async:
                await self.db_session.execute(stmt)
                await self.db_session.commit()
            else:
                self.db_session.execute(stmt)
                self.db_session.commit()
                
            # 更新後のエンティティを再取得
            return await self.find_by_id(id)
            
        except Exception as e:
            if self.is_async:
                await self.db_session.rollback()
            else:
                self.db_session.rollback()
                
            logger.error(f"エンティティの更新に失敗しました: {e}")
            raise


class UnitOfWork:
    """
    Unit of Workパターン実装クラス
    
    トランザクション管理の一元化を提供します。
    """
    
    def __init__(self, db_session: Union[AsyncSession, Session]):
        """
        コンストラクタ
        
        Args:
            db_session: データベースセッション
        """
        self.db_session = db_session
        self.is_async = isinstance(db_session, AsyncSession)
        self._repositories = {}
    
    def __getattribute__(self, name: str) -> Any:
        """
        属性アクセスをインターセプトして、リポジトリのオンデマンド生成をサポート
        
        Args:
            name: 属性名
            
        Returns:
            Any: 属性値
        """
        try:
            return super().__getattribute__(name)
        except AttributeError:
            # repository_<model_name> 形式の属性名であれば、リポジトリを生成
            if name.startswith('repository_'):
                model_name = name[len('repository_'):]
                return self._get_repository(model_name)
            raise
    
    def _get_repository(self, model_name: str) -> SQLAlchemyRepository:
        """
        モデル名からリポジトリを取得または生成する
        
        Args:
            model_name: モデル名
            
        Returns:
            SQLAlchemyRepository: リポジトリインスタンス
        """
        if model_name in self._repositories:
            return self._repositories[model_name]
        
        # モデルクラスを動的に取得
        try:
            import importlib
            models_module = importlib.import_module('src.models.db_models')
            model_class = getattr(models_module, model_name)
            
            # リポジトリを生成してキャッシュ
            repository = SQLAlchemyRepository(self.db_session, model_class)
            self._repositories[model_name] = repository
            
            return repository
            
        except (ImportError, AttributeError) as e:
            logger.error(f"モデル {model_name} のリポジトリ生成に失敗しました: {e}")
            raise ValueError(f"モデル {model_name} が見つかりません")
    
    def register_repository(self, name: str, repository: SQLAlchemyRepository) -> None:
        """
        リポジトリを登録する
        
        Args:
            name: リポジトリ名
            repository: リポジトリインスタンス
        """
        self._repositories[name] = repository
    
    async def commit(self) -> None:
        """
        トランザクションをコミットする
        """
        try:
            if self.is_async:
                await self.db_session.commit()
            else:
                self.db_session.commit()
        except Exception as e:
            await self.rollback()
            logger.error(f"トランザクションのコミットに失敗しました: {e}")
            raise
    
    async def rollback(self) -> None:
        """
        トランザクションをロールバックする
        """
        if self.is_async:
            await self.db_session.rollback()
        else:
            self.db_session.rollback()
    
    async def close(self) -> None:
        """
        セッションを閉じる
        """
        if self.is_async:
            await self.db_session.close()
        else:
            self.db_session.close() 