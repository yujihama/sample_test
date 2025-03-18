# ワークフローエンジン

## 概要
ワークフローエンジンは、各AIエージェント間の連携を管理し、監査プロセス全体を統括する中核コンポーネントです。LangGraphを活用した状態管理と遷移ロジックにより、複雑なワークフローを実現しています。改善版では、単一責任の原則（SRP）と依存性逆転の原則（DIP）に基づいて設計された`WorkflowService`クラスを中心に構成されています。

## 主要コンポーネント

### WorkflowState
ワークフローの状態を管理する中心的なデータクラスです。最新版では、統一されたデータモデルとして定義されています。

```python
class WorkflowState:
    """
    ワークフロー状態の基本クラス
    
    すべてのワークフロー状態オブジェクトが共通して持つプロパティを定義します。
    """
    workflow_id: str
    context_id: Optional[str] = None
    current_agent_id: Optional[str] = None
    status: str = "in_progress"  # in_progress, completed, failed, paused
    next_agent_ids: List[str] = []
    previous_agent_id: Optional[str] = None
    start_time: datetime = datetime.now()
    end_time: Optional[datetime] = None
    is_human_intervention_required: bool = False
    human_query: Optional[Dict[str, Any]] = None
    human_response: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}
    messages: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    results: Dict[str, Any] = {}
```

### GraphBuilder プロトコル
グラフ構築のための抽象インターフェースを定義するプロトコルです。依存性逆転の原則（DIP）を実現しています。

```python
class GraphBuilder(Protocol):
    """グラフビルダーのプロトコル定義"""
    
    def add_node(self, name: str, function: Callable) -> None:
        ...
    
    def add_edge(self, start: str, end: str) -> None:
        ...
    
    def add_conditional_edge(self, start: str, condition: Callable, destinations: Dict[str, str]) -> None:
        ...
    
    def set_entry_point(self, node_name: str) -> None:
        ...
    
    def compile(self) -> Any:
        ...
```

### WorkflowService
ワークフロー管理機能を統合した中核サービスクラスです。統一的なインターフェースを提供し、さまざまなタイプのワークフローをサポートします。

```python
class WorkflowService:
    """
    ワークフロー管理サービス（改善版）
    
    このサービスクラスは以下の役割を持ちます:
    1. 各種ワークフローグラフの作成を一元化
    2. ワークフロー実行機能の提供
    3. ワークフロー状態の管理
    """
    
    def create_workflow_graph(
        self,
        workflow_type: str = "agent",
        config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """ワークフローグラフを作成する（統合版）"""
        # 実装詳細...
    
    async def run_workflow(
        self,
        workflow_id: str,
        workflow_type: str = "agent",
        initial_data: Optional[Dict[str, Any]] = None,
        initial_agent_id: str = settings.AGENT_A_ID,
        config: Optional[Dict[str, Any]] = None,
        human_interaction_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """ワークフローを実行する（統合版）"""
        # 実装詳細...
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """ワークフローの状態を取得する"""
        # 実装詳細...
    
    def pause_workflow(self, workflow_id: str, reason: str = "manually_paused") -> bool:
        """ワークフローを一時停止する"""
        # 実装詳細...
    
    def resume_workflow(self, workflow_id: str) -> bool:
        """一時停止したワークフローを再開する"""
        # 実装詳細...
```

### シングルトンパターンによる一貫した管理

```python
# シングルトンインスタンスを提供する関数
def get_workflow_service() -> WorkflowService:
    """ワークフロー管理サービスのシングルトンインスタンスを取得します"""
    return WorkflowService()

# FastAPI依存関係注入関数
def get_workflow_service_dependency() -> WorkflowService:
    """FastAPIの依存関係注入のためのプロバイダー関数"""
    return get_workflow_service()
```

### ノード生成メソッド
ノード関数を動的に生成するファクトリーメソッドで、コードの重複を削減し、拡張性を向上させています。

```python
def _create_agent_node(self, agent_id: str) -> Callable:
    """エージェントノード関数を作成"""
    def agent_node(state: WorkflowState, config: Dict[str, Any]) -> WorkflowState:
        # エージェントノードの実装
        # ...
    return agent_node

def _create_human_intervention_node(self) -> Callable:
    """人間の介入ノード関数を作成"""
    def human_intervention_node(state: WorkflowState, config: Dict[str, Any]) -> WorkflowState:
        # 人間の介入処理の実装
        # ...
    return human_intervention_node

def _create_error_handling_node(self) -> Callable:
    """エラー処理ノード関数を作成"""
    def error_handling_node(state: WorkflowState, config: Dict[str, Any]) -> WorkflowState:
        # エラー処理の実装
        # ...
    return error_handling_node

def _create_end_node(self) -> Callable:
    """終了ノード関数を作成"""
    def end_node(state: WorkflowState, config: Dict[str, Any]) -> WorkflowState:
        # 終了処理の実装
        # ...
    return end_node
```

### 一時停止と再開機能
エラーにより一時停止したワークフローを再開するための機能と、手動での一時停止・再開機能を提供します。

