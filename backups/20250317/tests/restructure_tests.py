#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
テストコード整理ツール

このスクリプトは、テストディレクトリ内のテストコードを整理し、
必要なテスト（疎通テスト）を保持し、不要なテストを別のディレクトリに移動します。
"""

import os
import sys
import shutil
import argparse
import traceback
from datetime import datetime
from typing import List, Tuple

# カラーコード
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BLUE = "\033[94m"

# 保持するテストディレクトリ（疎通テスト用）
KEEP_DIRS = [
    "smoke_tests"
]

# 保持するファイル（共通設定ファイルなど）
KEEP_FILES = [
    "tests/conftest.py",
    "tests/pytest.ini",
    "tests/README.md",
    "tests/restructure_tests.py",
    "tests/run_smoke_tests.py"
]

def print_colored(message: str, color: str = RESET) -> None:
    """
    カラー付きでメッセージを表示
    
    Args:
        message: 表示するメッセージ
        color: 色コード
    """
    print(f"{color}{message}{RESET}")
    # 出力をフラッシュして確実に表示
    sys.stdout.flush()

def backup_directory(source_dir: str, target_dir: str) -> bool:
    """
    ディレクトリをバックアップ
    
    Args:
        source_dir: バックアップ元ディレクトリ
        target_dir: バックアップ先ディレクトリ
        
    Returns:
        バックアップ成功ならTrue、失敗ならFalse
    """
    try:
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        
        shutil.copytree(source_dir, target_dir)
        return True
    except Exception as e:
        print_colored(f"バックアップ中にエラーが発生しました: {e}", RED)
        traceback.print_exc()
        return False

def identify_tests_to_move(tests_dir: str, keep_dirs: List[str], keep_files: List[str]) -> List[Tuple[str, str]]:
    """
    移動対象のテストファイルを特定
    
    Args:
        tests_dir: テストディレクトリのパス
        keep_dirs: 保持するディレクトリのリスト
        keep_files: 保持するファイルのリスト
        
    Returns:
        移動元と移動先のパスのタプルのリスト
    """
    try:
        move_list = []
        
        # バックアップ用のディレクトリパス
        backup_root = os.path.join("backups", datetime.now().strftime("%Y%m%d"), "tests")
        
        for root, dirs, files in os.walk(tests_dir):
            # ルートディレクトリの相対パスを取得
            rel_root = os.path.relpath(root, tests_dir)
            
            # 保持するディレクトリはスキップ
            is_keep_dir = False
            for keep_dir in keep_dirs:
                # パスの区切りでスプリットして比較
                if rel_root == "." or keep_dir in rel_root.split(os.sep):
                    is_keep_dir = True
                    break
            
            if is_keep_dir:
                print_colored(f"保持するディレクトリ: {root}", BLUE)
                continue
            
            for file in files:
                source_path = os.path.join(root, file)
                
                # 保持するファイルはスキップ
                if any(source_path == keep_file for keep_file in keep_files):
                    print_colored(f"保持するファイル: {source_path}", BLUE)
                    continue
                
                # バックアップ先のパスを作成
                rel_path = os.path.relpath(source_path, os.path.dirname(tests_dir))
                target_path = os.path.join(backup_root, rel_path)
                
                move_list.append((source_path, target_path))
        
        return move_list
    except Exception as e:
        print_colored(f"テスト特定中にエラーが発生しました: {e}", RED)
        traceback.print_exc()
        return []

def move_tests(move_list: List[Tuple[str, str]], dry_run: bool = True) -> Tuple[int, int]:
    """
    テストファイルを移動
    
    Args:
        move_list: 移動元と移動先のパスのタプルのリスト
        dry_run: 実際に移動せずに表示のみ行う場合はTrue
        
    Returns:
        成功数と失敗数のタプル
    """
    try:
        success_count = 0
        fail_count = 0
        
        for source, target in move_list:
            try:
                # ターゲットディレクトリが存在しない場合は作成
                target_dir = os.path.dirname(target)
                if not os.path.exists(target_dir):
                    if not dry_run:
                        os.makedirs(target_dir, exist_ok=True)
                
                # ファイル移動（コピー後に削除）
                if not dry_run:
                    shutil.copy2(source, target)
                    os.remove(source)
                    print_colored(f"移動: {source} -> {target}", GREEN)
                else:
                    print_colored(f"移動予定: {source} -> {target}", BLUE)
                    
                success_count += 1
                
            except Exception as e:
                print_colored(f"エラー: {source} の移動中に問題が発生しました: {e}", RED)
                traceback.print_exc()
                fail_count += 1
        
        return success_count, fail_count
    except Exception as e:
        print_colored(f"テスト移動処理中にエラーが発生しました: {e}", RED)
        traceback.print_exc()
        return 0, len(move_list)

def main():
    """メイン処理"""
    try:
        parser = argparse.ArgumentParser(description="テストコード整理ツール")
        parser.add_argument("--dry-run", action="store_true", help="実際に変更を適用せずに、何が行われるかを表示します")
        args = parser.parse_args()
        
        print_colored("テストコード整理ツール", GREEN)
        print_colored("=" * 50, GREEN)
        
        if args.dry_run:
            print_colored("ドライラン実行中（変更は適用されません）", YELLOW)
        
        tests_dir = "tests"
        
        # バックアップの作成
        backup_dir = os.path.join("backups", datetime.now().strftime("%Y%m%d"), "tests")
        print_colored(f"テストディレクトリをバックアップします: {backup_dir}", BLUE)
        
        if not args.dry_run:
            backup_success = backup_directory(tests_dir, backup_dir)
            if not backup_success:
                print_colored("バックアップの作成に失敗しました。処理を中止します。", RED)
                return
        
        # 移動対象ファイルの特定
        print_colored("移動対象のテストファイルを特定しています...", BLUE)
        move_list = identify_tests_to_move(tests_dir, KEEP_DIRS, KEEP_FILES)
        
        print_colored(f"移動対象テストファイル数: {len(move_list)}", BLUE)
        
        if len(move_list) == 0:
            print_colored("移動対象のファイルがありません。", YELLOW)
            return
        
        # ファイルの移動
        print_colored("テストファイルを移動しています...", BLUE)
        success_count, fail_count = move_tests(move_list, args.dry_run)
        
        print_colored("=" * 50, GREEN)
        print_colored("整理完了", GREEN)
        print_colored(f"成功: {success_count} ファイル", GREEN)
        
        if fail_count > 0:
            print_colored(f"失敗: {fail_count} ファイル", RED)
        
        if args.dry_run:
            print_colored("\n実際に変更を適用するには、--dry-run オプションを外して再度実行してください。", YELLOW)
        else:
            print_colored(f"\nバックアップは {backup_dir} に保存されています。", BLUE)
    
    except Exception as e:
        print_colored(f"実行中に予期せぬエラーが発生しました: {e}", RED)
        traceback.print_exc()

if __name__ == "__main__":
    main() 