# エージェントアーキテクチャ

## 概要

内部監査サンプルデータ自動テストAIエージェントシステムは、4つの専門AIエージェントで構成されています。各エージェントは特定の監査プロセスタスクに特化し、LLM（大規模言語モデル）を活用して高度な自然言語処理と意思決定を行います。

## エージェント共通基盤

すべてのエージェントは共通の基盤クラス「AgentBase」を継承しています。

```python
class AgentBase:
    def __init__(self, model_name: str, model_provider: str, prompt_template: str):
        self.model_name = model_name
        self.model_provider = model_provider
        self.prompt_template = prompt_template
        self.llm = self._initialize_llm()
        
    async def execute(self, agent_state: AgentState) -> Dict[str, Any]:
        """エージェントのメイン実行メソッド"""
        # 入力の準備
        prompt = self._prepare_prompt(agent_state)
        
        # LLMの実行
        response = await self._run_llm(prompt)
        
        # 結果の解析と検証
        output = self._parse_response(response)
        self._validate_output(output)
        
        return output
```

### AgentState

エージェントの入出力と状態を管理するデータ構造です。

```python
class AgentState(TypedDict):
    """エージェントの状態を表すデータ構造"""
    input_data: Dict[str, Any]  # エージェントへの入力データ
    output_data: Optional[Dict[str, Any]]  # エージェントからの出力データ
    metadata: Dict[str, Any]  # メタデータ（実行時間、トークン数など）
    error: Optional[Dict[str, Any]]  # エラー情報
```

## エージェント管理サービス

エージェントの登録、ライフサイクル管理、タスク割り当て、監視を一元的に行うサービスクラスです。単一責任の原則（SRP）と依存性逆転の原則（DIP）に基づいて設計されています。

```python
class AgentManagementService:
    """
    エージェント管理サービス（改善版）
    
    このサービスクラスは以下の役割を持ちます:
    1. API層とコア機能の橋渡し
    2. エージェント管理機能の一元化
    3. エージェント関連の操作の統合インターフェース提供
    """
    
    def register_agent(
        self, 
        agent_id: str, 
        agent_type: str,
        agent_role: Optional[AgentRole] = None,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """エージェントを登録します"""
        # 実装詳細...
    
    def assign_task(
        self, 
        task_id: str, 
        agent_id: str, 
        task_data: Dict[str, Any],
        task_type: Optional[str] = None,
        workflow_id: Optional[str] = None,
        context_id: Optional[str] = None,
        priority: int = 1
    ) -> bool:
        """タスクをエージェントに割り当てます"""
        # 実装詳細...
    
    def update_task_status(
        self, 
        task_id: str, 
        status: str, 
        result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """タスクの状態を更新します"""
        # 実装詳細...
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """エージェントの状態を取得します"""
        # 実装詳細...
    
    def send_message(
        self, 
        from_agent_id: str, 
        to_agent_id: str, 
        message_type: str, 
        content: Dict[str, Any],
        workflow_id: Optional[str] = None,
        context_id: Optional[str] = None,
        priority: str = "normal",
        requires_response: bool = False
    ) -> str:
        """エージェント間でメッセージを送信します"""
        # 実装詳細...
```

### シングルトンパターンによる一貫した管理

```python
# シングルトンインスタンスを提供する関数
def get_agent_management_service() -> AgentManagementService:
    """エージェント管理サービスのシングルトンインスタンスを取得します"""
    return AgentManagementService()

# FastAPI依存関係注入関数
def get_agent_management_service_dependency() -> AgentManagementService:
    """FastAPIの依存関係注入のためのプロバイダー関数"""
    return get_agent_management_service()
```

### データ構造

```python
# エージェント情報
self.agents: Dict[str, Dict[str, Any]] = {}

# タスク情報
self.tasks: Dict[str, Dict[str, Any]] = {}

# エージェント役割情報
self.agent_roles: Dict[str, AgentRole] = {}

# アクティブタスク情報
self.active_tasks: Dict[str, Dict[str, Any]] = {}

# タスク割り当て情報
self.task_assignments: Dict[str, set] = {}
```

## 各エージェントの役割と構造

### Agent A: 監査手続き理解・テスト計画作成エージェント

監査手続きを分析し、テスト計画を作成するエージェントです。