```python
def pause_workflow(self, workflow_id: str, reason: str = "manually_paused") -> bool:
    """ワークフローを一時停止する"""
    if workflow_id not in self.active_workflows:
        logger.warning(f"ワークフロー {workflow_id} は実行中ではありません")
        return False
        
    # 一時停止状態に更新
    self.active_workflows[workflow_id]["status"] = "paused"
    self.active_workflows[workflow_id]["pause_reason"] = reason
    self.active_workflows[workflow_id]["paused_at"] = datetime.now()
    
    logger.info(f"ワークフロー {workflow_id} を一時停止しました: {reason}")
    return True

def resume_workflow(self, workflow_id: str) -> bool:
    """一時停止したワークフローを再開する"""
    if workflow_id not in self.active_workflows:
        logger.warning(f"ワークフロー {workflow_id} は存在しません")
        return False
        
    if self.active_workflows[workflow_id]["status"] != "paused":
        logger.warning(f"ワークフロー {workflow_id} は一時停止状態ではありません")
        return False
        
    # 実行中状態に更新
    self.active_workflows[workflow_id]["status"] = "running"
    self.active_workflows[workflow_id]["resumed_at"] = datetime.now()
    
    logger.info(f"ワークフロー {workflow_id} を再開しました")
    return True
```

## ワークフローグラフ定義
最新の実装では、以下のようにワークフローグラフが定義されています。

```python
def _create_agent_workflow_graph(self, config: Dict[str, Any]) -> Any:
    """エージェントワークフローグラフを作成する"""
    try:
        # StateGraphの作成
        from langgraph.graph import StateGraph
        builder = StateGraph(WorkflowState)
        
        # ノードの定義
        # エージェントノード
        builder.add_node("agent_a", self._create_agent_node(settings.AGENT_A_ID))
        builder.add_node("agent_b", self._create_agent_node(settings.AGENT_B_ID))
        builder.add_node("agent_c", self._create_agent_node(settings.AGENT_C_ID))
        builder.add_node("agent_d", self._create_agent_node(settings.AGENT_D_ID))
        
        # 特殊ノード
        builder.add_node("human_intervention", self._create_human_intervention_node())
        builder.add_node("error_handling", self._create_error_handling_node())
        builder.add_node("end", self._create_end_node())
        
        # エッジの追加（エージェントの実行順序の定義）
        # 基本的な実行パス: A -> B -> C -> D -> end
        builder.add_edge("agent_a", "agent_b")
        builder.add_edge("agent_b", "agent_c")
        builder.add_edge("agent_c", "agent_d")
        builder.add_edge("agent_d", "end")
        
        # 人間の介入
        builder.add_conditional_edge(
            "human_intervention",
            self._human_response_condition,
            {
                "has_response": "previous_agent",
                "no_response": "human_intervention"
            }
        )
        
        # エラー処理
        builder.add_edge("error_handling", "agent_a")
        
        # エントリーポイントの設定
        builder.set_entry_point("agent_a")
        
        # グラフをコンパイル
        workflow_graph = builder.compile()
        
        logger.info("エージェントワークフローグラフの作成完了")
        return workflow_graph
    
    except Exception as e:
        logger.error(f"ワークフローグラフの作成中にエラーが発生: {e}")
        raise
```

## 人間の介入処理
人間の介入が必要な場合の処理フローが強化されました。

```python
async def run_workflow(self, ..., human_interaction_callback: Optional[Callable] = None) -> Dict[str, Any]:
    # ...
    
    # 人間の介入が必要な場合の処理
    if human_interaction_callback:
        async def _handle_human_interaction(state: WorkflowState) -> WorkflowState:
            if state.is_human_intervention_required and state.human_query:
                try:
                    human_response = await human_interaction_callback(state.human_query)
                    state.human_response = human_response
                except Exception as e:
                    logger.error(f"人間の介入コールバックでエラーが発生: {e}")
                    state.errors.append({
                        "source": "human_interaction",
                        "timestamp": datetime.now().isoformat(),
                        "error": str(e),
                    })
            return state
        
        # 人間の介入ハンドラを登録
        execution_config["callbacks"] = [_handle_human_interaction]
    
    # ...
```

## ワークフロータイプの選択
異なるタイプのワークフローを統一的に管理できるようになりました。

```python
def create_workflow_graph(self, workflow_type: str = "agent", config: Optional[Dict[str, Any]] = None) -> Any:
    """ワークフローグラフを作成する（統合版）"""
    # 設定の初期化
    config = config or {}
    
    # キャッシュチェック
    cache_key = f"{workflow_type}:{hash(str(config))}"
    if cache_key in self.workflow_graph_cache:
        logger.info(f"キャッシュからワークフローグラフを取得: {workflow_type}")
        return self.workflow_graph_cache[cache_key]
    
    # タイプに応じたグラフ作成メソッドの選択
    if workflow_type == "agent":
        graph = self._create_agent_workflow_graph(config)
    elif workflow_type == "audit":
        graph = self._create_audit_workflow_graph(config)
    else:
        raise ValueError(f"未サポートのワークフロータイプ: {workflow_type}")
    
    # キャッシュに保存
    self.workflow_graph_cache[cache_key] = graph
    
    logger.info(f"ワークフローグラフを作成: {workflow_type}")
    return graph
``` 