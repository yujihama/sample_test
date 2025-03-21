"""
LLM API呼び出しのテスト

このスクリプトは実際のLLM APIを呼び出してテストします。
環境変数にAPIキーが設定されているか確認してください。
ストリーミングモードはデフォルトでオフになっていますが、必要に応じて --streaming フラグで有効化できます。
"""

import os
import sys
import asyncio
from loguru import logger
import argparse
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# 環境変数の読み込み
dotenv_path = os.path.join(project_root, 'config', '.env')
load_dotenv(dotenv_path)

from src.utils.llm_utils import get_llm
from src.core.config import settings

async def test_llm_api(prompt: str, model: str = None, streaming: bool = False):
    """
    LLM APIを呼び出してテストします
    
    Args:
        prompt: テスト用プロンプト
        model: 使用するモデル（省略時はデフォルト）
        streaming: ストリーミングモード有効化
    """
    # 環境変数が設定されているか確認
    if not os.environ.get("OPENAI_API_KEY") and not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEYが設定されていません。環境変数または設定ファイルで設定してください。")
        return
    
    try:
        # USE_MOCK_LLM環境変数を削除してモックを使用しないようにする
        if "USE_MOCK_LLM" in os.environ:
            del os.environ["USE_MOCK_LLM"]
        
        logger.info(f"LLM API呼び出しテスト: model={model or settings.LLM_MODEL}, streaming={streaming}")
        
        # LLMインスタンスを取得
        llm = get_llm(model_name=model, streaming=streaming)
        
        # プロンプトを送信して応答を取得
        messages = [{"role": "user", "content": prompt}]
        logger.info(f"プロンプト: {prompt}")
        
        # LLMからの応答を取得
        if streaming:
            logger.info("ストリーミングモードで応答を取得します...")
            response_chunks = []
            async for chunk in llm.astream([messages[0]]):
                chunk_text = chunk.content
                logger.info(f"チャンク: {chunk_text}")
                response_chunks.append(chunk_text)
            response_content = "".join(response_chunks)
        else:
            # 通常の応答取得
            response = await llm.ainvoke(messages)
            response_content = response.content
        
        # 応答を表示
        logger.info("LLM応答:")
        logger.info(response_content)
        
        return response_content
    
    except Exception as e:
        logger.error(f"LLM API呼び出し中にエラーが発生しました: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

async def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="LLM API呼び出しテスト")
    parser.add_argument("--prompt", "-p", type=str, default="こんにちは、あなたは誰ですか？", help="テスト用プロンプト")
    parser.add_argument("--model", "-m", type=str, help="使用するモデル（例: gpt-4o）")
    parser.add_argument("--api-key", "-k", type=str, help="OpenAI APIキー")
    parser.add_argument("--streaming", "-s", action="store_true", help="ストリーミングモードを有効にする")
    
    args = parser.parse_args()
    
    # APIキーが指定されていれば環境変数に設定
    if args.api_key:
        os.environ["OPENAI_API_KEY"] = args.api_key
    
    await test_llm_api(args.prompt, args.model, args.streaming)

if __name__ == "__main__":
    asyncio.run(main()) 