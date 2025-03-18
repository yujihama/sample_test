# スクリプトモジュール

このディレクトリには、内部監査AIエージェントシステムの運用・管理・初期化に関連するスクリプトが含まれています。
これらのスクリプトは主にシステムの初期設定、データ移行、バッチ処理などを行うために使用されます。

## スクリプトの概要

このディレクトリには以下のようなスクリプトが含まれています：

1. **初期化スクリプト**
   - `init_db.py` - データベースの初期化
   - `init_tools.py` - ツールの初期化と登録
   - `init_config.py` - 設定ファイルの初期化

2. **データ移行スクリプト**
   - `migrate_data.py` - データ移行の実行
   - `backup_db.py` - データベースのバックアップ
   - `restore_db.py` - データベースの復元

3. **バッチ処理スクリプト**
   - `batch_audit.py` - バッチ監査の実行
   - `generate_reports.py` - 監査レポートの自動生成
   - `cleanup_old_data.py` - 古いデータの削除

4. **ユーティリティスクリプト**
   - `check_system.py` - システム状態の確認
   - `generate_test_data.py` - テストデータの生成
   - `reset_password.py` - ユーザーパスワードのリセット

## ファイル構成

```
scripts/
├── __init__.py              - パッケージ初期化
├── init_db.py               - データベース初期化
├── init_tools.py            - ツール初期化
├── init_config.py           - 設定ファイル初期化
├── migrate_data.py          - データ移行
├── backup_db.py             - データベースバックアップ
├── restore_db.py            - データベース復元
├── batch_audit.py           - バッチ監査実行
├── generate_reports.py      - レポート生成
├── cleanup_old_data.py      - 古いデータ削除
├── check_system.py          - システム状態確認
├── generate_test_data.py    - テストデータ生成
└── reset_password.py        - パスワードリセット
```

## 主要スクリプトの詳細

### ツール初期化スクリプト

`init_tools.py` はシステムで利用可能なツールを初期化し、設定ファイルを生成します：

