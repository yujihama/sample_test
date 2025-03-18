# 設定ファイル管理ガイド

このディレクトリには内部監査AIエージェントシステムの設定ファイルが含まれています。
各設定ファイルはシステムの特定の側面を制御し、外部環境との接続を構成します。

## 設定ファイルの概要

### 現在実装されている設定ファイル

1. **ツール設定 (`tools_config.yaml`)**
   - ツール登録情報
   - ツールパラメータ
   - ツール有効/無効設定

### 今後実装が推奨される設定ファイル

以下の設定ファイルは現在実装されていませんが、システムの拡張時に作成することを推奨します：

1. **アプリケーション設定 (`app_config.yaml`)**
   - アプリケーション全体の基本設定
   - 環境別設定（開発、テスト、本番）
   - サーバー設定（ホスト、ポート等）

2. **データベース設定 (`database.yaml`)**
   - データベース接続情報
   - マイグレーション設定
   - リードレプリカ設定（該当する場合）

3. **LLM設定 (`llm_config.yaml`)**
   - LLM接続パラメータ
   - APIキー設定（実際のキーは環境変数または.envファイルから読み込み）
   - モデルパラメータ設定

4. **ロギング設定 (`logging.yaml`)**
   - ログレベル設定
   - ログローテーション設定
   - フォーマット設定

## 現在のファイル構成

```
config/
├── tools_config.yaml   - ツール設定（実装済み）
└── README.md           - このガイド
```

## 推奨ファイル構成（将来的）

```
config/
├── app_config.yaml     - アプリケーション設定（将来的）
├── database.yaml       - データベース設定（将来的）
├── llm_config.yaml     - LLM設定（将来的）
├── logging.yaml        - ロギング設定（将来的）
├── tools_config.yaml   - ツール設定（実装済み）
└── README.md           - このガイド
```

## 設定ファイルの例

### 現在実装されているファイル例

#### ツール設定例 (`tools_config.yaml`)

```yaml
tools:
  # 画像処理ツール
  ImageProcessor:
    module: src.tools.image_processor
    class: ImageProcessor
    enabled: true
    id_suffix: "001"
    metadata:
      description: "領収書などの画像分析や処理を行うツール"
      priority: high
      capabilities:
        - 印影検出・検証
        - 画像の鮮明化
        - 部分領域の拡大
  
  # エクセル解析ツール
  ExcelAnalyzer:
    module: src.tools.excel_analyzer
    class: ExcelAnalyzer
    enabled: true
    id_suffix: "001"
    metadata:
      description: "Excelファイルの構造解析や特定データの抽出を行うツール"
      priority: high
      capabilities:
        - 複数シートのデータ構造解析
        - 特定IDに基づくレコード抽出
        - シート間の関連データ照合
```

### 将来的な実装の参考例

#### アプリケーション設定例 (`app_config.yaml` - 実装例)

```yaml
app:
  name: "内部監査AIエージェントシステム"
  version: "1.0.0"
  description: "内部監査プロセスを自動化・効率化するAIエージェントシステム"

environment:
  dev:
    host: "127.0.0.1"
    port: 8000
    debug: true
    log_level: "DEBUG"
  
  test:
    host: "127.0.0.1"
    port: 8000
    debug: false
    log_level: "INFO"
  
  prod:
    host: "0.0.0.0"
    port: 8000
    debug: false
    log_level: "WARNING"

paths:
  upload_dir: "uploads"
  logs_dir: "logs"
  temp_dir: "temp"
```

## 設定の読み込みと使用

現在のシステムは `tools_config.yaml` のみを使用しています。将来的には以下の方法で設定ファイルを読み込むことを推奨します：

```python
# src/core/config.py の実装例
import os
import yaml
from pydantic import BaseSettings

class Settings(BaseSettings):
    # 基本設定
    APP_NAME: str = "内部監査AIエージェントシステム"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = os.getenv("APP_ENV", "development")
    
    # パス設定
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CONFIG_DIR: str = os.path.join(BASE_DIR, "..", "config")
    
    # 動的に読み込む設定
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._load_configs()
    
    def _load_configs(self):
        """設定ファイルの読み込み"""
        # ツール設定の読み込み（現在実装済み）
        tool_config_path = os.path.join(self.CONFIG_DIR, "tools_config.yaml")
        if os.path.exists(tool_config_path):
            with open(tool_config_path, "r") as f:
                self.TOOL_CONFIG = yaml.safe_load(f)
        
        # 将来的に実装予定の設定ファイル読み込み
        # app_config_path = os.path.join(self.CONFIG_DIR, "app_config.yaml")
        # if os.path.exists(app_config_path):
        #     with open(app_config_path, "r") as f:
        #         self.APP_CONFIG = yaml.safe_load(f)
        
        # 他の設定ファイルも同様に実装予定

# シングルトンインスタンス
settings = Settings()
```

## 環境変数による上書き

セキュリティ上の理由や環境ごとの設定変更を容易にするため、多くの設定は環境変数で上書きできます。一般的な環境変数の例：

- `APP_ENV`: アプリケーション環境（development, test, production）
- `DB_URL`: データベースURL
- `LLM_API_KEY`: LLM APIキー
- `LOG_LEVEL`: ログレベル

## ユースケースとの関連

設定ファイルはユースケースの実現に重要な役割を果たします：

1. **ツール設定**
   - ユースケースで説明される様々なツール（画像処理、データ照合など）の設定
   - 特定の監査業務に合わせたツール機能の有効化/無効化

2. **エージェント間通信の設定**
   - エージェント間メッセージングキューの設定
   - タイムアウト設定

3. **監査証跡の詳細度設定**
   - ログレベルとフォーマットの設定
   - 証跡保存期間の設定

## 設定ファイルの拡張

### 新しい設定ファイルの追加

1. 設定ファイルの作成
   ```yaml
   # config/new_feature_config.yaml
   new_feature:
     enabled: true
     param1: value1
     param2: value2
   ```

2. 設定読み込みロジックの追加
   ```python
   # src/core/config.py に追加
   def _load_configs(self):
       # 既存のロード処理...
       
       # 新しい設定ファイルの読み込み
       new_feature_config_path = os.path.join(self.CONFIG_DIR, "new_feature_config.yaml")
       if os.path.exists(new_feature_config_path):
           with open(new_feature_config_path, "r") as f:
               self.NEW_FEATURE_CONFIG = yaml.safe_load(f)
   ```

### 既存設定の拡張

既存の設定ファイルを拡張するには、新しいセクションやパラメータを追加します：

```yaml
# 既存の tools_config.yaml に新しいツールを追加
tools:
  # 既存のツール設定...
  
  # 新しいツール
  NewTool:
    module: src.tools.new_tool
    class: NewTool
    enabled: true
    id_suffix: "001"
    metadata:
      description: "新しいツールの説明"
```

## 設定管理のベストプラクティス

1. **機密情報は環境変数に**
   - APIキーやパスワードなどの機密情報は設定ファイルに直接記述せず、環境変数を使用

2. **環境別設定**
   - 開発、テスト、本番環境で異なる設定を使用
   - 環境変数 `APP_ENV` で切り替え

3. **設定の検証**
   - Pydanticモデルを使用して設定値を検証
   - 必須パラメータや型チェックを実施

4. **デフォルト値の提供**
   - すべての設定項目にデフォルト値を設定
   - 設定ファイルがない場合もシステムが動作するように 