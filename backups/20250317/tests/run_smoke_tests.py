#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
疎通テスト実行スクリプト

このスクリプトは、プロジェクトの疎通テストを実行するための
簡易的なインターフェースを提供します。
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# カラーコード
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BLUE = "\033[94m"

def print_colored(message: str, color: str = RESET) -> None:
    """
    カラー付きでメッセージを表示
    
    Args:
        message: 表示するメッセージ
        color: 色コード
    """
    print(f"{color}{message}{RESET}")

def run_command(command: List[str]) -> Tuple[int, str, str]:
    """
    コマンドを実行して結果を返す
    
    Args:
        command: 実行するコマンドとその引数のリスト
        
    Returns:
        終了コード、標準出力、標準エラー出力のタプル
    """
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr
    except Exception as e:
        return 1, "", str(e)

def run_smoke_tests(verbose: bool = False, filter_str: Optional[str] = None) -> bool:
    """
    疎通テストを実行
    
    Args:
        verbose: 詳細な出力を行う場合はTrue
        filter_str: 特定のテストを絞り込むための文字列
        
    Returns:
        テストが成功した場合はTrue、失敗した場合はFalse
    """
    print_colored("疎通テストを実行します...", BLUE)
    print_colored("=" * 50, BLUE)
    
    # コマンド作成
    cmd = ["python", "-m", "pytest", "tests/smoke_tests"]
    
    if verbose:
        cmd.append("-v")
    
    if filter_str:
        cmd.append(f"-k {filter_str}")
    
    # 開始時間
    start_time = datetime.now()
    
    # テスト実行
    return_code, stdout, stderr = run_command(cmd)
    
    # 終了時間と経過時間
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # 結果表示
    print_colored("=" * 50, BLUE)
    print_colored(f"テスト実行時間: {duration:.2f}秒", BLUE)
    
    if return_code == 0:
        print_colored("疎通テスト: 成功", GREEN)
        print(stdout)
        return True
    else:
        print_colored("疎通テスト: 失敗", RED)
        print(stdout)
        if stderr:
            print_colored("エラー:", RED)
            print(stderr)
        return False

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="疎通テスト実行スクリプト")
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細な出力を表示します")
    parser.add_argument("-k", "--filter", help="指定した文字列を含むテストのみを実行します")
    args = parser.parse_args()
    
    print_colored("内部監査サンプルデータ自動テストAIエージェントシステム", GREEN)
    print_colored("疎通テスト実行ツール", GREEN)
    print_colored("=" * 50, GREEN)
    
    success = run_smoke_tests(args.verbose, args.filter)
    
    # 終了コードを設定
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 