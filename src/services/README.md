# サービスレイヤーガイド

このディレクトリには内部監査AIエージェントシステムのビジネスロジックが含まれています。
サービスレイヤーはデータアクセスレイヤー（モデル）とプレゼンテーションレイヤー（API）の間に位置し、
アプリケーションの核となるロジックを実装します。

## サービスの概要

サービスレイヤーは以下の役割を担っています：

1. **監査サービス (`audit_service.py`)**
   - 監査ワークフローの作成・管理
   - 監査手続きの実行
   - 監査結果の集約

2. **エージェント管理サービス (`agent_service.py`)**
   - エージェントの初期化・管理
   - エージェント間通信の調整
   - エージェント状態の永続化

3. **ファイル管理サービス (`file_service.py`)**
   - ファイルのアップロード・ダウンロード
   - ファイル処理（変換・解析）
   - ファイルメタデータ管理

4. **ユーザー管理サービス (`user_service.py`)**
   - ユーザー認証・認可
   - ユーザープロファイル管理
   - セッション管理

5. **ツール管理サービス (`tool_service.py`)**
   - ツールの登録・管理
   - ツール設定の永続化
   - ツール実行の統計・ログ

6. **レポートサービス (`report_service.py`)**
   - 監査レポートの生成
   - データの集計・分析
   - レポートフォーマットの管理

## ファイル構成

```
services/
├── __init__.py             - パッケージ初期化
├── audit_service.py        - 監査サービス
├── agent_service.py        - エージェント管理サービス
├── file_service.py         - ファイル管理サービス
├── user_service.py         - ユーザー管理サービス
├── tool_service.py         - ツール管理サービス
├── report_service.py       - レポートサービス
├── auth.py                 - 認証関連ユーティリティ
├── cache.py                - キャッシュ管理
└── base_service.py         - サービス基底クラス
```

## 主要サービスの詳細

### 監査サービス

`audit_service.py` は監査ワークフローの中核となるロジックを実装します：

```python
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from src.models.repositories.audit_repository import AuditRepository
from src.models.audit_entities import AuditProcedure, AuditSample, AuditResult
from src.core.workflow import AuditWorkflow
import uuid
from datetime import datetime

class AuditService:
    """監査関連サービス"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repository = AuditRepository(db)
    
    async def create_workflow(self, workflow_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """新しい監査ワークフローを作成"""
        workflow_id = str(uuid.uuid4())
        
        # ワークフローの作成
        workflow = {
            "workflow_id": workflow_id,
            "procedure_id": workflow_data["procedure_id"],
            "sample_ids": workflow_data["sample_ids"],
            "status": "created",
            "created_at": datetime.now(),
            "created_by": user_id,
            "parameters": workflow_data.get("parameters")
        }
        
        # データベースに保存
        self.repository.create_workflow(workflow)
        
        return workflow
    
    async def start_workflow(self, workflow_id: str) -> bool:
        """監査ワークフローを開始"""
        # ワークフローの取得
        workflow_data = self.repository.get_workflow(workflow_id)
        if not workflow_data:
            return False
        
        # ワークフローインスタンスの作成
        workflow = AuditWorkflow(
            workflow_id=workflow_id,
            procedure_id=workflow_data["procedure_id"],
            sample_ids=workflow_data["sample_ids"]
        )
        
        # ワークフローの開始
        try:
            await workflow.start()
            # ステータスの更新
            self.repository.update_workflow_status(workflow_id, "running")
            return True
        except Exception as e:
            # エラーログ
            print(f"Error starting workflow: {e}")
            return False
    
    async def get_results(self, workflow_id: str) -> List[Dict[str, Any]]:
        """監査結果の取得"""
        return self.repository.get_results_by_workflow(workflow_id)
```

### エージェント管理サービス

`agent_service.py` はエージェントのライフサイクルと通信を管理します：

```python
from typing import Dict, Any, List, Optional
from src.core.messaging import MessageBroker
from src.models.agent_state import AgentState
from src.agents.agent_a import AgentA
from src.agents.agent_b import AgentB
from src.agents.agent_c import AgentC
from src.agents.agent_d import AgentD

class AgentService:
    """エージェント管理サービス"""
    
    def __init__(self):
        # エージェントマップの初期化
        self.agents = {
            "agent-a": AgentA(),
            "agent-b": AgentB(),
            "agent-c": AgentC(),
            "agent-d": AgentD()
        }
        self.message_broker = MessageBroker()
    
    async def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """エージェント情報の取得"""
        if agent_id not in self.agents:
            return None
        
        agent = self.agents[agent_id]
        return {
            "agent_id": agent_id,
            "description": agent.__class__.__doc__,
            "status": "active"
        }
    
    async def get_all_agents(self) -> List[Dict[str, Any]]:
        """すべてのエージェント情報を取得"""
        return [
            {
                "agent_id": agent_id,
                "description": agent.__class__.__doc__,
                "status": "active"
            }
            for agent_id, agent in self.agents.items()
        ]
    
    async def send_message(self, agent_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """エージェントにメッセージを送信"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        agent = self.agents[agent_id]
        response = await agent.process_message(message)
        return response
    
    async def get_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """エージェントの状態を取得"""
        if agent_id not in self.agents:
            return None
        
        agent = self.agents[agent_id]
        return agent.state.dict()
```

