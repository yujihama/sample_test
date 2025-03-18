"""
非同期処理ユーティリティ

このモジュールでは、非同期処理のための共通ユーティリティを提供します。
asyncioを中心とした標準化されたアプローチを使用し、長時間実行タスクの管理、
キャンセル、タイムアウト、リソース使用量の最適化などの機能を提供します。
"""

import asyncio
import time
import uuid
import functools
import signal
import threading
from typing import Dict, Any, List, Optional, Callable, Coroutine, TypeVar, Union, Set, Tuple
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass, field

from src.utils.logger import get_logger

logger = get_logger(__name__)

# 型変数
T = TypeVar('T')
R = TypeVar('R')

# グローバルタスクレジストリ
active_tasks: Dict[str, 'ManagedTask'] = {}
task_executions: Dict[str, List[Dict[str, Any]]] = {}

# スロットリング設定
_throttle_semaphores: Dict[str, asyncio.Semaphore] = {}


@dataclass
class TaskStatus:
    """タスクステータスクラス"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class TaskResult:
    """タスク結果クラス"""
    task_id: str
    status: str
    result: Any = None
    error: Optional[Exception] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskCancelledException(Exception):
    """タスクキャンセル例外"""
    pass


class TaskTimeoutException(Exception):
    """タスクタイムアウト例外"""
    pass


class ManagedTask:
    """管理対象タスククラス"""
    
    def __init__(
        self,
        coro: Coroutine,
        task_id: Optional[str] = None,
        timeout: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        on_complete: Optional[Callable[[TaskResult], None]] = None,
        on_error: Optional[Callable[[TaskResult], None]] = None
    ):
        """
        コンストラクタ
        
        Args:
            coro: タスクのコルーチン
            task_id: タスクID（省略時は自動生成）
            timeout: タイムアウト時間（秒）
            metadata: タスクのメタデータ
            on_complete: 完了時コールバック
            on_error: エラー時コールバック
        """
        self.coro = coro
        self.task_id = task_id or f"task-{uuid.uuid4()}"
        self.timeout = timeout
        self.metadata = metadata or {}
        self.on_complete = on_complete
        self.on_error = on_error
        
        self.task: Optional[asyncio.Task] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        
        # タスクレジストリに登録
        active_tasks[self.task_id] = self
        task_executions.setdefault(self.task_id, [])
    
    async def start(self) -> TaskResult:
        """
        タスクを開始する
        
        Returns:
            TaskResult: タスク結果
        """
        self.start_time = datetime.now()
        self.status = TaskStatus.RUNNING
        
        # 実行履歴に追加
        execution_record = {
            "start_time": self.start_time,
            "status": self.status,
            "metadata": self.metadata.copy()
        }
        task_executions[self.task_id].append(execution_record)
        
        try:
            # タイムアウト付きで実行
            if self.timeout:
                self.task = asyncio.create_task(self.coro)
                try:
                    self.result = await asyncio.wait_for(self.task, timeout=self.timeout)
                except asyncio.TimeoutError:
                    self.status = TaskStatus.TIMEOUT
                    self.error = TaskTimeoutException(f"タスクがタイムアウトしました: {self.timeout}秒")
                    raise self.error
            else:
                self.task = asyncio.create_task(self.coro)
                self.result = await self.task
            
            self.status = TaskStatus.COMPLETED
            
        except asyncio.CancelledError:
            self.status = TaskStatus.CANCELLED
            self.error = TaskCancelledException("タスクがキャンセルされました")
            raise self.error
            
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.error = e
            raise
            
        finally:
            self.end_time = datetime.now()
            execution_time = (self.end_time - self.start_time).total_seconds()
            
            # 実行履歴を更新
            execution_record["end_time"] = self.end_time
            execution_record["status"] = self.status
            execution_record["execution_time"] = execution_time
            if self.error:
                execution_record["error"] = str(self.error)
            
            # タスク結果を作成
            task_result = TaskResult(
                task_id=self.task_id,
                status=self.status,
                result=self.result,
                error=self.error,
                start_time=self.start_time,
                end_time=self.end_time,
                execution_time=execution_time,
                metadata=self.metadata
            )
            
            # コールバックを実行
            if self.status == TaskStatus.COMPLETED and self.on_complete:
                try:
                    self.on_complete(task_result)
                except Exception as e:
                    logger.error(f"完了コールバックの実行中にエラーが発生しました: {e}")
            
            if self.status != TaskStatus.COMPLETED and self.on_error:
                try:
                    self.on_error(task_result)
                except Exception as e:
                    logger.error(f"エラーコールバックの実行中にエラーが発生しました: {e}")
            
            # 完了したらレジストリから削除
            if self.task_id in active_tasks:
                del active_tasks[self.task_id]
            
            return task_result
    
    def cancel(self) -> bool:
        """
        タスクをキャンセルする
        
        Returns:
            bool: キャンセルに成功したかどうか
        """
        if not self.task:
            return False
        
        if self.task.done():
            return False
        
        self.task.cancel()
        self.status = TaskStatus.CANCELLED
        return True


async def run_managed_task(
    coro: Coroutine[Any, Any, T],
    task_id: Optional[str] = None,
    timeout: Optional[float] = None,
    metadata: Optional[Dict[str, Any]] = None,
    on_complete: Optional[Callable[[TaskResult], None]] = None,
    on_error: Optional[Callable[[TaskResult], None]] = None
) -> TaskResult:
    """
    管理対象タスクとして実行する
    
    Args:
        coro: 実行するコルーチン
        task_id: タスクID（省略時は自動生成）
        timeout: タイムアウト時間（秒）
        metadata: タスクのメタデータ
        on_complete: 完了時コールバック
        on_error: エラー時コールバック
        
    Returns:
        TaskResult: タスク結果
    """
    managed_task = ManagedTask(
        coro=coro,
        task_id=task_id,
        timeout=timeout,
        metadata=metadata,
        on_complete=on_complete,
        on_error=on_error
    )
    
    return await managed_task.start()


def get_active_tasks() -> Dict[str, Dict[str, Any]]:
    """
    アクティブなタスクの情報を取得する
    
    Returns:
        Dict[str, Dict[str, Any]]: タスクID -> タスク情報の辞書
    """
    tasks_info = {}
    
    for task_id, task in active_tasks.items():
        # タスク情報を作成
        info = {
            "task_id": task_id,
            "status": task.status,
            "start_time": task.start_time.isoformat() if task.start_time else None,
            "metadata": task.metadata,
            "timeout": task.timeout,
            "running_time": (datetime.now() - task.start_time).total_seconds() if task.start_time else None
        }
        tasks_info[task_id] = info
    
    return tasks_info


def cancel_task(task_id: str) -> bool:
    """
    タスクをキャンセルする
    
    Args:
        task_id: キャンセルするタスクのID
        
    Returns:
        bool: キャンセルに成功したかどうか
    """
    if task_id not in active_tasks:
        return False
    
    return active_tasks[task_id].cancel()


def get_task_history(task_id: str) -> List[Dict[str, Any]]:
    """
    タスクの実行履歴を取得する
    
    Args:
        task_id: タスクID
        
    Returns:
        List[Dict[str, Any]]: タスクの実行履歴
    """
    return task_executions.get(task_id, [])


async def run_with_retry(
    coro_factory: Callable[[], Coroutine[Any, Any, T]],
    max_attempts: int = 3,
    retry_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retry_exceptions: Union[List[Exception], Tuple[Exception, ...]] = (Exception,),
    task_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> T:
    """
    リトライ付きでコルーチンを実行する
    
    Args:
        coro_factory: コルーチンを生成する関数
        max_attempts: 最大試行回数
        retry_delay: 初回リトライまでの遅延時間（秒）
        backoff_factor: バックオフ係数
        retry_exceptions: リトライ対象の例外クラス
        task_id: タスクID
        metadata: タスクのメタデータ
        
    Returns:
        T: コルーチンの結果
        
    Raises:
        Exception: 最大試行回数を超えた場合
    """
    metadata = metadata or {}
    retry_metadata = metadata.setdefault("retry", {})
    retry_metadata["max_attempts"] = max_attempts
    
    attempt = 0
    current_delay = retry_delay
    last_exception = None
    
    while attempt < max_attempts:
        attempt += 1
        retry_metadata["current_attempt"] = attempt
        
        try:
            # 新しいコルーチンを生成して実行
            return await coro_factory()
            
        except retry_exceptions as e:
            last_exception = e
            
            # 最後の試行の場合は例外を再発生
            if attempt >= max_attempts:
                logger.error(f"最大試行回数({max_attempts})に到達しました: {e}")
                break
                
            # 次の試行までの遅延時間を計算
            retry_metadata["next_delay"] = current_delay
            logger.warning(f"試行 {attempt}/{max_attempts} が失敗しました: {e}. {current_delay}秒後に再試行します。")
            
            await asyncio.sleep(current_delay)
            current_delay *= backoff_factor
    
    if last_exception:
        raise last_exception
    
    # ここには到達しないはず
    raise RuntimeError("予期しないエラーが発生しました")


def get_throttle_semaphore(key: str, limit: int) -> asyncio.Semaphore:
    """
    スロットリング用のセマフォを取得する
    
    Args:
        key: セマフォのキー
        limit: 同時実行数の上限
        
    Returns:
        asyncio.Semaphore: セマフォオブジェクト
    """
    if key not in _throttle_semaphores:
        _throttle_semaphores[key] = asyncio.Semaphore(limit)
    return _throttle_semaphores[key]


async def run_throttled(
    coro: Coroutine[Any, Any, T],
    throttle_key: str,
    limit: int,
    timeout: Optional[float] = None
) -> T:
    """
    スロットリング付きでコルーチンを実行する
    
    Args:
        coro: 実行するコルーチン
        throttle_key: スロットリングキー
        limit: 同時実行数の上限
        timeout: タイムアウト時間（秒）
        
    Returns:
        T: コルーチンの結果
    """
    semaphore = get_throttle_semaphore(throttle_key, limit)
    
    async with semaphore:
        if timeout:
            return await asyncio.wait_for(coro, timeout=timeout)
        else:
            return await coro


class BackgroundTaskManager:
    """
    バックグラウンドタスク管理クラス
    
    非同期タスクをバックグラウンドで実行・管理するためのクラスです。
    インスタンスは通常、アプリケーション起動時に一つだけ作成し、
    アプリケーション全体で共有して使用します。
    """
    
    def __init__(self, max_workers: int = 10):
        """
        コンストラクタ
        
        Args:
            max_workers: スレッドプールの最大ワーカー数
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.loop = asyncio.get_event_loop()
        self.tasks: Dict[str, asyncio.Future] = {}
        self.results: Dict[str, Any] = {}
        self.running = True
    
    def start_task(
        self,
        coro_factory: Callable[[], Coroutine],
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        バックグラウンドタスクとして実行する
        
        Args:
            coro_factory: コルーチンを生成する関数
            task_id: タスクID（省略時は自動生成）
            metadata: タスクのメタデータ
            
        Returns:
            str: タスクID
        """
        task_id = task_id or f"bg-{uuid.uuid4()}"
        metadata = metadata or {}
        
        # バックグラウンド実行関数
        async def run_in_background():
            try:
                # コルーチンを生成して実行
                coro = coro_factory()
                result = await coro
                self.results[task_id] = {
                    "status": "completed",
                    "result": result,
                    "metadata": metadata,
                    "completed_at": datetime.now().isoformat()
                }
                return result
            except Exception as e:
                logger.error(f"バックグラウンドタスク {task_id} の実行中にエラーが発生しました: {e}")
                self.results[task_id] = {
                    "status": "failed",
                    "error": str(e),
                    "metadata": metadata,
                    "completed_at": datetime.now().isoformat()
                }
                raise
        
        # 非同期タスクを作成し、タスクレジストリに登録
        task = asyncio.run_coroutine_threadsafe(run_in_background(), self.loop)
        self.tasks[task_id] = task
        
        return task_id
    
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        タスクの結果を取得する
        
        Args:
            task_id: タスクID
            
        Returns:
            Optional[Dict[str, Any]]: タスク結果（存在しない場合はNone）
        """
        return self.results.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """
        タスクをキャンセルする
        
        Args:
            task_id: タスクID
            
        Returns:
            bool: キャンセルに成功したかどうか
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        if task.done():
            return False
        
        task.cancel()
        self.results[task_id] = {
            "status": "cancelled",
            "cancelled_at": datetime.now().isoformat()
        }
        return True
    
    def shutdown(self, wait: bool = True):
        """
        タスク管理をシャットダウンする
        
        Args:
            wait: 実行中のタスクの完了を待つかどうか
        """
        self.running = False
        self.executor.shutdown(wait=wait)
    
    def get_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        アクティブなタスクの情報を取得する
        
        Returns:
            Dict[str, Dict[str, Any]]: タスクID -> タスク情報の辞書
        """
        tasks_info = {}
        
        for task_id, task in self.tasks.items():
            # タスクがまだ実行中の場合のみ含める
            if not task.done():
                tasks_info[task_id] = {
                    "task_id": task_id,
                    "status": "running",
                    "metadata": self.results.get(task_id, {}).get("metadata", {})
                }
        
        return tasks_info


# シングルトンバックグラウンドタスクマネージャー
_background_task_manager: Optional[BackgroundTaskManager] = None


def get_background_task_manager() -> BackgroundTaskManager:
    """
    バックグラウンドタスクマネージャーのシングルトンインスタンスを取得する
    
    Returns:
        BackgroundTaskManager: バックグラウンドタスクマネージャー
    """
    global _background_task_manager
    if _background_task_manager is None:
        _background_task_manager = BackgroundTaskManager()
    return _background_task_manager


def cleanup_async_resources():
    """
    非同期リソースをクリーンアップする
    
    アプリケーション終了時に呼び出すことで、各種リソースを確実に解放します。
    """
    global _background_task_manager
    
    # バックグラウンドタスクマネージャーのシャットダウン
    if _background_task_manager is not None:
        _background_task_manager.shutdown(wait=True)
        _background_task_manager = None
    
    # その他のクリーンアップ処理
    _throttle_semaphores.clear()
    active_tasks.clear()
    task_executions.clear() 