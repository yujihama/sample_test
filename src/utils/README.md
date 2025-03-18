# ユーティリティモジュール

このディレクトリには、内部監査AIエージェントシステム全体で使用される共通のユーティリティ関数やヘルパーモジュールが含まれています。これらのユーティリティは、アプリケーションの様々な部分で再利用可能なコンポーネントを提供します。

## ユーティリティの概要

このディレクトリには以下のようなユーティリティが含まれています：

1. **ファイル処理 (`file_utils.py`)**
   - ファイルの読み書き
   - フォーマット変換
   - 一時ファイル管理

2. **日付・時間処理 (`date_utils.py`)**
   - 日付フォーマット
   - 期間計算
   - タイムゾーン処理

3. **テキスト処理 (`text_utils.py`)**
   - テキスト正規化
   - パターンマッチング
   - テキスト分割・結合

4. **セキュリティ (`security_utils.py`)**
   - ハッシュ関数
   - 暗号化・復号
   - 入力検証

5. **バリデーション (`validation_utils.py`)**
   - 入力検証
   - スキーマ検証
   - 整合性チェック

6. **ロギング (`logging_utils.py`)**
   - ログフォーマット
   - コンテキスト付きロギング
   - ログローテーション

7. **HTTP クライアント (`http_client.py`)**
   - REST API 呼び出し
   - リトライロジック
   - エラーハンドリング

## ファイル構成

```
utils/
├── __init__.py           - パッケージ初期化
├── file_utils.py         - ファイル操作ユーティリティ
├── date_utils.py         - 日付・時間操作ユーティリティ
├── text_utils.py         - テキスト処理ユーティリティ
├── security_utils.py     - セキュリティ関連ユーティリティ
├── validation_utils.py   - データバリデーションユーティリティ
├── logging_utils.py      - ロギングユーティリティ
├── http_client.py        - HTTP通信ユーティリティ
├── constants.py          - システム定数
├── exceptions.py         - カスタム例外
└── decorators.py         - 共通デコレータ
```

## 主要ユーティリティの詳細

### ファイル処理ユーティリティ

`file_utils.py` はファイル操作のための共通関数を提供します：

```python
import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional, BinaryIO, TextIO
import json
import csv
import yaml
from pathlib import Path

def ensure_directory(directory_path: str) -> str:
    """指定されたディレクトリが存在することを確認し、必要に応じて作成する"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)
    return directory_path

def safe_file_name(filename: str) -> str:
    """ファイル名を安全な形式に変換する"""
    # 不正な文字をアンダースコアに置換
    return "".join(c if c.isalnum() or c in "._- " else "_" for c in filename)

def read_json(file_path: str) -> Dict[str, Any]:
    """JSONファイルを読み込む"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(data: Dict[str, Any], file_path: str, pretty: bool = True) -> None:
    """データをJSONファイルに書き込む"""
    with open(file_path, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            json.dump(data, f, ensure_ascii=False)

def read_csv(file_path: str, delimiter: str = ',') -> List[Dict[str, str]]:
    """CSVファイルを読み込み、辞書のリストとして返す"""
    results = []
    with open(file_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        for row in reader:
            results.append(dict(row))
    return results

def write_csv(data: List[Dict[str, Any]], file_path: str, fieldnames: List[str] = None) -> None:
    """辞書のリストをCSVファイルに書き込む"""
    if not data:
        return
    
    if fieldnames is None:
        fieldnames = list(data[0].keys())
    
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def create_temp_file(prefix: str = "audit_", suffix: str = "", content: bytes = None) -> str:
    """一時ファイルを作成し、そのパスを返す"""
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
    try:
        if content:
            with os.fdopen(fd, 'wb') as f:
                f.write(content)
        else:
            os.close(fd)
    except:
        os.close(fd)
        raise
    
    return path

def delete_file_safely(file_path: str) -> bool:
    """ファイルを安全に削除する（存在しない場合はエラーを発生させない）"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        print(f"Failed to delete file {file_path}: {e}")
    return False

def get_file_extension(file_path: str) -> str:
    """ファイルの拡張子を取得する"""
    return os.path.splitext(file_path)[1].lower()

def get_file_size(file_path: str) -> int:
    """ファイルサイズをバイト単位で取得する"""
    return os.path.getsize(file_path)

def is_valid_file_type(file_path: str, allowed_extensions: List[str]) -> bool:
    """ファイルが許可された拡張子を持つかチェックする"""
    ext = get_file_extension(file_path)
    return ext in allowed_extensions
```

