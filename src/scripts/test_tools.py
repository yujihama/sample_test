"""
ツールテスト用サンプルスクリプト

実行方法:
    python -m src.scripts.test_tools
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Dict, Any

# パスの追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent.absolute()))

from loguru import logger
from src.tools.tool_registry import registry
from src.tools.image_processor import ImageProcessor
from src.tools.data_validator import DataValidator
from src.tools.excel_analyzer import ExcelAnalyzer
from src.tools.document_parser import DocumentParser

def initialize_tools():
    """ツールの初期化と登録"""
    # 各ツールのインスタンスを作成
    image_tool = ImageProcessor("test_image_processor")
    data_tool = DataValidator("test_data_validator")
    excel_tool = ExcelAnalyzer("test_excel_analyzer")
    doc_tool = DocumentParser("test_document_parser")
    
    # ツールをレジストリに登録
    registry.register_tool(image_tool)
    registry.register_tool(data_tool)
    registry.register_tool(excel_tool)
    registry.register_tool(doc_tool)
    
    logger.info("テスト用ツールを初期化しました")
    return {
        "ImageProcessor": image_tool,
        "DataValidator": data_tool,
        "ExcelAnalyzer": excel_tool,
        "DocumentParser": doc_tool
    }

async def test_image_processor(tools):
    """画像処理ツールのテスト"""
    logger.info("画像処理ツールのテスト開始")
    
    tool = tools["ImageProcessor"]
    
    # テスト用データディレクトリ
    data_dir = os.path.join(Path(__file__).parent.parent.parent, "data", "test")
    os.makedirs(data_dir, exist_ok=True)
    
    # テスト用のテキストファイルを作成（実際には画像ファイルを使用）
    test_file = os.path.join(data_dir, "test_image.txt")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("これはテスト用のダミーファイルです。\n実際のシステムでは画像ファイルを使用します。")
    
    # ツール実行
    params = {
        "operation": "partial_enlarge",
        "image_path": test_file,
        "x1": 10,
        "y1": 10,
        "x2": 50,
        "y2": 50,
        "scale": 2.0
    }
    
    result = await tool.execute(params)
    logger.info(f"画像処理ツール実行結果: {result.status}")
    logger.debug(f"戻り値: {result.data}")

async def test_data_validator(tools):
    """データ照合ツールのテスト"""
    logger.info("データ照合ツールのテスト開始")
    
    tool = tools["DataValidator"]
    
    # テスト用パラメータ
    params = {
        "operation": "verify_employee",
        "employee_id": "E001"
    }
    
    result = await tool.execute(params)
    logger.info(f"データ照合ツール実行結果: {result.status}")
    logger.debug(f"戻り値: {result.data}")
    
    # 承認権限の照合テスト
    params = {
        "operation": "validate_approval",
        "category": "出張申請",
        "amount": "150000",
        "approver_id": "E002"
    }
    
    result = await tool.execute(params)
    logger.info(f"承認権限照合実行結果: {result.status}")
    logger.debug(f"戻り値: {result.data}")

async def test_excel_analyzer(tools):
    """Excel解析ツールのテスト"""
    logger.info("Excel解析ツールのテスト開始")
    
    tool = tools["ExcelAnalyzer"]
    
    # テスト用データディレクトリ
    data_dir = os.path.join(Path(__file__).parent.parent.parent, "data", "test")
    os.makedirs(data_dir, exist_ok=True)
    
    # テスト用のCSVファイルを作成
    test_file = os.path.join(data_dir, "test_data.csv")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("id,name,amount,date\n")
        f.write("1,テスト1,10000,2025/03/01\n")
        f.write("2,テスト2,20000,2025/03/02\n")
        f.write("3,テスト3,30000,2025/03/03\n")
    
    # ツール実行（構造解析）
    params = {
        "operation": "analyze_structure",
        "file_path": test_file
    }
    
    result = await tool.execute(params)
    logger.info(f"Excel解析ツール（構造解析）実行結果: {result.status}")
    logger.debug(f"戻り値: {result.data}")
    
    # データ抽出テスト
    params = {
        "operation": "extract_data",
        "file_path": test_file,
        "sheet_name": "Sheet1"  # CSVの場合は無視される
    }
    
    result = await tool.execute(params)
    logger.info(f"Excel解析ツール（データ抽出）実行結果: {result.status}")
    logger.debug(f"戻り値: {result.data}")

async def test_document_parser(tools):
    """文書解析ツールのテスト"""
    logger.info("文書解析ツールのテスト開始")
    
    tool = tools["DocumentParser"]
    
    # テスト用データディレクトリ
    data_dir = os.path.join(Path(__file__).parent.parent.parent, "data", "test")
    os.makedirs(data_dir, exist_ok=True)
    
    # テスト用の領収書テキストファイルを作成
    test_file = os.path.join(data_dir, "test_receipt.txt")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("領収書\n")
        f.write("2025年3月17日\n")
        f.write("株式会社テスト様\n")
        f.write("金額：10,000円\n")
        f.write("但し：テスト料として\n")
        f.write("株式会社サンプル\n")
    
    # テキスト抽出テスト
    params = {
        "operation": "extract_text",
        "file_path": test_file
    }
    
    result = await tool.execute(params)
    logger.info(f"文書解析ツール（テキスト抽出）実行結果: {result.status}")
    logger.debug(f"戻り値: {result.data}")
    
    # フォーマット確認テスト
    params = {
        "operation": "check_format",
        "file_path": test_file,
        "format_name": "standard_receipt"
    }
    
    result = await tool.execute(params)
    logger.info(f"文書解析ツール（フォーマット確認）実行結果: {result.status}")
    logger.debug(f"戻り値: {result.data}")

async def main():
    """メイン処理"""
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    logger.info("ツールテストを開始します")
    
    # ツールの初期化
    tools = initialize_tools()
    
    # テスト実行
    await test_image_processor(tools)
    await test_data_validator(tools)
    await test_excel_analyzer(tools)
    await test_document_parser(tools)
    
    logger.info("すべてのテストが完了しました")

if __name__ == "__main__":
    asyncio.run(main()) 