# API実装ガイド

このディレクトリには内部監査AIエージェントシステムのAPI実装が含まれています。
FastAPIを使用したRESTful APIエンドポイントの定義と、クライアントアプリケーションとの通信インターフェースを提供します。

## API概要

このAPIは以下の主要な機能を提供します：

1. **監査ワークフロー管理**
   - 監査ワークフローの開始、一時停止、再開、終了
   - ワークフロー状態の取得
   - 監査結果の取得

2. **エージェント操作**
   - エージェントへのメッセージ送信
   - エージェント状態の取得
   - エージェント間通信の監視

3. **ファイル管理**
   - 監査対象ファイルのアップロード
   - ファイルメタデータの取得
   - 結果レポートのダウンロード

4. **ユーザー管理**
   - ユーザー認証・認可
   - ユーザープロファイル管理
   - アクセス権管理

5. **システム管理**
   - システム状態監視
   - ツール設定管理
   - ログ取得

## ファイル構成

```
api/
├── __init__.py           - パッケージ初期化
├── main.py               - FastAPIアプリケーション定義
├── dependencies.py       - 依存関係の定義
├── middleware.py         - ミドルウェア定義
├── routes/               - ルート定義
│   ├── __init__.py       - ルートパッケージ初期化
│   ├── audit.py          - 監査関連エンドポイント
│   ├── agents.py         - エージェント関連エンドポイント
│   ├── files.py          - ファイル管理エンドポイント
│   ├── users.py          - ユーザー管理エンドポイント
│   └── system.py         - システム管理エンドポイント
└── schemas/              - リクエスト/レスポンススキーマ
    ├── __init__.py       - スキーマパッケージ初期化
    ├── audit.py          - 監査関連スキーマ
    ├── agents.py         - エージェント関連スキーマ
    ├── files.py          - ファイル関連スキーマ
    ├── users.py          - ユーザー関連スキーマ
    └── system.py         - システム関連スキーマ
```

## 主要コンポーネント

### メインアプリケーション (`main.py`)

FastAPIアプリケーションの初期化とルーターの登録を行います：

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import audit, agents, files, users, system

app = FastAPI(
    title="内部監査AIエージェントシステム API",
    description="内部監査プロセスを自動化・効率化するAIエージェントシステムのAPI",
    version="1.0.0"
)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限すること
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(audit.router, prefix="/api/audit", tags=["監査"])
app.include_router(agents.router, prefix="/api/agents", tags=["エージェント"])
app.include_router(files.router, prefix="/api/files", tags=["ファイル"])
app.include_router(users.router, prefix="/api/users", tags=["ユーザー"])
app.include_router(system.router, prefix="/api/system", tags=["システム"])

@app.get("/")
async def root():
    return {"message": "内部監査AIエージェントシステム API"}
```

### 依存関係 (`dependencies.py`)

API内で使用される共通の依存関係を定義します：

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from sqlalchemy.orm import Session

from src.models.database import get_db
from src.models.users import User
from src.services.auth import verify_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/token")

# データベースセッションの依存関係
def get_db_session():
    db = get_db()
    try:
        yield db
    finally:
        db.close()

# 現在のユーザーを取得する依存関係
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証情報が無効です",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    user_id = verify_token(token)
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    return user

# 管理者権限を持つユーザーを取得する依存関係
async def get_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この操作には管理者権限が必要です"
        )
    return current_user
```

### ルーター例 (`routes/audit.py`)

監査関連のエンドポイントを定義するルーター例：

