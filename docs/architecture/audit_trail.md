# 監査証跡とログ強化（グラフベース）

## 概要

このドキュメントでは、グラフ状態履歴に基づいた監査証跡とログ強化機能の実装について説明します。この機能は、ワークフローの実行過程を詳細に記録し、状態遷移の追跡と可視化を可能にします。

## 主要コンポーネント

### 1. データモデル

- **GraphStateHistory**: グラフの状態変化を記録するモデル
  - ワークフローID、コンテキストID、エージェントID、ノードIDなどの識別情報
  - 状態スナップショット、状態差分、イベントタイプ、イベントデータなどの詳細情報
  - タイムスタンプとチェックポイント参照

- **CheckpointRecord**: チェックポイントの作成と復元を記録するモデル
  - ワークフローID、コンテキストID、エージェントID、チェックポイントタイプなどの識別情報
  - 状態参照、メタデータ、作成時刻、復元時刻、復元回数などの詳細情報

### 2. リポジトリレイヤー

- **GraphStateHistoryRepository**: グラフ状態履歴の作成、取得、検索機能を提供
  - 様々な条件（ワークフローID、エージェントID、時間範囲など）での検索をサポート

- **CheckpointRecordRepository**: チェックポイント記録の作成、取得、検索機能を提供
  - チェックポイントの復元状態の管理と追跡

### 3. サービスレイヤー

- **GraphExecutor**: グラフ実行サービスの拡張
  - 状態変化の記録と差分計算
  - チェックポイントの作成と復元の監査
  - エラー状態の記録と追跡

- **AgentContextManager**: エージェント間のコンテキスト共有の監査
  - コンテキスト共有イベントの記録
  - エージェント間の情報フローの追跡

### 4. APIエンドポイント

- **/audit/trails**: 基本的な監査証跡の取得
- **/audit/trails/export**: 監査証跡のエクスポート
- **/audit/state-history**: グラフ状態履歴の取得
- **/audit/checkpoints**: チェックポイント記録の取得
- **/audit/visualize/state-transitions**: 状態遷移の可視化データの取得

## 主要機能

### 1. 状態履歴の記録

- ワークフロー実行中の各状態変化を詳細に記録
- 状態スナップショットと差分の保存による効率的なストレージ利用
- イベントタイプと詳細データによるコンテキスト情報の提供

### 2. チェックポイント管理

- 自動および手動チェックポイントの作成と記録
- チェックポイントの復元履歴の追跡
- エラー発生時の自動チェックポイント作成によるリカバリーサポート

### 3. 状態遷移の可視化

- ノードとエッジによるグラフ表現
- 時系列での状態変化の追跡
- チェックポイントとの関連付けによる重要ポイントの強調

### 4. 監査証跡のエクスポート

- JSON形式での監査データのエクスポート
- メッセージログ、エージェント決定、状態履歴、チェックポイントの包括的な記録
- 外部システムとの統合や分析のためのデータ提供

## 使用例

### 状態履歴の取得

```python
# GraphStateHistoryRepositoryを使用して状態履歴を取得
repo = GraphStateHistoryRepository(db_session)
history_records = repo.search(
    workflow_id="workflow-123",
    agent_id="agent-a",
    start_time=datetime.now() - timedelta(hours=1),
    limit=100
)

# 状態変化の分析
for record in history_records:
    print(f"Event: {record.event_type}, Node: {record.node_id}, Time: {record.timestamp}")
    if record.state_diff:
        print(f"Changes: {record.state_diff}")
```

### チェックポイントの作成と復元

```python
# チェックポイントの作成
checkpoint_repo = CheckpointRecordRepository(db_session)
checkpoint_id = checkpoint_repo.create(
    workflow_id="workflow-123",
    agent_id="agent-a",
    checkpoint_type="user_requested",
    metadata={"reason": "ユーザーリクエスト", "importance": "high"}
)

# チェックポイントの復元
checkpoint = checkpoint_repo.get_by_id(checkpoint_id)
checkpoint_repo.mark_as_restored(checkpoint_id)
```

### 状態遷移の可視化

APIエンドポイント `/audit/visualize/state-transitions?workflow_id=workflow-123` を使用して、
ノードとエッジのデータを取得し、フロントエンドでグラフとして表示できます。

## 今後の拡張

1. **改ざん検出**: 監査証跡データの整合性を検証する機能
2. **高度な分析**: 状態遷移パターンの分析と異常検出
3. **パフォーマンス最適化**: 大規模データセットでの効率的な処理
4. **カスタムビュー**: 特定のユースケースに特化した監査ビューの提供 