```python
import os
import sys
import importlib
import inspect
import yaml
import logging
from typing import Dict, List, Any, Optional, Type
from pathlib import Path

# ルートディレクトリをパスに追加して相対インポートを有効にする
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.tools.tool_base import ToolBase

logger = logging.getLogger(__name__)

def discover_tools(tools_dir: str = "src/tools") -> Dict[str, Type[ToolBase]]:
    """指定されたディレクトリから利用可能なツールクラスを動的に発見する"""
    tools = {}
    
    # ツールディレクトリのパスを取得
    base_path = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    tools_path = base_path / tools_dir
    
    # Pythonモジュールとして認識されるようにする
    if not (tools_path / "__init__.py").exists():
        logger.warning(f"ツールディレクトリ {tools_dir} に __init__.py が見つかりません")
        return tools
    
    # 相対パスからインポートパスを生成
    import_base = tools_dir.replace("/", ".")
    
    # ディレクトリ内のPythonファイルを検索
    for file_path in tools_path.glob("*.py"):
        if file_path.name.startswith("__"):
            continue
        
        module_name = file_path.stem
        import_name = f"{import_base}.{module_name}"
        
        try:
            # モジュールの動的インポート
            module = importlib.import_module(import_name)
            
            # モジュール内のクラスを検索
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # ToolBaseのサブクラスを検索（ToolBase自体は除外）
                if (issubclass(obj, ToolBase) and 
                    obj != ToolBase and 
                    obj.__module__ == import_name):
                    
                    # ツール辞書に追加
                    tools[name] = obj
                    logger.debug(f"ツール {name} を発見しました")
        
        except Exception as e:
            logger.error(f"モジュール {import_name} のインポート中にエラーが発生しました: {e}")
    
    return tools

def generate_default_config(tools: Dict[str, Type[ToolBase]], 
                           output_path: str = "config/tools_config.yaml") -> bool:
    """発見されたツールの設定ファイルを生成する"""
    try:
        # 出力ディレクトリの確認
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 設定辞書の作成
        config = {
            "version": "1.0",
            "tools": {}
        }
        
        # 各ツールの設定を追加
        for name, tool_class in tools.items():
            # ツールのメタデータを取得
            metadata = {}
            if hasattr(tool_class, 'get_metadata'):
                metadata = tool_class.get_metadata()
            
            # 設定に追加
            config["tools"][name] = {
                "enabled": True,
                "metadata": metadata
            }
        
        # YAMLファイルに書き込み
        with open(output_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        logger.info(f"{len(tools)} ツールの設定を {output_path} に生成しました")
        return True
    
    except Exception as e:
        logger.error(f"設定ファイルの生成中にエラーが発生しました: {e}")
        return False

def init_tools(tools_dir: str = "src/tools", 
              config_path: str = "config/tools_config.yaml",
              force_update: bool = False) -> Dict[str, Any]:
    """ツールの初期化と設定ファイルの生成を行う"""
    # 既存の設定ファイルの確認
    if os.path.exists(config_path) and not force_update:
        logger.info(f"設定ファイル {config_path} が既に存在します。上書きするには force_update=True を指定してください。")
        
        # 既存の設定を読み込む
        try:
            with open(config_path, 'r') as f:
                existing_config = yaml.safe_load(f)
            
            return {
                "status": "existing",
                "message": f"既存の設定ファイルを使用します: {config_path}",
                "tool_count": len(existing_config.get("tools", {})),
                "config_path": config_path
            }
        except Exception as e:
            logger.warning(f"既存の設定ファイルの読み込み中にエラーが発生しました: {e}")
    
    # ツールの発見
    logger.info(f"ディレクトリ {tools_dir} からツールを検索しています...")
    tools = discover_tools(tools_dir)
    
    if not tools:
        logger.warning(f"ディレクトリ {tools_dir} にツールが見つかりませんでした。")
        return {
            "status": "empty",
            "message": "ツールが見つかりませんでした",
            "tool_count": 0,
            "config_path": config_path
        }
    
    # 設定ファイルの生成
    logger.info(f"{len(tools)} ツールが見つかりました。設定ファイルを生成しています...")
    success = generate_default_config(tools, config_path)
    
    if success:
        return {
            "status": "success",
            "message": f"{len(tools)} ツールの設定を {config_path} に生成しました",
            "tool_count": len(tools),
            "tools": list(tools.keys()),
            "config_path": config_path
        }
    else:
        return {
            "status": "error",
            "message": "設定ファイルの生成中にエラーが発生しました",
            "tool_count": 0,
            "config_path": config_path
        }

if __name__ == "__main__":
    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # コマンドライン引数の解析
    import argparse
    parser = argparse.ArgumentParser(description='ツールの初期化と設定ファイルの生成')
    parser.add_argument('--tools-dir', default='src/tools', help='ツールディレクトリへのパス')
    parser.add_argument('--config-path', default='config/tools_config.yaml', help='出力設定ファイルのパス')
    parser.add_argument('--force', action='store_true', help='既存の設定ファイルを上書きする')
    args = parser.parse_args()
    
    # ツールの初期化
    result = init_tools(
        tools_dir=args.tools_dir,
        config_path=args.config_path,
        force_update=args.force
    )
    
    # 結果の表示
    if result["status"] == "success":
        logger.info(f"初期化成功: {result['message']}")
        logger.info(f"登録されたツール: {', '.join(result['tools'])}")
    else:
        logger.info(f"初期化状態: {result['status']}, {result['message']}")
```

### データベース初期化スクリプト

`init_db.py` はデータベースの初期化とスキーマの作成を行います：

