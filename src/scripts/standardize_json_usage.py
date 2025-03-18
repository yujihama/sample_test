#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
JSON処理標準化ツール

プロジェクト内のファイルをスキャンし、json.dumps/json.loadsの直接呼び出しを
src.utils.json_utilsの対応する関数に置き換えます。
"""

import os
import re
import sys
from pathlib import Path
import argparse
from typing import List, Tuple, Set

# 置換パターン
PATTERNS = [
    # json.dumps を json_serialize に置換
    (
        r'json\.dumps\((.*?)(?:,\s*(?:ensure_ascii\s*=\s*False|indent\s*=\s*\d+|cls\s*=\s*\w+|sort_keys\s*=\s*(?:True|False)))*\)',
        r'json_utils.json_serialize(\1)'
    ),
    # json.loads を json_deserialize に置換
    (
        r'json\.loads\((.*?)\)',
        r'json_utils.json_deserialize(\1)'
    )
]

# 対象外とするディレクトリやファイル
EXCLUDED_DIRS = {
    ".git", ".github", "__pycache__", "venv", "env", ".env", "node_modules",
    ".pytest_cache", "backups", "migrations"
}
EXCLUDED_FILES = {
    "standardize_json_usage.py",  # このスクリプト自体
    "json_utils.py"  # JSONユーティリティファイル自体
}

# インポート文を追加する正規表現パターン
IMPORT_PATTERN = re.compile(r'^(import\s+.*?$|from\s+.*?$)', re.MULTILINE)
JSON_IMPORT_PATTERN = re.compile(r'^import\s+json\s*$|^from\s+json\s+import', re.MULTILINE)
JSON_UTILS_IMPORT_PATTERN = re.compile(r'from\s+src\.utils\s+import\s+json_utils|from\s+src\.utils\.json_utils\s+import', re.MULTILINE)

def find_python_files(base_dir: Path) -> List[Path]:
    """
    指定したディレクトリ以下の全Pythonファイルを検索します。
    
    Args:
        base_dir: 検索を開始するディレクトリ
        
    Returns:
        Pythonファイルのパスのリスト
    """
    python_files = []
    
    for root, dirs, files in os.walk(base_dir):
        # 除外ディレクトリを処理対象から外す
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        
        for file in files:
            if file.endswith('.py') and file not in EXCLUDED_FILES:
                python_files.append(Path(root) / file)
    
    return python_files

def contains_json_calls(content: str) -> bool:
    """
    ファイル内容にjson.dumps/json.loadsの呼び出しが含まれているかをチェックします。
    
    Args:
        content: ファイル内容
        
    Returns:
        json.dumps/json.loadsの呼び出しが含まれている場合はTrue
    """
    return re.search(r'json\.dumps\(|json\.loads\(', content) is not None

def add_json_utils_import(content: str) -> str:
    """
    必要に応じてjson_utilsのインポート文を追加します。
    
    Args:
        content: ファイル内容
        
    Returns:
        更新されたファイル内容
    """
    # すでにjson_utilsがインポートされている場合は何もしない
    if JSON_UTILS_IMPORT_PATTERN.search(content):
        return content
    
    # jsonモジュールがインポートされている場合、その後にjson_utilsのインポートを追加
    if JSON_IMPORT_PATTERN.search(content):
        return re.sub(
            JSON_IMPORT_PATTERN,
            r'\g<0>\nfrom src.utils import json_utils',
            content,
            count=1
        )
    
    # jsonモジュールがインポートされていない場合、最初のインポート文の後にインポートを追加
    if IMPORT_PATTERN.search(content):
        return re.sub(
            IMPORT_PATTERN,
            r'\g<0>\n\nfrom src.utils import json_utils',
            content,
            count=1
        )
    
    # インポート文が見つからない場合は、ファイルの先頭に追加
    return 'from src.utils import json_utils\n\n' + content

def process_file(file_path: Path, dry_run: bool = False) -> Tuple[bool, str]:
    """
    ファイルを処理し、必要に応じてJSON呼び出しを置き換えます。
    
    Args:
        file_path: 処理するファイルのパス
        dry_run: Trueの場合、実際の変更は行わずに変更内容を報告するのみ
        
    Returns:
        (変更があったかどうか, 変更の説明)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # json.dumps/json.loadsの呼び出しがない場合はスキップ
    if not contains_json_calls(content):
        return False, f"スキップ: JSON呼び出しなし"
    
    # バックアップを作成
    backup_content = content
    
    # json_utilsのインポートを追加
    content = add_json_utils_import(content)
    
    # パターンに基づいて置換
    for pattern, replacement in PATTERNS:
        content = re.sub(pattern, replacement, content)
    
    # ファイルに変更がない場合はスキップ
    if content == backup_content:
        return False, f"スキップ: 変更なし"
    
    if not dry_run:
        # 変更内容を書き込み
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return True, f"更新: json.*を json_utils.*に置換"

def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='JSON処理の標準化ツール')
    parser.add_argument('--dry-run', action='store_true', help='変更を適用せずに結果のみを表示します')
    parser.add_argument('--dir', type=str, default='.', help='処理を開始するディレクトリ')
    args = parser.parse_args()
    
    base_dir = Path(args.dir).resolve()
    print(f"処理開始: {base_dir}")
    print(f"ドライラン: {'有効' if args.dry_run else '無効'}")
    
    # Pythonファイルを検索
    python_files = find_python_files(base_dir)
    print(f"検出されたPythonファイル: {len(python_files)}個")
    
    # 各ファイルを処理
    updated_files = 0
    skipped_files = 0
    
    for file_path in python_files:
        try:
            updated, message = process_file(file_path, args.dry_run)
            if updated:
                updated_files += 1
                print(f"✅ {file_path}: {message}")
            else:
                skipped_files += 1
                if args.dry_run:
                    print(f"⏭ {file_path}: {message}")
        except Exception as e:
            print(f"❌ {file_path}: エラー - {str(e)}")
    
    print("\n処理完了:")
    print(f"- 処理したファイル: {len(python_files)}個")
    print(f"- 更新したファイル: {updated_files}個")
    print(f"- スキップしたファイル: {skipped_files}個")
    
    if args.dry_run:
        print("\n注意: ドライランモードでの実行のため、実際の変更は適用されていません。")
        print("実際に変更を適用するには、--dry-runオプションを外して再実行してください。")

if __name__ == "__main__":
    main() 