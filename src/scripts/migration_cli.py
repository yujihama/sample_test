"""
マイグレーションコマンドラインインターフェース

データベースマイグレーションを管理するCLIツール
"""

import sys
import argparse
from loguru import logger

from migrations.manager import MigrationManager


def parse_args():
    """コマンドライン引数の解析"""
    parser = argparse.ArgumentParser(description="データベースマイグレーション管理ツール")
    
    subparsers = parser.add_subparsers(dest="command", help="サブコマンド")
    
    # マイグレーション実行コマンド
    run_parser = subparsers.add_parser("run", help="マイグレーションを実行")
    
    # マイグレーション作成コマンド
    create_parser = subparsers.add_parser("create", help="新しいマイグレーションを作成")
    create_parser.add_argument("name", help="マイグレーション名")
    
    # 初期マイグレーション作成コマンド
    init_parser = subparsers.add_parser("init", help="初期マイグレーションを作成")
    
    # 適用済みマイグレーション一覧コマンド
    list_parser = subparsers.add_parser("list", help="適用済みマイグレーションを一覧表示")
    
    return parser.parse_args()


def main():
    """メイン処理"""
    args = parse_args()
    
    manager = MigrationManager()
    
    if args.command == "run":
        logger.info("マイグレーションを実行します")
        manager.run_migrations()
    
    elif args.command == "create":
        if not args.name:
            logger.error("マイグレーション名を指定してください")
            return 1
        
        logger.info(f"新しいマイグレーション '{args.name}' を作成します")
        migration_file = manager.create_migration(args.name)
        logger.info(f"マイグレーションファイルを作成しました: {migration_file}")
    
    elif args.command == "init":
        logger.info("初期マイグレーションを作成します")
        migration_file = manager.create_initial_migration()
        logger.info(f"初期マイグレーションファイルを作成しました: {migration_file}")
    
    elif args.command == "list":
        logger.info("適用済みマイグレーション:")
        applied_migrations = manager.get_applied_migrations()
        
        if not applied_migrations:
            logger.info("適用済みのマイグレーションはありません")
        else:
            for migration in applied_migrations:
                logger.info(f" - {migration}")
    
    else:
        logger.error("コマンドを指定してください: run, create, init, list")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 