```python
class AgentA(AgentBase):
    """監査手続き理解・テスト計画作成エージェント"""
    
    def __init__(self):
        super().__init__(
            model_name="gpt-4",
            model_provider="openai",
            prompt_template="agent_a/plan_test"
        )
    
    def _prepare_prompt(self, agent_state: AgentState) -> str:
        """
        監査手続きとサンプルデータのメタ情報からプロンプトを生成
        """
        # 実装詳細...
        
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        LLMからのレスポンスをパースしてテスト計画を抽出
        """
        # 実装詳細...
```

#### Agent A の入出力

- **入力**: 監査手続きテキスト、サンプルデータメタ情報
- **出力**: テスト計画（テスト項目リスト、検証方法、期待結果など）

### Agent B: テスト実行エージェント

テスト計画に基づいてサンプルデータに対するテストを実行するエージェントです。

```python
class AgentB(AgentBase):
    """テスト実行エージェント"""
    
    def __init__(self):
        super().__init__(
            model_name="gpt-4",
            model_provider="openai",
            prompt_template="agent_b/execute_test"
        )
    
    def _prepare_prompt(self, agent_state: AgentState) -> str:
        """
        テスト計画とサンプルデータからプロンプトを生成
        """
        # 実装詳細...
        
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        LLMからのレスポンスをパースしてテスト結果を抽出
        """
        # 実装詳細...
```

#### Agent B の入出力

- **入力**: テスト計画、サンプルデータ
- **出力**: テスト結果（テスト項目の成否、検出された異常、例外など）

### Agent C: 結果評価・総括エージェント

テスト結果を評価し、監査総括を作成するエージェントです。

```python
class AgentC(AgentBase):
    """結果評価・総括エージェント"""
    
    def __init__(self):
        super().__init__(
            model_name="gpt-4",
            model_provider="openai",
            prompt_template="agent_c/evaluate_results"
        )
    
    def _prepare_prompt(self, agent_state: AgentState) -> str:
        """
        テスト結果と監査目的からプロンプトを生成
        """
        # 実装詳細...
        
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        LLMからのレスポンスをパースして評価結果を抽出
        """
        # 実装詳細...
```

#### Agent C の入出力

- **入力**: テスト結果、監査目的、テスト計画
- **出力**: 評価結果（重要な発見事項、リスクアセスメント、追加テスト推奨など）

### Agent D: 報告書作成エージェント

評価結果に基づいて監査報告書を作成するエージェントです。

```python
class AgentD(AgentBase):
    """報告書作成エージェント"""
    
    def __init__(self):
        super().__init__(
            model_name="gpt-4",
            model_provider="openai",
            prompt_template="agent_d/generate_report"
        )
    
    def _prepare_prompt(self, agent_state: AgentState) -> str:
        """
        評価結果と監査情報からプロンプトを生成
        """
        # 実装詳細...
        
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        LLMからのレスポンスをパースして報告書を抽出
        """
        # 実装詳細...
```

#### Agent D の入出力

- **入力**: 評価結果、監査目的、テスト計画、テスト結果
- **出力**: 監査報告書（エグゼクティブサマリー、詳細分析、推奨事項など）

## プロンプトテンプレート管理

各エージェントは、YAML形式で定義されたプロンプトテンプレートを使用します。

```yaml
# src/prompts/agent_a/plan_test.yaml
name: テスト計画作成
description: 監査手続きを理解し、テスト計画を作成するためのプロンプト
version: 1.0.0
template: |
  あなたは内部監査の専門家です。以下の監査手続きを分析し、テスト計画を作成してください。

  ## 監査手続き
  {{procedure_text}}

  ## サンプルデータ情報
  {{sample_data_info}}

  ## 出力形式
  JSON形式で以下の構造に従って出力してください:
  ```json
  {
    "test_plan": {
      "objective": "テストの目的",
      "test_items": [
        {
          "id": "test-001",
          "description": "テスト項目の説明",
          "method": "テスト方法",
          "expected_result": "期待される結果"
        }
      ]
    }
  }
  ```
```

## エージェント間のデータフロー

エージェント管理サービスを中心に各エージェント間でメッセージとタスクが流れます。

```
                        ┌────────────────────────┐
                        │                        │
                        │  AgentManagementService │
                        │                        │
                        └───────────┬────────────┘
                                    │
                 ┌─────────────────┼────────────────┐
                 │                 │                │
    ┌────────────▼────────┐ ┌─────▼──────┐ ┌───────▼───────┐
    │                     │ │            │ │               │
    │ タスク割り当て        │ │ メッセージング │ │ 状態管理      │
    │                     │ │            │ │               │
    └─────────┬───────────┘ └──────┬─────┘ └───────┬───────┘
              │                    │               │
              └────────────┬───────┴───────────────┘
                           │
     ┌─────────────────────┼────────────────────────┐
     │                     │                        │
┌────▼───┐           ┌─────▼───┐              ┌─────▼───┐
│        │           │         │              │         │
│Agent A ├──────────►│ Agent B ├─────────────►│ Agent C ├─────────────┐
│        │           │         │              │         │             │
└────────┘           └─────────┘              └─────────┘             │
     ▲                                                                │
     │                                                                │
     │                                                                │
     │                       ┌─────────┐                              │
     └───────────────────────┤ Agent D ◄──────────────────────────────┘
                             │         │
                             └─────────┘
```