```python
import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy_utils import database_exists, create_database
from alembic.config import Config
from alembic import command

# ルートディレクトリをパスに追加して相対インポートを有効にする
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.core.config import settings

logger = logging.getLogger(__name__)

def init_database(connection_string: str, alembic_ini_path: str = "alembic.ini") -> bool:
    """データベースの初期化とマイグレーションを実行する"""
    try:
        # データベースエンジンの作成
        engine = create_engine(connection_string)
        
        # データベースが存在しない場合は作成
        if not database_exists(engine.url):
            logger.info(f"データベースが存在しないため作成します: {engine.url}")
            create_database(engine.url)
        
        # Alembicの設定
        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("sqlalchemy.url", connection_string)
        
        # マイグレーションの実行
        logger.info("データベースマイグレーションを実行します...")
        command.upgrade(alembic_cfg, "head")
        
        logger.info("データベースの初期化が完了しました")
        return True
    
    except Exception as e:
        logger.error(f"データベースの初期化中にエラーが発生しました: {e}")
        return False

def seed_initial_data(connection_string: str) -> bool:
    """初期データを投入する"""
    try:
        # データベースエンジンの作成
        engine = create_engine(connection_string)
        
        # 管理者ユーザーの作成
        with engine.connect() as conn:
            # ユーザーがまだ存在しないことを確認
            result = conn.execute(text("SELECT COUNT(*) FROM users WHERE username = 'admin'"))
            if result.scalar() == 0:
                # 管理者ユーザーの作成
                conn.execute(text("""
                    INSERT INTO users (username, email, hashed_password, is_admin, created_at)
                    VALUES ('admin', 'admin@example.com', 
                            '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 
                            true, CURRENT_TIMESTAMP)
                """))
                conn.commit()
                logger.info("管理者ユーザーを作成しました (username: admin, password: password)")
        
        logger.info("初期データの投入が完了しました")
        return True
    
    except Exception as e:
        logger.error(f"初期データの投入中にエラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # コマンドライン引数の解析
    import argparse
    parser = argparse.ArgumentParser(description='データベースの初期化とマイグレーション')
    parser.add_argument('--connection-string', help='データベース接続文字列')
    parser.add_argument('--alembic-ini', default='alembic.ini', help='Alembic設定ファイルのパス')
    parser.add_argument('--seed-data', action='store_true', help='初期データを投入する')
    args = parser.parse_args()
    
    # 接続文字列の取得
    if args.connection_string:
        connection_string = args.connection_string
    else:
        connection_string = settings.DATABASE_URL
    
    # データベースの初期化
    if init_database(connection_string, args.alembic_ini):
        logger.info("データベースの初期化に成功しました")
        
        # 初期データの投入
        if args.seed_data:
            if seed_initial_data(connection_string):
                logger.info("初期データの投入に成功しました")
            else:
                logger.error("初期データの投入に失敗しました")
    else:
        logger.error("データベースの初期化に失敗しました")
```

### システム状態確認スクリプト

`check_system.py` はシステムの状態を診断し、問題があれば報告します：

