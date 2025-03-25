# リアルタイム通知システム - フロントエンド実装ガイド

## 概要
このドキュメントでは、フロントエンドで監査エージェントシステムのリアルタイム通知を実装するためのガイドラインを提供します。システムはWebSocketを使用して、ワークフロー、タスク、エージェントの状態変化などをリアルタイムで通知します。

## 通知システムの特徴
- **WebSocketベース**: 双方向通信による低レイテンシーな更新
- **トピックベースの購読**: 必要な情報のみを選択的に購読
- **フォールバックメカニズム**: WebSocketが利用できない環境向けのポーリングオプション
- **自動再接続**: 接続が切断された場合の自動復帰機能

## 実装方法

### 1. WebSocket接続の確立

```typescript
// useWebSocket.ts - WebSocketを管理するReactフック
import { useState, useEffect, useCallback, useRef } from 'react';

interface WebSocketOptions {
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
}

export const useWebSocket = (
  url: string, 
  userId: string,
  options: WebSocketOptions = {}
) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const [error, setError] = useState<Error | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const { 
    reconnectInterval = 3000, 
    maxReconnectAttempts = 10,
    onOpen,
    onClose,
    onError
  } = options;

  // メッセージ送信関数
  const sendMessage = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(typeof data === 'string' ? data : JSON.stringify(data));
      return true;
    }
    return false;
  }, []);

  // トピック購読関数
  const subscribeTopic = useCallback((topic: string) => {
    return sendMessage({
      command: 'subscribe',
      topic
    });
  }, [sendMessage]);

  // トピック購読解除関数
  const unsubscribeTopic = useCallback((topic: string) => {
    return sendMessage({
      command: 'unsubscribe',
      topic
    });
  }, [sendMessage]);

  // 接続関数
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    // 既存の接続を閉じる
    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      // WebSocketのURL末尾にユーザーIDを付加
      const fullUrl = `${url}/${userId}`;
      const ws = new WebSocket(fullUrl);

      ws.onopen = (event) => {
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        if (onOpen) onOpen(event);
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        if (onClose) onClose(event);
        
        // 自動再接続
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectIntervalRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1;
            connect();
          }, reconnectInterval);
        } else {
          setError(new Error('Maximum reconnect attempts reached'));
        }
      };

      ws.onerror = (event) => {
        setError(new Error('WebSocket connection error'));
        if (onError) onError(event);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
        } catch (e) {
          console.error('Failed to parse WebSocket message', e);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      setError(error instanceof Error ? error : new Error('Failed to connect'));
    }
  }, [url, userId, onOpen, onClose, onError, maxReconnectAttempts, reconnectInterval]);

  // 切断関数
  const disconnect = useCallback(() => {
    if (reconnectIntervalRef.current) {
      clearTimeout(reconnectIntervalRef.current);
      reconnectIntervalRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
  }, []);

  // コンポーネントマウント時に接続を確立
  useEffect(() => {
    connect();
    
    // クリーンアップ関数
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    error,
    sendMessage,
    subscribeTopic,
    unsubscribeTopic,
    connect,
    disconnect
  };
};
```

### 2. 通知管理コンポーネントの実装

