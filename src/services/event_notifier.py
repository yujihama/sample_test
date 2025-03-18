"""
イベント通知システム

このモジュールは、グラフ状態変更の通知を管理するシステムを提供します。
以下の機能を含みます：
- Webhook登録と通知
- Server-Sent Events (SSE)サポート
- イベント永続化メカニズム
"""

import asyncio
import uuid
import json
from src.utils import json_utils
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Tuple
import aiohttp
from fastapi import Request
from sse_starlette.sse import EventSourceResponse
from loguru import logger

# 注: 必要に応じてインポート調整
# from src.utils.db_manager import get_db_session
# from src.repositories.event_repository import EventRepository


class EventNotifier:
    """イベント通知を管理するサービス"""
    
    def __init__(self):
        """EventNotifierの初期化"""
        # Webhook登録情報 {(event_type, workflow_id?): [callback_urls]}
        self.webhooks: Dict[Tuple[str, Optional[str]], List[Dict[str, Any]]] = {}
        
        # SSEクライアント {client_id: queue}
        self.sse_clients: Dict[str, asyncio.Queue] = {}
        
        # イベント履歴（メモリキャッシュ）
        self.events_cache: List[Dict[str, Any]] = []
        
        # リポジトリの初期化
        # self.event_repository = EventRepository(get_db_session())
        
        logger.info("EventNotifierが初期化されました")
    
    async def register_webhook(
        self, 
        event_type: str, 
        callback_url: str, 
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Webhookを登録
        
        Args:
            event_type: 購読するイベントタイプ
            callback_url: 通知先URL
            workflow_id: 特定のワークフローに限定する場合のID（オプション）
            
        Returns:
            webhook_id: 登録されたWebhookのID
        """
        key = (event_type, workflow_id)
        webhook_id = f"wh-{uuid.uuid4().hex[:8]}"
        
        if key not in self.webhooks:
            self.webhooks[key] = []
            
        webhook_data = {
            "webhook_id": webhook_id,
            "callback_url": callback_url,
            "created_at": datetime.now().isoformat()
        }
        
        self.webhooks[key].append(webhook_data)
        
        logger.info(f"Webhookを登録しました: {event_type} ({workflow_id or 'all'}) -> {callback_url}")
        return {"success": True, "webhook_id": webhook_id}
    
    async def unregister_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Webhookの登録を解除
        
        Args:
            webhook_id: 解除するWebhookのID
            
        Returns:
            success: 操作結果
        """
        # 全てのキーで検索
        for key in self.webhooks:
            self.webhooks[key] = [wh for wh in self.webhooks[key] if wh["webhook_id"] != webhook_id]
            
        logger.info(f"Webhookの登録を解除しました: {webhook_id}")
        return {"success": True}
    
    async def notify_subscribers(
        self, 
        workflow_id: str, 
        event_type: str, 
        payload: Dict[str, Any]
    ) -> str:
        """
        登録済みの購読者に通知
        
        Args:
            workflow_id: ワークフローID
            event_type: イベントタイプ
            payload: イベントデータ
            
        Returns:
            event_id: 生成されたイベントID
        """
        # イベントデータの作成
        event_id = f"evt-{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now().isoformat()
        
        event = {
            "event_id": event_id,
            "workflow_id": workflow_id,
            "event_type": event_type,
            "payload": payload,
            "timestamp": timestamp
        }
        
        # イベントを永続化
        await self.save_event(event)
        
        # Webhook通知（グローバルと特定ワークフロー両方）
        await self._notify_webhooks(event)
        
        # SSE通知
        await self._notify_sse_clients(event)
        
        logger.info(f"イベント通知を送信しました: {event_type} - {workflow_id}")
        return event_id
    
    async def register_sse_client(self, client_id: str) -> Dict[str, Any]:
        """
        SSEクライアントを登録
        
        Args:
            client_id: クライアントID
            
        Returns:
            success: 操作結果
        """
        self.sse_clients[client_id] = asyncio.Queue()
        logger.info(f"SSEクライアントを登録しました: {client_id}")
        return {"success": True}
    
    async def unregister_sse_client(self, client_id: str) -> Dict[str, Any]:
        """
        SSEクライアントの登録を解除
        
        Args:
            client_id: クライアントID
            
        Returns:
            success: 操作結果
        """
        if client_id in self.sse_clients:
            del self.sse_clients[client_id]
            logger.info(f"SSEクライアントの登録を解除しました: {client_id}")
        return {"success": True}
    
    async def subscribe_to_events(self, request: Request, client_id: Optional[str] = None) -> EventSourceResponse:
        """
        イベントストリームを提供（FastAPIエンドポイント用）
        
        Args:
            request: FastAPIリクエスト
            client_id: カスタムクライアントID（省略可）
            
        Returns:
            EventSourceResponse: SSEレスポンス
        """
        if client_id is None:
            client_id = f"client-{uuid.uuid4().hex[:8]}"
            
        await self.register_sse_client(client_id)
        
        async def event_generator():
            try:
                # クライアントキューを取得
                queue = self.sse_clients[client_id]
                
                # 接続確立メッセージ
                yield {
                    "event": "connection_established",
                    "id": f"conn-{uuid.uuid4().hex[:8]}",
                    "data": json_utils.json_serialize({"client_id": client_id})
                }
                
                # イベントの待機とストリーミング
                while True:
                    if await request.is_disconnected():
                        break
                        
                    # キューからイベントを取得（非ブロッキング）
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=30.0)
                        
                        yield {
                            "event": event["event_type"],
                            "id": event["event_id"],
                            "data": json_utils.json_serialize(event)
                        }
                    except asyncio.TimeoutError:
                        # キープアライブ
                        yield {
                            "event": "ping",
                            "id": f"ping-{uuid.uuid4().hex[:8]}",
                            "data": json_utils.json_serialize({"timestamp": datetime.now().isoformat()})
                        }
            finally:
                # 切断時にクライアント登録解除
                await self.unregister_sse_client(client_id)
                
        return EventSourceResponse(event_generator())
    
    async def save_event(self, event: Dict[str, Any]) -> str:
        """
        イベントを永続化
        
        Args:
            event: 保存するイベント
            
        Returns:
            event_id: イベントID
        """
        # メモリキャッシュに追加（最新1000件のみ保持）
        self.events_cache.append(event)
        if len(self.events_cache) > 1000:
            self.events_cache = self.events_cache[-1000:]
            
        # データベースに保存（実際の実装では有効化）
        # await self.event_repository.save_event(event)
        
        return event["event_id"]
    
    async def get_events(
        self, 
        workflow_id: str, 
        event_type: Optional[str] = None, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        イベント履歴を取得
        
        Args:
            workflow_id: ワークフローID
            event_type: イベントタイプでフィルタリング（オプション）
            limit: 取得する最大件数
            
        Returns:
            イベントのリスト
        """
        # メモリキャッシュからフィルタリング
        filtered_events = [e for e in self.events_cache if e["workflow_id"] == workflow_id]
        
        if event_type:
            filtered_events = [e for e in filtered_events if e["event_type"] == event_type]
            
        # 最新順にソート
        filtered_events.sort(key=lambda e: e["timestamp"], reverse=True)
        
        # 制限
        return filtered_events[:limit]
    
    async def send_sse_event(self, client_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        特定のSSEクライアントにイベントを送信
        
        Args:
            client_id: クライアントID
            event: 送信するイベント
            
        Returns:
            success: 操作結果
        """
        if client_id in self.sse_clients:
            queue = self.sse_clients[client_id]
            await queue.put(event)
            return {"success": True}
        return {"success": False, "error": "クライアントが見つかりません"}
    
    async def _notify_webhooks(self, event: Dict[str, Any]) -> None:
        """
        Webhook登録者に通知
        
        Args:
            event: 通知するイベント
        """
        workflow_id = event["workflow_id"]
        event_type = event["event_type"]
        
        # 対象Webhookのリスト作成
        target_webhooks = []
        
        # グローバルWebhook
        global_key = (event_type, None)
        if global_key in self.webhooks:
            target_webhooks.extend(self.webhooks[global_key])
            
        # ワークフロー固有Webhook
        specific_key = (event_type, workflow_id)
        if specific_key in self.webhooks:
            target_webhooks.extend(self.webhooks[specific_key])
            
        # 通知を送信
        for webhook in target_webhooks:
            callback_url = webhook["callback_url"]
            asyncio.create_task(self._send_webhook_request(callback_url, event))
    
    async def _send_webhook_request(self, url: str, event: Dict[str, Any]) -> None:
        """
        HTTP POSTリクエストを送信
        
        Args:
            url: 送信先URL
            event: 送信するイベント
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=event, timeout=10.0) as response:
                    if response.status >= 400:
                        logger.warning(f"Webhook通知に失敗: {url} - ステータス {response.status}")
                    else:
                        logger.debug(f"Webhook通知を送信: {url}")
        except Exception as e:
            logger.error(f"Webhook通知エラー: {url} - {str(e)}")
    
    async def _notify_sse_clients(self, event: Dict[str, Any]) -> None:
        """
        全SSEクライアントに通知
        
        Args:
            event: 通知するイベント
        """
        for client_id, queue in self.sse_clients.items():
            try:
                await queue.put(event)
            except Exception as e:
                logger.error(f"SSE通知エラー: {client_id} - {str(e)}")


# シングルトンインスタンスを提供する関数
_event_notifier_instance = None

def get_event_notifier() -> EventNotifier:
    """EventNotifierのシングルトンインスタンスを取得"""
    global _event_notifier_instance
    if _event_notifier_instance is None:
        _event_notifier_instance = EventNotifier()
    return _event_notifier_instance 