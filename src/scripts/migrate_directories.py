"""
ディレクトリ構造の重複を解消するためのマイグレーションスクリプト

このスクリプトは、プロジェクト内の重複したディレクトリ構造を統合します。
以下の処理を行います：
1. src/tests/ → tests/ への移動
2. src/data/ → data/ への移動
3. src/migrations/ → migrations/ への移動
4. ツールの整理 (src/tools/ と tools/ の整理)
"""

import os
import sys
import shutil
from pathlib import Path
import datetime
import argparse

# ルートディレクトリをパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

def create_backup(path):
    """
    指定されたパスのバックアップを作成する
    
    Args:
        path: バックアップするディレクトリのパス
        
    Returns:
        バックアップ先のパス
    """
    if not os.path.exists(path):
        return None
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}_backup_{timestamp}"
    shutil.copytree(path, backup_path, dirs_exist_ok=True)
    print(f"バックアップを作成しました: {backup_path}")
    return backup_path

def merge_directories(src_dir, dest_dir, is_dry_run=False):
    """
    ソースディレクトリの内容を宛先ディレクトリにマージする
    
    Args:
        src_dir: ソースディレクトリのパス
        dest_dir: 宛先ディレクトリのパス
        is_dry_run: ドライランモードの場合True
    """
    # ソースディレクトリが存在しない場合は何もしない
    if not os.path.exists(src_dir):
        return
        
    # 宛先ディレクトリが存在しない場合は作成する
    if not os.path.exists(dest_dir) and not is_dry_run:
        os.makedirs(dest_dir)
    
    # ソースディレクトリの各アイテムを宛先にコピー
    for item in os.listdir(src_dir):
        src_item_path = os.path.join(src_dir, item)
        dest_item_path = os.path.join(dest_dir, item)
        
        # ディレクトリの場合は再帰的にマージ
        if os.path.isdir(src_item_path):
            if not os.path.exists(dest_item_path) and not is_dry_run:
                os.makedirs(dest_item_path)
            merge_directories(src_item_path, dest_item_path, is_dry_run)
        # ファイルの場合
        else:
            # 宛先に同名のファイルが存在するかチェック
            if os.path.exists(dest_item_path):
                # 確認プロンプト
                print(f"警告: 宛先に同名のファイルが存在します: {dest_item_path}")
                if not is_dry_run:
                    confirm = input("上書きしますか？ (y/n): ")
                    if confirm.lower() == 'y':
                        shutil.copy2(src_item_path, dest_item_path)
                        print(f"ファイルを上書きしました: {dest_item_path}")
                else:
                    print(f"[ドライラン] ファイルを上書きします: {dest_item_path}")
            else:
                if not is_dry_run:
                    shutil.copy2(src_item_path, dest_item_path)
                    print(f"アイテムをコピーしました: {src_item_path} -> {dest_item_path}")
                else:
                    print(f"[ドライラン] アイテムをコピーします: {src_item_path} -> {dest_item_path}")

def migrate_tests(is_dry_run=False):
    """
    テストディレクトリの統合
    src/tests/ -> tests/
    """
    print("\n=== テストディレクトリの統合を開始します ===")
    
    try:
        # パスの設定
        src_tests_dir = os.path.join(root_dir, "src", "tests")
        dest_tests_dir = os.path.join(root_dir, "tests")
        
        # src/testsディレクトリが存在しない場合はスキップ
        if not os.path.exists(src_tests_dir):
            print("ソースディレクトリが存在しません: " + src_tests_dir)
            return False
            
        # バックアップの作成
        if not is_dry_run:
            create_backup(dest_tests_dir)
        else:
            print(f"[ドライラン] バックアップを作成します: {dest_tests_dir}")
        
        # ディレクトリのマージ
        merge_directories(src_tests_dir, dest_tests_dir, is_dry_run)
        
        # マージ後、元のディレクトリを削除
        if not is_dry_run:
            shutil.rmtree(src_tests_dir)
            print(f"ソースディレクトリを削除しました: {src_tests_dir}")
        else:
            print(f"[ドライラン] ソースディレクトリを削除します: {src_tests_dir}")
        
        # pytest.iniの更新（必要に応じて）
        pytest_ini_path = os.path.join(root_dir, "pytest.ini")
        if os.path.exists(pytest_ini_path):
            try:
                with open(pytest_ini_path, "r+", encoding="utf-8") as f:
                    content = f.read()
                    # パスの更新
                    content = content.replace("src/tests", "tests")
                    if not is_dry_run:
                        f.seek(0)
                        f.write(content)
                        f.truncate()
                        print("pytest.iniを更新しました")
                    else:
                        print("[ドライラン] pytest.iniを更新します")
            except Exception as e:
                print(f"pytest.iniの更新中にエラーが発生しました: {e}")
        
    except Exception as e:
        print(f"テストディレクトリの統合中にエラーが発生しました: {e}")
        return False
    
    print("=== テストディレクトリの統合が完了しました ===")
    return True