### 日付・時間処理ユーティリティ

`date_utils.py` は日付と時間の操作を簡単にするヘルパー関数を提供します：

```python
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
import pytz

DEFAULT_TIMEZONE = pytz.timezone('Asia/Tokyo')

def now(tz: Optional[timezone] = None) -> datetime:
    """現在の日時を取得する（タイムゾーン指定可能）"""
    if tz is None:
        tz = DEFAULT_TIMEZONE
    return datetime.now(tz)

def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """日時を指定されたフォーマットで文字列に変換する"""
    return dt.strftime(format_str)

def parse_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S", 
                 tz: Optional[timezone] = None) -> datetime:
    """文字列を日時に変換する"""
    dt = datetime.strptime(date_str, format_str)
    if tz:
        dt = dt.replace(tzinfo=tz)
    return dt

def add_days(dt: datetime, days: int) -> datetime:
    """指定された日数を日時に加算する"""
    return dt + timedelta(days=days)

def add_hours(dt: datetime, hours: int) -> datetime:
    """指定された時間を日時に加算する"""
    return dt + timedelta(hours=hours)

def get_date_range(start_date: datetime, end_date: datetime) -> list:
    """開始日から終了日までの日付リストを生成する"""
    date_list = []
    current_date = start_date
    
    while current_date <= end_date:
        date_list.append(current_date)
        current_date = add_days(current_date, 1)
    
    return date_list

def is_same_day(dt1: datetime, dt2: datetime) -> bool:
    """2つの日時が同じ日かどうかをチェックする"""
    return dt1.date() == dt2.date()

def get_fiscal_year_start(dt: datetime) -> datetime:
    """指定された日時の会計年度の開始日を取得する（4月1日始まり）"""
    year = dt.year
    if dt.month < 4:
        year -= 1
    return datetime(year, 4, 1, tzinfo=dt.tzinfo)

def get_fiscal_year_end(dt: datetime) -> datetime:
    """指定された日時の会計年度の終了日を取得する（3月31日終わり）"""
    year = dt.year
    if dt.month >= 4:
        year += 1
    return datetime(year, 3, 31, 23, 59, 59, tzinfo=dt.tzinfo)

def get_quarter(dt: datetime) -> int:
    """指定された日時の四半期（1-4）を取得する"""
    month = dt.month
    if 1 <= month <= 3:
        return 1
    elif 4 <= month <= 6:
        return 2
    elif 7 <= month <= 9:
        return 3
    else:
        return 4
```

### HTTP クライアント

`http_client.py` はAPIリクエストを行うための共通関数を提供します：

