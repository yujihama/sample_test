"""
文書解析ツール - PDF・スキャン文書の解析やテキスト抽出を行うツール
"""

import os
from typing import Dict, List, Any, Optional
import uuid
import json
from datetime import datetime
import re

from loguru import logger
from src.core.tool_base import ToolBase, ToolResult
from src.core.config import settings


class DocumentParser(ToolBase):
    """文書解析ツール"""
    
    def __init__(self, tool_id: str = None):
        """
        文書解析ツールの初期化
        
        Args:
            tool_id: ツールID（省略時は自動生成）
        """
        super().__init__(tool_id)
        self.description = "文書解析ツール - PDF・スキャン文書の解析やテキスト抽出を行う"
        self.version = "1.0.0"
        self.capabilities = [
            "extract_text",         # テキスト抽出
            "check_format",         # フォーマット認識
            "validate_document"     # 文書形式の検証
        ]
        
        # 一時ファイル保存先
        self.temp_dir = os.path.join(settings.UPLOAD_DIR, "document_analysis")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # フォーマット定義の保存先
        self.format_dir = os.path.join(settings.DATA_DIR, "document_formats")
        os.makedirs(self.format_dir, exist_ok=True)
        
        # サンプルフォーマット定義の作成
        self._prepare_sample_formats()
        
        logger.info(f"文書解析ツール初期化完了: {self.tool_id}")
    
    def _prepare_sample_formats(self):
        """サンプルのフォーマット定義を作成"""
        # 領収書フォーマット
        receipt_format = {
            "name": "standard_receipt",
            "description": "標準的な領収書フォーマット",
            "required_fields": [
                {"name": "title", "regex": "領\\s*収\\s*書", "required": True},
                {"name": "date", "regex": "\\d{4}年\\s*\\d{1,2}月\\s*\\d{1,2}日|\\d{4}/\\d{1,2}/\\d{1,2}", "required": True},
                {"name": "amount", "regex": "金額.*?\\d[,\\d]*円|\\d[,\\d]*円", "required": True},
                {"name": "payee", "regex": "(?:宛名|宛先)\\s*[:：]\\s*(.*)", "required": False}
            ],
            "validation_rules": [
                {"type": "field_presence", "field": "title", "message": "領収書タイトルが見つかりません"},
                {"type": "field_presence", "field": "date", "message": "日付が見つかりません"},
                {"type": "field_presence", "field": "amount", "message": "金額が見つかりません"}
            ]
        }
        
        # 申請書フォーマット
        application_format = {
            "name": "expense_application",
            "description": "経費申請書フォーマット",
            "required_fields": [
                {"name": "title", "regex": "経費\\s*申請\\s*書", "required": True},
                {"name": "applicant", "regex": "申請者\\s*[:：]\\s*(.*)", "required": True},
                {"name": "department", "regex": "部署\\s*[:：]\\s*(.*)", "required": False},
                {"name": "date", "regex": "申請日\\s*[:：]\\s*(\\d{4}年\\s*\\d{1,2}月\\s*\\d{1,2}日|\\d{4}/\\d{1,2}/\\d{1,2})", "required": True},
                {"name": "amount", "regex": "申請金額\\s*[:：]\\s*(\\d[,\\d]*円)", "required": True},
                {"name": "purpose", "regex": "目的\\s*[:：]\\s*(.*)", "required": True},
                {"name": "approver", "regex": "承認者\\s*[:：]\\s*(.*)", "required": True}
            ],
            "validation_rules": [
                {"type": "field_presence", "field": "title", "message": "申請書タイトルが見つかりません"},
                {"type": "field_presence", "field": "applicant", "message": "申請者が見つかりません"},
                {"type": "field_presence", "field": "date", "message": "申請日が見つかりません"},
                {"type": "field_presence", "field": "amount", "message": "申請金額が見つかりません"},
                {"type": "field_presence", "field": "purpose", "message": "目的が見つかりません"},
                {"type": "field_presence", "field": "approver", "message": "承認者が見つかりません"}
            ]
        }
        
        # フォーマット定義をJSONファイルとして保存
        formats = {
            "standard_receipt": receipt_format,
            "expense_application": application_format
        }
        
        for format_name, format_def in formats.items():
            with open(os.path.join(self.format_dir, f"{format_name}.json"), "w", encoding="utf-8") as f:
                json.dump(format_def, f, ensure_ascii=False, indent=2)
    
    def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        パラメータのバリデーション
        
        Args:
            params: 検証するパラメータ
            
        Returns:
            bool: 検証結果
        """
        if "operation" not in params:
            logger.error("operation パラメータが必要です")
            return False
            
        operation = params["operation"]
        
        if operation not in self.capabilities:
            logger.error(f"サポートされていない操作です: {operation}")
            return False
            
        # テキスト入力の確認
        if "text" not in params and "file_path" not in params:
            logger.error("text または file_path パラメータが必要です")
            return False
            
        # 操作別の必須パラメータ確認
        if operation == "check_format" or operation == "validate_document":
            if "format_name" not in params:
                logger.error("format_name パラメータが必要です")
                return False
        
        return True
    
    async def execute(self, params: Dict[str, Any]) -> ToolResult:
        """
        ツール実行のメイン処理
        
        Args:
            params: 実行パラメータ
            
        Returns:
            ToolResult: 実行結果
        """
        try:
            if not self.validate_params(params):
                return ToolResult(
                    tool_id=self.tool_id,
                    status="error",
                    data={},
                    error_message="パラメータが無効です"
                )
            
            operation = params["operation"]
            
            # テキストの取得
            text = None
            if "text" in params:
                text = params["text"]
            elif "file_path" in params:
                file_path = params["file_path"]
                # ファイルの存在確認
                if not os.path.exists(file_path):
                    return ToolResult(
                        tool_id=self.tool_id,
                        status="error",
                        data={},
                        error_message=f"ファイルが見つかりません: {file_path}"
                    )
                    
                # 実際のPDFファイルの読み込みはPyPDFやpdfplumberなどのライブラリを使用するが、
                # ここではシミュレーションとしてテキストファイルから読み込む
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                except Exception as e:
                    return ToolResult(
                        tool_id=self.tool_id,
                        status="error",
                        data={},
                        error_message=f"ファイルの読み込みに失敗しました: {e}"
                    )
            
            # 操作の実行
            if operation == "extract_text":
                result_data = await self._process_extract_text(text, params)
            elif operation == "check_format":
                result_data = await self._process_check_format(text, params)
            elif operation == "validate_document":
                result_data = await self._process_validate_document(text, params)
            else:
                return ToolResult(
                    tool_id=self.tool_id,
                    status="error",
                    data={},
                    error_message=f"操作 {operation} は未実装です"
                )
            
            return ToolResult(
                tool_id=self.tool_id,
                status="success",
                data=result_data
            )
            
        except Exception as e:
            logger.error(f"文書解析ツール実行エラー: {e}")
            return await self.handle_error(e, params)
    
    async def _process_extract_text(self, text: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """テキスト抽出処理"""
        # 実際のOCR処理などはここで行うが、今回はテキストが直接与えられていると仮定
        
        # テキストの基本統計情報
        lines = text.split("\n")
        char_count = len(text)
        word_count = len(re.findall(r"\w+", text))
        
        # 構造化情報の抽出（単純な例）
        date_matches = re.findall(r"\d{4}[年/]\s*\d{1,2}[月/]\s*\d{1,2}日?", text)
        amount_matches = re.findall(r"\d[,\d]*円", text)
        
        return {
            "text": text,
            "statistics": {
                "line_count": len(lines),
                "character_count": char_count,
                "word_count": word_count
            },
            "extracted_info": {
                "dates": date_matches[:5],  # 最初の5件のみ
                "amounts": amount_matches[:5]  # 最初の5件のみ
            }
        }
    
    async def _process_check_format(self, text: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """フォーマット認識処理"""
        format_name = params["format_name"]
        
        # フォーマット定義の読み込み
        format_path = os.path.join(self.format_dir, f"{format_name}.json")
        if not os.path.exists(format_path):
            return {
                "error": True,
                "message": f"指定されたフォーマット '{format_name}' の定義が見つかりません"
            }
            
        with open(format_path, "r", encoding="utf-8") as f:
            format_def = json.load(f)
        
        # フィールドの抽出
        extracted_fields = {}
        for field in format_def["required_fields"]:
            field_name = field["name"]
            field_regex = field["regex"]
            matches = re.search(field_regex, text)
            
            if matches:
                # 正規表現に()が含まれる場合はグループを使用
                if "(" in field_regex:
                    # 複数のグループがあれば、最初のグループを使用
                    group_val = matches.group(1) if matches.groups() else matches.group(0)
                    extracted_fields[field_name] = group_val.strip()
                else:
                    extracted_fields[field_name] = matches.group(0).strip()
            else:
                extracted_fields[field_name] = None
        
        # フィールドの存在確認
        missing_fields = []
        for field in format_def["required_fields"]:
            if field["required"] and (field["name"] not in extracted_fields or extracted_fields[field["name"]] is None):
                missing_fields.append(field["name"])
        
        # フォーマット一致率の計算
        total_required = len([f for f in format_def["required_fields"] if f["required"]])
        found_required = total_required - len(missing_fields)
        match_percentage = (found_required / total_required * 100) if total_required > 0 else 0
        
        return {
            "format_name": format_name,
            "extracted_fields": extracted_fields,
            "missing_fields": missing_fields,
            "match_percentage": round(match_percentage, 2),
            "is_valid_format": len(missing_fields) == 0
        }
    
    async def _process_validate_document(self, text: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """文書形式の検証処理"""
        format_name = params["format_name"]
        
        # フォーマット定義の読み込み
        format_path = os.path.join(self.format_dir, f"{format_name}.json")
        if not os.path.exists(format_path):
            return {
                "error": True,
                "message": f"指定されたフォーマット '{format_name}' の定義が見つかりません"
            }
            
        with open(format_path, "r", encoding="utf-8") as f:
            format_def = json.load(f)
        
        # フィールドの抽出（check_formatと同様）
        check_result = await self._process_check_format(text, params)
        
        # バリデーションルールの適用
        validation_errors = []
        for rule in format_def.get("validation_rules", []):
            rule_type = rule["type"]
            
            if rule_type == "field_presence":
                field = rule["field"]
                if field not in check_result["extracted_fields"] or check_result["extracted_fields"][field] is None:
                    validation_errors.append(rule["message"])
        
        # 検証結果
        is_valid = len(validation_errors) == 0 and check_result.get("is_valid_format", False)
        
        return {
            "format_name": format_name,
            "is_valid": is_valid,
            "extracted_fields": check_result["extracted_fields"],
            "validation_errors": validation_errors,
            "match_percentage": check_result["match_percentage"]
        } 