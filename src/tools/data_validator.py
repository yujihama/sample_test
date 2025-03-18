"""
データ照合ツール - 社員マスタなどのリファレンスデータと照合するツール
"""

import os
from typing import Dict, List, Any, Optional
import uuid
import json
import pandas as pd
from datetime import datetime

from loguru import logger
from src.core.tool_base import ToolBase, ToolResult
from src.core.config import settings


class DataValidator(ToolBase):
    """データ照合ツール"""
    
    def __init__(self, tool_id: str = None):
        """
        データ照合ツールの初期化
        
        Args:
            tool_id: ツールID（省略時は自動生成）
        """
        super().__init__(tool_id)
        self.description = "データ照合ツール - 社員情報・承認権限の照合などを行う"
        self.version = "1.0.0"
        self.capabilities = [
            "verify_employee",     # 社員情報照会
            "check_authority",     # 権限レベル確認
            "validate_approval",   # 承認権限の照合
        ]
        
        # デモデータの保存先
        self.data_dir = os.path.join(settings.DATA_DIR, "reference_data")
        os.makedirs(self.data_dir, exist_ok=True)
        
        # デモ用のサンプルデータ作成（実際の環境では外部DBから取得）
        self._prepare_demo_data()
        
        logger.info(f"データ照合ツール初期化完了: {self.tool_id}")
    
    def _prepare_demo_data(self):
        """デモ用のサンプルデータを準備"""
        # 社員情報サンプルデータ
        employee_data = [
            {"id": "E001", "name": "山田太郎", "department": "経理部", "position": "部長", "authority_level": 5},
            {"id": "E002", "name": "佐藤花子", "department": "経理部", "position": "課長", "authority_level": 4},
            {"id": "E003", "name": "鈴木一郎", "department": "経理部", "position": "主任", "authority_level": 3},
            {"id": "E004", "name": "田中実", "department": "営業部", "position": "部長", "authority_level": 5},
            {"id": "E005", "name": "中村誠", "department": "営業部", "position": "課長", "authority_level": 4},
            {"id": "E006", "name": "小林智子", "department": "開発部", "position": "部長", "authority_level": 5}
        ]
        
        # 承認権限サンプルデータ
        approval_rules = [
            {"category": "出張申請", "min_amount": 0, "max_amount": 100000, "required_level": 3},
            {"category": "出張申請", "min_amount": 100001, "max_amount": 300000, "required_level": 4},
            {"category": "出張申請", "min_amount": 300001, "max_amount": None, "required_level": 5},
            {"category": "経費精算", "min_amount": 0, "max_amount": 50000, "required_level": 3},
            {"category": "経費精算", "min_amount": 50001, "max_amount": 200000, "required_level": 4},
            {"category": "経費精算", "min_amount": 200001, "max_amount": None, "required_level": 5}
        ]
        
        # データをJSONファイルとして保存
        with open(os.path.join(self.data_dir, "employees.json"), "w", encoding="utf-8") as f:
            json.dump(employee_data, f, ensure_ascii=False, indent=2)
            
        with open(os.path.join(self.data_dir, "approval_rules.json"), "w", encoding="utf-8") as f:
            json.dump(approval_rules, f, ensure_ascii=False, indent=2)
    
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
            
        # 操作別の必須パラメータ確認
        if operation == "verify_employee":
            if not any(k in params for k in ["employee_id", "employee_name"]):
                logger.error("employee_id または employee_name が必要です")
                return False
                
        elif operation == "check_authority":
            if "employee_id" not in params:
                logger.error("employee_id パラメータが必要です")
                return False
                
        elif operation == "validate_approval":
            required = ["category", "amount", "approver_id"]
            if not all(k in params for k in required):
                logger.error(f"操作 {operation} には次のパラメータが必要です: {required}")
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
            
            if operation == "verify_employee":
                result_data = await self._process_verify_employee(params)
            elif operation == "check_authority":
                result_data = await self._process_check_authority(params)
            elif operation == "validate_approval":
                result_data = await self._process_validate_approval(params)
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
            logger.error(f"データ照合ツール実行エラー: {e}")
            return await self.handle_error(e, params)
    
    async def _process_verify_employee(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """社員情報の照合処理"""
        # 社員データの読み込み
        with open(os.path.join(self.data_dir, "employees.json"), "r", encoding="utf-8") as f:
            employees = json.load(f)
        
        # 検索条件
        employee_id = params.get("employee_id")
        employee_name = params.get("employee_name")
        
        # 検索
        result = None
        if employee_id:
            for emp in employees:
                if emp["id"] == employee_id:
                    result = emp
                    break
        elif employee_name:
            for emp in employees:
                if emp["name"] == employee_name:
                    result = emp
                    break
        
        if result:
            return {
                "found": True,
                "employee_info": result
            }
        else:
            return {
                "found": False,
                "message": "指定された社員情報が見つかりません"
            }
    
    async def _process_check_authority(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """権限レベルの確認処理"""
        # 社員データの読み込み
        with open(os.path.join(self.data_dir, "employees.json"), "r", encoding="utf-8") as f:
            employees = json.load(f)
        
        # 社員ID
        employee_id = params["employee_id"]
        
        # 検索
        employee = None
        for emp in employees:
            if emp["id"] == employee_id:
                employee = emp
                break
        
        if not employee:
            return {
                "found": False,
                "message": "指定された社員IDが見つかりません"
            }
        
        return {
            "found": True,
            "employee_id": employee["id"],
            "name": employee["name"],
            "department": employee["department"],
            "position": employee["position"],
            "authority_level": employee["authority_level"]
        }
    
    async def _process_validate_approval(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """承認権限の照合処理"""
        # データの読み込み
        with open(os.path.join(self.data_dir, "employees.json"), "r", encoding="utf-8") as f:
            employees = json.load(f)
            
        with open(os.path.join(self.data_dir, "approval_rules.json"), "r", encoding="utf-8") as f:
            rules = json.load(f)
        
        # パラメータの取得
        category = params["category"]
        amount = float(params["amount"])
        approver_id = params["approver_id"]
        
        # 承認者の情報を取得
        approver = None
        for emp in employees:
            if emp["id"] == approver_id:
                approver = emp
                break
        
        if not approver:
            return {
                "valid": False,
                "message": "指定された承認者IDが見つかりません"
            }
        
        # 適用されるルールを検索
        applicable_rule = None
        for rule in rules:
            if rule["category"] == category:
                min_amount = rule["min_amount"] or 0
                max_amount = rule["max_amount"] or float('inf')
                
                if min_amount <= amount and amount <= max_amount:
                    applicable_rule = rule
                    break
        
        if not applicable_rule:
            return {
                "valid": False,
                "message": f"指定されたカテゴリと金額に対応するルールが見つかりません: {category}, {amount}"
            }
        
        # 承認権限の検証
        required_level = applicable_rule["required_level"]
        approver_level = approver["authority_level"]
        
        is_valid = approver_level >= required_level
        
        return {
            "valid": is_valid,
            "required_level": required_level,
            "approver_level": approver_level,
            "approver_name": approver["name"],
            "approver_position": approver["position"],
            "message": "承認権限は有効です" if is_valid else "承認権限が不足しています"
        } 