#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
テスト構造再構築ツール

このスクリプトは、テストディレクトリ構造を再構築し、
階層化されたテスト体系を作成します。
"""

import os
import sys
import shutil
import argparse
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Any

# カラーコード
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BLUE = "\033[94m"

# 新しいテスト構造
NEW_TEST_STRUCTURE = {
    "unit": {  # 単体テスト
        "agents": [],  # エージェント単体テスト
        "core": [],    # コア機能単体テスト
        "utils": [],   # ユーティリティ単体テスト
        "db": [],      # データベース単体テスト
        "api": [],     # API単体テスト
    },
    "integration": {  # 統合テスト
        "workflow": [],  # ワークフロー統合テスト
        "agents": [],    # エージェント間連携テスト
        "api": [],       # API統合テスト
        "db": [],        # DB統合テスト
    },
    "e2e": {  # エンドツーエンドテスト
        "scenarios": [],  # 各種シナリオテスト
    },
    "utils": {  # テスト用ユーティリティ
        "scripts": [],    # テスト実行スクリプト
        "mocks": [],      # モックオブジェクト
        "fixtures": [],   # 共通フィクスチャ
    }
}

# バックアップディレクトリからコピーするファイルマッピング
FILE_MAPPING = {
    # 単体テスト
    "unit/agents": [
        ("tests/agents/test_agent_a.py", "test_agent_a.py"),
        ("tests/agents/test_agent_b.py", "test_agent_b.py"),
        ("tests/agents/test_agent_c.py", "test_agent_c.py"),
        ("tests/agents/test_agent_d.py", "test_agent_d.py"),
    ],
    "unit/core": [
        ("tests/core/test_agent_context_manager.py", "test_agent_context_manager.py"),
        ("tests/core/test_audit_trail.py", "test_audit_trail.py"),
    ],
    "unit/utils": [
        ("tests/utils/test_backup_manager.py", "test_backup_manager.py"),
        ("tests/utils/test_helpers.py", "test_helpers.py"),
        ("tests/utils/__init__.py", "__init__.py"),
    ],
    "unit/db": [
        ("tests/db_integration/test_db_connection.py", "test_db_connection.py"),
        ("tests/db_integration/test_repositories.py", "test_repositories.py"),
    ],
    "unit/api": [
        ("tests/api/test_graph_endpoints.py", "test_graph_endpoints.py"),
        ("tests/api/test_audit_trail_endpoints.py", "test_audit_trail_endpoints.py"),
    ],
    
    # 統合テスト
    "integration/workflow": [
        ("tests/workflow/test_workflow.py", "test_workflow.py"),
        ("tests/workflow/test_workflow_state.py", "test_workflow_state.py"),
        ("tests/workflow/test_workflow_api.py", "test_workflow_api.py"),
    ],
    "integration/agents": [
        ("tests/agents/test_agent_communication.py", "test_agent_communication.py"),
        ("tests/agents/test_agent_b_graph.py", "test_agent_b_graph.py"),
        ("tests/integration/test_agent_a_workflow.py", "test_agent_a_workflow.py"),
        ("tests/integration/test_agent_b_workflow.py", "test_agent_b_workflow.py"),
        ("tests/integration/test_agent_c_workflow.py", "test_agent_c_workflow.py"),
        ("tests/integration/test_agent_d_workflow.py", "test_agent_d_workflow.py"),
    ],
    "integration/api": [
        ("tests/workflow/test_workflow_api.py", "test_workflow_api.py"),
    ],
    "integration/db": [
        ("tests/db_integration/test_repository_pattern.py", "test_repository_pattern.py"),
        ("tests/db_integration/test_index.py", "test_index.py"),
    ],
    
    # エンドツーエンドテスト
    "e2e/scenarios": [
        ("tests/workflow/test_human_intervention.py", "test_human_intervention.py"),
        ("tests/integration/test_workflow_state.py", "test_workflow_state.py"),
    ],
    
    # ユーティリティ
    "utils/scripts": [
        ("tests/scripts/run_tests.py", "run_tests.py"),
        ("tests/scripts/create_test_data.py", "create_test_data.py"),
        ("tests/workflow/run_workflow_tests.ps1", "run_workflow_tests.ps1"),
    ],
    "utils/mocks": [
        ("tests/scripts/mock_llm_responder.py", "mock_llm_responder.py"),
        ("tests/workflow/mock_repositories.py", "mock_repositories.py"),
    ],
    "utils/fixtures": [
        ("tests/integration/db_init.py", "db_init.py"),
    ],
}

# 作成するREADMEファイル
README_FILES = {
    "unit": """# 単体テスト (Unit Tests)

