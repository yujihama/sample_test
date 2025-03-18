"""
規程情報ユーティリティモジュール

このモジュールは、規程情報の処理に関する共通のユーティリティ関数を提供します。
サービス層とリポジトリ層で共通して使用する機能を集約しています。
"""

from typing import Dict, Any, List, Optional, Union, TypeVar, Type, Generic
import json
from datetime import datetime
import re
import logging
from pydantic import BaseModel

from src.models.schema import RegulationBase, RegulationCreate, RegulationUpdate, RegulationResponse
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 型変数を定義（型安全な関数のため）
T = TypeVar('T')
U = TypeVar('U', bound=BaseModel)


def serialize_json(data: Any) -> Optional[str]:
    """
    データをJSON文字列にシリアライズする
    
    Args:
        data (Any): シリアライズするデータ
        
    Returns:
        Optional[str]: JSON文字列、またはNone
    """
    if data is None:
        return None
    try:
        return json.dumps(data, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"JSONシリアライズに失敗しました: {str(e)}")
        return None


def deserialize_json(json_str: str) -> Any:
    """
    JSON文字列をデシリアライズする
    
    Args:
        json_str (str): デシリアライズするJSON文字列
        
    Returns:
        Any: デシリアライズされたデータ
    """
    if not json_str:
        return None
    try:
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"JSONデシリアライズに失敗しました: {str(e)}")
        return None


def convert_db_to_response(regulation) -> RegulationResponse:
    """
    DBモデルからレスポンスモデルに変換する
    
    Args:
        regulation: DBモデル
        
    Returns:
        RegulationResponse: レスポンスモデル
    """
    # JSON文字列をデシリアライズ
    structured_content = deserialize_json(regulation.structured_content)
    keywords = deserialize_json(regulation.keywords)
    metadata = deserialize_json(regulation.meta_data)
    
    # レスポンスモデルを作成
    return RegulationResponse(
        id=regulation.id,
        code=regulation.code,
        title=regulation.title,
        category=regulation.category,
        content=regulation.content,
        structured_content=structured_content,
        version=regulation.version,
        effective_date=regulation.effective_date,
        expiration_date=regulation.expiration_date,
        parent_id=regulation.parent_id,
        keywords=keywords,
        metadata=metadata,
        created_at=regulation.created_at,
        updated_at=regulation.updated_at
    )


def validate_regulation_data(regulation_data: RegulationBase) -> List[str]:
    """
    規程情報データを検証する
    
    Args:
        regulation_data: 検証する規程情報データ
        
    Returns:
        List[str]: エラーメッセージのリスト（問題なければ空リスト）
    """
    errors = []
    
    # 規程コードの検証（英数字、ハイフン、アンダースコアのみ許可）
    if hasattr(regulation_data, 'code') and regulation_data.code:
        if not re.match(r'^[A-Za-z0-9\-_]+$', regulation_data.code):
            errors.append("規程コードは英数字、ハイフン、アンダースコアのみ使用可能です")
    
    # バージョン形式の検証（セマンティックバージョニング）
    if hasattr(regulation_data, 'version') and regulation_data.version:
        if not re.match(r'^(\d+)\.(\d+)\.(\d+)$', regulation_data.version):
            errors.append("バージョンは 'X.Y.Z' の形式で指定してください")
    
    # 日付の検証
    if hasattr(regulation_data, 'effective_date') and regulation_data.effective_date:
        if regulation_data.effective_date > datetime.now():
            errors.append("発効日は現在日時より前である必要があります")
    
    # 有効期限と発効日の検証
    if (hasattr(regulation_data, 'expiration_date') and 
        hasattr(regulation_data, 'effective_date') and 
        regulation_data.expiration_date and 
        regulation_data.effective_date and 
        regulation_data.expiration_date < regulation_data.effective_date):
        errors.append("失効日は発効日より後である必要があります")
    
    return errors


def extract_text_matches(query: str, content: str, context_chars: int = 40) -> List[Dict[str, Any]]:
    """
    テキスト内の検索クエリにマッチする部分を抽出する
    
    Args:
        query (str): 検索クエリ
        content (str): 検索対象のテキスト
        context_chars (int, optional): 前後のコンテキスト文字数
        
    Returns:
        List[Dict[str, Any]]: マッチ情報のリスト
    """
    matches = []
    if not query or not content:
        return matches
    
    # 大文字小文字を区別せずに検索
    try:
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        for match in pattern.finditer(content):
            start, end = match.span()
            # 前後のコンテキストを取得
            context_start = max(0, start - context_chars)
            context_end = min(len(content), end + context_chars)
            
            # マッチ情報を作成
            matches.append({
                "text": content[start:end],
                "position": {"start": start, "end": end},
                "context": content[context_start:context_end],
                "context_position": {"start": context_start, "end": context_end}
            })
    except Exception as e:
        logger.error(f"テキストマッチの抽出に失敗しました: {str(e)}")
    
    return matches


