# 補助ツールモジュールガイド

このディレクトリには内部監査AIエージェントシステムで使用される補助ツールの実装が含まれています。
これらのツールはエージェント（特にエージェントB）が監査業務を効率的に実行するために活用されます。

## ツールの概要

ユースケースに記載されているような「階層的問題解決アプローチ」を実現するため、以下のような様々なツールが提供されています：

1. **画像処理ツール (`image_processor.py`)**
   - 機能:
     - 印影検出・検証
     - 画像の部分拡大
     - 画像の鮮明化
     - 文字/署名の抽出・検証
   - ユースケース例:
     - 領収書の印影検証
     - 承認者の署名確認

2. **データ照合ツール (`data_validator.py`)**
   - 機能:
     - 社員マスタとの照合
     - 権限レベル確認
     - データ一貫性検証
   - ユースケース例:
     - 承認者の権限確認
     - 取引担当者の確認

3. **Excel解析ツール (`excel_analyzer.py`)**
   - 機能:
     - 複数シートのデータ構造解析
     - 特定条件でのデータ抽出
     - シート間の関連データ照合
   - ユースケース例:
     - 複数シートにまたがる取引履歴の検証
     - 申請・承認・実行履歴の整合性確認

4. **文書解析ツール (`document_parser.py`)**
   - 機能:
     - OCRによるテキスト抽出
     - フォーマット認識
     - 形式チェック
   - ユースケース例:
     - PDFスキャンからのデータ抽出
     - 文書形式の検証

## ファイル構成

```
tools/
├── image_processor.py   - 画像処理ツール
├── data_validator.py    - データ照合ツール
├── excel_analyzer.py    - Excel解析ツール
├── document_parser.py   - 文書解析ツール
├── tool_registry.py     - ツール登録・管理
└── __init__.py          - パッケージ初期化ファイル
```

## ツールレジストリ

`tool_registry.py` はすべてのツールを登録・管理し、エージェントからのアクセスを一元化します。シングルトンパターンで実装されており、以下の機能を提供します：

- ツールクラスの登録
- ツールインスタンスの生成
- ツール実行の統一インターフェース
- ツール設定の管理

```python
# ツールレジストリの使用例
from src.tools import registry

# 利用可能なツール一覧を取得
available_tools = registry.get_tool_info()

# ツールの実行
result = await registry.execute_tool('ImageProcessor_001', {
    'operation': 'partial_enlarge',
    'image_path': '/path/to/image.jpg',
    'x1': 100, 'y1': 100, 'x2': 300, 'y2': 300,
    'scale': 2.0
})
```

## ツールの実装詳細

各ツールは共通の基底クラス `ToolBase` を継承して実装されています：

```python
class SomeSpecificTool(ToolBase):
    """特定のツール実装"""
    
    def __init__(self, tool_id: str = None):
        """初期化"""
        super().__init__(tool_id)
        self.description = "このツールの説明"
        self.version = "1.0.0"
        self.capabilities = [
            "specific_operation_1",
            "specific_operation_2"
        ]
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """パラメータのバリデーション"""
        # パラメータ検証ロジック
        return True
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """ツール実行のメイン処理"""
        operation = params.get("operation")
        
        if operation == "specific_operation_1":
            # 特定操作1の処理
            result_data = self._process_operation_1(params)
        elif operation == "specific_operation_2":
            # 特定操作2の処理
            result_data = self._process_operation_2(params)
        else:
            return ToolResult(
                tool_id=self.tool_id,
                status="error",
                data={},
                error_message="サポートされていない操作です"
            )
        
        return ToolResult(
            tool_id=self.tool_id,
            status="success",
            data=result_data
        )
```

## 設定ファイル

ツールの設定は `config/tools_config.yaml` ファイルで管理されています：

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
  
  # 他のツール設定...
```

## ユースケースとの対応

ユースケースに記載されているツール活用例は以下のように実装されています：

1. **「エージェントB→画像処理ツール（実行要求）」**
   - エージェントBの `process_image()` メソッドを使用
   - ツールレジストリを介してImageProcessorを実行

2. **「画像処理ツール→エージェントB（実行結果）」**
   - `ToolResult` オブジェクトによる結果返却
   - エージェントBでの結果処理

3. **「エージェントB→データ照合ツール（実行要求）」**
   - エージェントBの内部メソッドで実行
   - 社員マスタデータとの照合処理

## 拡張方法

### 新しいツールの追加

1. ツールクラスの実装
   ```python
   # new_tool.py
   from src.core.tool_base import ToolBase, ToolResult
   
   class NewTool(ToolBase):
       """新しいツール実装"""
       
       def __init__(self, tool_id: str = None):
           """初期化"""
           super().__init__(tool_id)
           self.description = "新しいツールの説明"
           self.capabilities = ["operation1", "operation2"]
           
       async def execute(self, params: Dict[str, Any]) -> ToolResult:
           """ツール実行のメイン処理"""
           # 実装
           return ToolResult(tool_id=self.tool_id, status="success", data={...})
   ```

2. 設定ファイルへの追加
   ```yaml
   # config/tools_config.yaml に追加
   NewTool:
     module: src.tools.new_tool
     class: NewTool
     enabled: true
     id_suffix: "001"
     metadata:
       description: "新しいツールの説明"
       priority: medium
   ```

3. ツールを使用するヘルパーメソッドの追加（オプション）
   ```python
   # agent_b.py に追加
   async def use_new_tool(self, param1, param2) -> Dict[str, Any]:
       """新しいツールを使用するヘルパーメソッド"""
       tool_params = {
           "operation": "operation1",
           "param1": param1,
           "param2": param2
       }
       result = await self._execute_tool('NewTool_001', tool_params)
       return result.dict()
   ```

### 既存ツールの拡張

1. 新しい操作（capability）の追加
   ```python
   # 既存のツールクラスに追加
   self.capabilities.append("new_operation")
   
   # execute()メソッドに新しい操作の処理を追加
   elif operation == "new_operation":
       result_data = self._process_new_operation(params)
   ```

## ユースケースを実現するためのヒント

1. **印影検出ツールの強化**
   - 機械学習モデルの統合による高精度化
   - 複数印影パターンのサポート

2. **Excelデータ解析の高度化**
   - シート間関係の自動検出
   - 過去データとの差分検出機能

3. **新たな監査業務向けツールの追加**
   - 契約書解析ツール
   - リスク評価ツール
   - 異常検知ツール 