## 概要

このディレクトリには、システムの個別コンポーネントの単体テストが含まれています。
各サブディレクトリは、特定のコンポーネントグループに関連するテストを格納しています。

## 構成

- **agents/** - 各エージェント（A, B, C, D）の基本機能の単体テスト
- **core/** - コアシステム機能（コンテキスト管理、監査証跡など）の単体テスト
- **utils/** - ユーティリティ関数と共通ヘルパーの単体テスト
- **db/** - データベース関連機能の単体テスト
- **api/** - API個別エンドポイントの単体テスト

## 実行方法

```powershell
# 全ての単体テストを実行
pytest tests/unit -v

# 特定のコンポーネントの単体テストを実行
pytest tests/unit/agents -v
```

## 注意事項

- 単体テストは各コンポーネントを独立して検証するため、外部依存はモックまたはスタブ化されています
- データベース単体テストはインメモリDBを使用し、実際のデータには影響しません
""",

    "integration": """# 統合テスト (Integration Tests)

## 概要

このディレクトリには、複数のコンポーネントが連携する統合テストが含まれています。
これらのテストは、コンポーネント間の接続と相互作用を検証します。

## 構成

- **workflow/** - ワークフロー管理と状態遷移の統合テスト
- **agents/** - エージェント間の連携と通信の統合テスト
- **api/** - APIとバックエンドシステムの統合テスト
- **db/** - データベースリポジトリパターンとデータアクセスの統合テスト

## 実行方法

```powershell
# 全ての統合テストを実行
pytest tests/integration -v

# 特定の統合テストグループを実行
pytest tests/integration/workflow -v
```

## 注意事項

- 統合テストは実際のデータベースに接続するため、テスト環境での実行を推奨します
- 一部の統合テストは実行に時間がかかる場合があります
""",

    "e2e": """# エンドツーエンドテスト (End-to-End Tests)

## 概要

このディレクトリには、システム全体を通したエンドツーエンドテストが含まれています。
これらのテストは、実際のユーザーシナリオを再現し、システム全体の動作を検証します。

## 構成

- **scenarios/** - 各種監査シナリオのエンドツーエンドテスト

## 実行方法

```powershell
# 全てのエンドツーエンドテストを実行
pytest tests/e2e -v

# 特定のシナリオテストを実行
pytest tests/e2e/scenarios/test_human_intervention.py -v
```

## 注意事項

- エンドツーエンドテストは実行に時間がかかる場合があります
- 一部のテストはLLM APIへの実際の接続を必要とする場合があります
""",

    "utils": """# テスト用ユーティリティ (Test Utilities)

## 概要

このディレクトリには、テスト実行をサポートするための各種ユーティリティが含まれています。
これらは直接テストではなく、テスト環境の構築や実行をサポートするツールです。

## 構成

- **scripts/** - テスト実行スクリプトとユーティリティスクリプト
- **mocks/** - モックオブジェクトとテスト用のスタブ実装
- **fixtures/** - 共通のテストフィクスチャとセットアップコード

## 使用方法

```powershell
# テストデータ生成スクリプトの実行例
python tests/utils/scripts/create_test_data.py

# ワークフローテスト実行スクリプト
./tests/utils/scripts/run_workflow_tests.ps1
```

## 注意事項

- これらのユーティリティは直接テストではなく、テストの支援ツールです
- 必要に応じて各スクリプトのヘルプを確認してください
"""
}

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

def create_directories(base_dir: str, structure: Dict[str, Any]) -> bool:
    """
    ディレクトリ構造を作成
    
    Args:
        base_dir: 基本ディレクトリ
        structure: ディレクトリ構造の定義
        
    Returns:
        作成成功ならTrue、失敗ならFalse
    """
    try:
        for key in structure:
            dir_path = os.path.join(base_dir, key)
            os.makedirs(dir_path, exist_ok=True)
            print_colored(f"ディレクトリを作成しました: {dir_path}", GREEN)
            
            # サブディレクトリを作成
            if isinstance(structure[key], dict):
                for subkey in structure[key]:
                    subdir_path = os.path.join(dir_path, subkey)
                    os.makedirs(subdir_path, exist_ok=True)
                    print_colored(f"サブディレクトリを作成しました: {subdir_path}", GREEN)
        
        return True
    except Exception as e:
        print_colored(f"ディレクトリ作成中にエラーが発生しました: {e}", RED)
        traceback.print_exc()
        return False

def create_readme_files(base_dir: str, readme_files: Dict[str, str]) -> bool:
    """
    READMEファイルを作成
    
    Args:
        base_dir: 基本ディレクトリ
        readme_files: READMEファイルの内容
        
    Returns:
        作成成功ならTrue、失敗ならFalse
    """
    try:
        for dir_name, content in readme_files.items():
            file_path = os.path.join(base_dir, dir_name, "README.md")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print_colored(f"READMEファイルを作成しました: {file_path}", GREEN)
        
        return True
    except Exception as e:
        print_colored(f"READMEファイル作成中にエラーが発生しました: {e}", RED)
        traceback.print_exc()
        return False

def copy_test_files(backup_dir: str, tests_dir: str, file_mapping: Dict[str, List[Tuple[str, str]]], dry_run: bool = True) -> Tuple[int, int]:
    """
    テストファイルをコピー
    
    Args:
        backup_dir: バックアップディレクトリのパス
        tests_dir: テストディレクトリのパス
        file_mapping: ファイルマッピング
        dry_run: 実際にコピーせずに表示のみ行う場合はTrue
        
    Returns:
        成功数と失敗数のタプル
    """
    try:
        success_count = 0
        fail_count = 0
        
        for target_dir, file_list in file_mapping.items():
            target_path = os.path.join(tests_dir, target_dir)
            os.makedirs(target_path, exist_ok=True)
            
            for source_rel, target_file in file_list:
                source_path = os.path.join(backup_dir, source_rel)
                target_path_full = os.path.join(target_path, target_file)
                
                try:
                    if os.path.exists(source_path):
                        if not dry_run:
                            shutil.copy2(source_path, target_path_full)
                            print_colored(f"コピー: {source_path} -> {target_path_full}", GREEN)
                        else:
                            print_colored(f"コピー予定: {source_path} -> {target_path_full}", BLUE)
                        success_count += 1
                    else:
                        print_colored(f"警告: ソースファイルが見つかりません: {source_path}", YELLOW)
                        fail_count += 1
                except Exception as e:
                    print_colored(f"エラー: {source_path} のコピー中に問題が発生しました: {e}", RED)
                    traceback.print_exc()
                    fail_count += 1
        
        return success_count, fail_count
    except Exception as e:
        print_colored(f"ファイルコピー処理中にエラーが発生しました: {e}", RED)
        traceback.print_exc()
        return 0, len([file for files in file_mapping.values() for file in files])

def create_init_files(tests_dir: str, structure: Dict[str, Any], dry_run: bool = True) -> bool:
    """
    __init__.pyファイルを作成
    
    Args:
        tests_dir: テストディレクトリのパス
        structure: ディレクトリ構造
        dry_run: 実際に作成せずに表示のみ行う場合はTrue
        
    Returns:
        作成成功ならTrue、失敗ならFalse
    """
    try:
        # テストディレクトリ自体の__init__.py
        init_file = os.path.join(tests_dir, "__init__.py")
        if not os.path.exists(init_file):
            if not dry_run:
                with open(init_file, "w", encoding="utf-8") as f:
                    f.write('"""テストパッケージ"""\n')
                print_colored(f"__init__.pyファイルを作成しました: {init_file}", GREEN)
            else:
                print_colored(f"__init__.pyファイル作成予定: {init_file}", BLUE)
        
        # サブディレクトリの__init__.py
        for key in structure:
            dir_path = os.path.join(tests_dir, key)
            init_file = os.path.join(dir_path, "__init__.py")
            
            if not os.path.exists(init_file):
                if not dry_run:
                    with open(init_file, "w", encoding="utf-8") as f:
                        f.write(f'"""{key}テストパッケージ"""\n')
                    print_colored(f"__init__.pyファイルを作成しました: {init_file}", GREEN)
                else:
                    print_colored(f"__init__.pyファイル作成予定: {init_file}", BLUE)
            
            # サブディレクトリにも__init__.py作成
            if isinstance(structure[key], dict):
                for subkey in structure[key]:
                    subdir_path = os.path.join(dir_path, subkey)
                    init_file = os.path.join(subdir_path, "__init__.py")
                    
                    if not os.path.exists(init_file):
                        if not dry_run:
                            with open(init_file, "w", encoding="utf-8") as f:
                                f.write(f'"""{subkey}テストパッケージ"""\n')
                            print_colored(f"__init__.pyファイルを作成しました: {init_file}", GREEN)
                        else:
                            print_colored(f"__init__.pyファイル作成予定: {init_file}", BLUE)
        
        return True
    except Exception as e:
        print_colored(f"__init__.pyファイル作成中にエラーが発生しました: {e}", RED)
        traceback.print_exc()
        return False

def update_main_readme(tests_dir: str, dry_run: bool = True) -> bool:
    """
    メインのREADME.mdを更新
    
    Args:
        tests_dir: テストディレクトリのパス
        dry_run: 実際に更新せずに表示のみ行う場合はTrue
        
    Returns:
        更新成功ならTrue、失敗ならFalse
    """
    try:
        readme_path = os.path.join(tests_dir, "README.md")
        
        # 元のREADMEファイルを読み込み
        with open(readme_path, "r", encoding="utf-8") as f:
            original_content = f.read()
        
        # 更新内容
        new_content = original_content
        
        # テスト構成部分を更新
        test_structure_section = """
## 2. テスト構成

テストは以下の階層構造で構成されています：

### 2.1 疎通テスト（Smoke Tests）

システムの基本的な機能が正常に動作していることを素早く確認するためのテストです。詳細なテストの前に実行され、主要コンポーネントが機能していることを確認します。

- **データベース接続テスト** (`smoke_tests/test_db_connection.py`): データベースへの接続と主要テーブルの存在確認
- **APIエンドポイントテスト** (`smoke_tests/test_api_endpoints.py`): 主要APIエンドポイントの応答確認
- **エージェント基本機能テスト** (`smoke_tests/test_agents_basic.py`): 各エージェントの初期化と基本機能確認
- **ワークフロー初期化テスト** (`smoke_tests/test_workflow_init.py`): ワークフロー初期化処理の確認

### 2.2 単体テスト（Unit Tests）

個別コンポーネントの機能を検証するテストです。

- **エージェントテスト** (`unit/agents/`): 各エージェントの個別機能テスト
- **コア機能テスト** (`unit/core/`): システムコア機能の検証
- **ユーティリティテスト** (`unit/utils/`): 共通ユーティリティのテスト
- **データベーステスト** (`unit/db/`): データベース単体機能テスト
- **APIテスト** (`unit/api/`): 個別APIエンドポイントのテスト

### 2.3 統合テスト（Integration Tests）

複数のコンポーネントが連携する機能を検証するテストです。

- **ワークフローテスト** (`integration/workflow/`): ワークフロー管理と状態遷移のテスト
- **エージェント連携テスト** (`integration/agents/`): エージェント間の連携と通信のテスト
- **API統合テスト** (`integration/api/`): APIとバックエンドシステムの統合テスト
- **DB統合テスト** (`integration/db/`): データベースリポジトリパターンと高度なデータアクセステスト

### 2.4 エンドツーエンドテスト（End-to-End Tests）

システム全体を通した機能を検証するテストです。

- **シナリオテスト** (`e2e/scenarios/`): 実際のユーザーシナリオを再現した総合テスト

### 2.5 テストユーティリティ（Test Utilities）

テスト実行をサポートするためのユーティリティです。

- **スクリプト** (`utils/scripts/`): テスト実行と管理のためのスクリプト
- **モック** (`utils/mocks/`): テスト用のモックオブジェクト
- **フィクスチャ** (`utils/fixtures/`): 共通のテストフィクスチャとセットアップコード
"""
        
        # テスト実行方法部分を更新
        test_execution_section = """
## 3. テスト実行方法

### 3.1 疎通テスト（推奨）

疎通テストを実行するには、以下のコマンドを使用します：

```powershell
# 仮想環境の有効化
.\venv\Scripts\activate

# すべての疎通テストを実行
python tests/run_smoke_tests.py

# 詳細出力で実行
python tests/run_smoke_tests.py -v

# 特定のテストだけを実行（例：データベーステスト）
python tests/run_smoke_tests.py -k "database"
```

### 3.2 階層別テスト実行

特定の階層のテストを実行するには、以下のコマンドを使用します：

```powershell
# 単体テストを実行
pytest tests/unit -v

# 統合テストを実行
pytest tests/integration -v

# エンドツーエンドテストを実行
pytest tests/e2e -v

# 特定のコンポーネントのテストを実行（例：エージェント単体テスト）
pytest tests/unit/agents -v
```

### 3.3 テスト整理ツール

テストを整理するためのツールが実装されています：

```powershell
# テスト構造を再構築（ドライランモード）
python tests/rebuild_test_structure.py --dry-run

# テスト構造を実際に再構築
python tests/rebuild_test_structure.py
```
"""
        
        # 元のセクションを新しいセクションで置換
        import re
        
        # テスト構成セクションの置換
        pattern1 = r"## 2\. テスト構成[\s\S]*?## 3\."
        replacement1 = test_structure_section + "\n## 3."
        new_content = re.sub(pattern1, replacement1, new_content, flags=re.DOTALL)
        
        # テスト実行方法セクションの置換
        pattern2 = r"## 3\. テスト実行方法[\s\S]*?## 4\."
        replacement2 = test_execution_section + "\n## 4."
        new_content = re.sub(pattern2, replacement2, new_content, flags=re.DOTALL)
        
        # ファイルを更新
        if not dry_run:
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print_colored(f"メインREADMEファイルを更新しました: {readme_path}", GREEN)
        else:
            print_colored(f"メインREADMEファイル更新予定: {readme_path}", BLUE)
        
        return True
    except Exception as e:
        print_colored(f"メインREADMEファイル更新中にエラーが発生しました: {e}", RED)
        traceback.print_exc()
        return False

def main():
    """メイン処理"""
    try:
        parser = argparse.ArgumentParser(description="テスト構造再構築ツール")
        parser.add_argument("--dry-run", action="store_true", help="実際に変更を適用せずに、何が行われるかを表示します")
        args = parser.parse_args()
        
        print_colored("テスト構造再構築ツール", GREEN)
        print_colored("=" * 50, GREEN)
        
        if args.dry_run:
            print_colored("ドライラン実行中（変更は適用されません）", YELLOW)
        
        tests_dir = "tests"
        
        # 最新のバックアップディレクトリを検索
        today_date = datetime.now().strftime("%Y%m%d")
        backup_dir = os.path.join("backups", today_date, "tests")
        
        if not os.path.exists(backup_dir):
            print_colored(f"警告: バックアップディレクトリが見つかりません: {backup_dir}", YELLOW)
            print_colored("このスクリプトを実行する前に restructure_tests.py を実行してください。", YELLOW)
            return
        
        # 新しいディレクトリ構造を作成
        print_colored("新しいディレクトリ構造を作成しています...", BLUE)
        create_success = create_directories(tests_dir, NEW_TEST_STRUCTURE)
        
        if not create_success:
            print_colored("ディレクトリ構造の作成に失敗しました。処理を中止します。", RED)
            return
        
        # READMEファイルを作成
        print_colored("READMEファイルを作成しています...", BLUE)
        readme_success = create_readme_files(tests_dir, README_FILES)
        
        if not readme_success:
            print_colored("READMEファイルの作成に失敗しました。", YELLOW)
        
        # __init__.pyファイルを作成
        print_colored("__init__.pyファイルを作成しています...", BLUE)
        init_success = create_init_files(tests_dir, NEW_TEST_STRUCTURE, args.dry_run)
        
        if not init_success:
            print_colored("__init__.pyファイルの作成に失敗しました。", YELLOW)
        
        # テストファイルをコピー
        print_colored("テストファイルをコピーしています...", BLUE)
        success_count, fail_count = copy_test_files(backup_dir, tests_dir, FILE_MAPPING, args.dry_run)
        
        # メインREADMEを更新
        print_colored("メインREADMEファイルを更新しています...", BLUE)
        update_main_readme(tests_dir, args.dry_run)
        
        print_colored("=" * 50, GREEN)
        print_colored("再構築完了", GREEN)
        print_colored(f"成功: {success_count} ファイル", GREEN)
        
        if fail_count > 0:
            print_colored(f"失敗: {fail_count} ファイル", RED)
        
        if args.dry_run:
            print_colored("\n実際に変更を適用するには、--dry-run オプションを外して再度実行してください。", YELLOW)
    
    except Exception as e:
        print_colored(f"実行中に予期せぬエラーが発生しました: {e}", RED)
        traceback.print_exc()

if __name__ == "__main__":
    main() 