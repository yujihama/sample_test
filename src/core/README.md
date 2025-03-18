# コアモジュールガイド

このディレクトリには内部監査AIエージェントシステムの基盤となるコアコンポーネントが含まれています。
システム全体のアーキテクチャを支える重要なクラスと機能が実装されています。

## コアコンポーネントの概要

1. **エージェント基盤 (`agent_base.py`)**
   - AgentBaseクラス: すべてのエージェントの基底クラス
   - AgentStateクラス: エージェント状態の管理
   - メッセージ処理の共通インターフェース

2. **ツール基盤 (`tool_base.py`)**
   - ToolBaseクラス: すべてのツールの基底クラス
   - ToolResultクラス: ツール実行結果の標準形式
   - パラメータバリデーションの枠組み

3. **ワークフロー管理 (`workflow.py`)**
   - 監査ワークフローの定義と実行
   - エージェント間の連携フローの管理
   - ワークフロー状態の追跡

4. **メッセージング (`messaging.py`)**
   - エージェント間通信の実装
   - メッセージングキューの管理
   - 非同期通信のサポート

5. **コンテキスト管理 (`context_manager.py`)**
   - 共有コンテキストの管理
   - エージェント間のコンテキスト共有
   - コンテキスト履歴の追跡

6. **LLM統合 (`llm/`)**
   - 大規模言語モデルとの連携
   - プロンプト管理と最適化
   - モデル応答のパース処理

7. **設定管理 (`config.py`)**
   - アプリケーション設定の一元管理
   - 環境変数との統合
   - 動的設定の読み込み

8. **エラー処理 (`error_handler.py`)**
   - エラー処理と例外管理
   - フォールバック戦略
   - 監査証跡のためのエラーログ

## ファイル構成

```
core/
├── agent_base.py      - エージェント基底クラス
├── tool_base.py       - ツール基底クラス
├── workflow.py        - ワークフロー管理
├── messaging.py       - エージェント間通信
├── context_manager.py - コンテキスト管理
├── config.py          - 設定管理
├── error_handler.py   - エラー処理
├── llm/               - LLM統合モジュール
└── __init__.py        - パッケージ初期化ファイル
```

## 主要クラスと概念

### エージェント基盤

`AgentBase` クラスはシステム内のすべてのエージェントの基底クラスです。このクラスは以下の機能を提供します：

- メッセージの送受信インターフェース
- エージェント状態の管理
- 非同期タスク処理のサポート
- コンテキスト管理との連携

```python
# エージェント基底クラスの例
class AgentBase(Generic[T]):
    """エージェントの基本クラス"""
    
    def __init__(self, agent_id: str, state_class: Type[T]):
        self.agent_id = agent_id
        self.state = state_class(agent_id=agent_id)
        # ...

    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """メッセージ処理の抽象メソッド"""
        raise NotImplementedError()
```

### ツール基盤

`ToolBase` クラスはシステム内のすべてのツールの基底クラスです：

```python
# ツール基底クラスの例
class ToolBase(ABC):
    """補助ツール基底クラス"""
    
    def __init__(self, tool_id: str = None):
        self.tool_id = tool_id or f"{self.__class__.__name__}_{uuid.uuid4().hex[:8]}"
        # ...
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """ツール実行のメイン処理"""
        pass
```

### ワークフロー管理

`workflow.py` は監査プロセス全体のワークフローを定義・管理します：

```python
# ワークフロー定義の例
class AuditWorkflow:
    """監査ワークフロー管理"""
    
    def __init__(self, workflow_id: str, procedure_id: str, sample_id: str):
        self.workflow_id = workflow_id
        self.procedure_id = procedure_id
        self.sample_id = sample_id
        self.status = "created"
        self.steps = []
        # ...
        
    async def start(self):
        """ワークフローの開始"""
        # ワークフロー実行ロジック
```

## ユースケースとの関連

コアモジュールはユースケースに記載されている監査プロセスの基盤となる機能を提供します：

1. **エージェント間通信の実現**
   - `messaging.py` がエージェント間のメッセージング基盤を提供
   - ユースケースにある「エージェントA→エージェントB」のようなやり取りを実現

2. **ツール活用の基盤**
   - `tool_base.py` がツール実装の共通インターフェースを定義
   - ユースケースの「エージェントB→ツール」のやり取りの基盤

3. **階層的解決アプローチの実現**
   - `workflow.py` が問題解決の流れを管理
   - 「ツール→追加情報→人間」という階層的な解決プロセスの管理

## 拡張方法

### 新しいコアコンポーネントの追加

1. 新しいコアモジュールファイルの作成
   ```python
   # new_core_component.py
   
   class NewCoreComponent:
       """新しいコアコンポーネント"""
       
       def __init__(self, config=None):
           self.config = config or {}
           # 初期化
           
       def core_functionality(self, params):
           """主要機能"""
           # 実装
   ```

2. 新コンポーネントのインポートと使用
   ```python
   # 他のファイルでの使用例
   from src.core.new_core_component import NewCoreComponent
   
   component = NewCoreComponent()
   result = component.core_functionality(params)
   ```

### 既存コアコンポーネントの拡張

既存のコンポーネントを拡張するには、対象のファイルに新しいメソッドや機能を追加します：

```python
# エージェント基底クラスの拡張例
class AgentBase(Generic[T]):
    # 既存のメソッド...
    
    async def new_core_functionality(self, params):
        """新しい共通機能"""
        # 実装
```

## 設計原則

コアモジュールは以下の設計原則に従っています：

1. **疎結合**: コンポーネント間の依存関係を最小限に
2. **抽象化**: 具体的な実装より抽象インターフェースを優先
3. **単一責任**: 各モジュールは明確に定義された単一の責任を持つ
4. **拡張性**: 新機能の追加が容易な設計
5. **再利用性**: 共通機能の再利用を促進

## ワークフロー拡張のためのヒント

1. **新しいワークフロータイプの追加**
   - `workflow.py` に新しいワークフロークラスを追加
   - 既存のワークフロー基盤を継承して拡張

2. **メッセージングの拡張**
   - 新しいメッセージタイプの追加
   - メッセージングパターンの強化

3. **コンテキスト管理の強化**
   - より高度なコンテキスト共有メカニズムの実装
   - 長期的なコンテキスト追跡機能の追加 