"""
人間監査人とのインタラクション機能の疎通確認テスト

このスクリプトは、APIサーバーの健全性チェックと人間介入要求の作成をテストします。

使用方法:
python src/tests/test_human_intervention.py [--debug]
"""

import requests
import json
from src.utils import json_utils
import logging
import sys
import traceback
import uuid
import argparse
import os
from datetime import datetime

# ルートディレクトリへのパスを設定
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(root_dir)

# テスト用ユーティリティをインポート
from src.tests.utils.test_helpers import setup_test_environment
from src.models.db_models import HumanInterventionRequest
from sqlalchemy.orm import Session

# コマンドライン引数の解析
parser = argparse.ArgumentParser(description='人間監査人とのインタラクション機能のテスト')
parser.add_argument('--debug', action='store_true', help='デバッグモードを有効にする')
args = parser.parse_args()

# ロギングの設定
log_level = logging.DEBUG if args.debug else logging.INFO
logging.basicConfig(
    level=log_level, 
    format='%(asctime)s - %(levelname)s - %(message)s', 
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("test_human_intervention.log")
    ]
)
logger = logging.getLogger(__name__)

# APIのベースURL
BASE_URL = "http://127.0.0.1:8000"

def print_separator():
    """区切り線を出力"""
    logger.debug("\n" + "-" * 80)

