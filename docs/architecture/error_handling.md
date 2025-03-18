# エラーハンドリング機能

## 概要
エラーハンドリング機能は、AIエージェントシステムの堅牢性と信頼性を向上させるために設計された機能です。様々なタイプのエラーを検出し、適切な回復戦略を実行することで、システムの継続的な運用を可能にします。

## エラータイプ

システムは以下のタイプのエラーを識別・処理します：

- **一時的エラー (Transient)**: 再試行により解決可能なエラー（ネットワークの一時的な問題など）
- **永続的エラー (Permanent)**: 再試行では解決できないエラー（権限の問題など）
- **ビジネスロジックエラー (Business)**: アプリケーションロジックに関連するエラー
- **タイムアウトエラー (Timeout)**: 処理時間が制限を超えたエラー
- **データエラー (Data)**: データ構造や値に関連するエラー

## ErrorHandlerクラス

中核となるエラーハンドリングクラスです。

```python
class ErrorHandler:
    """
    エラーハンドリングと回復戦略を実装するクラス
    """
    
    def __init__(self, context_store: Any = None):
        """初期化"""
        self.context_store = context_store
        self.error_strategies = {
            # 各種エラータイプとそのハンドラーのマッピング
            ...
        }
```

### 主要メソッド

#### handle_error
エラーを処理し、回復できるかどうかを判断します。

```python
async def handle_error(self, state: WorkflowState, error: Exception) -> Tuple[bool, WorkflowState]:
    """
    エラーを処理し、回復できた場合はTrue、できなかった場合はFalseを返す
    """
    # エラー処理ロジック
    ...
```

#### エラータイプ別ハンドラー
各エラータイプに対する専用のハンドリング関数を提供します。

```python
async def _handle_rate_limit_error(self, state: WorkflowState, error: Exception) -> Tuple[bool, WorkflowState]:
    """レート制限エラーの処理（一時停止して再試行）"""
    # 処理ロジック...

async def _handle_token_limit_error(self, state: WorkflowState, error: Exception) -> Tuple[bool, WorkflowState]:
    """トークン制限エラーの処理（プロンプトやコンテキストを短縮）"""
    # 処理ロジック...

# その他のハンドラー...
```

## LLM専用エラークラス

LLMサービスに関連する特殊なエラーを処理するためのカスタム例外クラスです。

```python
class LLMError(Exception):
    """LLM関連の基本例外クラス"""
    ...

class RateLimitError(LLMError):
    """APIレート制限に達した場合のエラー"""
    ...

class TokenLimitError(LLMError):
    """トークン数制限を超えた場合のエラー"""
    ...

# その他のLLMエラークラス...
```

## LLMエラーユーティリティ

LLMエラーを解析し、適切な処理を行うためのユーティリティ関数群です。

```python
class LLMErrorParser:
    """
    LLMエラーを解析し、適切なカスタム例外に変換するクラス
    """
    # 実装詳細...

class LLMErrorHandler:
    """
    LLMエラーを処理するためのユーティリティクラス
    """
    # 実装詳細...

def safe_parse_json(json_str: str) -> Tuple[bool, Union[Dict[str, Any], List[Any], str]]:
    """
    安全にJSONを解析する関数
    """
    # 実装詳細...
```

## エラー発生時のワークフロー

1. エージェント関数でエラーが発生
2. `with_error_handling`デコレータがエラーをキャッチ
3. `ErrorHandler.handle_error`メソッドがエラータイプを識別
4. 適切なエラーハンドラー関数が呼び出される
5. 回復可能な場合は状態を更新して処理を再開
6. 回復不可能な場合はエラー状態を記録して終了

## 監視とロギング

エラーハンドリングプロセスは詳細にロギングされ、監視できるようになっています。

```python
logger.error(
    f"エラー発生: {error_type_name} ({error_category}), "
    f"メッセージ: {str(error)}, "
    f"エージェント: {state.get('current_agent', 'unknown')}, "
    f"ワークフローID: {state.get('workflow_id', 'unknown')}"
)
```

## データベース関連エラーハンドリング

データベース操作に関連するエラーは、アプリケーションの安定性と信頼性に大きな影響を与えます。このセクションでは、データベース関連のエラーハンドリング手法について説明します。

### SQLAlchemyエラータイプ

システムでは、以下のSQLAlchemy関連エラーを適切に処理します：

- **DBAPIError**: SQLAlchemyのDBAPIレベルでのエラー
- **IntegrityError**: データ整合性違反によるエラー（一意制約違反など）
- **OperationalError**: データベース操作中のエラー（接続タイムアウトなど）
- **SQLAlchemyError**: SQLAlchemy操作に関連する一般的なエラー

### テキストSQLの適切な使用

SQLAlchemy 2.0以降では、文字列形式のSQLクエリを実行する際に`text()`関数を使用することが必須となりました。この変更は、SQLインジェクションを防止し、タイプセーフティを向上させるための重要なセキュリティ対策です。

```python
from sqlalchemy import text

# 正しい方法
db.execute(text("SELECT 1"))

# 誤った方法（例外が発生）
db.execute("SELECT 1")  # sqlalchemy.exc.ArgumentError: Textual SQL expression 'SELECT 1' should be explicitly declared as text('SELECT 1')
```

### データベース接続リトライ機構

データベース接続の問題に対処するため、システムには自動リトライ機構が組み込まれています：

```python
retries = 0
while retries <= DB_MAX_RETRIES:
    try:
        db = db_session()
        db.execute(text("SELECT 1"))  # 接続テスト
        break
    except exc.DBAPIError as e:
        retries += 1
        if retries <= DB_MAX_RETRIES:
            logger.warning(f"データベース接続に失敗しました。再試行中... ({retries}/{DB_MAX_RETRIES})")
            time.sleep(DB_RETRY_INTERVAL * retries)  # 指数バックオフ
        else:
            raise ConnectionError(f"データベースへの接続に失敗しました: {e}")
```

### トランザクション管理とロールバック

エラー発生時には、データの一貫性を保つためにトランザクションをロールバックします：

```python
try:
    # データベース操作
    db.commit()
except exc.IntegrityError as e:
    db.rollback()
    logger.error(f"データ整合性違反によりトランザクションをロールバックしました: {e}")
except exc.SQLAlchemyError as e:
    db.rollback()
    logger.error(f"SQLAlchemyエラーによりトランザクションをロールバックしました: {e}")
finally:
    db.close()
```

### セッションクリーンアップ

メモリリークとリソース枯渇を防ぐため、未終了のデータベースセッションを適切にクローズします：

```python
def close_db_connections():
    """アクティブなすべてのデータベース接続を閉じる"""
    active_count = len(_active_sessions)
    if active_count > 0:
        logger.warning(f"{active_count}個のアクティブなデータベースセッションを強制的に閉じています")
        for session in list(_active_sessions):
            try:
                session.close()
                _active_sessions.remove(session)
            except Exception as e:
                logger.error(f"セッションのクローズ中にエラーが発生しました: {e}")
``` 