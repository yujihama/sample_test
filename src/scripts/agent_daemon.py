"""
エージェントデーモン

このスクリプトは、エージェントをバックグラウンドで実行し、
メッセージキューを継続的にポーリングして処理するためのデーモンプロセスを提供します。
"""

import asyncio
import uuid
import signal
import sys
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
import multiprocessing
from threading import Thread

# ログの設定
from loguru import logger
from src.utils.logger import setup_logger
logger = setup_logger("agent_daemon")

# エージェントと設定のインポート
from src.core.config import settings
from src.agents.agent_a import AgentA
from src.agents.agent_b import AgentB
from src.agents.agent_c import AgentC
from src.agents.agent_d import AgentD
from src.core.messaging import MessageBroker, MessageClient
from src.core.agent_base import AgentBase


class AgentWorker(Thread):
    """
    エージェントをバックグラウンドで実行するワーカースレッド
    
    このクラスは指定されたエージェントを継続的に実行し、
    メッセージキューをポーリングして処理します。
    """
    
    def __init__(
        self, 
        agent: AgentBase, 
        polling_interval: float = 1.0,
        is_daemon: bool = True
    ):
        """
        Args:
            agent: 実行するエージェントのインスタンス
            polling_interval: メッセージポーリングの間隔（秒）
            is_daemon: デーモンスレッドとして実行するかどうか
        """
        Thread.__init__(self)
        self.daemon = is_daemon
        self.agent = agent
        self.polling_interval = polling_interval
        self.running = False
        self.stop_event = asyncio.Event()
        
        # 非同期実行のためのイベントループ
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        logger.info(f"AgentWorker initialized for {self.agent.agent_id}")
    
    async def _run_async(self):
        """非同期実行のメインループ"""
        self.running = True
        logger.info(f"Starting agent worker for {self.agent.agent_id}")
        
        try:
            while self.running and not self.stop_event.is_set():
                try:
                    # メッセージをポーリングして処理
                    messages = await self.agent.get_and_process_messages()
                    
                    if messages:
                        logger.info(f"Agent {self.agent.agent_id} processed {len(messages)} messages")
                    
                    # 次のポーリングまで待機
                    await asyncio.sleep(self.polling_interval)
                    
                except Exception as e:
                    logger.error(f"Error in agent worker for {self.agent.agent_id}: {e}")
                    # エラー発生時も継続実行
                    await asyncio.sleep(self.polling_interval * 2)  # エラー時は間隔を長めに
        
        except asyncio.CancelledError:
            logger.info(f"Agent worker for {self.agent.agent_id} was cancelled")
        
        finally:
            self.running = False
            logger.info(f"Agent worker for {self.agent.agent_id} stopped")
    
    def run(self):
        """スレッドのメインメソッド"""
        try:
            self.loop.run_until_complete(self._run_async())
        except Exception as e:
            logger.error(f"Error in agent worker thread for {self.agent.agent_id}: {e}")
        finally:
            self.loop.close()
    
    def stop(self):
        """ワーカーを停止する"""
        self.running = False
        
        # 停止イベントを設定
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.stop_event.set)
        
        logger.info(f"Stopping agent worker for {self.agent.agent_id}")


class AgentDaemon:
    """
    複数のエージェントワーカーを管理するデーモン
    
    このクラスは複数のエージェントワーカーを起動し、管理します。
    シグナルハンドリングや優雅な終了処理も実装しています。
    """
    
    def __init__(self):
        """初期化"""
        # 共通のメッセージブローカー
        self.broker = MessageBroker()
        
        # 各エージェントのインスタンス
        self.agents = {
            settings.AGENT_A_ID: AgentA(),
            settings.AGENT_B_ID: AgentB(),
            settings.AGENT_C_ID: AgentC(),
            settings.AGENT_D_ID: AgentD(),
        }
        
        # エージェントワーカー
        self.workers: Dict[str, AgentWorker] = {}
        
        # シグナルハンドラの設定
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        
        logger.info("AgentDaemon initialized")
    
    def start(self):
        """すべてのエージェントワーカーを開始"""
        logger.info("Starting all agent workers")
        
        for agent_id, agent in self.agents.items():
            # ワーカーの作成と開始
            worker = AgentWorker(agent, polling_interval=1.0, is_daemon=True)
            worker.start()
            self.workers[agent_id] = worker
            
            logger.info(f"Started worker for {agent_id}")
        
        logger.info("All agent workers started")
    
    def stop(self):
        """すべてのエージェントワーカーを停止"""
        logger.info("Stopping all agent workers")
        
        for agent_id, worker in self.workers.items():
            worker.stop()
            logger.info(f"Stopped worker for {agent_id}")
        
        # 全ワーカーのスレッドが停止するまで待機
        for agent_id, worker in self.workers.items():
            if worker.is_alive():
                worker.join(timeout=5.0)
                if worker.is_alive():
                    logger.warning(f"Worker for {agent_id} did not stop gracefully")
        
        logger.info("All agent workers stopped")
    
    def _handle_signal(self, sig, frame):
        """シグナルハンドラ"""
        logger.info(f"Received signal {sig}, shutting down")
        self.stop()
        sys.exit(0)
    
    def run(self):
        """デーモンを実行"""
        try:
            self.start()
            
            # メインスレッドを終了せずに実行し続ける
            logger.info("Agent daemon running. Press Ctrl+C to stop.")
            
            # 無限ループでバックグラウンド実行
            while True:
                try:
                    # スレッドが終了していないか確認
                    for agent_id, worker in list(self.workers.items()):
                        if not worker.is_alive():
                            logger.warning(f"Worker for {agent_id} died unexpectedly, restarting")
                            
                            # ワーカーを再起動
                            worker = AgentWorker(self.agents[agent_id], polling_interval=1.0, is_daemon=True)
                            worker.start()
                            self.workers[agent_id] = worker
                    
                    # 定期的な健全性チェック
                    # TODO: エージェントの健全性をモニタリングする機能を追加
                    
                    # メインループを継続
                    asyncio.sleep(10)
                
                except Exception as e:
                    logger.error(f"Error in agent daemon main loop: {e}")
        
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down")
        
        finally:
            self.stop()


if __name__ == "__main__":
    """エージェントデーモンをスタンドアロンプロセスとして実行"""
    daemon = AgentDaemon()
    daemon.run() 