### ツール管理サービス

`tool_service.py` はツールの登録・設定・実行を管理します：

```python
from typing import Dict, Any, List, Optional
from src.tools.tool_registry import ToolRegistry
import yaml
import os

class ToolService:
    """ツール管理サービス"""
    
    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "tools_config.yaml")
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """利用可能なすべてのツール情報を取得"""
        tools = self.tool_registry.get_tool_info()
        return tools
    
    def get_tool_info(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """特定のツール情報を取得"""
        tools = self.tool_registry.get_tool_info()
        for tool in tools:
            if tool["tool_id"] == tool_id:
                return tool
        return None
    
    def update_tool_config(self, tool_id: str, config: Dict[str, Any]) -> bool:
        """ツール設定を更新"""
        try:
            # 現在の設定を読み込み
            with open(self.config_path, "r") as f:
                current_config = yaml.safe_load(f)
            
            # ツールIDから基本ツール名を抽出（例: ImageProcessor_001 → ImageProcessor）
            tool_base_name = tool_id.split("_")[0]
            
            # 設定の更新
            if "tools" in current_config and tool_base_name in current_config["tools"]:
                # メタデータ設定の更新
                if "metadata" in config:
                    current_config["tools"][tool_base_name]["metadata"].update(config["metadata"])
                
                # 有効/無効設定の更新
                if "enabled" in config:
                    current_config["tools"][tool_base_name]["enabled"] = config["enabled"]
                
                # 設定の保存
                with open(self.config_path, "w") as f:
                    yaml.dump(current_config, f, default_flow_style=False)
                
                # ツールレジストリの再読み込み
                self.tool_registry.reload_config()
                return True
            
            return False
        except Exception as e:
            # エラーログ
            print(f"Error updating tool config: {e}")
            return False
```

## サービス間の連携

サービスは単一責任の原則に従い、必要に応じて他のサービスと連携します：

```python
# 監査サービスがエージェントサービスとツールサービスを使用する例
class AuditService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = AuditRepository(db)
        self.agent_service = AgentService()
        self.tool_service = ToolService()
    
    async def execute_workflow_step(self, workflow_id: str, step_data: Dict[str, Any]) -> Dict[str, Any]:
        """ワークフローステップの実行"""
        # エージェントへのメッセージ送信
        agent_id = step_data["agent_id"]
        message = step_data["message"]
        
        response = await self.agent_service.send_message(agent_id, message)
        
        # ツール情報の取得
        if "tool_id" in step_data:
            tool_info = self.tool_service.get_tool_info(step_data["tool_id"])
            # ツール情報をレスポンスに追加
            response["tool_info"] = tool_info
        
        return response
```

## サービスレイヤーの使用例

APIエンドポイントからサービスを使用する例：

```python
# routes/audit.py の例
@router.post("/workflows/{workflow_id}/start")
async def start_audit_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """監査ワークフローを開始"""
    audit_service = AuditService(db)
    result = await audit_service.start_workflow(workflow_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ワークフローの開始に失敗しました"
        )
    
    return {"status": "started", "workflow_id": workflow_id}
```

## トランザクション管理

サービスレイヤーはデータベーストランザクションを管理し、処理の整合性を保証します：

```python
def update_workflow_with_results(self, workflow_id: str, results: List[Dict[str, Any]]) -> bool:
    """ワークフローと結果を一貫して更新"""
    try:
        # トランザクション開始
        self.db.begin()
        
        # ワークフロー更新
        self.repository.update_workflow_status(workflow_id, "completed")
        
        # 結果の保存
        for result in results:
            self.repository.create_result(result)
        
        # トランザクションのコミット
        self.db.commit()
        return True
    except Exception as e:
        # エラー時はロールバック
        self.db.rollback()
        # エラーログ
        print(f"Error updating workflow with results: {e}")
        return False
```

## キャッシュ戦略

パフォーマンス向上のためのキャッシュ戦略を実装します：

