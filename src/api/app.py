"""
FastAPIアプリケーションのメインエントリーポイント
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import (
    workflow_management,
    agent_management,
    tool_execution,
    human_interaction
)
from src.api.graph_endpoints import router as graph_router
from src.api.agent_context_endpoints import router as agent_context_router

app = FastAPI(
    title="監査ワークフロー管理API",
    description="監査ワークフローの管理とエージェントの制御を行うAPI",
    version="1.0.0"
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
app.include_router(workflow_management.router, prefix="/api/v1")
app.include_router(agent_management.router, prefix="/api/v1")
app.include_router(tool_execution.router, prefix="/api/v1")
app.include_router(human_interaction.router, prefix="/api/v1")
app.include_router(graph_router, prefix="/api/v1")
app.include_router(agent_context_router, prefix="/api/v1")

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "監査ワークフロー管理APIへようこそ",
        "version": "1.0.0",
        "status": "ok"
    } 