```python
import os
import sys
import logging
import time
import json
import platform
import psutil
import requests
import asyncio
from sqlalchemy import create_engine, text
from typing import Dict, Any, List

# ルートディレクトリをパスに追加して相対インポートを有効にする
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.core.config import settings

logger = logging.getLogger(__name__)

async def check_database_connection() -> Dict[str, Any]:
    """データベース接続を確認する"""
    try:
        # データベースエンジンの作成
        engine = create_engine(settings.DATABASE_URL)
        
        # 接続テスト
        start_time = time.time()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        
        response_time = time.time() - start_time
        
        return {
            "status": "ok",
            "response_time": response_time,
            "message": "データベース接続に成功しました"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"データベース接続エラー: {str(e)}"
        }

async def check_api_endpoints() -> Dict[str, Any]:
    """APIエンドポイントの応答を確認する"""
    endpoints = [
        "/api/health",
        "/api/agents",
        "/api/tools"
    ]
    
    results = {}
    base_url = f"http://{settings.HOST}:{settings.PORT}"
    
    for endpoint in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            start_time = time.time()
            response = requests.get(url, timeout=5)
            response_time = time.time() - start_time
            
            results[endpoint] = {
                "status": "ok" if response.status_code == 200 else "error",
                "status_code": response.status_code,
                "response_time": response_time,
                "message": "OK" if response.status_code == 200 else f"Error: {response.status_code}"
            }
        except Exception as e:
            results[endpoint] = {
                "status": "error",
                "message": f"接続エラー: {str(e)}"
            }
    
    # 全体の状態を判定
    overall_status = "ok"
    for endpoint, result in results.items():
        if result["status"] != "ok":
            overall_status = "error"
            break
    
    return {
        "status": overall_status,
        "endpoints": results
    }

async def check_system_resources() -> Dict[str, Any]:
    """システムリソースの状態を確認する"""
    try:
        # CPUの使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # メモリの使用状況
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # ディスクの使用状況
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # 各リソースの状態を判定
        cpu_status = "ok" if cpu_percent < 80 else "warning" if cpu_percent < 90 else "critical"
        memory_status = "ok" if memory_percent < 80 else "warning" if memory_percent < 90 else "critical"
        disk_status = "ok" if disk_percent < 80 else "warning" if disk_percent < 90 else "critical"
        
        # 全体の状態を判定
        overall_status = "ok"
        if "critical" in [cpu_status, memory_status, disk_status]:
            overall_status = "critical"
        elif "warning" in [cpu_status, memory_status, disk_status]:
            overall_status = "warning"
        
        return {
            "status": overall_status,
            "cpu": {
                "status": cpu_status,
                "percent": cpu_percent,
                "message": f"CPU使用率: {cpu_percent}%"
            },
            "memory": {
                "status": memory_status,
                "percent": memory_percent,
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "message": f"メモリ使用率: {memory_percent}%"
            },
            "disk": {
                "status": disk_status,
                "percent": disk_percent,
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "message": f"ディスク使用率: {disk_percent}%"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"システムリソース確認エラー: {str(e)}"
        }

async def check_tools_status() -> Dict[str, Any]:
    """ツールの状態を確認する"""
    try:
        # ツール設定ファイルのパス
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                   "config", "tools_config.yaml")
        
        if not os.path.exists(config_path):
            return {
                "status": "error",
                "message": f"ツール設定ファイルが見つかりません: {config_path}"
            }
        
        # 設定ファイルの読み込み
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        tools = config.get("tools", {})
        enabled_tools = [name for name, tool_config in tools.items() 
                         if tool_config.get("enabled", False)]
        
        return {
            "status": "ok" if enabled_tools else "warning",
            "total_tools": len(tools),
            "enabled_tools": len(enabled_tools),
            "disabled_tools": len(tools) - len(enabled_tools),
            "message": f"有効なツール: {len(enabled_tools)}/{len(tools)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"ツール状態確認エラー: {str(e)}"
        }

async def run_system_check() -> Dict[str, Any]:
    """システム全体の診断を実行する"""
    # 各チェックを並行して実行
    db_check, api_check, resource_check, tools_check = await asyncio.gather(
        check_database_connection(),
        check_api_endpoints(),
        check_system_resources(),
        check_tools_status()
    )
    
    # システム情報の取得
    system_info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "python_version": platform.python_version(),
        "hostname": platform.node()
    }
    
    # 全体の状態を判定
    overall_status = "ok"
    components = [db_check, api_check, resource_check, tools_check]
    
    for component in components:
        if component["status"] == "error":
            overall_status = "error"
            break
        elif component["status"] == "critical" and overall_status != "error":
            overall_status = "critical"
        elif component["status"] == "warning" and overall_status not in ["error", "critical"]:
            overall_status = "warning"
    
    # 結果をまとめる
    result = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": overall_status,
        "system_info": system_info,
        "components": {
            "database": db_check,
            "api": api_check,
            "resources": resource_check,
            "tools": tools_check
        }
    }
    
    return result

if __name__ == "__main__":
    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # コマンドライン引数の解析
    import argparse
    parser = argparse.ArgumentParser(description='システム状態の診断')
    parser.add_argument('--output', help='診断結果の出力先ファイル')
    parser.add_argument('--format', choices=['text', 'json'], default='text', 
                       help='出力フォーマット (デフォルト: text)')
    args = parser.parse_args()
    
    # 診断の実行
    result = asyncio.run(run_system_check())
    
    # 結果の表示
    if args.format == 'json':
        output = json.dumps(result, indent=2)
    else:
        # テキスト形式での出力
        lines = [
            f"システム診断レポート - {result['timestamp']}",
            f"全体状態: {result['status'].upper()}",
            "",
            "システム情報:",
            f"  OS: {result['system_info']['os']} {result['system_info']['os_version']}",
            f"  ホスト名: {result['system_info']['hostname']}",
            f"  Python: {result['system_info']['python_version']}",
            "",
            "コンポーネント状態:",
            f"  データベース: {result['components']['database']['status'].upper()} - {result['components']['database'].get('message', '')}",
            f"  API: {result['components']['api']['status'].upper()} - {len([e for e in result['components']['api']['endpoints'].values() if e['status'] == 'ok'])}/{len(result['components']['api']['endpoints'])} エンドポイントが正常",
            f"  システムリソース: {result['components']['resources']['status'].upper()}",
            f"    CPU: {result['components']['resources']['cpu']['percent']}%",
            f"    メモリ: {result['components']['resources']['memory']['percent']}% ({result['components']['resources']['memory']['used_gb']}/{result['components']['resources']['memory']['total_gb']} GB)",
            f"    ディスク: {result['components']['resources']['disk']['percent']}% ({result['components']['resources']['disk']['used_gb']}/{result['components']['resources']['disk']['total_gb']} GB)",
            f"  ツール: {result['components']['tools']['status'].upper()} - 有効: {result['components']['tools']['enabled_tools']}/{result['components']['tools']['total_tools']}"
        ]
        output = "\n".join(lines)
    
    # 出力先の指定があれば、ファイルに書き込む
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        logger.info(f"診断結果を {args.output} に出力しました")
    else:
        # 標準出力に表示
        print(output)
```

## バッチ処理実行例

### レポート生成

バッチ処理でレポートを自動生成する例：