def create_audit_details(data: Any) -> Dict[str, Any]:
    """
    監査証跡用の詳細情報を作成する
    
    Args:
        data: 監査証跡に記録するデータ
        
    Returns:
        Dict[str, Any]: 監査証跡用の詳細情報
    """
    # Pydanticモデルの場合
    if hasattr(data, "dict"):
        return {"data": data.dict(exclude_unset=True)}
    
    # 辞書の場合
    if isinstance(data, dict):
        return {"data": data}
    
    # その他の場合
    return {"data": str(data)}


# 以下、新規追加の統一スキーマ検証・データ変換機能 #

class DataValidator:
    """データ検証のためのユーティリティクラス"""
    
    @staticmethod
    def validate_model(model_class: Type[U], data: Dict[str, Any]) -> Union[U, List[str]]:
        """
        データをPydanticモデルに対して検証する
        
        Args:
            model_class: 検証に使用するPydanticモデルクラス
            data: 検証するデータ
            
        Returns:
            Union[U, List[str]]: 検証済みモデルインスタンスまたはエラーメッセージのリスト
        """
        try:
            # Pydanticモデルを使用して検証
            validated_model = model_class(**data)
            return validated_model
        except Exception as e:
            errors = []
            if hasattr(e, 'errors'):
                for error in e.errors():
                    loc = '.'.join(str(x) for x in error['loc'])
                    errors.append(f"{loc}: {error['msg']}")
            else:
                errors.append(str(e))
            return errors
    
    @staticmethod
    def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """
        JSONスキーマに対してデータを検証する
        
        Args:
            data: 検証するデータ
            schema: JSONスキーマ
            
        Returns:
            List[str]: エラーメッセージのリスト（問題なければ空リスト）
        """
        try:
            import jsonschema
            errors = []
            
            try:
                jsonschema.validate(data, schema)
            except jsonschema.exceptions.ValidationError as e:
                errors.append(f"JSONスキーマ検証エラー: {e.message}")
            
            return errors
        except ImportError:
            logger.warning("jsonschemaモジュールがインストールされていません。スキップします。")
            return []


class ModelConverter(Generic[T, U]):
    """モデル変換のためのジェネリッククラス"""
    
    @staticmethod
    def db_to_response(db_model: T, response_model_class: Type[U], excluded_fields: Optional[List[str]] = None) -> U:
        """
        DBモデルからレスポンスモデルに変換する汎用メソッド
        
        Args:
            db_model: DBモデル
            response_model_class: レスポンスモデルクラス
            excluded_fields: 除外するフィールドのリスト
            
        Returns:
            U: 変換されたレスポンスモデル
        """
        if db_model is None:
            return None
        
        excluded_fields = excluded_fields or []
        data = {}
        
        # DBモデルの属性を取得
        for key in dir(db_model):
            # 内部属性や関数は除外
            if key.startswith('_') or callable(getattr(db_model, key)) or key in excluded_fields:
                continue
            
            value = getattr(db_model, key)
            
            # JSON文字列をデシリアライズ
            if isinstance(value, str) and key in ['structured_content', 'keywords', 'meta_data']:
                value = deserialize_json(value)
            
            data[key] = value
        
        # レスポンスモデルを生成
        try:
            return response_model_class(**data)
        except Exception as e:
            logger.error(f"モデル変換に失敗しました: {str(e)}")
            raise


# JSONフィールドのスキーマ定義（検証用）
REGULATION_SCHEMAS = {
    "metadata": {
        "type": "object",
        "properties": {
            "created_by": {"type": "string"},
            "department": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "revision_history": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "version": {"type": "string"},
                        "date": {"type": "string", "format": "date-time"},
                        "changes": {"type": "string"},
                        "editor": {"type": "string"}
                    },
                    "required": ["version", "date"]
                }
            },
            "related_regulations": {
                "type": "array",
                "items": {"type": "string"}
            }
        }
    },
    "structured_content": {
        "type": "object",
        "properties": {
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "subsections": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "content": {"type": "string"}
                                },
                                "required": ["title", "content"]
                            }
                        }
                    },
                    "required": ["title", "content"]
                }
            }
        },
        "required": ["sections"]
    }
} 