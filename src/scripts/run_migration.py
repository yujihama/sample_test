#!/usr/bin/env python
"""
データベースマイグレーション実行スクリプト

使用方法:
    python src/scripts/run_migration.py

このスクリプトはデータベースをバックアップした後、
モデル定義に基づいてマイグレーションを実行します。
"""

import os
import sys
from pathlib import Path

# ルートディレクトリをパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(root_dir)

if __name__ == "__main__":
    print("データベースマイグレーションを開始します...")
    
    # アプリケーションの初期化
    from src.core.config import initialize_app
    initialize_app()
    
    # マイグレーションの実行
    from src.utils.db_migration import perform_migration
    result = perform_migration()
    
    if result:
        print("マイグレーションが正常に完了しました。")
        sys.exit(0)
    else:
        print("マイグレーションに失敗しました。")
        sys.exit(1) 