```python
import asyncio
import json
from typing import Any, Dict, List, Optional, Union
import aiohttp
from aiohttp.client_exceptions import ClientError

class HttpClient:
    """非同期HTTPクライアント"""
    
    def __init__(self, base_url: str = "", timeout: int = 30, 
                retry_count: int = 3, retry_delay: float = 1.0):
        """
        初期化
        
        Args:
            base_url: ベースURL
            timeout: タイムアウト秒数
            retry_count: リトライ回数
            retry_delay: リトライ間隔（秒）
        """
        self.base_url = base_url
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.session = None
    
    async def __aenter__(self):
        """非同期コンテキストマネージャのエントリー"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャの終了"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """内部リクエストメソッド（リトライロジック付き）"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        
        # URLの構築
        if not url.startswith(('http://', 'https://')):
            url = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"
        
        for attempt in range(self.retry_count + 1):
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    # レスポンスボディの読み込み
                    content_type = response.headers.get('Content-Type', '')
                    if 'application/json' in content_type:
                        data = await response.json()
                    else:
                        text = await response.text()
                        try:
                            data = json.loads(text)
                        except json.JSONDecodeError:
                            data = text
                    
                    # ステータスコードのチェック
                    if response.status >= 400:
                        error_msg = f"HTTP Error {response.status}: {data}"
                        if response.status >= 500 and attempt < self.retry_count:
                            # サーバーエラーの場合はリトライ
                            await asyncio.sleep(self.retry_delay * (2 ** attempt))
                            continue
                        else:
                            # クライアントエラーまたはリトライ回数超過
                            return {
                                "success": False,
                                "status_code": response.status,
                                "error": error_msg,
                                "data": data
                            }
                    
                    # 成功時のレスポンス
                    return {
                        "success": True,
                        "status_code": response.status,
                        "data": data,
                        "headers": dict(response.headers)
                    }
            
            except (ClientError, asyncio.TimeoutError) as e:
                if attempt < self.retry_count:
                    # ネットワークエラーの場合はリトライ
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                else:
                    # リトライ回数超過
                    return {
                        "success": False,
                        "status_code": None,
                        "error": f"Request failed after {self.retry_count} retries: {str(e)}",
                        "data": None
                    }
    
    async def get(self, url: str, params: Optional[Dict[str, Any]] = None, 
                headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """GETリクエスト"""
        return await self._request('GET', url, params=params, headers=headers)
    
    async def post(self, url: str, data: Optional[Dict[str, Any]] = None, 
                 json_data: Optional[Dict[str, Any]] = None,
                 headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """POSTリクエスト"""
        return await self._request('POST', url, data=data, json=json_data, headers=headers)
    
    async def put(self, url: str, data: Optional[Dict[str, Any]] = None, 
                json_data: Optional[Dict[str, Any]] = None,
                headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """PUTリクエスト"""
        return await self._request('PUT', url, data=data, json=json_data, headers=headers)
    
    async def delete(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """DELETEリクエスト"""
        return await self._request('DELETE', url, headers=headers)
```

### セキュリティユーティリティ

`security_utils.py` はセキュリティ関連の機能を提供します：

```python
import hashlib
import secrets
import string
import re
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Dict, Optional, Tuple

def generate_password_hash(password: str, salt: Optional[str] = None) -> Dict[str, str]:
    """パスワードのハッシュを生成する"""
    if salt is None:
        salt = secrets.token_hex(16)
    
    # SHA-256ハッシュの計算
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # イテレーション回数
    ).hex()
    
    return {
        'hash': pw_hash,
        'salt': salt
    }

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """パスワードがハッシュと一致するか検証する"""
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # イテレーション回数
    ).hex()
    
    return secrets.compare_digest(pw_hash, stored_hash)

def generate_secure_token(length: int = 32) -> str:
    """安全なランダムトークンを生成する"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def sanitize_input(text: str) -> str:
    """ユーザー入力を安全にサニタイズする"""
    # HTML/スクリプトタグを削除
    text = re.sub(r'<[^>]*>', '', text)
    
    # SQLインジェクション対策
    text = re.sub(r'[\'";]', '', text)
    
    return text

def encrypt_data(data: str, key: bytes) -> str:
    """データを暗号化する"""
    f = Fernet(key)
    return f.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str, key: bytes) -> str:
    """暗号化されたデータを復号する"""
    f = Fernet(key)
    return f.decrypt(encrypted_data.encode()).decode()

def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """パスワードからキーを導出する"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def generate_key() -> Tuple[bytes, bytes]:
    """暗号化キーとソルトを生成する"""
    salt = secrets.token_bytes(16)
    master_key = secrets.token_bytes(32)
    return master_key, salt
```

## デコレータ

`decorators.py` には共通で使用できるデコレータが定義されています：

