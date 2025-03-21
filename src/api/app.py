"""
FastAPIアプリケーションのメインエントリーポイント
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 個々のルーターを直接インポート
from src.api.routers.workflow_management import router as workflow_router
from src.api.routers.agent_management import router as agent_router
from src.api.routers.tool_execution import router as tool_router
from src.api.routers.human_interaction import router as human_interaction_router
from src.api.routers.sample_management import router as sample_router
from src.api.routers.task_management import router as task_router
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
    allow_origins=["http://localhost:3002", "http://127.0.0.1:3002", "http://localhost:8080", "http://127.0.0.1:8080"],  # フロントエンドのURL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(workflow_router, prefix="/api/v1")
app.include_router(agent_router, prefix="/api/v1")
app.include_router(tool_router, prefix="/api/v1")
app.include_router(human_interaction_router, prefix="/api/v1")
app.include_router(sample_router, prefix="/api/v1")
app.include_router(task_router, prefix="/api/v1")
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