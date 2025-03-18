"""
イベントバスモジュール

このモジュールでは、イベント駆動アーキテクチャを実現するための
イベントバスの実装を提供します。アプリケーション内の疎結合な
コンポーネント間通信を可能にします。
"""

import asyncio
import uuid
import inspect
import traceback
from typing import Dict, List, Any, Callable, Optional, Set, Type, TypeVar, Generic, Union
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum, auto

from src.utils.logger import get_logger
from src.utils.async_utils import get_background_task_manager

logger = get_logger(__name__)

# 型変数
T = TypeVar('T', bound='Event')


class EventPriority(Enum):
    """イベント優先度"""
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class Event:
    """
    イベント基底クラス
    
    システム内で発生するすべてのイベントの基底クラスです。
    すべてのカスタムイベントはこのクラスから派生する必要があります。
    """
    # イベントのメタデータ
    event_id: str = field(default_factory=lambda: f"evt-{uuid.uuid4()}")
    event_type: str = field(init=False)
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None
    priority: EventPriority = EventPriority.NORMAL
    
    def __post_init__(self):
        """
        初期化後の処理
        
        イベントタイプをクラス名から自動設定します
        """
        self.event_type = self.__class__.__name__
    
    def to_dict(self) -> Dict[str, Any]:
        """
        イベントを辞書に変換する
        
        Returns:
            Dict[str, Any]: イベントデータの辞書
        """
        result = asdict(self)
        # Enum値を文字列に変換
        if 'priority' in result:
            result['priority'] = result['priority'].name
        return result


class EventHandler:
    """
    イベントハンドラ

    イベントを購読するためのデコレータとして使用します。
    """
    
    def __init__(
        self,
        event_type: Optional[Type[Event]] = None,
        priority: EventPriority = EventPriority.NORMAL,
        async_execution: bool = True
    ):
        """
        コンストラクタ
        
        Args:
            event_type: 購読するイベントタイプ（Noneの場合はすべてのイベント）
            priority: ハンドラの優先度
            async_execution: 非同期実行を行うかどうか
        """
        self.event_type = event_type
        self.priority = priority
        self.async_execution = async_execution
    
    def __call__(self, func):
        """
        デコレータとして機能します
        
        Args:
            func: デコレート対象の関数
            
        Returns:
            Callable: デコレートされた関数
        """
        # ハンドラ情報を設定
        func._event_handler = True
        func._event_type = self.event_type.__name__ if self.event_type else None
        func._priority = self.priority
        func._async_execution = self.async_execution
        
        return func


@dataclass
class HandlerInfo:
    """ハンドラー情報"""
    handler: Callable
    event_type: Optional[str]
    priority: EventPriority
    async_execution: bool