```typescript
// NotificationProvider.tsx - 通知を管理するContextProvider
import React, { createContext, useContext, useState, useEffect } from 'react';
import { useWebSocket } from './useWebSocket';

interface Notification {
  id: string;
  type: string;
  title: string;
  content: any;
  severity: 'info' | 'warning' | 'error' | 'critical';
  timestamp: string;
  topic: string;
  read: boolean;
}

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  subscribeTopic: (topic: string) => boolean;
  unsubscribeTopic: (topic: string) => boolean;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  clear: () => void;
  isConnected: boolean;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

interface NotificationProviderProps {
  children: React.ReactNode;
  userId: string;
  baseUrl?: string;
  maxNotifications?: number;
}

export const NotificationProvider: React.FC<NotificationProviderProps> = ({
  children,
  userId,
  baseUrl = window.location.origin.replace('http', 'ws'),
  maxNotifications = 100
}) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const wsUrl = `${baseUrl}/api/v1/notifications/ws`;
  
  const { 
    isConnected, 
    lastMessage, 
    subscribeTopic, 
    unsubscribeTopic 
  } = useWebSocket(wsUrl, userId);

  // 通知の追加
  useEffect(() => {
    if (lastMessage && lastMessage.topic) {
      const newNotification: Notification = {
        id: `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        type: lastMessage.type || 'generic',
        title: lastMessage.title || 'New Notification',
        content: lastMessage.content || {},
        severity: lastMessage.severity || 'info',
        timestamp: lastMessage.timestamp || new Date().toISOString(),
        topic: lastMessage.topic,
        read: false
      };

      setNotifications(prev => {
        const updated = [newNotification, ...prev];
        // 最大数を超えた場合、古い通知を削除
        return updated.slice(0, maxNotifications);
      });
    }
  }, [lastMessage, maxNotifications]);

  // 通知を既読にする
  const markAsRead = (id: string) => {
    setNotifications(prev => 
      prev.map(notification => 
        notification.id === id ? { ...notification, read: true } : notification
      )
    );
  };

  // すべての通知を既読にする
  const markAllAsRead = () => {
    setNotifications(prev => 
      prev.map(notification => ({ ...notification, read: true }))
    );
  };

  // 通知をクリアする
  const clear = () => {
    setNotifications([]);
  };

  // 未読通知数を計算
  const unreadCount = notifications.filter(n => !n.read).length;

  const value = {
    notifications,
    unreadCount,
    subscribeTopic,
    unsubscribeTopic,
    markAsRead,
    markAllAsRead,
    clear,
    isConnected
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
};
```

### 3. コンポーネントでの使用例

```typescript
// App.tsx - アプリケーションのルートコンポーネント
import React from 'react';
import { NotificationProvider } from './NotificationProvider';
import MainLayout from './layouts/MainLayout';

const App: React.FC = () => {
  // 認証済みユーザーのIDを取得
  const userId = useAuth().user?.id || 'anonymous';

  return (
    <NotificationProvider userId={userId}>
      <MainLayout />
    </NotificationProvider>
  );
};
```

```typescript
// NotificationBell.tsx - 通知ベルアイコンコンポーネント
import React, { useEffect } from 'react';
import { useNotifications } from './NotificationProvider';
import { Badge, IconButton, Popover } from '@mui/material';
import NotificationsIcon from '@mui/icons-material/Notifications';
import NotificationList from './NotificationList';

const NotificationBell: React.FC = () => {
  const { 
    unreadCount, 
    subscribeTopic, 
    unsubscribeTopic, 
    isConnected 
  } = useNotifications();
  const [anchorEl, setAnchorEl] = React.useState<HTMLButtonElement | null>(null);

  // 必要なトピックを購読
  useEffect(() => {
    if (isConnected) {
      // エージェント関連の通知を購読
      subscribeTopic('agent_status_changed');
      
      // タスク関連の通知を購読
      subscribeTopic('task_completed');
      subscribeTopic('task_failed');
      
      // ワークフロー関連の通知を購読
      subscribeTopic('workflow_completed');
      subscribeTopic('workflow_failed');
      
      // システム通知を購読
      subscribeTopic('system_alert');
      subscribeTopic('error_occurred');
    }
    
    return () => {
      // コンポーネントのアンマウント時に購読解除
      if (isConnected) {
        unsubscribeTopic('agent_status_changed');
        unsubscribeTopic('task_completed');
        unsubscribeTopic('task_failed');
        unsubscribeTopic('workflow_completed');
        unsubscribeTopic('workflow_failed');
        unsubscribeTopic('system_alert');
        unsubscribeTopic('error_occurred');
      }
    };
  }, [isConnected, subscribeTopic, unsubscribeTopic]);

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const open = Boolean(anchorEl);

  return (
    <>
      <IconButton 
        color="inherit" 
        onClick={handleClick}
        aria-label={`${unreadCount} 件の未読通知`}
      >
        <Badge badgeContent={unreadCount} color="error">
          <NotificationsIcon />
        </Badge>
      </IconButton>
      
      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        <NotificationList onClose={handleClose} />
      </Popover>
    </>
  );
};

