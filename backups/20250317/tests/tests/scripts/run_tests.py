"""
テスト実行スクリプト

このスクリプトは、APIサーバーを起動し、テストケースを実行し、結果を確認します。
"""

import os
import sys
import subprocess
import time
import logging
from datetime import datetime

# ルートディレクトリへのパスを設定
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(root_dir)

# ロギングの設定
log_file = os.path.join(root_dir, "test_run.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)

def run_all_tests():
    """すべてのテストを実行する"""
    start_time = datetime.now()
    logger.info(f"テスト実行を開始しました: {start_time}")
    
    # APIサーバーの起動
    logger.info("APIサーバーを起動しています...")
    server_process = subprocess.Popen(
        ["python", "-m", "src.main"],
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    
    try:
        # サーバーの起動を待機
        time.sleep(3)
        logger.info("APIサーバーが起動しました")
        
        # テストの実行
        logger.info("人間監査人インタラクションテストを実行しています...")
        test_result = subprocess.run(
            ["python", "src/tests/test_human_intervention.py", "--debug"],
            capture_output=True,
            text=True
        )
        
        # テスト結果の表示
        logger.info(f"テスト出力:\n{test_result.stdout}")
        if test_result.stderr:
            logger.error(f"テストエラー出力:\n{test_result.stderr}")
        
        if test_result.returncode == 0:
            logger.info("テストが正常に完了しました")
            return True
        else:
            logger.error(f"テストに失敗しました: 終了コード {test_result.returncode}")
            return False
    except Exception as e:
        logger.error(f"テスト実行中にエラーが発生しました: {e}")
        return False
    finally:
        # APIサーバーの停止
        logger.info("APIサーバーを停止しています...")
        server_process.terminate()
        server_process.wait(timeout=5)
        logger.info("APIサーバーが停止しました")
        
        # 実行時間を計算
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"テスト実行が完了しました: 所要時間 {duration}")

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 