def migrate_data(is_dry_run=False):
    """
    データディレクトリの統合
    src/data/ -> data/
    """
    print("\n=== データディレクトリの統合を開始します ===")
    
    try:
        # パスの設定
        src_data_dir = os.path.join(root_dir, "src", "data")
        dest_data_dir = os.path.join(root_dir, "data")
        
        # src/dataディレクトリが存在しない場合はスキップ
        if not os.path.exists(src_data_dir):
            print("ソースディレクトリが存在しません: " + src_data_dir)
            return False
            
        # バックアップの作成
        if not is_dry_run:
            create_backup(dest_data_dir)
        else:
            print(f"[ドライラン] バックアップを作成します: {dest_data_dir}")
        
        # ディレクトリのマージ
        merge_directories(src_data_dir, dest_data_dir, is_dry_run)
        
        # マージ後、元のディレクトリを削除
        if not is_dry_run:
            shutil.rmtree(src_data_dir)
            print(f"ソースディレクトリを削除しました: {src_data_dir}")
        else:
            print(f"[ドライラン] ソースディレクトリを削除します: {src_data_dir}")
        
    except Exception as e:
        print(f"データディレクトリの統合中にエラーが発生しました: {e}")
        return False
    
    print("=== データディレクトリの統合が完了しました ===")
    return True

def migrate_migrations(is_dry_run=False):
    """
    マイグレーションディレクトリの統合
    src/migrations/ -> migrations/
    """
    print("\n=== マイグレーションディレクトリの統合を開始します ===")
    
    try:
        # パスの設定
        src_migrations_dir = os.path.join(root_dir, "src", "migrations")
        dest_migrations_dir = os.path.join(root_dir, "migrations")
        scripts_dir = os.path.join(root_dir, "scripts")
        
        # src/migrationsディレクトリが存在しない場合はスキップ
        if not os.path.exists(src_migrations_dir):
            print("ソースディレクトリが存在しません: " + src_migrations_dir)
            return False
            
        # バックアップの作成
        if not is_dry_run:
            create_backup(dest_migrations_dir)
        else:
            print(f"[ドライラン] バックアップを作成します: {dest_migrations_dir}")
        
        # マイグレーションマネージャとCLIを scripts/ ディレクトリに移動
        src_manager_path = os.path.join(src_migrations_dir, "manager.py")
        dest_manager_path = os.path.join(scripts_dir, "db_migration_manager.py")
        
        src_cli_path = os.path.join(src_migrations_dir, "cli.py")
        dest_cli_path = os.path.join(scripts_dir, "db_migration_cli.py")
        
        if os.path.exists(src_manager_path):
            if not is_dry_run:
                shutil.copy2(src_manager_path, dest_manager_path)
                print("マイグレーションマネージャをスクリプトディレクトリに移動しました")
            else:
                print("[ドライラン] マイグレーションマネージャをスクリプトディレクトリに移動します")
                
        if os.path.exists(src_cli_path):
            if not is_dry_run:
                shutil.copy2(src_cli_path, dest_cli_path)
                print("マイグレーションCLIをスクリプトディレクトリに移動しました")
            else:
                print("[ドライラン] マイグレーションCLIをスクリプトディレクトリに移動します")
        
        # バージョンディレクトリのマイグレーション
        src_versions_dir = os.path.join(src_migrations_dir, "versions")
        dest_versions_dir = os.path.join(dest_migrations_dir, "versions")
        
        if os.path.exists(src_versions_dir):
            # ディレクトリが存在しない場合は作成
            if not os.path.exists(dest_versions_dir) and not is_dry_run:
                os.makedirs(dest_versions_dir)
                
            # 各バージョンファイルをコピー
            for version_file in os.listdir(src_versions_dir):
                src_version_path = os.path.join(src_versions_dir, version_file)
                dest_version_path = os.path.join(dest_versions_dir, version_file)
                
                if os.path.isfile(src_version_path):
                    if not is_dry_run:
                        shutil.copy2(src_version_path, dest_version_path)
                        print(f"マイグレーションバージョンをコピーしました: {version_file}")
                    else:
                        print(f"[ドライラン] マイグレーションバージョンをコピーします: {version_file}")
        
        # マージ後、元のディレクトリを削除
        if not is_dry_run:
            shutil.rmtree(src_migrations_dir)
            print(f"ソースディレクトリを削除しました: {src_migrations_dir}")
        else:
            print(f"[ドライラン] ソースディレクトリを削除します: {src_migrations_dir}")
        
    except Exception as e:
        print(f"マイグレーションディレクトリの統合中にエラーが発生しました: {e}")
        return False
    
    print("=== マイグレーションディレクトリの統合が完了しました ===")
    return True

