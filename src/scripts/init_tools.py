"""
ツール初期化スクリプト

実行方法:
    python -m src.scripts.init_tools
"""

import os
import sys
import importlib
from pathlib import Path
import yaml
import argparse
from typing import Dict, Any, List

# パスの追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent.absolute()))

from loguru import logger
from src.tools.tool_registry import registry


def init_tools(config_path: str = None, verbose: bool = False) -> Dict[str, Any]:
    """
    ツールの初期化
    
    Args:
        config_path: 設定ファイルパス
        verbose: 詳細ログ出力フラグ
        
    Returns:
        Dict[str, Any]: 初期化結果
    """
    # ツールレジストリのインスタンス取得
    tool_registry = registry
    
    # 設定ファイルパスが指定されていれば、そのパスを使用
    if config_path:
        tool_registry.config_path = config_path
        # 設定を再読み込み
        tool_registry._load_config()
    
    # ツールモジュールの動的インポート
    tools_dir = Path(__file__).parent.parent / "tools"
    if verbose:
        logger.info(f"ツールディレクトリ: {tools_dir}")
    
    if not tools_dir.exists():
        logger.error(f"ツールディレクトリが見つかりません: {tools_dir}")
        return {"status": "error", "message": "ツールディレクトリが見つかりません"}
    
    # 自動登録対象のツールモジュールファイルを検索
    tool_modules = []
    for item in tools_dir.glob("*.py"):
        if item.is_file() and item.name != "__init__.py" and item.name != "tool_registry.py":
            module_name = item.stem
            tool_modules.append(module_name)
    
    if verbose:
        logger.info(f"検出したツールモジュール: {tool_modules}")
    
    # ツールクラスの自動登録
    registered_tools = []
    for module_name in tool_modules:
        try:
            # モジュールをインポート
            module_path = f"src.tools.{module_name}"
            module = importlib.import_module(module_path)
            
            # モジュール内のクラスを検索
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                
                # クラスで、'ToolBase'を継承しており、モジュール自身で定義されたものを登録
                if isinstance(attr, type) and hasattr(attr, '__module__') and attr.__module__ == module_path:
                    # 基底クラス名のチェック (直接的な型チェックは避ける)
                    bases = [base.__name__ for base in attr.__bases__]
                    if 'ToolBase' in bases:
                        # ツールクラスを登録
                        tool_registry.register_tool_class(attr)
                        registered_tools.append(attr.__name__)
                        if verbose:
                            logger.info(f"ツールクラス登録: {attr.__name__}")
        
        except Exception as e:
            logger.error(f"ツールモジュール '{module_name}' のロード中にエラー: {e}")
    
    # 設定ファイルからツールをロード
    tool_registry.load_tools_from_config()
    
    # 登録されたツールの情報を取得
    available_tools = tool_registry.get_tool_info()
    
    return {
        "status": "success",
        "registered_classes": registered_tools,
        "available_tools": available_tools
    }


def create_default_config(output_path: str = None) -> bool:
    """
    デフォルト設定ファイルの作成
    
    Args:
        output_path: 出力パス
        
    Returns:
        bool: 成功フラグ
    """
    # デフォルト設定
    default_config = {
        "tools": {
            "ImageProcessor": {
                "module": "src.tools.image_processor",
                "class": "ImageProcessor",
                "enabled": True,
                "id_suffix": "default",
                "metadata": {
                    "description": "画像処理ツール - デフォルト設定",
                    "priority": "medium"
                }
            }
        }
    }
    
    # 出力パスが指定されていなければデフォルトパスを使用
    if not output_path:
        output_path = os.path.join("config", "tools_config.yaml")
    
    try:
        # ディレクトリが存在しなければ作成
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 設定ファイルの書き出し
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
            
        logger.info(f"デフォルト設定ファイルを作成しました: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"設定ファイル作成エラー: {e}")
        return False


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="ツール初期化スクリプト")
    parser.add_argument("--config", type=str, help="設定ファイルのパス")
    parser.add_argument("--create-config", action="store_true", help="デフォルト設定ファイルを作成")
    parser.add_argument("--verbose", action="store_true", help="詳細ログを出力")
    
    args = parser.parse_args()
    
    # ロギング設定
    log_level = "DEBUG" if args.verbose else "INFO"
    logger.remove()
    logger.add(sys.stderr, level=log_level)
    
    # デフォルト設定ファイル作成
    if args.create_config:
        success = create_default_config(args.config)
        if success:
            logger.info("デフォルト設定ファイルの作成に成功しました")
        else:
            logger.error("デフォルト設定ファイルの作成に失敗しました")
        return
    
    # ツール初期化
    result = init_tools(args.config, args.verbose)
    
    if result["status"] == "success":
        logger.info(f"ツールクラス登録数: {len(result['registered_classes'])}")
        logger.info(f"利用可能なツール数: {len(result['available_tools'])}")
        
        if args.verbose:
            logger.info("利用可能なツール一覧:")
            for tool_info in result["available_tools"]:
                logger.info(f"  - {tool_info['name']}: {tool_info['description']}")
    else:
        logger.error(f"ツール初期化に失敗: {result['message']}")


if __name__ == "__main__":
    main() 