def test_create_human_intervention():
    """人間介入要求の作成をテストする"""
    print_separator()
    logger.debug("[CREATE TEST] 人間介入要求の作成テスト開始")
    
    # テスト環境をセットアップ（テスト用のワークフローを作成）
    test_env = setup_test_environment()
    db = test_env["db"]
    workflow_id = test_env["workflow_id"]
    
    try:
        url = f"{BASE_URL}/api/human-intervention"
        
        # リクエストデータ
        data = {
            "workflow_id": workflow_id,
            "requesting_agent": "test-agent",
            "intervention_type": "question",
            "title": "テスト質問",
            "description": "これはテスト用の質問です。正常に機能しますか？",
            "options": ["はい", "いいえ", "わからない"],
            "context_data": {"test_key": "test_value"},
            "priority": "normal",
            "pause_workflow": False
        }
        
        # リクエストデータの詳細をログに記録
        logger.debug(f"[CREATE TEST] リクエストURL: {url}")
        logger.debug(f"[CREATE TEST] リクエストデータ:\n{json_utils.json_serialize(data)}")
        
        try:
            logger.debug("[CREATE TEST] POSTリクエスト送信中...")
            response = requests.post(url, json=data)
            logger.debug("[CREATE TEST] POSTリクエスト送信完了")
            
            # レスポンスの詳細をログに記録
            logger.debug(f"[CREATE TEST] レスポンスステータスコード: {response.status_code}")
            logger.debug(f"[CREATE TEST] レスポンスヘッダー:\n{json_utils.json_serialize(dict(response.headers), indent=2)}")
            
            # レスポンス本文を個別に処理
            try:
                response_text = response.text
                logger.debug(f"[CREATE TEST] レスポンス本文:\n{response_text}")
            except Exception as e:
                logger.error(f"[CREATE TEST] レスポンス本文の取得に失敗: {e}")
            
            # ステータスコードを確認
            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.debug(f"[CREATE TEST] JSONレスポンスのパース成功:\n{json_utils.json_serialize(result)}")
                    logger.info(f"[CREATE TEST] 人間介入要求の作成テスト成功: ID={result.get('id')}")
                    
                    # データベースに保存されたことを確認
                    intervention = db.query(HumanInterventionRequest).filter(HumanInterventionRequest.id == result.get("id")).first()
                    if intervention:
                        logger.info(f"[CREATE TEST] データベースに人間介入要求が保存されました: {intervention.id}")
                    else:
                        logger.error("[CREATE TEST] データベースに人間介入要求が保存されていません")
                    
                    return result.get("id")
                except json.JSONDecodeError as e:
                    logger.error(f"[CREATE TEST] JSONのパースに失敗: {e}")
                    logger.error(f"[CREATE TEST] レスポンス本文: {response_text}")
                    return None
            else:
                logger.error(f"[CREATE TEST] HTTPエラー: {response.status_code}")
                try:
                    error_json = response.json()
                    logger.error(f"[CREATE TEST] エラーレスポンス:\n{json_utils.json_serialize(error_json)}")
                except json.JSONDecodeError:
                    logger.error(f"[CREATE TEST] エラーレスポンス (非JSON):\n{response_text}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"[CREATE TEST] リクエスト例外: {e}")
            logger.error(traceback.format_exc())
            return None
    except Exception as e:
        logger.error(f"[CREATE TEST] 予期せぬエラー: {e}")
        logger.error(traceback.format_exc())
        return None
    finally:
        # セッションを作成した場合は閉じる
        if test_env.get("session_created", False):
            db.close()
        print_separator()

def check_api_status():
    """APIサーバーの状態を確認する"""
    print_separator()
    logger.debug("[HEALTH CHECK] APIサーバーの状態確認開始")
    
    url = f"{BASE_URL}/health"
    logger.debug(f"[HEALTH CHECK] リクエストURL: {url}")
    
    try:
        logger.debug("[HEALTH CHECK] GETリクエスト送信中...")
        response = requests.get(url)
        logger.debug("[HEALTH CHECK] GETリクエスト送信完了")
        
        # レスポンスの詳細をログに記録
        logger.debug(f"[HEALTH CHECK] レスポンスステータスコード: {response.status_code}")
        logger.debug(f"[HEALTH CHECK] レスポンスヘッダー:\n{json_utils.json_serialize(dict(response.headers), indent=2)}")
        
        # レスポンス本文を個別に処理
        try:
            response_text = response.text
            logger.debug(f"[HEALTH CHECK] レスポンス本文:\n{response_text}")
        except Exception as e:
            logger.error(f"[HEALTH CHECK] レスポンス本文の取得に失敗: {e}")
        
        if response.status_code == 200:
            logger.info("[HEALTH CHECK] APIサーバーは正常に稼働しています")
            return True
        else:
            logger.error(f"[HEALTH CHECK] APIサーバーの状態確認に失敗しました: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"[HEALTH CHECK] リクエスト例外: {e}")
        logger.error(traceback.format_exc())
        return False
    except Exception as e:
        logger.error(f"[HEALTH CHECK] 予期せぬエラー: {e}")
        logger.error(traceback.format_exc())
        return False
    finally:
        print_separator()

if __name__ == "__main__":
    try:
        logger.info("========== テスト開始 ==========")
        
        # APIサーバーの状態を確認
        logger.info("[MAIN] APIサーバーの健全性チェック実行中...")
        api_status = check_api_status()
        logger.info(f"[MAIN] APIサーバーの健全性チェック結果: {'成功' if api_status else '失敗'}")
        
        if not api_status:
            logger.error("[MAIN] APIサーバーに接続できないため、テストを中断します")
            print("APIサーバーに接続できません。APIサーバーを起動してから再試行してください。")
            sys.exit(1)
            
        # 人間介入要求の作成をテスト
        logger.info(f"[MAIN] 人間介入要求の作成テスト実行中...")
        intervention_id = test_create_human_intervention()
        logger.info(f"[MAIN] 人間介入要求の作成テスト結果: {'成功' if intervention_id else '失敗'}")
        
        logger.info("========== テスト終了 ==========")
        
        if intervention_id:
            print(f"人間介入要求が正常に作成されました。ID: {intervention_id}")
            sys.exit(0)
        else:
            print("人間介入要求の作成に失敗しました。ログファイル (test_human_intervention.log) を確認してください。")
            sys.exit(1)
    except Exception as e:
        logger.error(f"[MAIN] テスト実行中に予期せぬエラーが発生しました: {e}")
        logger.error(traceback.format_exc())
        print("テスト実行中にエラーが発生しました。ログファイル (test_human_intervention.log) を確認してください。")
        sys.exit(1) 