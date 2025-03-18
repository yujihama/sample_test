"""
不明点発生時の自動的な対応策決定ロジックを提供するモジュール

このモジュールは、エージェントが不明点に遭遇した際に、
1. 補助ツールの使用
2. 追加データの要求
3. 人間への質問
の階層的なアプローチで問題解決を試みるロジックを提供します。
"""

import json
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from enum import Enum
from loguru import logger

from src.models.schema import MessageType, MessagePriority
from src.core.messaging import MessageClient
from src.core.config import settings
from src.tools.tool_registry import ToolRegistry


class ResolutionStrategy(Enum):
    """不明点解決のための戦略タイプ"""
    USE_TOOL = "use_tool"            # 補助ツールを利用する
    REQUEST_DATA = "request_data"    # 追加データを要求する
    ASK_HUMAN = "ask_human"          # 人間に質問する
    MAKE_ASSUMPTION = "make_assumption"  # 仮定を立てて進む
    ABORT = "abort"                  # 処理を中断する


class ConfidenceLevel(Enum):
    """不明点に対する確信度レベル"""
    HIGH = "high"        # 高い確信（80-100%）
    MEDIUM = "medium"    # 中程度の確信（50-80%）
    LOW = "low"          # 低い確信（20-50%）
    VERY_LOW = "very_low"  # 非常に低い確信（0-20%）