## エラーハンドリング

各エージェントは、エラーハンドリングデコレータを通じて、様々なエラー状況に対処する機能を持っています。

```python
@with_error_handling
async def execute(self, agent_state: AgentState) -> Dict[str, Any]:
    """エージェントのメイン実行メソッド（エラーハンドリング付き）"""
    # 実装詳細...
```

エラーハンドリングの詳細については、[エラーハンドリング機能](./error_handling.md)を参照してください。

## 監査証跡システムとエージェント間通信

### 監査証跡システム

#### 概要
監査証跡システムは、エージェントの活動、通信、意思決定プロセスを詳細に記録・追跡するためのフレームワークです。このシステムにより、AIエージェントによる意思決定プロセスの透明性と説明可能性が向上し、監査における信頼性と検証可能性が確保されます。

#### 主要コンポーネント

1. **データモデル**
   - `AuditTrail`: エージェントのアクションや活動を記録
   - `MessageLog`: エージェント間のメッセージを記録
   - `AgentDecision`: エージェントの意思決定プロセスと結果を記録

2. **リポジトリ**
   - `AuditTrailRepository`: 監査証跡データの作成、取得、検索、更新
   - `MessageLogRepository`: メッセージログの管理
   - `AgentDecisionRepository`: 決定プロセスデータの管理

3. **ユーティリティ関数**
   - 監査証跡の記録: `record_audit_trail()`
   - メッセージログの記録: `record_message_log()`
   - エージェント決定の記録: `record_agent_decision()`
   - 監査データの取得: `get_workflow_audit_trail()`
   - データのエクスポート: `export_workflow_audit_trail()`

### 強化されたエージェント間通信

#### 機能拡張
エージェント間通信機能が大幅に強化され、以下の機能が追加されました：

1. **MessageClient拡張**
   - メッセージ履歴管理: 送受信したメッセージを保持
   - 会話履歴管理: エージェントごとの会話履歴を追跡
   - 決定プロセス記録: 重要な意思決定を追跡
   - 監査証跡連携: 通信活動と監査証跡システムを統合

2. **メッセージの標準化**
   - 構造化されたメッセージフォーマット
   - メッセージのバリデーション
   - タイプ別のコンテンツ標準化
   - 優先度管理とメタデータ付与

3. **効率的な通信パターン**
   - 非同期メッセージング
   - 待機と応答メカニズム
   - コンテキスト伝播
   - エラー処理と再試行メカニズム

#### 通信フロー
エージェント間の通信は以下の流れで処理されます：

1. 送信側エージェントがメッセージを作成し標準化
2. メッセージブローカーを通じてメッセージを送信
3. 監査証跡システムにメッセージが記録される
4. 受信側エージェントがメッセージを受信し処理
5. 応答が必要な場合、応答メッセージが作成され送信
6. 全ての通信が監査証跡としてログに記録される

### システム統合

監査証跡システムとエージェント間通信機能は、以下のように統合されています：

1. **ワークフローエンジンとの統合**
   - ワークフローの各ステップで自動的に監査証跡を生成
   - ワークフロー状態の変更を追跡
   - エラーや例外を詳細に記録

2. **エージェントベースクラスとの統合**
   - 各エージェントに標準的な監査機能を提供
   - 一貫した通信パターンの確保
   - 透明性と説明可能性の向上

3. **フロントエンドとの統合**
   - 監査データのAPI経由でのアクセス
   - 監査証跡の視覚化
   - 監査レポートの生成

### ユースケース例

1. **監査の透明性**
   - 監査プロセス全体の詳細な記録
   - エージェントの意思決定の追跡
   - 結果の検証と説明可能性の確保

2. **問題診断と最適化**
   - エラーの根本原因分析
   - パフォーマンスボトルネックの特定
   - システム改善点の発見

3. **コンプライアンス**
   - 監査プロセスのコンプライアンス確認
   - 決定プロセスの透明性確保
   - 規制要件への適合証明 