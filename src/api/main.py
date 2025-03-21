#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FastAPIアプリケーションのメインモジュール
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from src.api.routers.agent_management import router as agent_router
from src.api.routers.task_management import router as task_router
from src.api.routers.workflow_management import router as workflow_router
from src.api.routers.error_management import router as error_router
from src.api.routers.human_interaction import router as human_router
from src.api.routers.tool_execution import router as tool_router
from src.api.routers.sample_management import router as sample_router
from src.api.routers.audit_procedure import router as procedure_router
from src.api.routers.log_endpoints import router as log_router
from src.api.routers.dashboard_endpoints import router as dashboard_router
from src.api.dependencies import get_current_user

# グラフとエージェントコンテキスト関連のルーターを追加
try:
    from src.api.graph_endpoints import router as graph_router
    from src.api.agent_context_endpoints import router as agent_context_router
    HAS_GRAPH_ROUTERS = True
except ImportError:
    HAS_GRAPH_ROUTERS = False

app = FastAPI(
    title="Agent Collaboration API",
    description="エージェント協調システムのAPI",
    version="1.0.0",
    dependencies=[Depends(get_current_user)],
    docs_url="/docs",  # Swagger UIのURL
    redoc_url="/redoc",  # ReDocのURL
    openapi_url="/openapi.json"  # OpenAPI仕様のURL
)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(agent_router, prefix="/api/v1")
app.include_router(task_router, prefix="/api/v1")
app.include_router(workflow_router, prefix="/api/v1")
app.include_router(error_router, prefix="/api/v1")
app.include_router(human_router, prefix="/api/v1")
app.include_router(tool_router, prefix="/api/v1")
app.include_router(sample_router, prefix="/api/v1")
app.include_router(procedure_router, prefix="/api/v1")
app.include_router(log_router, prefix="/api/v1/logs")
app.include_router(dashboard_router, prefix="/api/v1")

# グラフとエージェントコンテキスト関連のルーターを登録
if HAS_GRAPH_ROUTERS:
    app.include_router(graph_router, prefix="/api/v1")
    app.include_router(agent_context_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {
        "message": "監査ワークフロー管理APIへようこそ",
        "version": "1.0.0",
        "docs_url": "/docs",
        "status": "ok"
    } 