```python
import time
import functools
import logging
from typing import Any, Callable, Dict, Optional, TypeVar, cast

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

logger = logging.getLogger(__name__)

def timer(func: F) -> F:
    """関数の実行時間を計測するデコレータ"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.debug(f"{func.__name__} took {end_time - start_time:.4f} seconds to execute")
        return result
    return cast(F, wrapper)

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0,
          exceptions: tuple = (Exception,)) -> Callable[[F], F]:
    """失敗時にリトライするデコレータ"""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(f"Retry failed after {max_attempts} attempts: {str(e)}")
                        raise
                    
                    logger.warning(f"Retry attempt {attempt} after error: {str(e)}")
                    time.sleep(current_delay)
                    current_delay *= backoff
        
        return cast(F, wrapper)
    return decorator

def memoize(func: F) -> F:
    """関数の結果をキャッシュするデコレータ"""
    cache: Dict[str, Any] = {}
    
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # キャッシュキーの生成
        key = str(args) + str(kwargs)
        
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        
        return cache[key]
    
    return cast(F, wrapper)

def log_execution(level: int = logging.INFO) -> Callable[[F], F]:
    """関数の実行をログに記録するデコレータ"""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = func.__name__
            logger.log(level, f"Executing {func_name} with args={args}, kwargs={kwargs}")
            
            try:
                result = func(*args, **kwargs)
                logger.log(level, f"{func_name} completed successfully")
                return result
            except Exception as e:
                logger.error(f"{func_name} failed with error: {str(e)}")
                raise
        
        return cast(F, wrapper)
    return decorator

def validate_args(*validators: Callable) -> Callable[[F], F]:
    """引数を検証するデコレータ"""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 引数の検証
            for i, (arg, validator) in enumerate(zip(args[1:], validators)):
                if not validator(arg):
                    raise ValueError(f"Argument {i+1} failed validation")
            
            return func(*args, **kwargs)
        
        return cast(F, wrapper)
    return decorator
```

## ユースケースとの対応

ユーティリティモジュールは様々なユースケースをサポートします：

1. **監査ワークフロー**
   - `file_utils.py` で監査証拠ファイルの処理をサポート
   - `date_utils.py` で監査期間の管理をサポート
   - `http_client.py` で外部データソースとの連携をサポート

2. **エージェント間連携**
   - `logging_utils.py` でエージェント間の通信ログを記録
   - `validation_utils.py` でメッセージ形式の検証をサポート

3. **セキュリティ要件**
   - `security_utils.py` でデータの暗号化・復号をサポート
   - 入力サニタイズでセキュリティリスクを低減

4. **パフォーマンス最適化**
   - デコレータを使用した関数実行時間の測定
   - メモ化による計算結果のキャッシュ

## 拡張方法

### 新しいユーティリティの追加

ユーティリティを追加するには、以下の手順に従います：

1. 新しいPythonファイル（例：`new_utils.py`）を作成
2. 関連する機能をグループ化して実装
3. `__init__.py` にインポート文を追加して利用しやすくする

```python
# new_utils.py の例
from typing import Any, List, Dict, Optional

def utility_function1(param1: str, param2: int) -> str:
    """新しいユーティリティ関数1の説明"""
    # 実装
    result = f"{param1}_{param2}"
    return result

def utility_function2(data: Dict[str, Any]) -> List[Any]:
    """新しいユーティリティ関数2の説明"""
    # 実装
    result = []
    for key, value in data.items():
        result.append(value)
    return result
```

### 既存ユーティリティの拡張

既存のユーティリティモジュールを拡張するには、新しい関数を追加します：

```python
# file_utils.py に以下の関数を追加
def compress_files(file_paths: List[str], output_path: str, format: str = "zip") -> str:
    """複数のファイルを圧縮する"""
    import zipfile
    import tarfile
    
    if format == "zip":
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in file_paths:
                zipf.write(file_path, os.path.basename(file_path))
    elif format == "tar.gz":
        with tarfile.open(output_path, "w:gz") as tar:
            for file_path in file_paths:
                tar.add(file_path, arcname=os.path.basename(file_path))
    else:
        raise ValueError(f"Unsupported compression format: {format}")
    
    return output_path
```

## ベストプラクティス

1. **関数のドキュメント化**
   - すべての関数に型ヒントとドキュメント文字列を追加
   - パラメータと戻り値の詳細な説明を提供

2. **エラー処理**
   - 堅牢なエラー処理を実装
   - 意味のあるエラーメッセージを提供

3. **テスト可能性**
   - ユーティリティ関数は単体テストしやすい設計にする
   - 依存性を最小限に抑える

4. **パフォーマンス**
   - 頻繁に使用される関数のパフォーマンスを最適化
   - 不要な計算や処理を避ける 