def migrate_tools(is_dry_run=False):
    """
    ツールディレクトリの整理
    - src/tools/ (APIツール) - そのまま残す
    - tools/ (CLIツール)
    - scripts/ (ユーティリティスクリプト)
    """
    print("\n=== ツールディレクトリの整理を開始します ===")
    
    try:
        # パスの設定
        src_tools_dir = os.path.join(root_dir, "src", "tools")
        root_tools_dir = os.path.join(root_dir, "tools")
        scripts_dir = os.path.join(root_dir, "scripts")
        
        # バックアップの作成
        if not is_dry_run:
            create_backup(src_tools_dir)
            create_backup(root_tools_dir)
        else:
            print(f"[ドライラン] バックアップを作成します: {src_tools_dir}")
            print(f"[ドライラン] バックアップを作成します: {root_tools_dir}")
        
        # tools/ にあるPythonスクリプトを適切な場所に移動
        if os.path.exists(root_tools_dir):
            for item in os.listdir(root_tools_dir):
                src_item_path = os.path.join(root_tools_dir, item)
                
                # CLIツールかどうかを判断（.pyファイルでargparseまたはclickをインポートしているか）
                is_cli_tool = False
                if os.path.isfile(src_item_path) and item.endswith(".py"):
                    try:
                        with open(src_item_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            if "argparse" in content or "click" in content or "__main__" in content:
                                is_cli_tool = True
                    except:
                        pass
                
                # CLIツールでない場合はscriptsに移動
                if not is_cli_tool and os.path.isfile(src_item_path):
                    dest_item_path = os.path.join(scripts_dir, item)
                    if not is_dry_run:
                        shutil.copy2(src_item_path, dest_item_path)
                        os.remove(src_item_path)
                        print(f"ユーティリティスクリプトを移動しました: {item}")
                    else:
                        print(f"[ドライラン] ユーティリティスクリプトを移動します: {item}")
        
        # src/tools からAPIツール以外のものを適切な場所に移動
        if os.path.exists(src_tools_dir):
            for item in os.listdir(src_tools_dir):
                src_item_path = os.path.join(src_tools_dir, item)
                
                # APIツールかどうかを判断（.pyファイルでflaskまたはfastAPIをインポートしているか）
                is_api_tool = False
                if os.path.isfile(src_item_path) and item.endswith(".py"):
                    try:
                        with open(src_item_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            if "flask" in content.lower() or "fastapi" in content.lower() or "requests" in content.lower():
                                is_api_tool = True
                    except:
                        pass
                
                # APIツールでない場合は適切な場所に移動
                if not is_api_tool and os.path.isfile(src_item_path):
                    # CLIツールかどうかを判断
                    is_cli_tool = False
                    try:
                        with open(src_item_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            if "argparse" in content or "click" in content or "__main__" in content:
                                is_cli_tool = True
                    except:
                        pass
                    
                    if is_cli_tool:
                        dest_item_path = os.path.join(root_tools_dir, item)
                    else:
                        dest_item_path = os.path.join(scripts_dir, item)
                        
                    if not is_dry_run:
                        shutil.copy2(src_item_path, dest_item_path)
                        os.remove(src_item_path)
                        print(f"ツールを移動しました: {item}")
                    else:
                        print(f"[ドライラン] ツールを移動します: {item}")
    
    except Exception as e:
        print(f"ツール整理エラー: {e}")
    
    print("=== ツールディレクトリの整理が完了しました ===")
    return True

def main(is_dry_run=False):
    """
    メイン処理
    
    Args:
        is_dry_run: ドライランモードの場合True
    """
    print("ディレクトリ構造の重複を解消するマイグレーションを開始します...")
    
    # 各種ディレクトリの統合
    migrate_tests(is_dry_run)
    migrate_data(is_dry_run)
    migrate_migrations(is_dry_run)
    migrate_tools(is_dry_run)
    
    print("\nディレクトリ構造の重複解消が完了しました。")
    print("以下の変更が行われました：")
    print("1. テストディレクトリを tests/ に統合")
    print("2. データディレクトリを data/ に統合")
    print("3. マイグレーションディレクトリを migrations/ に統合")
    print("4. ツールディレクトリを整理（API/CLI/スクリプト別）")
    
if __name__ == "__main__":
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='ディレクトリ構造の重複を解消するマイグレーションスクリプト')
    parser.add_argument('--dry-run', action='store_true', help='実際の変更を行わずに、何が行われるかをシミュレートします')
    parser.add_argument('-y', '--yes', '--force', action='store_true', help='確認プロンプトをスキップして実行します')
    args = parser.parse_args()
    
    # ドライランモードの場合
    if args.dry_run:
        print("*** ドライランモード: 実際の変更は行われません ***")
        main(is_dry_run=True)
        sys.exit(0)
    
    # 確認プロンプト（--force/-y オプションがない場合）
    if not args.yes:
        print("この操作はディレクトリ構造を変更します。実行前にバックアップが作成されますが、念のため手動でもバックアップを取ることをお勧めします。")
        confirm = input("続行しますか？ (y/n): ")
        
        if confirm.lower() != 'y':
            print("操作をキャンセルしました。")
            sys.exit(0)
    
    # 実行
    main(is_dry_run=False) 