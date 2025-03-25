"""
イベント通知サービス

システム内のさまざまなイベントを通知するためのサービスを提供します。
"""

import logging
import asyncio
import json
import httpx
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
from enum import Enum

# ロガーのセットアップ
logger = logging.getLogger(__name__)

# イベントタイプの定義
class EventType(str, Enum):
    # エージェント関連
    AGENT_STATUS_CHANGED = "agent_status_changed"
    AGENT_REGISTERED = "agent_registered"
    AGENT_UNREGISTERED = "agent_unregistered"
    
    # タスク関連
    TASK_CREATED = "task_created"
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    
    # ワークフロー関連
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_STATUS_CHANGED = "workflow_status_changed"
    
    # その他
    SYSTEM_ALERT = "system_alert"
    ERROR_OCCURRED = "error_occurred"
    USER_INTERACTION_REQUIRED = "user_interaction_required"


# 通知の緊急度
class NotificationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationService:
    """通知サービスクラス"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        通知サービスの初期化
        
        Args:
            base_url: APIサーバーのベースURL
        """
        self.base_url = base_url
        self.notification_endpoint = f"{base_url}/api/v1/notifications/send"
        self.event_callbacks: Dict[str, List[Callable]] = {}
        self._http_client = None
    
    @property
    def http_client(self):
        """HTTPクライアントの取得（遅延初期化）"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=10.0)
        return self._http_client
    
    async def close(self):
        """リソースの解放"""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
    
    def register_callback(self, event_type: Union[EventType, str], callback: Callable):
        """
        特定のイベントタイプに対するコールバック関数を登録
        
        Args:
            event_type: イベントタイプ
            callback: コールバック関数（イベントデータを引数に取る）
        """
        event_key = event_type.value if isinstance(event_type, EventType) else event_type
        
        if event_key not in self.event_callbacks:
            self.event_callbacks[event_key] = []
        
        self.event_callbacks[event_key].append(callback)
        logger.debug(f"イベント '{event_key}' にコールバックを登録しました")
    
    def unregister_callback(self, event_type: Union[EventType, str], callback: Callable):
        """
        特定のイベントタイプからコールバック関数の登録を解除
        
        Args:
            event_type: イベントタイプ
            callback: 登録解除するコールバック関数
        """
        event_key = event_type.value if isinstance(event_type, EventType) else event_type
        
        if event_key in self.event_callbacks and callback in self.event_callbacks[event_key]:
            self.event_callbacks[event_key].remove(callback)
            logger.debug(f"イベント '{event_key}' からコールバックの登録を解除しました")
            
            # コールバックがなくなった場合はキーを削除
            if not self.event_callbacks[event_key]:
                del self.event_callbacks[event_key]
    
    async def notify(
        self, 
        event_type: Union[EventType, str], 
        title: str, 
        content: Dict[str, Any],
        severity: NotificationSeverity = NotificationSeverity.INFO
    ):
        """
        イベントを通知する
        
        Args:
            event_type: イベントタイプ
            title: 通知のタイトル
            content: 通知の内容（JSON可能なデータ）
            severity: 通知の緊急度
        
        Returns:
            通知の送信結果
        """
        event_key = event_type.value if isinstance(event_type, EventType) else event_type
        severity_val = severity.value if isinstance(severity, NotificationSeverity) else severity
        
        # コールバックの実行
        if event_key in self.event_callbacks:
            for callback in self.event_callbacks[event_key]:
                try:
                    callback({
                        "event_type": event_key,
                        "title": title,
                        "content": content,
                        "severity": severity_val,
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    logger.error(f"コールバック実行エラー (イベント: {event_key}): {str(e)}")
        
        # WebSocket通知の送信
        try:
            notification_data = {
                "topic": event_key,
                "message_type": "event",
                "title": title,
                "content": content,
                "severity": severity_val
            }
            
            # APIエンドポイントに通知を送信
            try:
                response = await self.http_client.post(
                    self.notification_endpoint,
                    json=notification_data,
                    timeout=5.0  # タイムアウトを短く設定
                )
                
                if response.status_code != 200:
                    logger.warning(f"通知送信エラー: ステータスコード {response.status_code}, レスポンス: {response.text}")
                    return {
                        "status": "error",
                        "message": f"Failed to send notification: {response.status_code}"
                    }
                
                return response.json()
            except httpx.ConnectError as e:
                logger.warning(f"通知サーバーに接続できません ({self.notification_endpoint}): {str(e)}")
                return {
                    "status": "error",
                    "message": "Notification server unreachable"
                }
            except httpx.TimeoutException as e:
                logger.warning(f"通知送信タイムアウト: {str(e)}")
                return {
                    "status": "error",
                    "message": "Notification timeout"
                }
        
        except Exception as e:
            import traceback
            logger.error(f"通知送信中にエラーが発生しました: {str(e)}")
            logger.debug(f"通知送信エラーの詳細: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"Error sending notification: {str(e)}"
            }
    
    # 便利なヘルパーメソッド
    async def notify_agent_status(self, agent_id: str, status: str, metadata: Dict[str, Any] = None):
        """エージェントのステータス変更を通知"""
        return await self.notify(
            EventType.AGENT_STATUS_CHANGED,
            f"エージェント {agent_id} のステータスが変更されました",
            {
                "agent_id": agent_id,
                "status": status,
                "metadata": metadata or {}
            }
        )
    
    async def notify_task_status(
        self, 
        task_id: str, 
        status: str, 
        agent_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ):
        """タスクのステータス変更を通知"""
        event_type = EventType.TASK_CREATED
        if status == "assigned":
            event_type = EventType.TASK_ASSIGNED
        elif status == "started":
            event_type = EventType.TASK_STARTED
        elif status == "completed":
            event_type = EventType.TASK_COMPLETED
        elif status == "failed":
            event_type = EventType.TASK_FAILED
        
        return await self.notify(
            event_type,
            f"タスク {task_id} の状態が '{status}' に変更されました",
            {
                "task_id": task_id,
                "status": status,
                "agent_id": agent_id,
                "workflow_id": workflow_id,
                "metadata": metadata or {}
            }
        )
    
    async def notify_workflow_status(
        self, 
        workflow_id: str, 
        status: str,
        metadata: Dict[str, Any] = None
    ):
        """ワークフローのステータス変更を通知"""
        event_type = EventType.WORKFLOW_STATUS_CHANGED
        
        if status == "created":
            event_type = EventType.WORKFLOW_CREATED
        elif status == "started" or status == "in_progress":
            event_type = EventType.WORKFLOW_STARTED
        elif status == "completed":
            event_type = EventType.WORKFLOW_COMPLETED
        elif status == "failed" or status == "error":
            event_type = EventType.WORKFLOW_FAILED
        
        severity = NotificationSeverity.INFO
        if status == "failed" or status == "error":
            severity = NotificationSeverity.ERROR
        
        return await self.notify(
            event_type,
            f"ワークフロー {workflow_id} の状態が '{status}' に変更されました",
            {
                "workflow_id": workflow_id,
                "status": status,
                "metadata": metadata or {}
            },
            severity=severity
        )
    
    async def notify_error(
        self, 
        error_message: str, 
        error_type: str = "general", 
        source: Optional[str] = None,
        details: Dict[str, Any] = None
    ):
        """エラーを通知"""
        return await self.notify(
            EventType.ERROR_OCCURRED,
            f"エラーが発生しました: {error_type}",
            {
                "message": error_message,
                "type": error_type,
                "source": source,
                "details": details or {}
            },
            severity=NotificationSeverity.ERROR
        )
    
    async def notify_system_alert(
        self, 
        title: str, 
        message: str, 
        severity: NotificationSeverity = NotificationSeverity.WARNING,
        details: Dict[str, Any] = None
    ):
        """システムアラートを通知"""
        return await self.notify(
            EventType.SYSTEM_ALERT,
            title,
            {
                "message": message,
                "details": details or {}
            },
            severity=severity
        )
    
    async def request_user_interaction(
        self,
        interaction_id: str,
        title: str,
        message: str,
        interaction_type: str = "confirmation",
        options: Optional[List[Dict[str, Any]]] = None,
        workflow_id: Optional[str] = None,
        task_id: Optional[str] = None
    ):
        """ユーザーの介入を要求する通知を送信"""
        return await self.notify(
            EventType.USER_INTERACTION_REQUIRED,
            title,
            {
                "interaction_id": interaction_id,
                "message": message,
                "interaction_type": interaction_type,
                "options": options or [],
                "workflow_id": workflow_id,
                "task_id": task_id
            },
            severity=NotificationSeverity.WARNING
        )


# グローバルなシングルトンインスタンス
_notification_service = None

def get_notification_service(base_url: str = None) -> NotificationService:
    """
    通知サービスのシングルトンインスタンスを取得
    
    Args:
        base_url: オプションでAPIサーバーのベースURLを指定
    
    Returns:
        NotificationServiceのインスタンス
    """
    global _notification_service
    
    # デフォルトのURLを設定
    default_url = base_url
    if default_url is None:
        from src.core.config import settings
        if hasattr(settings, 'APP_HOST') and hasattr(settings, 'APP_PORT'):
            default_url = f"http://{settings.APP_HOST}:{settings.APP_PORT}"
        else:
            default_url = "http://localhost:8000"
    
    if _notification_service is None:
        _notification_service = NotificationService(base_url=default_url)
    elif base_url is not None and base_url != _notification_service.base_url:
        # 異なるURLが指定された場合は新しいインスタンスを作成
        _notification_service = NotificationService(base_url=base_url)
        
    return _notification_service 