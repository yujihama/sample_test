"""
JSON処理ユーティリティ

JSONシリアライズと逆シリアライズに関する機能を提供
"""

import json
from datetime import datetime, date, time
from enum import Enum
from uuid import UUID
from decimal import Decimal
from dataclasses import is_dataclass, asdict
from typing import Any, Dict, List, Optional, Union, Set, Tuple


class JSONEncoder(json.JSONEncoder):
    """拡張されたJSONエンコーダ

    以下の特殊な型をサポート:
    - datetime/date/time: ISOフォーマットに変換
    - UUID: 文字列に変換
    - Enum: 値を取得
    - Set: リストに変換
    - dataclass: 辞書に変換
    - Decimal: 浮動小数点数に変換
    """
    
    def default(self, obj):
        """特殊型を変換するためのメソッド"""
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, Decimal):
            return float(obj)
        elif is_dataclass(obj):
            return asdict(obj)
        
        # 特殊型に該当しない場合はデフォルトの処理
        return super().default(obj)


def json_serialize(obj: Any) -> str:
    """オブジェクトをJSON文字列にシリアライズ

    Args:
        obj: シリアライズするオブジェクト

    Returns:
        JSON文字列
    """
    return json.dumps(obj, cls=JSONEncoder, ensure_ascii=False)


def json_deserialize(json_str: str) -> Any:
    """JSON文字列をオブジェクトに逆シリアライズ

    Args:
        json_str: デシリアライズするJSON文字列

    Returns:
        デシリアライズされたオブジェクト
    """
    return json.loads(json_str)


def json_serialize_to_dict(obj: Any) -> Dict:
    """オブジェクトをJSON互換の辞書に変換

    Args:
        obj: 変換するオブジェクト

    Returns:
        JSON互換の辞書
    """
    # 一旦JSONにシリアライズしてから戻すことで、すべての型を適切に変換
    return json_deserialize(json_serialize(obj))


def is_json_serializable(obj: Any) -> bool:
    """オブジェクトがJSON互換かどうかをチェック

    Args:
        obj: チェックするオブジェクト

    Returns:
        JSON互換ならTrue
    """
    try:
        json_serialize(obj)
        return True
    except (TypeError, ValueError):
        return False


def make_json_serializable(obj: Any) -> Any:
    """オブジェクトをJSON互換形式に変換

    Args:
        obj: 変換するオブジェクト

    Returns:
        JSON互換形式のオブジェクト
    """
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    elif isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, Decimal):
        return float(obj)
    elif is_dataclass(obj):
        return make_json_serializable(asdict(obj))
    else:
        # その他の型はそのまま返す
        return obj 