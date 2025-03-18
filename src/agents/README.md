# エージェントモジュールガイド

このディレクトリには内部監査AIエージェントシステムで使用されるエージェントの実装が含まれています。
各エージェントは特定の役割を持ち、協調して監査業務を効率的に実行します。

## エージェントの概要

システムは複数のエージェントによる分業体制でタスクを実行します。各エージェントの役割は以下の通りです：

1. **エージェントA (`agent_a.py`)**
   - 役割: 監査手続き理解・設計
   - 機能:
     - 監査手続きの理解と分析
     - 監査基準と判断ルールの定義
     - テスト計画の立案と指示書の作成
     - エージェントBへの指示提供

2. **エージェントB (`agent_b.py`)**
   - 役割: サンプル検証実行
   - 機能:
     - サンプルデータの検証実行
     - 補助ツールの活用による詳細検証
     - 検証結果の整理
     - 不明点の解決（ツール活用→追加情報要求→人間への質問）

3. **エージェントC (`agent_c.py`)**
   - 役割: 結果集約
   - 機能:
     - 複数サンプルの検証結果の集約
     - パターン認識と共通課題の抽出
     - 監査所見のとりまとめ
     - 報告書素材の提供

4. **エージェントD (`agent_d.py`)**
   - 役割: 報告書作成
   - 機能:
     - 監査報告書の作成
     - エビデンスの整理
     - 改善提案の作成
     - 最終報告書の編集

## ファイル構成

```
agents/
├── agent_a.py  - 監査手続き理解・設計エージェント
├── agent_b.py  - サンプル検証実行エージェント
├── agent_c.py  - 結果集約エージェント
├── agent_d.py  - 報告書作成エージェント
└── __init__.py - パッケージ初期化ファイル
```

## エージェント間の関係

エージェント間は疎結合なメッセージング方式で連携します。基本的な情報の流れは以下の通りです：

```
エージェントA ──指示─→ エージェントB ──結果─→ エージェントC ──素材─→ エージェントD
             ←─質問─┘             ←─質問─┘             ←─質問─┘
```

## エージェントの実装詳細

各エージェントは共通の基底クラス `AgentBase` を継承して実装されています。

### 共通構造

```python
class AgentX(AgentBase[AgentXState]):
    """エージェントXの実装"""
    
    def __init__(self):
        """初期化"""
        super().__init__(agent_id=settings.AGENT_X_ID, state_class=AgentXState)
        
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """メッセージ処理のエントリーポイント"""
        # メッセージタイプに応じた処理分岐
        
    async def handle_xxx(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """各種メッセージハンドラ"""
        # 特定タイプのメッセージ処理
```

### エージェントBのツール活用（ユースケース実装例）

エージェントBは以下のような方法でツールを活用します：

```python
# ツール実行メソッド
async def _execute_tool(self, tool_id: str, params: Dict[str, Any]) -> ToolResult:
    """ツールの実行"""
    return await tool_registry.execute_tool(tool_id, params)

# 画像処理ツール活用例
async def process_image(self, image_path: str, operation: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """画像処理ツールを利用する"""
    tool_params = {
        "operation": operation,
        "image_path": image_path,
        **(params or {})
    }
    result = await self._execute_tool('ImageProcessor_001', tool_params)
    return result.dict()
```

## ユースケースとの対応

ユースケースに記載されているエージェント間の対話は、以下のように実装されています：

1. **「エージェントA→エージェントB（通常の指示）」**:
   - `agent_a.py` の `send_instruction_to_agent_b()` メソッド
   - メッセージングシステムを通じた指示の送信

2. **「エージェントB→エージェントA（不明点と対応策の提案）」**:
   - `agent_b.py` の `send_question_to_agent_a()` メソッド
   - 不明点と解決策の提案を構造化したメッセージング

3. **「エージェントB→画像処理ツール（実行要求）」**:
   - `agent_b.py` の `process_image()` メソッド
   - ツールレジストリを通じたツール実行

## 拡張方法

### 新しいエージェントの追加

1. エージェント状態クラスの定義
   ```python
   class AgentEState(AgentState):
       """エージェントEの状態クラス"""
       # 状態プロパティを定義
   ```

2. エージェントクラスの実装
   ```python
   class AgentE(AgentBase[AgentEState]):
       """新しいエージェントE"""
       
       def __init__(self):
           """初期化"""
           super().__init__(agent_id=settings.AGENT_E_ID, state_class=AgentEState)
           
       async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
           """メッセージ処理"""
           # 実装
   ```

3. `config.py` に新しいエージェントIDを追加
4. 必要に応じてワークフローを更新

### エージェント機能の拡張

エージェントに新しい機能を追加するには、対応するエージェントファイルに新しいメソッドを追加します：

```python
async def handle_new_task(self, content: Dict[str, Any]) -> Dict[str, Any]:
    """新しいタスク処理"""
    # 実装
    
async def new_helper_method(self, param1, param2):
    """新しいヘルパーメソッド"""
    # 実装
```

## ユースケースを実現するためのヒント

1. **階層的問題解決アプローチの実装**:
   - エージェントBの `resolve_issue()` メソッドを拡張
   - 3段階の解決プロセス（ツール→追加情報→人間）を実装

2. **監査証跡の強化**:
   - 各エージェントの `_save_agent_state()` メソッドを活用
   - 判断プロセスを記録する詳細なロギング追加

3. **新規ユースケースの追加**:
   - 適切なエージェントに新しいメッセージハンドラを追加
   - 必要に応じて新しいツールを開発・統合 