class AutoResolutionEngine:
    """
    不明点を自動的に解決するためのエンジン
    
    1. 不明点の種類と重要度を評価
    2. 利用可能なツールを検索
    3. 適切な解決戦略を決定
    4. 選択した戦略を実行
    """
    
    def __init__(
        self, 
        agent_id: str,
        message_client: MessageClient,
        tool_registry: Optional[ToolRegistry] = None
    ):
        """
        Args:
            agent_id: エンジンを使用するエージェントのID
            message_client: エージェント間通信用のメッセージクライアント
            tool_registry: 利用可能なツールのレジストリ
        """
        self.agent_id = agent_id
        self.message_client = message_client
        self.tool_registry = tool_registry or ToolRegistry()
        
        # 戦略選択の閾値設定
        self.strategy_thresholds = {
            "tool_confidence_threshold": 0.6,  # ツール使用の最低確信度
            "data_request_threshold": 0.4,     # データ要求の最低確信度
            "human_escalation_threshold": 0.2,  # 人間への質問の最低確信度
            "max_tool_attempts": 2,            # ツール使用の最大試行回数
            "max_data_requests": 2,            # データ要求の最大回数
        }
        
        # 処理履歴
        self.resolution_history = {}

    def determine_strategy(
        self,
        uncertainty_type: str,
        description: str,
        context: Dict[str, Any],
        confidence_level: ConfidenceLevel,
        already_tried: Optional[List[ResolutionStrategy]] = None,
        workflow_id: Optional[str] = None
    ) -> Tuple[ResolutionStrategy, Dict[str, Any]]:
        """
        不明点に対する最適な解決戦略を決定する
        
        Args:
            uncertainty_type: 不明点の種類（例: 'data_validation', 'rule_interpretation'）
            description: 不明点の詳細な説明
            context: 関連するコンテキスト情報
            confidence_level: 現在の確信度レベル
            already_tried: すでに試した戦略のリスト
            workflow_id: 関連するワークフローID
            
        Returns:
            選択された戦略とその実行に必要なパラメータのタプル
        """
        if already_tried is None:
            already_tried = []
            
        # 戦略の試行回数を追跡
        strategy_attempts = {s: 0 for s in ResolutionStrategy}
        for strategy in already_tried:
            strategy_attempts[strategy] += 1
            
        # 履歴の記録
        history_key = f"{workflow_id}_{uncertainty_type}" if workflow_id else uncertainty_type
        if history_key not in self.resolution_history:
            self.resolution_history[history_key] = []
            
        # ステップ1: 使用可能なツールを探す
        available_tools = self._find_matching_tools(uncertainty_type, description, context)
        
        # ステップ2: 確信度と過去の試行に基づいて戦略を選択
        if (confidence_level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM] and 
                available_tools and 
                strategy_attempts[ResolutionStrategy.USE_TOOL] < self.strategy_thresholds["max_tool_attempts"]):
            # ツールを使用する戦略
            best_tool = self._select_best_tool(available_tools, context)
            strategy = ResolutionStrategy.USE_TOOL
            params = {
                "tool_id": best_tool["id"],
                "tool_parameters": best_tool["suggested_parameters"]
            }
            
        elif (confidence_level in [ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW] and 
                strategy_attempts[ResolutionStrategy.REQUEST_DATA] < self.strategy_thresholds["max_data_requests"]):
            # 追加データを要求する戦略
            data_request = self._generate_data_request(uncertainty_type, description, context)
            strategy = ResolutionStrategy.REQUEST_DATA
            params = {
                "request_type": data_request["type"],
                "request_details": data_request["details"],
                "priority": MessagePriority.HIGH
            }
            
        elif confidence_level in [ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW]:
            # 人間に質問する戦略
            human_query = self._generate_human_query(uncertainty_type, description, context, already_tried)
            strategy = ResolutionStrategy.ASK_HUMAN
            params = {
                "query": human_query["query"],
                "options": human_query.get("options", []),
                "priority": MessagePriority.CRITICAL
            }
            
        else:
            # 他の戦略が使えない場合は仮定を立てて進むか中断する
            if confidence_level != ConfidenceLevel.VERY_LOW:
                strategy = ResolutionStrategy.MAKE_ASSUMPTION
                params = {
                    "assumption": self._generate_reasonable_assumption(description, context),
                    "confidence": confidence_level.value
                }
            else:
                strategy = ResolutionStrategy.ABORT
                params = {
                    "reason": f"解決策が見つかりませんでした: {description}",
                    "suggestions": self._generate_abort_suggestions(uncertainty_type, context)
                }
        
        # 履歴に記録
        self.resolution_history[history_key].append({
            "strategy": strategy.value,
            "params": params,
            "confidence_level": confidence_level.value,
            "context_summary": self._summarize_context(context)
        })
        
        return strategy, params
    
    def execute_strategy(
        self,
        strategy: ResolutionStrategy,
        params: Dict[str, Any],
        workflow_id: Optional[str] = None,
        context_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        選択された戦略を実行する
        
        Args:
            strategy: 実行する戦略
            params: 戦略実行のためのパラメータ
            workflow_id: 関連するワークフローID
            context_id: 関連するコンテキストID
            
        Returns:
            戦略実行の結果
        """
        result = {
            "strategy": strategy.value,
            "status": "executed",
            "data": None,
            "error": None
        }
        
        try:
            if strategy == ResolutionStrategy.USE_TOOL:
                # ツールを実行
                tool_id = params["tool_id"]
                tool_parameters = params["tool_parameters"]
                
                tool = self.tool_registry.get_tool(tool_id)
                if tool:
                    tool_result = tool.execute(tool_parameters)
                    result["data"] = tool_result
                else:
                    result["status"] = "failed"
                    result["error"] = f"ツール '{tool_id}' が見つかりません"
                
            elif strategy == ResolutionStrategy.REQUEST_DATA:
                # データ要求メッセージを送信
                request_type = params["request_type"]
                request_details = params["request_details"]
                priority = params.get("priority", MessagePriority.HIGH)
                
                message_id = self.message_client.send_message(
                    to_agent=settings.AGENT_A_ID,  # 通常はデータ管理エージェントに要求
                    message_type=MessageType.DATA_REQUEST,
                    content={
                        "request_type": request_type,
                        "request_details": request_details
                    },
                    priority=priority,
                    requires_response=True,
                    workflow_id=workflow_id,
                    context_id=context_id
                )
                
                result["data"] = {
                    "request_sent": True,
                    "message_id": message_id,
                    "waiting_for_response": True
                }
                
            elif strategy == ResolutionStrategy.ASK_HUMAN:
                # 人間へのクエリを送信
                query = params["query"]
                options = params.get("options", [])
                priority = params.get("priority", MessagePriority.CRITICAL)
                
                message_id = self.message_client.send_message(
                    to_agent=settings.HUMAN_AGENT_ID,  # 人間エージェント
                    message_type=MessageType.HUMAN_QUERY,
                    content={
                        "query": query,
                        "options": options
                    },
                    priority=priority,
                    requires_response=True,
                    workflow_id=workflow_id,
                    context_id=context_id
                )
                
                result["data"] = {
                    "query_sent": True,
                    "message_id": message_id,
                    "waiting_for_response": True
                }
                
            elif strategy == ResolutionStrategy.MAKE_ASSUMPTION:
                # 仮定を記録
                assumption = params["assumption"]
                confidence = params.get("confidence", "medium")
                
                result["data"] = {
                    "assumption": assumption,
                    "confidence": confidence,
                    "is_assumption": True
                }
                
                # 仮定の記録
                if workflow_id:
                    self.message_client.record_decision(
                        workflow_id=workflow_id,
                        decision_type="assumption",
                        decision_context={"context_id": context_id},
                        input_data={"issue": "uncertainty_resolution"},
                        decision_output={
                            "assumption": assumption,
                            "confidence": confidence
                        }
                    )
                
            elif strategy == ResolutionStrategy.ABORT:
                # 処理の中断
                reason = params["reason"]
                suggestions = params.get("suggestions", [])
                
                # 中断メッセージを送信
                message_id = self.message_client.send_message(
                    to_agent=settings.AGENT_A_ID,  # ワークフロー管理エージェント
                    message_type=MessageType.WORKFLOW_INTERRUPT,
                    content={
                        "reason": reason,
                        "suggestions": suggestions
                    },
                    priority=MessagePriority.CRITICAL,
                    workflow_id=workflow_id,
                    context_id=context_id
                )
                
                result["data"] = {
                    "abort_message_sent": True,
                    "message_id": message_id,
                    "reason": reason
                }
                
            else:
                result["status"] = "failed"
                result["error"] = f"未知の戦略タイプ: {strategy}"
                
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"戦略実行中にエラーが発生: {str(e)}")
            
        return result
    
    def _find_matching_tools(
        self, 
        uncertainty_type: str, 
        description: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """不明点を解決できる可能性のあるツールを見つける"""
        matching_tools = []
        
        if not self.tool_registry:
            return matching_tools
            
        # 使用可能な全ツールを取得
        all_tools = self.tool_registry.list_tools()
        
        # 各ツールの適合性をスコアリング
        for tool in all_tools:
            # ツールの機能説明に基づく簡易なマッチング
            # 実際の実装では、より高度なNLPベースのマッチングが必要
            relevance_score = self._calculate_tool_relevance(tool, uncertainty_type, description)
            
            if relevance_score > 0.3:  # 最低限の関連性閾値
                matching_tools.append({
                    "id": tool.tool_id,
                    "name": tool.name,
                    "description": tool.description,
                    "relevance_score": relevance_score,
                    "required_params": tool.get_required_parameters(),
                    "suggested_parameters": self._suggest_tool_parameters(tool, context)
                })
        
        # 関連性スコアの降順でソート
        matching_tools.sort(key=lambda x: x["relevance_score"], reverse=True)
        return matching_tools
    
    def _calculate_tool_relevance(
        self, 
        tool: Any, 
        uncertainty_type: str, 
        description: str
    ) -> float:
        """
        ツールと不明点の関連性をスコアリングする
        
        Note: 
            実際の実装では、より高度なNLPベースのマッチングアルゴリズムを使用する
        """
        # シンプルなキーワードマッチングの例
        # 本格的な実装では、埋め込みベクトルの類似性計算などを行う
        relevance = 0.0
        
        # ツールのメタデータと説明文から関連キーワードを抽出
        tool_keywords = set((tool.name + " " + tool.description).lower().split())
        uncertainty_keywords = set((uncertainty_type + " " + description).lower().split())
        
        # 共通するキーワードの数に基づくスコアリング
        common_keywords = tool_keywords.intersection(uncertainty_keywords)
        if common_keywords:
            relevance = len(common_keywords) / (len(tool_keywords) + len(uncertainty_keywords) - len(common_keywords))
        
        # ツールのタグに基づく調整
        if hasattr(tool, 'tags') and isinstance(tool.tags, list):
            for tag in tool.tags:
                if tag.lower() in uncertainty_type.lower() or tag.lower() in description.lower():
                    relevance += 0.2
        
        return min(relevance, 1.0)  # 最大値は1.0
    
    def _suggest_tool_parameters(self, tool: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        コンテキスト情報からツールのパラメータ候補を提案する
        """
        suggested_params = {}
        required_params = tool.get_required_parameters()
        
        # 各必須パラメータに対して、コンテキストから適切な値を抽出
        for param_name in required_params:
            # コンテキストから直接パラメータを抽出
            if param_name in context:
                suggested_params[param_name] = context[param_name]
            # 入れ子になったデータ構造から抽出を試みる
            elif 'data' in context and isinstance(context['data'], dict) and param_name in context['data']:
                suggested_params[param_name] = context['data'][param_name]
            # その他の潜在的なマッピング（命名規則に基づく）
            else:
                for context_key, context_value in context.items():
                    # パラメータ名が長いコンテキストキーに含まれる場合
                    if param_name in context_key:
                        suggested_params[param_name] = context_value
                        break
        
        return suggested_params
    
    def _select_best_tool(
        self, 
        matching_tools: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        最適なツールを選択する
        """
        if not matching_tools:
            raise ValueError("選択可能なツールがありません")
            
        # 関連性スコアが最も高いツールを選択（すでにソート済み）
        best_tool = matching_tools[0]
        
        # パラメータの充足度も考慮
        for tool in matching_tools:
            required_params = set(tool["required_params"])
            suggested_params = set(tool["suggested_parameters"].keys())
            
            # 必須パラメータをどれだけ提案できるかをチェック
            params_coverage = len(suggested_params.intersection(required_params)) / max(len(required_params), 1)
            
            # 総合スコア = 関連性スコア × パラメータ充足度
            total_score = tool["relevance_score"] * (0.5 + 0.5 * params_coverage)
            
            if total_score > best_tool.get("_total_score", tool["relevance_score"]):
                best_tool = tool
                best_tool["_total_score"] = total_score
        
        return best_tool
    
    def _generate_data_request(
        self, 
        uncertainty_type: str, 
        description: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        不明点に基づいて適切なデータ要求を生成する
        """
        # リクエストタイプを判定
        request_types = {
            "データ検証": "data_validation",
            "画像確認": "image_verification",
            "ドキュメント": "document_request",
            "エクセルデータ": "excel_data",
            "規程情報": "regulation_information",
            "ユーザー情報": "user_information"
        }
        
        request_type = "additional_data"  # デフォルト
        for key, value in request_types.items():
            if key in description or key in uncertainty_type:
                request_type = value
                break
        
        # 詳細を生成
        details = {
            "uncertainty_type": uncertainty_type,
            "description": description,
            "context_summary": self._summarize_context(context),
            "specific_data_needed": self._extract_data_needs(description, context)
        }
        
        return {
            "type": request_type,
            "details": details
        }
    
    def _extract_data_needs(self, description: str, context: Dict[str, Any]) -> List[str]:
        """
        不明点の説明から具体的なデータニーズを抽出する
        """
        # より高度なNLPベースの抽出が必要
        # ここでは簡易的な実装
        data_needs = []
        
        # キーワードベースのデータ需要の判断例
        keywords_to_needs = {
            "日付": "日付情報",
            "金額": "金額データ",
            "承認者": "承認者情報",
            "ドキュメント": "対象文書",
            "規程": "規程データ",
            "マニュアル": "マニュアル文書",
            "画像": "画像データ",
            "写真": "画像データ",
            "エクセル": "Excelファイル",
            "表": "表形式データ",
            "履歴": "履歴データ",
            "記録": "記録データ"
        }
        
        for keyword, need in keywords_to_needs.items():
            if keyword in description:
                data_needs.append(need)
        
        return list(set(data_needs))  # 重複を除去
    
    def _generate_human_query(
        self, 
        uncertainty_type: str, 
        description: str, 
        context: Dict[str, Any],
        already_tried: List[ResolutionStrategy]
    ) -> Dict[str, Any]:
        """
        人間に提示する質問を生成する
        """
        # 試行済みの方法についての情報を含める
        tried_approaches = []
        for strategy in already_tried:
            if strategy == ResolutionStrategy.USE_TOOL:
                tried_approaches.append("補助ツールによる解決")
            elif strategy == ResolutionStrategy.REQUEST_DATA:
                tried_approaches.append("追加データの要求")
        
        tried_info = ""
        if tried_approaches:
            tried_info = "これまでに " + "、".join(tried_approaches) + " を試みましたが解決に至りませんでした。"
        
        # 質問の構築
        query = f"""以下の不明点について判断が必要です：
        
【課題タイプ】{uncertainty_type}
【詳細】{description}
【コンテキスト】{self._summarize_context(context)}

{tried_info}

どのように進めるべきか、ご指示をお願いします。"""
        
        # 選択肢の提案（オプショナル）
        options = []
        
        # 不明点の種類に基づいて選択肢を生成
        if "規程" in uncertainty_type or "規則" in uncertainty_type:
            options = [
                "規程を厳格に適用して処理を進める",
                "例外として柔軟に解釈して進める",
                "上位管理者の判断を仰ぐ",
                "処理を保留する"
            ]
        elif "データ整合性" in uncertainty_type:
            options = [
                "データの不一致を警告として記録し、処理を続行",
                "より信頼性の高いデータ源を優先して処理",
                "追加の検証を行った上で処理",
                "不整合が解消されるまで処理を中止"
            ]
        
        return {
            "query": query,
            "options": options
        }
    
    def _generate_reasonable_assumption(
        self, 
        description: str, 
        context: Dict[str, Any]
    ) -> str:
        """
        合理的な仮定を生成する
        
        Note:
            実際の実装では、より高度な推論や過去の類似事例の参照などが必要
        """
        # コンテキストと不明点の種類に基づいて仮定を生成する例
        return f"利用可能な情報に基づく最も妥当な判断: 標準的な処理手順に従う。不明点「{description}」については、デフォルトの処理規則を適用。"
    
    def _generate_abort_suggestions(
        self, 
        uncertainty_type: str, 
        context: Dict[str, Any]
    ) -> List[str]:
        """
        処理を中断する場合の提案を生成する
        """
        suggestions = [
            "必要な追加情報を明確にして、データ要求プロセスを改善する",
            "同様のケースの処理例を参照し、処理規則を更新する",
            "不明点解決のための意思決定マトリックスを定義する"
        ]
        
        if "規程" in uncertainty_type:
            suggestions.append("規程の曖昧な部分を明確化するための改訂を提案する")
        elif "データ" in uncertainty_type:
            suggestions.append("データの一貫性チェックプロセスを強化する")
        
        return suggestions
    
    def _summarize_context(self, context: Dict[str, Any]) -> str:
        """
        コンテキスト情報を要約する
        """
        # 実際の実装では、より高度な要約アルゴリズムが必要
        summary_parts = []
        
        important_keys = ["workflow_id", "task_type", "document_type", "entity_id", "user_id", "request_date"]
        for key in important_keys:
            if key in context:
                summary_parts.append(f"{key}: {context[key]}")
        
        # その他の重要な情報を追加
        if "data" in context and isinstance(context["data"], dict):
            data_summary = []
            for k, v in context["data"].items():
                if isinstance(v, (str, int, float, bool)):
                    data_summary.append(f"{k}: {v}")
                elif v is None:
                    data_summary.append(f"{k}: なし")
                else:
                    data_summary.append(f"{k}: {type(v).__name__}")
            
            if data_summary:
                summary_parts.append("データ: " + ", ".join(data_summary[:5]))
                if len(data_summary) > 5:
                    summary_parts[-1] += f" (他 {len(data_summary)-5} 項目)"
        
        return "; ".join(summary_parts) 