```python
# cache.py
import functools
import asyncio
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar

T = TypeVar('T')

cache = {}  # シンプルなインメモリキャッシュ

def cached(ttl_seconds: int = 300):
    """関数の結果をキャッシュするデコレータ"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # キャッシュキーの生成
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # キャッシュの確認
            if key in cache:
                timestamp, value = cache[key]
                # TTLチェック
                if asyncio.get_event_loop().time() - timestamp < ttl_seconds:
                    return value
            
            # キャッシュがない場合、関数を実行
            result = await func(*args, **kwargs)
            
            # 結果をキャッシュ
            cache[key] = (asyncio.get_event_loop().time(), result)
            
            return result
        return wrapper
    return decorator

# キャッシュ使用例
@cached(ttl_seconds=60)
async def get_tool_info(self, tool_id: str) -> Optional[Dict[str, Any]]:
    """特定のツール情報を取得（キャッシュあり）"""
    tools = self.tool_registry.get_tool_info()
    for tool in tools:
        if tool["tool_id"] == tool_id:
            return tool
    return None
```

## ロギング戦略

サービスレイヤーでは詳細なロギングを実装し、システムの透明性と監査可能性を確保します：

```python
import logging
from src.core.config import settings

# ロガーの設定
logger = logging.getLogger(__name__)

class AuditService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = AuditRepository(db)
        logger.info("AuditService initialized")
    
    async def start_workflow(self, workflow_id: str) -> bool:
        """監査ワークフローを開始"""
        logger.info(f"Starting workflow {workflow_id}")
        
        # ワークフローの取得
        workflow_data = self.repository.get_workflow(workflow_id)
        if not workflow_data:
            logger.warning(f"Workflow {workflow_id} not found")
            return False
        
        # ワークフローの開始
        try:
            # 処理
            logger.info(f"Workflow {workflow_id} started successfully")
            return True
        except Exception as e:
            logger.error(f"Error starting workflow {workflow_id}: {e}", exc_info=True)
            return False
```

## 拡張方法

### 新しいサービスの追加

1. 新しいサービスファイルの作成
   ```python
   # services/new_service.py
   from typing import Dict, Any, List, Optional
   
   class NewService:
       """新しいサービスの説明"""
       
       def __init__(self):
           # 初期化
           pass
       
       async def some_method(self, param1, param2) -> Dict[str, Any]:
           """メソッドの説明"""
           # 実装
           return {"result": "some value"}
   ```

2. 既存サービスからの利用
   ```python
   # 既存サービスからの新サービスの利用
   from src.services.new_service import NewService
   
   class ExistingService:
       def __init__(self):
           self.new_service = NewService()
       
       async def existing_method(self):
           # 新しいサービスの利用
           result = await self.new_service.some_method("param1", "param2")
           # 処理
   ```

### 既存サービスの拡張

既存のサービスを拡張するには、新しいメソッドを追加します：

```python
# audit_service.py に追加
async def export_audit_results(self, workflow_id: str, format: str = "json") -> Dict[str, Any]:
    """監査結果のエクスポート"""
    results = self.repository.get_results_by_workflow(workflow_id)
    
    if format == "json":
        # JSON形式でエクスポート
        return {"format": "json", "data": results}
    elif format == "csv":
        # CSV形式でエクスポート
        # CSVへの変換ロジック
        csv_data = self._convert_to_csv(results)
        return {"format": "csv", "data": csv_data}
    else:
        raise ValueError(f"Unsupported format: {format}")
```

## ユースケースとの対応

サービスレイヤーはユースケースに記載されている業務フローを実現します：

1. **監査プロセスの全体フロー**
   - `AuditService.create_workflow()`でワークフローを作成
   - `AuditService.start_workflow()`で監査を開始
   - `AgentService.send_message()`でエージェント間の連携を実現

2. **階層的問題解決アプローチ**
   - `ToolService`がツール実行をサポート
   - `AgentService`がエージェント間の質問・回答をサポート
   - `UserService`がユーザーへの確認プロセスをサポート

## 監査証跡とコンプライアンス

監査証跡のための詳細なロギングを実装しています：

```python
# 監査証跡用の特殊ロガー
audit_logger = logging.getLogger("audit_trail")

def log_audit_event(event_type: str, user_id: str, details: Dict[str, Any]) -> None:
    """監査イベントを記録"""
    event = {
        "event_type": event_type,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
        "details": details
    }
    audit_logger.info(f"AUDIT: {event}")

# 使用例
@router.post("/workflows/{workflow_id}/start")
async def start_audit_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """監査ワークフローを開始"""
    # 監査イベントのログ
    log_audit_event(
        "workflow_start",
        current_user.id,
        {"workflow_id": workflow_id}
    )
    
    # 以下、通常の処理
    # ...
```

## パフォーマンス最適化のヒント

1. **非同期処理の活用**
   - 長時間実行されるタスクは非同期で処理
   - `asyncio.gather()`による並列処理

2. **キャッシュの活用**
   - 頻繁にアクセスされるデータをキャッシュ
   - TTL（有効期限）の適切な設定

3. **バッチ処理**
   - 複数のデータベース操作をバッチ処理
   - 一括クエリの使用 