```python
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from sqlalchemy.orm import Session

from ..dependencies import get_current_user, get_db_session
from ..schemas.audit import (
    AuditWorkflowCreate, 
    AuditWorkflowResponse, 
    AuditResultResponse
)
from src.models.users import User
from src.services.audit import AuditService

router = APIRouter()

@router.post("/workflows", response_model=AuditWorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_audit_workflow(
    workflow_data: AuditWorkflowCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """新しい監査ワークフローを作成します"""
    audit_service = AuditService(db)
    return await audit_service.create_workflow(workflow_data, current_user.id)

@router.get("/workflows/{workflow_id}", response_model=AuditWorkflowResponse)
async def get_audit_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """指定されたIDの監査ワークフローを取得します"""
    audit_service = AuditService(db)
    workflow = await audit_service.get_workflow(workflow_id)
    
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ワークフロー ID {workflow_id} が見つかりません"
        )
    
    return workflow

@router.post("/workflows/{workflow_id}/start")
async def start_audit_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """指定された監査ワークフローを開始します"""
    audit_service = AuditService(db)
    result = await audit_service.start_workflow(workflow_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ワークフローの開始に失敗しました"
        )
    
    return {"status": "started", "workflow_id": workflow_id}

@router.get("/results/{workflow_id}", response_model=List[AuditResultResponse])
async def get_audit_results(
    workflow_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """指定されたワークフローの監査結果を取得します"""
    audit_service = AuditService(db)
    results = await audit_service.get_results(workflow_id)
    
    return results
```

## スキーマ例 (`schemas/audit.py`)

APIリクエストとレスポンスのデータ構造を定義するPydanticモデル例：

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class WorkflowStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class AuditWorkflowCreate(BaseModel):
    procedure_id: str = Field(..., description="監査手続きID")
    sample_ids: List[str] = Field(..., description="監査対象サンプルIDのリスト")
    parameters: Optional[Dict[str, Any]] = Field(None, description="監査パラメータ")
    priority: Optional[str] = Field("normal", description="優先度")

class AuditWorkflowResponse(BaseModel):
    workflow_id: str
    procedure_id: str
    sample_ids: List[str]
    status: WorkflowStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: str
    parameters: Optional[Dict[str, Any]] = None
    
    class Config:
        orm_mode = True

class AuditResultResponse(BaseModel):
    result_id: str
    workflow_id: str
    sample_id: str
    agent_id: str
    result_type: str
    status: str
    results: Dict[str, Any]
    created_at: datetime
    
    class Config:
        orm_mode = True
