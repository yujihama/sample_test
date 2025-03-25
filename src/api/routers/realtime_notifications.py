"""
リアルタイム通知機能を提供するモジュール

WebSocketを利用してクライアントにリアルタイムで通知を送信する機能を提供します。
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, status
from pydantic import BaseModel

# ロガーのセットアップ
logger = logging.getLogger(__name__)

# ルーターの設定
router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    responses={404: {"description": "Not found"}},
)

# WebSocketコネクションマネージャー
class ConnectionManager:
    def __init__(self):
        # アクティブな接続を格納する辞書
        # キー: ユーザーID、値: WebSocketオブジェクトのリスト
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # 購読情報
        # キー: トピック名、値: {ユーザーID: WebSocketインデックスのリスト}
        self.subscriptions: Dict[str, Dict[str, List[int]]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket接続が確立されました: ユーザー {user_id}")
        return len(self.active_connections[user_id]) - 1  # 接続のインデックスを返す

    def disconnect(self, user_id: str, index: int):
        """指定されたユーザーの特定のWebSocket接続を切断する"""
        if user_id in self.active_connections and index < len(self.active_connections[user_id]):
            # 接続リストから削除
            self.active_connections[user_id].pop(index)
            
            # ユーザーの接続がなくなった場合は辞書からユーザーエントリも削除
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            
            # 購読情報からもこの接続を削除
            for topic in self.subscriptions:
                if user_id in self.subscriptions[topic]:
                    # インデックスが削除対象のものより大きいものは1つ減らす
                    self.subscriptions[topic][user_id] = [
                        i if i < index else i - 1 
                        for i in self.subscriptions[topic][user_id] 
                        if i != index
                    ]
                    # ユーザーの購読がなくなった場合はトピックからユーザーを削除
                    if not self.subscriptions[topic][user_id]:
                        del self.subscriptions[topic][user_id]
            
            logger.info(f"WebSocket接続が切断されました: ユーザー {user_id}, インデックス {index}")
        else:
            logger.warning(f"切断しようとした接続が見つかりません: ユーザー {user_id}, インデックス {index}")

    def subscribe(self, topic: str, user_id: str, connection_index: int):
        """特定のトピックにユーザーの接続を購読登録する"""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = {}
        
        if user_id not in self.subscriptions[topic]:
            self.subscriptions[topic][user_id] = []
        
        if connection_index not in self.subscriptions[topic][user_id]:
            self.subscriptions[topic][user_id].append(connection_index)
            logger.info(f"トピック '{topic}' に購読登録: ユーザー {user_id}, インデックス {connection_index}")
        else:
            logger.debug(f"既に購読済み: トピック '{topic}', ユーザー {user_id}, インデックス {connection_index}")

    def unsubscribe(self, topic: str, user_id: str, connection_index: int):
        """特定のトピックからユーザーの接続の購読を解除する"""
        if (topic in self.subscriptions and 
            user_id in self.subscriptions[topic] and 
            connection_index in self.subscriptions[topic][user_id]):
            
            self.subscriptions[topic][user_id].remove(connection_index)
            
            # ユーザーの購読がなくなった場合
            if not self.subscriptions[topic][user_id]:
                del self.subscriptions[topic][user_id]
                
            # トピックの購読者がいなくなった場合
            if not self.subscriptions[topic]:
                del self.subscriptions[topic]
                
            logger.info(f"トピック '{topic}' の購読解除: ユーザー {user_id}, インデックス {connection_index}")
        else:
            logger.warning(f"購読解除しようとしたエントリが見つかりません: トピック '{topic}', ユーザー {user_id}, インデックス {connection_index}")

    async def broadcast(self, topic: str, message: Dict[str, Any]):
        """特定のトピックを購読しているすべての接続にメッセージをブロードキャストする"""
        if topic not in self.subscriptions:
            logger.debug(f"トピック '{topic}' を購読しているユーザーはいません")
            return
        
        # メッセージにトピック情報とタイムスタンプを追加
        enriched_message = {
            **message,
            "topic": topic,
            "timestamp": datetime.now().isoformat()
        }
        
        # JSONに変換
        json_message = json.dumps(enriched_message)
        
        # 送信カウンタ
        send_count = 0
        error_count = 0
        
        # トピックを購読しているすべてのユーザーにメッセージを送信
        for user_id, indices in self.subscriptions[topic].items():
            if user_id in self.active_connections:
                for idx in indices:
                    if idx < len(self.active_connections[user_id]):
                        try:
                            await self.active_connections[user_id][idx].send_text(json_message)
                            send_count += 1
                        except Exception as e:
                            logger.error(f"メッセージ送信エラー: ユーザー {user_id}, インデックス {idx}: {str(e)}")
                            error_count += 1
                    else:
                        logger.warning(f"無効な接続インデックス: ユーザー {user_id}, インデックス {idx}")
            else:
                logger.warning(f"ユーザー {user_id} の接続が見つかりません")
        
        logger.info(f"トピック '{topic}' に {send_count} 件のメッセージを送信しました（エラー: {error_count}件）")


# グローバルなコネクションマネージャーのインスタンス
manager = ConnectionManager()


# モデル定義
class NotificationMessage(BaseModel):
    """通知メッセージ"""
    topic: str
    message_type: str
    title: str
    content: Dict[str, Any]
    severity: Optional[str] = "info"


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocketエンドポイント"""
    connection_index = await manager.connect(websocket, user_id)
    
    try:
        while True:
            # クライアントからのメッセージを待機
            data = await websocket.receive_text()
            
            try:
                # JSONデータをパース
                message = json.loads(data)
                
                # コマンドを処理
                if "command" in message:
                    if message["command"] == "subscribe" and "topic" in message:
                        manager.subscribe(message["topic"], user_id, connection_index)
                        await websocket.send_json({
                            "status": "subscribed",
                            "topic": message["topic"]
                        })
                    
                    elif message["command"] == "unsubscribe" and "topic" in message:
                        manager.unsubscribe(message["topic"], user_id, connection_index)
                        await websocket.send_json({
                            "status": "unsubscribed",
                            "topic": message["topic"]
                        })
                    
                    else:
                        await websocket.send_json({
                            "status": "error",
                            "message": "Unknown command or missing parameters"
                        })
                
                else:
                    await websocket.send_json({
                        "status": "error",
                        "message": "Invalid message format, command is required"
                    })
            
            except json.JSONDecodeError:
                await websocket.send_json({
                    "status": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"WebSocketメッセージ処理エラー: {str(e)}")
                await websocket.send_json({
                    "status": "error",
                    "message": f"Error processing message: {str(e)}"
                })
    
    except WebSocketDisconnect:
        manager.disconnect(user_id, connection_index)
    except Exception as e:
        logger.error(f"WebSocket接続エラー: {str(e)}")
        manager.disconnect(user_id, connection_index)


@router.post("/send")
async def send_notification(
    notification: NotificationMessage
):
    """
    特定のトピックを購読しているすべてのクライアントに通知を送信する
    """
    try:
        message_dict = {
            "type": notification.message_type,
            "title": notification.title,
            "content": notification.content,
            "severity": notification.severity
        }
        
        await manager.broadcast(notification.topic, message_dict)
        
        return {
            "status": "sent",
            "topic": notification.topic,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"通知送信エラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}"
        )


@router.get("/topics")
async def get_active_topics():
    """
    アクティブな通知トピックの一覧を取得する
    """
    topics = list(manager.subscriptions.keys())
    topic_info = {}
    
    for topic in topics:
        subscriber_count = sum(len(indices) for indices in manager.subscriptions[topic].values())
        topic_info[topic] = {
            "subscribers": subscriber_count,
            "user_count": len(manager.subscriptions[topic])
        }
    
    return {
        "topics": topic_info,
        "count": len(topics)
    } 