"""
アプリケーション起動処理モジュール

このモジュールでは、アプリケーションの起動時に実行される処理を定義します。
データベース接続、キャッシュ初期化、非同期タスク管理、シャットダウン処理など
アプリケーション全体のライフサイクルに関わる機能を提供します。
"""

import os
import sys
import time
import atexit
import signal
import asyncio
from loguru import logger
from fastapi import FastAPI
from contextlib import asynccontextmanager
import traceback

from src.db.connection import init_db, close_db
from src.utils.logger import configure_logger
from src.utils.async_utils import get_background_task_manager, cleanup_async_resources
from src.events.event_bus import (
    get_event_bus, ApplicationStartedEvent, ApplicationShutdownEvent, 
    ErrorEvent, publish_event
)

# グローバル変数
app_state = {
    "initialized": False,
    "shutdown_requested": False,
    "start_time": time.time()
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPIアプリケーションのライフスパン管理
    
    Args:
        app: FastAPIアプリケーション
    """
    # アプリケーション起動時の処理
    await startup(app)
    
    try:
        # アプリケーションのメインライフサイクル
        yield
    finally:
        # アプリケーション終了時の処理
        await shutdown(app)


async def startup(app: FastAPI) -> None:
    """
    アプリケーション起動時の処理
    
    Args:
        app: FastAPIアプリケーション
    """
    if app_state["initialized"]:
        logger.warning("アプリケーションはすでに初期化されています")
        return
    
    logger.info("アプリケーションを起動しています...")
    app_state["start_time"] = time.time()
    
    # ロガーの設定
    configure_logger()
    
    try:
        # データベース接続の初期化
        await init_db()
        logger.info("データベース接続を初期化しました")
        
        # バックグラウンドタスクマネージャーの初期化
        task_manager = get_background_task_manager()
        logger.info("バックグラウンドタスクマネージャーを初期化しました")
        
        # イベントバスの初期化
        event_bus = get_event_bus()
        logger.info("イベントバスを初期化しました")
        
        # シャットダウンハンドラの登録
        register_shutdown_handlers()
        
        # 初期化完了フラグを設定
        app_state["initialized"] = True
        logger.info("アプリケーションの起動処理が完了しました")
        
        # アプリケーション起動イベントを発行
        env = os.environ.get("APP_ENV", "development")
        startup_event = ApplicationStartedEvent(
            startup_time=app_state["start_time"],
            environment=env
        )
        await publish_event(startup_event)
        
    except Exception as e:
        logger.error(f"アプリケーションの起動中にエラーが発生しました: {e}")
        
        # エラーイベントを発行
        try:
            error_event = ErrorEvent(
                error_type="StartupError",
                error_message=str(e),
                stacktrace=traceback.format_exc(),
                context={"phase": "startup"}
            )
            await publish_event(error_event, sync=True)
        except Exception:
            pass
            
        sys.exit(1)


async def shutdown(app: FastAPI) -> None:
    """
    アプリケーション終了時の処理
    
    Args:
        app: FastAPIアプリケーション
    """
    if app_state["shutdown_requested"]:
        logger.warning("シャットダウン処理は既に実行中です")
        return
    
    app_state["shutdown_requested"] = True
    logger.info("アプリケーションをシャットダウンしています...")
    
    try:
        # 起動からの経過時間を計算
        uptime = time.time() - app_state["start_time"]
        
        # アプリケーション終了イベントを発行
        shutdown_event = ApplicationShutdownEvent(
            uptime=uptime,
            shutdown_reason="normal"
        )
        await publish_event(shutdown_event, sync=True)
        
        # 非同期リソースのクリーンアップ
        cleanup_async_resources()
        logger.info("非同期リソースをクリーンアップしました")
        
        # データベース接続のクローズ
        await close_db()
        logger.info("データベース接続を閉じました")
        
        logger.info(f"アプリケーションのシャットダウンが完了しました（稼働時間: {uptime:.2f}秒）")
        
    except Exception as e:
        logger.error(f"アプリケーションのシャットダウン中にエラーが発生しました: {e}")
        
        # エラーイベントを発行
        try:
            error_event = ErrorEvent(
                error_type="ShutdownError",
                error_message=str(e),
                stacktrace=traceback.format_exc(),
                context={"phase": "shutdown"}
            )
            await publish_event(error_event, sync=True)
        except Exception:
            pass


def register_shutdown_handlers() -> None:
    """
    シャットダウンハンドラを登録する
    """
    # 終了時にクリーンアップ処理を実行するためのハンドラを登録
    atexit.register(lambda: asyncio.run(shutdown(None)))
    
    # シグナルハンドラを登録
    for sig in [signal.SIGINT, signal.SIGTERM]:
        try:
            signal.signal(sig, signal_handler)
        except (OSError, ValueError):
            # Windows環境ではSIGTERMが利用できない場合がある
            pass


def signal_handler(sig, frame) -> None:
    """
    シグナルハンドラ
    
    Args:
        sig: シグナル番号
        frame: 現在のスタックフレーム
    """
    logger.info(f"シグナルを受信しました: {sig}")
    # 非同期関数を実行するためにイベントループを取得
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # イベントループがない場合は新規作成
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # シャットダウン処理を実行
    loop.run_until_complete(shutdown(None))
    sys.exit(0) 