class EventBus:
    """
    イベントバス
    
    アプリケーション内の疎結合なコンポーネント間通信を実現します。
    発行者と購読者の分離パターンを使用して、スケーラブルな
    イベント処理機能を提供します。
    """
    
    def __init__(self):
        """コンストラクタ"""
        # イベントタイプごとのハンドラマップ
        self._handlers: Dict[str, List[HandlerInfo]] = {}
        # 汎用ハンドラリスト（すべてのイベントを処理）
        self._global_handlers: List[HandlerInfo] = []
        # ハンドラ実行の同期オプション（デフォルトは非同期）
        self._sync_processing = False
        # イベント履歴（最新の100件を保持）
        self._event_history: List[Dict[str, Any]] = []
        self._max_history_size = 100
    
    def register_handler(
        self,
        handler: Callable,
        event_type: Optional[Type[Event]] = None,
        priority: EventPriority = EventPriority.NORMAL,
        async_execution: bool = True
    ) -> None:
        """
        イベントハンドラを登録する
        
        Args:
            handler: イベントハンドラ関数
            event_type: 処理するイベントタイプ（Noneの場合はすべてのイベント）
            priority: ハンドラの優先度
            async_execution: 非同期実行を行うかどうか
        """
        handler_info = HandlerInfo(
            handler=handler,
            event_type=event_type.__name__ if event_type else None,
            priority=priority,
            async_execution=async_execution
        )
        
        if event_type:
            event_type_name = event_type.__name__
            if event_type_name not in self._handlers:
                self._handlers[event_type_name] = []
            self._handlers[event_type_name].append(handler_info)
            logger.debug(f"ハンドラを登録しました: {handler.__name__} for {event_type_name}")
        else:
            # 汎用ハンドラを登録
            self._global_handlers.append(handler_info)
            logger.debug(f"汎用ハンドラを登録しました: {handler.__name__}")
    
    def register_class_handlers(self, handler_class: Any) -> None:
        """
        クラス内のすべてのイベントハンドラを登録する
        
        Args:
            handler_class: ハンドラメソッドを持つクラス
        """
        # クラスのインスタンスメソッドを検査
        for method_name, method in inspect.getmembers(handler_class, inspect.ismethod):
            if hasattr(method, '_event_handler') and method._event_handler:
                # ハンドラとして登録
                self.register_handler(
                    handler=method,
                    event_type=method._event_type,
                    priority=method._priority,
                    async_execution=method._async_execution
                )
    
    def unregister_handler(self, handler: Callable, event_type: Optional[Type[Event]] = None) -> bool:
        """
        イベントハンドラの登録を解除する
        
        Args:
            handler: 登録解除するハンドラ
            event_type: ハンドラが登録されているイベントタイプ
            
        Returns:
            bool: 登録解除に成功したかどうか
        """
        # 特定のイベントタイプのハンドラを登録解除
        if event_type:
            event_type_name = event_type.__name__
            if event_type_name in self._handlers:
                for i, handler_info in enumerate(self._handlers[event_type_name]):
                    if handler_info.handler == handler:
                        self._handlers[event_type_name].pop(i)
                        logger.debug(f"ハンドラの登録を解除しました: {handler.__name__} from {event_type_name}")
                        return True
        # 汎用ハンドラを登録解除
        else:
            for i, handler_info in enumerate(self._global_handlers):
                if handler_info.handler == handler:
                    self._global_handlers.pop(i)
                    logger.debug(f"汎用ハンドラの登録を解除しました: {handler.__name__}")
                    return True
        
        return False
    
    async def publish(self, event: Event, sync: bool = False) -> None:
        """
        イベントを発行する
        
        Args:
            event: 発行するイベント
            sync: 同期的に処理するかどうか（デフォルトは非同期）
        """
        # イベント履歴に追加
        self._add_to_history(event)
        
        event_type = event.__class__.__name__
        logger.debug(f"イベントを発行します: {event_type} (ID: {event.event_id})")
        
        # ハンドラのリストを収集
        handlers_to_call = self._get_handlers_for_event(event)
        
        # 同期または非同期で処理
        if sync or self._sync_processing:
            await self._process_handlers_sync(handlers_to_call, event)
        else:
            await self._process_handlers_async(handlers_to_call, event)
    
    def _get_handlers_for_event(self, event: Event) -> List[HandlerInfo]:
        """
        イベントを処理するハンドラの一覧を取得する
        
        Args:
            event: イベント
            
        Returns:
            List[HandlerInfo]: ハンドラ情報のリスト
        """
        event_type = event.__class__.__name__
        
        # 特定のイベントタイプのハンドラを取得
        handlers = self._handlers.get(event_type, []).copy()
        
        # 汎用ハンドラを追加
        handlers.extend(self._global_handlers)
        
        # 優先度でソート（高い順）
        return sorted(handlers, key=lambda h: h.priority.value, reverse=True)
    
    async def _process_handlers_sync(self, handlers: List[HandlerInfo], event: Event) -> None:
        """
        ハンドラを同期的に処理する
        
        Args:
            handlers: ハンドラのリスト
            event: 処理するイベント
        """
        for handler_info in handlers:
            try:
                # 非同期ハンドラの場合
                if inspect.iscoroutinefunction(handler_info.handler):
                    await handler_info.handler(event)
                # 同期ハンドラの場合
                else:
                    handler_info.handler(event)
                    
            except Exception as e:
                logger.error(f"ハンドラの実行中にエラーが発生しました: {e}")
                logger.debug(traceback.format_exc())
    
    async def _process_handlers_async(self, handlers: List[HandlerInfo], event: Event) -> None:
        """
        ハンドラを非同期で処理する
        
        Args:
            handlers: ハンドラのリスト
            event: 処理するイベント
        """
        # 非同期タスクをグループ化して実行
        async_tasks = []
        
        for handler_info in handlers:
            # 非同期実行フラグがあり、非同期関数の場合
            if handler_info.async_execution and inspect.iscoroutinefunction(handler_info.handler):
                # タスクの作成
                task = asyncio.create_task(self._execute_handler_safe(handler_info, event))
                async_tasks.append(task)
            else:
                # 同期ハンドラや非同期実行を無効にしたハンドラを直接実行
                try:
                    if inspect.iscoroutinefunction(handler_info.handler):
                        await handler_info.handler(event)
                    else:
                        handler_info.handler(event)
                except Exception as e:
                    logger.error(f"ハンドラの実行中にエラーが発生しました: {e}")
                    logger.debug(traceback.format_exc())
        
        # 非同期タスクの実行を待機
        if async_tasks:
            await asyncio.gather(*async_tasks, return_exceptions=True)
    
    async def _execute_handler_safe(self, handler_info: HandlerInfo, event: Event) -> None:
        """
        ハンドラを安全に実行する
        
        Args:
            handler_info: ハンドラ情報
            event: 処理するイベント
        """
        try:
            await handler_info.handler(event)
        except Exception as e:
            logger.error(f"非同期ハンドラの実行中にエラーが発生しました: {e}")
            logger.debug(traceback.format_exc())
    
    def _add_to_history(self, event: Event) -> None:
        """
        イベント履歴に追加する
        
        Args:
            event: 追加するイベント
        """
        # イベント情報を履歴に追加
        event_info = event.to_dict()
        self._event_history.append(event_info)
        
        # 履歴サイズを制限
        if len(self._event_history) > self._max_history_size:
            self._event_history = self._event_history[-self._max_history_size:]
    
    def get_event_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        イベント履歴を取得する
        
        Args:
            limit: 取得する履歴の最大数
            
        Returns:
            List[Dict[str, Any]]: イベント履歴
        """
        return self._event_history[-limit:]
    
    def clear_event_history(self) -> None:
        """イベント履歴をクリアする"""
        self._event_history.clear()
    
    def set_sync_processing(self, sync: bool) -> None:
        """
        同期処理モードを設定する
        
        Args:
            sync: 同期的に処理するかどうか
        """
        self._sync_processing = sync


# シングルトンイベントバス
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    イベントバスのシングルトンインスタンスを取得する
    
    Returns:
        EventBus: イベントバスインスタンス
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


# ------ ドメインイベント定義 ------ #

@dataclass
class DomainEvent(Event):
    """
    ドメインイベント基底クラス
    
    ドメインモデルの状態変化を表すイベントの基底クラスです。
    """
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None


@dataclass
class EntityCreatedEvent(DomainEvent):
    """エンティティ作成イベント"""
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityUpdatedEvent(DomainEvent):
    """エンティティ更新イベント"""
    changes: Dict[str, Any] = field(default_factory=dict)
    previous_state: Optional[Dict[str, Any]] = None


@dataclass
class EntityDeletedEvent(DomainEvent):
    """エンティティ削除イベント"""
    entity_data: Optional[Dict[str, Any]] = None


# ------ システムイベント定義 ------ #

@dataclass
class SystemEvent(Event):
    """
    システムイベント基底クラス
    
    システム全体に関わる状態変化やアクションを表すイベントの基底クラスです。
    """
    pass


@dataclass
class ApplicationStartedEvent(SystemEvent):
    """アプリケーション起動イベント"""
    startup_time: float = field(default_factory=lambda: time.time())
    environment: str = "development"


@dataclass
class ApplicationShutdownEvent(SystemEvent):
    """アプリケーション終了イベント"""
    uptime: float = 0
    shutdown_reason: Optional[str] = None


@dataclass
class ErrorEvent(SystemEvent):
    """エラーイベント"""
    error_type: str
    error_message: str
    stacktrace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


# ------ 便利なユーティリティ関数 ------ #

async def publish_event(event: Event, sync: bool = False) -> None:
    """
    イベントを発行する（ユーティリティ関数）
    
    Args:
        event: 発行するイベント
        sync: 同期的に処理するかどうか
    """
    event_bus = get_event_bus()
    await event_bus.publish(event, sync)


def event_handler(
    event_type: Optional[Type[Event]] = None,
    priority: EventPriority = EventPriority.NORMAL,
    async_execution: bool = True
):
    """
    イベントハンドラデコレータ（ユーティリティ関数）
    
    Args:
        event_type: 処理するイベントタイプ
        priority: ハンドラの優先度
        async_execution: 非同期実行を行うかどうか
        
    Returns:
        Callable: デコレータ関数
    """
    return EventHandler(event_type, priority, async_execution) 