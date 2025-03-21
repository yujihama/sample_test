from fastapi import APIRouter, Body, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional
from loguru import logger
import os
import sys
import traceback
from datetime import datetime
from src.core.config import settings

router = APIRouter()

# クライアントログ専用のファイルを設定
frontend_log_path = os.path.join(settings.LOGS_DIR, "frontend_errors.log")
print(f"フロントエンドログファイルの場所: {frontend_log_path}")

# フロントエンドログ用のシンクを追加
try:
    # 先に既存のファイルを作成
    with open(frontend_log_path, "a", encoding="utf-8") as f:
        f.write(f"=== FRONTEND LOG SYSTEM STARTED AT {datetime.now().isoformat()} ===\n")
    
    # loguruにシンクを追加
    logger.add(
        frontend_log_path,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | FRONTEND: {message}",
        level="DEBUG",
        rotation="10 MB",
        filter=lambda record: "frontend" in record["extra"]
    )
    print(f"フロントエンドログ設定完了: {frontend_log_path}")
except Exception as e:
    print(f"フロントエンドログファイル設定エラー: {str(e)}")
    traceback.print_exc()

class ClientLogEntry(BaseModel):
    level: str
    message: str
    context: Dict[str, Any] = {}
    stack: Optional[str] = None

@router.post("/client")
async def log_client_error(request: Request, log_entry: ClientLogEntry = Body(...)):
    """クライアントからのログを受け取り、専用ログファイルに記録する"""
    try:
        print(f"\n=== フロントエンドログ受信 ===\nレベル: {log_entry.level}\nメッセージ: {log_entry.message}")
        
        # リクエスト情報をデバッグ表示
        auth_header = request.headers.get('Authorization', 'なし')
        print(f"認証ヘッダー: {auth_header}")
        
        # コンテキスト情報の処理
        context_str = ", ".join([f"{k}={v}" for k, v in log_entry.context.items()])
        
        # 時刻
        timestamp = datetime.now().isoformat()
        
        # ログメッセージ作成
        log_message = f"[{timestamp}] {log_entry.level}: {log_entry.message} | {context_str}"
        
        # loguru経由でログ出力（frontend属性付き）
        logger_with_context = logger.bind(frontend=True)
        
        if log_entry.level.lower() == "error":
            logger_with_context.error(log_message)
            if log_entry.stack:
                logger_with_context.error(f"Stack trace: {log_entry.stack}")
        elif log_entry.level.lower() == "warning":
            logger_with_context.warning(log_message)
        else:
            logger_with_context.info(log_message)
        
        # 確実に記録するため直接ファイルにも書き込み
        with open(frontend_log_path, "a", encoding="utf-8") as f:
            f.write(f"{log_message}\n")
            if log_entry.stack:
                f.write(f"[{timestamp}] Stack: {log_entry.stack}\n")
            f.write("---\n")
        
        print(f"フロントエンドログを記録しました: {frontend_log_path}")
        return {"status": "success", "message": "ログを記録しました"}
    
    except Exception as e:
        error_msg = f"ログ処理エラー: {str(e)}"
        print(error_msg)
        traceback.print_exc()
        
        # エラーが発生しても何かを記録しようとする
        try:
            with open(frontend_log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] ERROR IN LOGGER: {str(e)}\n")
                f.write(f"Original message: {log_entry.message}\n")
                f.write("---\n")
        except:
            pass
            
        return {"status": "error", "message": error_msg} 