```bash
# 昨日の監査に関するレポートを生成
python src/scripts/generate_reports.py --date yesterday

# 特定の期間のレポートを生成
python src/scripts/generate_reports.py --start-date 2023-01-01 --end-date 2023-01-31

# 特定の形式でレポートを生成
python src/scripts/generate_reports.py --format pdf
```

### データベースバックアップ

データベースを定期的にバックアップする例：

```bash
# データベースの完全バックアップを実行
python src/scripts/backup_db.py --type full

# 特定のスキーマのみバックアップ
python src/scripts/backup_db.py --schema audit_data

# バックアップファイルの出力先を指定
python src/scripts/backup_db.py --output /path/to/backup/dir
```

## スケジュール実行

これらのスクリプトを定期的に実行するためのcrontab設定例：

```bash
# 毎日午前2時にデータベースをバックアップ
0 2 * * * /usr/bin/python /path/to/project/src/scripts/backup_db.py --type full

# 毎週月曜日の午前3時に古いデータを削除
0 3 * * 1 /usr/bin/python /path/to/project/src/scripts/cleanup_old_data.py --days 90

# 毎日午前4時にシステム状態を確認
0 4 * * * /usr/bin/python /path/to/project/src/scripts/check_system.py --output /var/log/audit_system/daily_check.log
```

## スクリプトの拡張方法

### 新しいスクリプトの追加

新しいスクリプトを追加するには、以下の手順に従います：

1. 新しいPythonファイル（例：`new_script.py`）を作成
2. 適切なインポートと初期化を行う
3. コマンドライン引数を解析する
4. ヘルパー関数を実装する
5. メイン処理を実装する

```python
# new_script.py の例
import os
import sys
import logging
import argparse
from typing import Dict, Any

# ルートディレクトリをパスに追加して相対インポートを有効にする
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# 必要なモジュールをインポート
from src.core.config import settings

logger = logging.getLogger(__name__)

def do_something(param1: str, param2: int) -> Dict[str, Any]:
    """スクリプトの主要な処理を行う関数"""
    logger.info(f"処理を開始します: {param1}, {param2}")
    
    # ここに処理を実装
    result = {
        "status": "success",
        "param1": param1,
        "param2": param2
    }
    
    return result

if __name__ == "__main__":
    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='新しいスクリプトの説明')
    parser.add_argument('--param1', required=True, help='パラメーター1の説明')
    parser.add_argument('--param2', type=int, default=10, help='パラメーター2の説明')
    args = parser.parse_args()
    
    # 処理の実行
    try:
        result = do_something(args.param1, args.param2)
        logger.info(f"処理が完了しました: {result}")
    except Exception as e:
        logger.error(f"処理中にエラーが発生しました: {e}")
        sys.exit(1)
```

### ユースケースとの対応

スクリプトモジュールは以下のユースケースをサポートします：

1. **システム初期化**
   - 初回セットアップ時のデータベースとツールの初期化
   - 設定ファイルの生成とカスタマイズ

2. **データメンテナンス**
   - 定期的なバックアップによるデータ保護
   - 古いデータの削除によるストレージ最適化

3. **自動監査プロセス**
   - バッチ監査の自動実行
   - レポートの定期的な生成と配布

4. **システム監視**
   - リソース使用状況の監視
   - 構成要素の稼働状態チェック

## セキュリティ上の注意事項

スクリプトを安全に使用するための注意点：

1. **権限管理**
   - スクリプトの実行には適切な権限を持つユーザーのみ許可する
   - 機密データにアクセスするスクリプトには特に注意

2. **パスワード管理**
   - スクリプト内にハードコードされたパスワードを避ける
   - 環境変数または安全な認証情報管理を使用する

3. **エラーハンドリング**
   - 適切なエラーハンドリングを実装し、エラー状態を明確に報告
   - 障害時にも安全な状態を維持する

4. **ログ記録**
   - 重要な操作は監査ログに記録
   - デバッグ情報が本番環境で漏洩しないよう注意

## ベストプラクティス

1. **冪等性の確保**
   - スクリプトは何度実行しても同じ結果になるよう設計する
   - 既存の状態を確認してから処理を実行する

2. **エラー処理と回復**
   - 堅牢なエラー処理を実装
   - 途中で失敗した場合のロールバック機能を提供

3. **ログ出力と監視**
   - 詳細なログを出力して操作の追跡を可能にする
   - 長時間実行されるスクリプトは進捗状況を報告する

4. **効率的な実装**
   - リソースを効率的に使用し、不要な処理を避ける
   - 大規模データセットを扱う場合はバッチ処理やストリーミング処理を検討 