export default NotificationBell;
```

## 利用可能な通知トピック

システムでは以下の通知トピックが利用可能です：

### エージェント関連の通知
- `agent_status_changed` - エージェントのステータスが変更された
- `agent_registered` - 新しいエージェントが登録された
- `agent_unregistered` - エージェントが登録解除された

### タスク関連の通知
- `task_created` - 新しいタスクが作成された
- `task_assigned` - タスクがエージェントに割り当てられた
- `task_started` - タスクが開始された
- `task_completed` - タスクが完了した
- `task_failed` - タスクが失敗した

### ワークフロー関連の通知
- `workflow_created` - 新しいワークフローが作成された
- `workflow_started` - ワークフローが開始された
- `workflow_completed` - ワークフローが完了した
- `workflow_failed` - ワークフローが失敗した
- `workflow_status_changed` - ワークフローのステータスが変更された
- `workflow_deleted` - ワークフローが削除された

### その他の通知
- `system_alert` - システムアラート
- `error_occurred` - エラーが発生した
- `user_interaction_required` - ユーザーの介入が必要

## 通知メッセージ形式

WebSocketから受信する通知メッセージは以下の形式です：

```typescript
interface NotificationMessage {
  // メッセージのタイプ（event, alert, info など）
  type: string;
  
  // 通知のタイトル
  title: string;
  
  // 通知の内容（オブジェクト）
  content: {
    // トピックによって異なるプロパティ
    [key: string]: any;
  };
  
  // 重要度（info, warning, error, critical）
  severity: string;
  
  // トピック名
  topic: string;
  
  // タイムスタンプ（ISO 8601形式）
  timestamp: string;
}
```

## フォールバックメカニズム

WebSocketが利用できない環境では、以下のようなポーリングベースのフォールバックメカニズムを実装できます：

```typescript
// useNotificationPolling.ts
import { useState, useEffect, useRef } from 'react';

export const useNotificationPolling = (
  userId: string,
  baseUrl: string = window.location.origin,
  interval: number = 10000 // 10秒ごとにポーリング
) => {
  const [lastChecked, setLastChecked] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<any[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const fetchNotifications = async () => {
    try {
      const params = new URLSearchParams();
      if (lastChecked) {
        params.append('since', lastChecked);
      }
      
      const response = await fetch(
        `${baseUrl}/api/v1/notifications/poll?${params.toString()}`,
        {
          headers: {
            'Authorization': `Bearer ${getAuthToken()}`, // 認証トークンを取得する関数
          }
        }
      );
      
      if (response.ok) {
        const data = await response.json();
        if (data.notifications && data.notifications.length > 0) {
          setNotifications(prev => [...data.notifications, ...prev]);
          setLastChecked(new Date().toISOString());
        }
      }
    } catch (error) {
      console.error('Failed to poll notifications', error);
    }
  };

  useEffect(() => {
    // 初回読み込み
    fetchNotifications();
    
    // ポーリング開始
    timerRef.current = setInterval(fetchNotifications, interval);
    
    return () => {
      // クリーンアップ
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [interval]);

  return {
    notifications,
    refetch: fetchNotifications
  };
};
```

## 注意事項

1. **接続管理**: WebSocket接続は可能な限り長く保持するように実装してください。接続が切断された場合は自動的に再接続を試みます。

2. **エラーハンドリング**: 通信エラーが発生した場合は、適切なフォールバックを提供し、エラーメッセージをユーザーに表示してください。

3. **認証**: WebSocket接続のURLにユーザーIDを含めることで認証を行います。セキュリティ要件が高い場合は、JWTなどのトークンをクエリパラメータや認証ヘッダーとして追加してください。

4. **メモリ管理**: 通知履歴は適切に制限し、古い通知はメモリから削除するようにしてください。

5. **ネットワーク帯域**: 大量のイベントが発生する場合、すべてのトピックを購読すると多くの通知が送信される可能性があります。必要なトピックのみを選択的に購読することをお勧めします。 