```

## APIエンドポイント一覧

### 監査管理

- `POST /api/audit/workflows` - 新規監査ワークフロー作成
- `GET /api/audit/workflows` - 監査ワークフロー一覧取得
- `GET /api/audit/workflows/{workflow_id}` - 監査ワークフロー詳細取得
- `POST /api/audit/workflows/{workflow_id}/start` - 監査ワークフロー開始
- `POST /api/audit/workflows/{workflow_id}/pause` - 監査ワークフロー一時停止
- `POST /api/audit/workflows/{workflow_id}/resume` - 監査ワークフロー再開
- `DELETE /api/audit/workflows/{workflow_id}` - 監査ワークフロー削除
- `GET /api/audit/results/{workflow_id}` - 監査結果取得

### エージェント管理

- `GET /api/agents` - 利用可能なエージェント一覧取得
- `GET /api/agents/{agent_id}` - エージェント情報取得
- `POST /api/agents/{agent_id}/messages` - エージェントへのメッセージ送信
- `GET /api/agents/{agent_id}/state` - エージェント状態取得

### ファイル管理

- `POST /api/files/upload` - ファイルアップロード
- `GET /api/files/{file_id}` - ファイル取得
- `GET /api/files/{file_id}/metadata` - ファイルメタデータ取得
- `GET /api/files/reports/{workflow_id}` - 監査レポート取得

### ユーザー管理

- `POST /api/users/register` - ユーザー登録
- `POST /api/users/token` - アクセストークン取得（ログイン）
- `GET /api/users/me` - 現在のユーザー情報取得
- `PUT /api/users/me` - ユーザー情報更新

### システム管理

- `GET /api/system/status` - システム状態取得
- `GET /api/system/tools` - 利用可能なツール一覧取得
- `PUT /api/system/tools/{tool_id}/config` - ツール設定更新

## 認証と認可

APIは JWT（JSON Web Token）ベースの認証を使用しています：

1. ユーザーが `/api/users/token` エンドポイントでログイン情報を送信
2. 認証に成功すると、アクセストークンが発行される
3. 以降のリクエストでは、`Authorization: Bearer {token}` ヘッダーを使用して認証

権限レベルに応じたアクセス制御が行われます：

- 一般ユーザー：自分の監査ワークフローのみアクセス可能
- 監査管理者：すべての監査ワークフローにアクセス可能
- システム管理者：システム設定を変更可能

## エラーハンドリング

APIはHTTPステータスコードと統一されたエラーレスポンス形式を使用します：

```json
{
  "status_code": 400,
  "detail": "エラーの詳細メッセージ",
  "path": "/api/audit/workflows/invalid-id",
  "timestamp": "2023-09-01T12:34:56.789Z"
}
```

一般的なエラーコード：

- `400 Bad Request` - リクエストパラメータが無効
- `401 Unauthorized` - 認証情報が無効または不足
- `403 Forbidden` - 必要な権限がない
- `404 Not Found` - リソースが見つからない
- `422 Unprocessable Entity` - リクエストデータのバリデーションエラー
- `500 Internal Server Error` - サーバー内部エラー

## 拡張方法

### 新しいエンドポイントの追加

1. 対応するスキーマを `schemas/` ディレクトリに定義
   ```python
   # schemas/new_feature.py
   from pydantic import BaseModel
   
   class NewFeatureRequest(BaseModel):
       name: str
       description: str
   
   class NewFeatureResponse(BaseModel):
       id: str
       name: str
       description: str
       created_at: datetime
       
       class Config:
           orm_mode = True
   ```

2. 新しいルーターファイルを `routes/` ディレクトリに作成
   ```python
   # routes/new_feature.py
   from fastapi import APIRouter, Depends
   from ..dependencies import get_current_user
   from ..schemas.new_feature import NewFeatureRequest, NewFeatureResponse
   
   router = APIRouter()
   
   @router.post("/", response_model=NewFeatureResponse)
   async def create_new_feature(
       data: NewFeatureRequest,
       current_user = Depends(get_current_user)
   ):
       # 実装
       ...
   ```

3. メインアプリケーションに新しいルーターを登録
   ```python
   # main.py に追加
   from .routes import new_feature
   
   app.include_router(
       new_feature.router,
       prefix="/api/new-feature",
       tags=["新機能"]
   )
   ```

### 既存エンドポイントの拡張

既存のエンドポイントを拡張するには、対応するルーターファイルに新しいパスやメソッドを追加します：

```python
# routes/audit.py に追加
@router.get("/workflows/{workflow_id}/timeline", response_model=List[AuditTimelineEvent])
async def get_workflow_timeline(
    workflow_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """監査ワークフローのタイムラインイベントを取得します"""
    # 実装
    ...
```

## OpenAPI ドキュメント

APIのOpenAPIドキュメントは以下のURLでアクセスできます：

- Swagger UI: `/docs`
- ReDoc: `/redoc`

これらのドキュメントは各エンドポイントの説明、パラメータ、レスポンス形式を提供し、APIをインタラクティブにテストすることができます。

## APIのメトリクスと監視

APIはPrometheusと連携して以下のメトリクスを収集します：

- リクエスト数
- レスポンス時間
- エラー率
- エンドポイント別の使用状況

メトリクスのエンドポイント: `/metrics`

## パフォーマンス最適化

1. **非同期処理**
   - 長時間実行されるタスクは非同期で処理
   - バックグラウンドタスクにはCeleryを使用

2. **キャッシュ**
   - 頻繁にアクセスされるデータをRedisでキャッシュ
   - キャッシュヘッダーの適切な設定

3. **データベース最適化**
   - クエリの最適化
   - インデックスの適切な設定
   - データベース接続プールの使用 