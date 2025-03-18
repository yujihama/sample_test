"""
エージェントB: 監査テスト実行
"""

import uuid
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple, cast
from datetime import datetime
import asyncio
import json
import os

from loguru import logger
from pydantic import BaseModel, Field

from src.core.agent_base import AgentBase, AgentState
from src.core.config import settings
from src.utils.data_utils import (
    load_sample_data,
    validate_dataframe,
    execute_test_item,
    generate_test_summary,
)
from src.tools.tool_registry import ToolRegistry
from src.agents.agent_b_graph import create_agent_b_graph
from src.core.messaging import MessageClient, MessageType


class AgentBState(AgentState):
    """エージェントBの状態クラス"""
    # テスト計画関連
    test_plan_id: Optional[str] = None
    test_plan: Optional[Dict[str, Any]] = None
    
    # サンプルデータ関連
    sample_id: Optional[str] = None
    sample_path: Optional[str] = None
    
    # 出力関連
    test_results: Optional[Dict[str, Any]] = None
    
    # ツール関連
    tool_execution_history: List[Dict[str, Any]] = Field(default_factory=list)
    requested_tools: List[str] = Field(default_factory=list)
    pending_tool_requests: List[Dict[str, Any]] = Field(default_factory=list)
    
    # グラフ関連（追加）
    graph_state: Optional[Dict[str, Any]] = Field(default_factory=dict)
    current_step: Optional[str] = None
    problem_type: Optional[str] = None
    checkpoints: List[Dict[str, Any]] = Field(default_factory=list)
    
    # その他
    is_processing: bool = False


class AgentB(AgentBase):
    def __init__(self, message_client: Optional[MessageClient] = None):
        """
        初期化
        
        Args:
            message_client: メッセージクライアント（オプション）
        """
        super().__init__(
            agent_id=settings.AGENT_B_ID,
            state_class=AgentBState,
            agent_name="監査テスト実行エージェント"
        )
        self.message_client = message_client
        
        # ツールレジストリの初期化
        self.tool_registry = ToolRegistry()
        
        # エージェントBグラフの作成
        self.graph = create_agent_b_graph()
        
        # メッセージングプロパティの追加（テスト用）
        self.messaging = self.message_client
        
        logger.info("AgentB initialized")
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """メッセージ処理のエントリーポイント"""
        content = message.get("content", {})
        message_type = message.get("type", "unknown")
        
        logger.info(f"AgentB: {message_type}メッセージを受信")
        
        if message_type == "test_plan":
            return await self.handle_test_plan(content)
        elif message_type == "execute_test":
            return await self.handle_execute_test(content)
        elif message_type == "sample_data_update":
            return await self.handle_sample_data_update(content)
        elif message_type == "question":
            return await self.handle_question(content)
        # データリクエストの処理を追加
        elif message_type == MessageType.DATA_REQUEST:
            return await self.handle_data_request(content)
        # ツール関連メッセージタイプを追加
        elif message_type == "tool_request":
            return await self.handle_tool_request(content)
        elif message_type == "tool_response":
            return await self.handle_tool_response(content)
        # LangGraph拡張: 情報追加メッセージタイプ
        elif message_type == "additional_info":
            return await self.handle_additional_info(content)
        # LangGraph拡張: チェックポイント関連
        elif message_type == "restore_checkpoint":
            return await self.handle_restore_checkpoint(content)
        else:
            logger.warning(f"AgentB: 未知のメッセージタイプ {message_type}")
            return {
                "status": "error",
                "message": f"未知のメッセージタイプ: {message_type}"
            }
    
    async def handle_test_plan(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        テスト計画メッセージの処理
        
        Args:
            content: メッセージコンテンツ
            
        Returns:
            処理結果
        """
        if self.state.is_processing:
            return {
                "status": "busy", 
                "message": "エージェントは既にタスクを処理中です",
                "current_task": "テスト実行中"
            }
        
        test_plan = content.get("test_plan")
        if not test_plan:
            return {"status": "error", "error": "テスト計画が必要です"}
        
        procedure_id = content.get("procedure_id")
        sample_id = content.get("sample_id")
        workflow_id = content.get("workflow_id")
        
        # 必須パラメータの検証
        if not all([procedure_id, sample_id]):
            missing_params = []
            if not procedure_id:
                missing_params.append("procedure_id")
            if not sample_id:
                missing_params.append("sample_id")
            
            return {
                "status": "error", 
                "error": f"必須パラメータがありません: {', '.join(missing_params)}"
            }
        
        # テスト計画のバリデーション
        if not test_plan.get("test_items"):
            return {
                "status": "error", 
                "error": "テスト計画にテスト項目がありません"
            }
        
        # テスト計画の詳細をログに記録
        test_items = test_plan.get("test_items", [])
        test_count = len(test_items)
        logger.info(f"テスト計画を受信しました: {test_count}個のテスト項目があります")
        
        for i, item in enumerate(test_items, 1):
            logger.info(f"テスト項目 {i}: {item.get('name')} - リスク: {item.get('risk_addressed', '未指定')}")
        
        # テスト計画IDを生成
        test_plan_id = f"plan-{uuid.uuid4().hex[:8]}"
        
        # 状態を更新
        self.state.update(
            test_plan_id=test_plan_id,
            test_plan=test_plan,
            sample_id=sample_id,
            is_processing=False
        )
        
        # データベースに関連情報が登録されていれば、サンプルパスを取得
        try:
            from src.models.repositories import SampleDataRepository
            from src.utils.db_manager import get_db
            
            db = next(get_db())
            sample_repo = SampleDataRepository()
            sample_data = sample_repo.get(db, sample_id)
            
            if sample_data and sample_data.file_path:
                self.state.update(sample_path=sample_data.file_path)
                logger.info(f"サンプルデータパスをデータベースから取得しました: {sample_data.file_path}")
        except Exception as e:
            logger.warning(f"サンプルデータパスのデータベース参照中にエラー: {e}")
        
        # ワークフローIDを保存（存在する場合）
        if workflow_id:
            self.state.metadata["workflow_id"] = workflow_id
        
        # 状態の保存
        self._save_agent_state()
        
        return {
            "status": "success",
            "message": f"テスト計画を受け入れました。{test_count}個のテスト項目があります。",
            "test_plan_id": test_plan_id
        }
    
    async def handle_execute_test(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        テスト実行メッセージの処理
        
        Args:
            content: メッセージコンテンツ
            
        Returns:
            処理結果
        """
        if self.state.is_processing:
            return {
                "status": "busy", 
                "message": "エージェントは既にタスクを処理中です",
                "current_task": "テスト実行中"
            }
        
        # サンプルパスの入手（優先順位：メッセージ内 > 状態保存済み > データベース参照）
        sample_path = content.get("sample_path", self.state.sample_path)
        sample_id = content.get("sample_id", self.state.sample_id)
        
        # パスがない場合はデータベースから取得を試みる
        if not sample_path and sample_id:
            try:
                from src.models.repositories import SampleDataRepository
                from src.utils.db_manager import get_db
                
                db = next(get_db())
                sample_repo = SampleDataRepository()
                sample_data = sample_repo.get(db, sample_id)
                
                if sample_data and sample_data.file_path:
                    sample_path = sample_data.file_path
                    logger.info(f"サンプルデータパスをデータベースから取得しました: {sample_path}")
            except Exception as e:
                logger.error(f"サンプルデータパスのデータベース参照中にエラー: {e}")
        
        # サンプルパスの検証
        if not sample_path:
            return {
                "status": "error", 
                "error": "サンプルデータのパスが必要です。sample_pathパラメータを指定してください。"
            }
        
        # テスト計画の検証
        if not self.state.test_plan:
            return {
                "status": "error", 
                "error": "テスト計画が設定されていません。先にテスト計画を送信してください。"
            }
        
        # 処理状態を更新
        self.state.update(
            sample_path=sample_path,
            is_processing=True,
            status="busy"
        )
        self._save_agent_state()
        
        try:
            # LangGraph拡張: 実行モードを選択
            if content.get("use_graph", True):
                # LangGraphを使った実行
                return await self.execute_test_with_graph(content)
            else:
                # 従来の方法での実行
                # サンプルデータをロード
                logger.info(f"サンプルデータをロード中: {sample_path}")
                df, metadata = await asyncio.to_thread(load_sample_data, sample_path)
                
                # 基本的なデータ検証
                if df.empty:
                    self.state.update(is_processing=False, status="error")
                    return {"status": "error", "error": "サンプルデータが空です"}
                
                # サンプルデータの基本情報をログに記録
                row_count = len(df)
                col_count = len(df.columns)
            # サンプルデータをロード
            logger.info(f"サンプルデータをロード中: {sample_path}")
            df, metadata = await asyncio.to_thread(load_sample_data, sample_path)
            
            # 基本的なデータ検証
            if df.empty:
                self.state.update(is_processing=False, status="error")
                return {"status": "error", "error": "サンプルデータが空です"}
            
            # サンプルデータの基本情報をログに記録
            row_count = len(df)
            col_count = len(df.columns)
            logger.info(f"サンプルデータをロードしました: {row_count}行 x {col_count}列")
            logger.info(f"カラム: {', '.join(df.columns.tolist())}")
            
            # サンプルIDを更新（メタデータから取得するか、与えられたIDを使用）
            sample_id = metadata.get("id") or sample_id
            if sample_id:
                self.state.update(sample_id=sample_id)
            
            # テスト項目を実行
            logger.info(f"テスト項目の実行を開始します: {len(self.state.test_plan.get('test_items', []))}個")
            results = await self.execute_test_items(df, self.state.test_plan.get("test_items", []))
            
            # テスト結果をまとめる
            summary = generate_test_summary(results)
            
            # テスト結果を作成
            test_result = {
                "id": f"exec-{uuid.uuid4().hex[:8]}",
                "plan_id": self.state.test_plan_id,
                "execution_status": "completed",
                "results": results,
                "summary": summary,
                "executed_at": datetime.now().isoformat(),
                "sample_id": sample_id,
                "sample_metadata": {
                    "row_count": row_count,
                    "column_count": col_count,
                    "columns": df.columns.tolist()
                }
            }
            
            # ワークフローIDがあれば追加
            if "workflow_id" in self.state.metadata:
                test_result["workflow_id"] = self.state.metadata["workflow_id"]
            
            # 状態を更新
            self.state.update(
                test_results=test_result,
                is_processing=False,
                status="idle"
            )
            self._save_agent_state()
            
            # 結果の詳細をログに記録
            logger.info(f"テスト実行完了: 合格={summary.get('pass', 0)}, 失敗={summary.get('fail', 0)}, エラー={summary.get('error', 0)}")
            
            # エージェントCにテスト結果を送信
            message_id = self.send_message(
                to_agent=settings.AGENT_C_ID,
                message_type="test_results",
                content={
                    "results": test_result,
                    "test_plan": self.state.test_plan,
                    "workflow_id": self.state.metadata.get("workflow_id")
                }
            )
            
            logger.info(f"テスト結果をエージェントCに送信しました: {message_id}")
            
            return {
                "status": "success",
                "message": f"テスト実行が完了しました: 合格={summary.get('pass', 0)}, 失敗={summary.get('fail', 0)}, エラー={summary.get('error', 0)}",
                "test_results": test_result
            }
        
        except Exception as e:
            logger.error(f"テスト実行中にエラーが発生しました: {e}")
            self.state.update(is_processing=False, status="error")
            self._save_agent_state()
            return {
                "status": "error", 
                "error": f"テスト実行中にエラーが発生しました: {str(e)}"
            }
    
    async def handle_sample_data_update(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        サンプルデータ更新メッセージの処理
        
        Args:
            content: メッセージコンテンツ
            
        Returns:
            処理結果
        """
        sample_path = content.get("sample_path")
        if not sample_path:
            return {"status": "error", "error": "Sample data path is required"}
        
        # 状態を更新
        self.state.update(sample_path=sample_path)
        
        # テスト計画が既にある場合は、テストを実行
        if self.state.test_plan:
            return await self.handle_execute_test({"sample_path": sample_path})
        
        return {
            "status": "success",
            "message": "Sample data path updated",
            "awaiting_test_plan": True
        }
    
    async def handle_question(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        質問メッセージの処理
        
        Args:
            content: メッセージコンテンツ
            
        Returns:
            処理結果
        """
        question = content.get("question")
        from_agent = content.get("from_agent")
        
        if not question:
            return {"status": "error", "error": "Question is required"}
        
        try:
            # ここで質問に回答するロジックを実装する
            # 単純な情報提供のためのダミー回答
            answer = f"""
            現在のテスト実行状況:
            
            テスト計画ID: {self.state.test_plan_id or 'なし'}
            サンプルデータパス: {self.state.sample_path or 'なし'}
            テスト実行状態: {self.state.status}
            
            テスト結果サマリー: {self.state.test_results.get('summary') if self.state.test_results else 'まだ実行されていません'}
            
            質問: {question}
            回答: これはエージェントBからの自動応答です。実際のアプリケーションでは、LLMを使用してより適切な回答を生成します。
            """
            
            # 返信メッセージの送信（質問者がいる場合）
            if from_agent:
                self.send_message(
                    to_agent=from_agent,
                    message_type="answer",
                    content={"question": question, "answer": answer}
                )
            
            return {
                "status": "success",
                "answer": answer
            }
        
        except Exception as e:
            logger.error(f"Error in handle_question: {e}")
            return {"status": "error", "error": str(e)}
    
    async def execute_test_items(
        self, df: pd.DataFrame, test_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        テスト項目を実行
        
        Args:
            df: 対象のDataFrame
            test_items: テスト項目のリスト
            
        Returns:
            テスト結果のリスト
        """
        results = []
        
        for item in test_items:
            try:
                # テスト項目の実行をスレッドプールで実行（I/O待ちになる可能性があるため）
                result = await asyncio.to_thread(execute_test_item, df, item)
                results.append(result)
            except Exception as e:
                logger.error(f"Error executing test item {item.get('id')}: {e}")
                results.append({
                    "test_item_id": item.get("id"),
                    "result": "error",
                    "details": f"テスト実行中にエラーが発生しました: {str(e)}",
                    "affected_rows": [],
                    "exception_data": {},
                })
        
        return results

    def _save_agent_state(self):
        """
        エージェントの状態をデータベースに保存
        """
        try:
            from src.models.repositories import AgentStateRepository
            from src.utils.db_manager import get_db
            
            # DBセッションを取得
            db = next(get_db())
            
            # 状態リポジトリを初期化
            state_repo = AgentStateRepository()
            
            # 現在の状態をシリアライズ
            state_data = self.state.dict()
            
            # データが存在するか確認して保存または更新
            try:
                # 状態を保存 (upsert操作)
                if hasattr(state_repo, 'save_agent_state'):
                    state_repo.save_agent_state(db, self.agent_id, state_data)
                elif hasattr(state_repo, 'upsert'):
                    state_repo.upsert(db, {"agent_id": self.agent_id, "state_data": state_data})
                else:
                    # 既存データの確認
                    existing = state_repo.get_by_agent_id(db, self.agent_id)
                    if existing:
                        # 更新
                        state_repo.update(db, self.agent_id, {"state_data": state_data})
                    else:
                        # 新規作成
                        state_repo.create(db, {
                            "agent_id": self.agent_id,
                            "state_data": state_data,
                            "updated_at": datetime.now()
                        })
                
                logger.debug(f"エージェントBの状態を保存しました: {self.agent_id}")
            except Exception as db_error:
                logger.error(f"データベース操作中にエラー: {db_error}")
        except Exception as e:
            logger.error(f"エージェントBの状態保存中にエラー: {e}")
            # エラーが発生しても処理は続行する（非クリティカル機能）

    # 新規追加: ツールリクエスト処理
    async def handle_tool_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        ツールリクエストの処理
        
        Args:
            content: リクエスト内容
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        tool_id = content.get("tool_id")
        params = content.get("params", {})
        request_id = content.get("request_id", str(uuid.uuid4()))
        
        logger.info(f"AgentB: ツールリクエスト受信 - {tool_id}")
        
        if not tool_id:
            return {
                "status": "error",
                "message": "ツールIDが指定されていません",
                "request_id": request_id
            }
            
        # ツールの実行
        result = await self._execute_tool(tool_id, params, request_id)
        
        # 要求元に結果を通知
        if content.get("requires_response", True):
            requester = content.get("requester", settings.AGENT_A_ID)
            self.send_response(
                to_agent=requester,
                in_response_to=content.get("message_id", ""),
                message_type="tool_response",
                content={
                    "request_id": request_id,
                    "tool_id": tool_id,
                    "result": result.dict(),
                    "status": result.status
                }
            )
            
        # ツール実行履歴を記録
        self.state.tool_execution_history.append({
            "request_id": request_id,
            "tool_id": tool_id,
            "params": params,
            "result": result.dict(),
            "timestamp": datetime.now().isoformat()
        })
        self._save_agent_state()
        
        return {
            "status": "success",
            "message": f"ツール {tool_id} を実行しました",
            "request_id": request_id,
            "result": result.dict()
        }
    
    # 新規追加: ツールレスポンス処理
    async def handle_tool_response(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        ツール実行結果の処理
        
        Args:
            content: レスポンス内容
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        request_id = content.get("request_id")
        result = content.get("result", {})
        
        logger.info(f"AgentB: ツール実行結果受信 - リクエストID: {request_id}")
        
        # 保留中のリクエストから該当するものを探す
        for i, req in enumerate(self.state.pending_tool_requests):
            if req.get("request_id") == request_id:
                # 保留中リクエストを削除
                req = self.state.pending_tool_requests.pop(i)
                
                # コールバック処理があれば実行
                callback = req.get("callback")
                if callback and callable(callback):
                    await callback(result)
                
                break
        
        self._save_agent_state()
        
        return {
            "status": "success",
            "message": f"ツール実行結果を処理しました: {request_id}",
            "request_id": request_id
        }
    
    # 新規追加: ツール実行の内部処理
    async def _execute_tool(self, tool_id: str, params: Dict[str, Any], request_id: str = None):
        """
        ツールの実行
        
        Args:
            tool_id: ツールID
            params: 実行パラメータ
            request_id: リクエストID
            
        Returns:
            ToolResult: ツール実行結果
        """
        logger.info(f"AgentB: ツール実行 - {tool_id}")
        
        # リクエストIDがなければ生成
        if not request_id:
            request_id = str(uuid.uuid4())
            
        # ツールレジストリからツールを取得して実行
        return await self.tool_registry.execute_tool(tool_id, params)
    
    # 新規追加: 利用可能なツールのリストを取得
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        利用可能なツールのリストを取得
        
        Returns:
            List[Dict[str, Any]]: ツール情報リスト
        """
        return self.tool_registry.get_tool_info()
    
    # 新規追加: 画像処理ツールを利用するヘルパーメソッド
    async def process_image(self, image_path: str, operation: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        画像処理ツールを利用する
        
        Args:
            image_path: 画像ファイルパス
            operation: 実行する操作
            params: 追加パラメータ
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        if not params:
            params = {}
            
        tool_params = {
            "operation": operation,
            "image_path": image_path,
            **params
        }
        
        # 画像処理ツールを探す
        tools = self.tool_registry.get_all_tools()
        image_tool_id = None
        
        for tool_id, tool in tools.items():
            if tool.__class__.__name__ == "ImageProcessor":
                image_tool_id = tool_id
                break
                
        if not image_tool_id:
            logger.error("画像処理ツールが登録されていません")
            return {"status": "error", "message": "画像処理ツールが利用できません"}
            
        # ツール実行
        result = await self._execute_tool(image_tool_id, tool_params)
        
        return result.dict() if result else {"status": "error", "message": "画像処理ツールの実行に失敗しました"}
    
    # 新規追加: Excelデータ解析ツールを利用するヘルパーメソッド
    async def analyze_excel(self, file_path: str, operation: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Excelデータ解析ツールを利用する
        
        Args:
            file_path: Excelファイルパス
            operation: 実行する操作
            params: 追加パラメータ
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        if not params:
            params = {}
            
        tool_params = {
            "operation": operation,
            "file_path": file_path,
            **params
        }
        
        # Excelツールを探す
        tools = self.tool_registry.get_all_tools()
        excel_tool_id = None
        
        for tool_id, tool in tools.items():
            if tool.__class__.__name__ == "ExcelAnalyzer":
                excel_tool_id = tool_id
                break
                
        if not excel_tool_id:
            logger.error("Excelデータ解析ツールが登録されていません")
            return {"status": "error", "message": "Excelデータ解析ツールが利用できません"}
            
        # ツール実行
        result = await self._execute_tool(excel_tool_id, tool_params)
        
        return result.dict() if result else {"status": "error", "message": "Excelデータ解析ツールの実行に失敗しました"}
    
    async def execute_test_with_graph(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraphを使ってテストを実行
        
        Args:
            content: メッセージコンテンツ
            
        Returns:
            処理結果
        """
        logger.info(f"LangGraphを使ってテスト実行を開始: {self.state.test_plan_id}")
        
        # 初期グラフ状態の作成
        workflow_id = content.get("workflow_id", self.state.metadata.get("workflow_id", f"wf-{uuid.uuid4().hex[:8]}"))
        
        # グラフ状態の初期化
        graph_state = {
            "workflow_id": workflow_id,
            "procedure_id": self.state.metadata.get("procedure_id", ""),
            "procedure_text": content.get("procedure_text", ""),
            "sample_id": self.state.sample_id,
            "sample_path": self.state.sample_path,
            "test_plan": self.state.test_plan,
            "status": "in_progress",
            "current_step": "problem_classification",
            "required_info": [],
            "collected_info": {},
            "selected_tools": [],
            "tool_results": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        
        try:
            # グラフを実行
            logger.info(f"グラフ実行開始: {workflow_id}")
            result_state = await self.graph.ainvoke(graph_state)
            
            # 結果の解析
            status = result_state.get("status", "error")
            
            if status == "completed":
                # 完了状態
                solution = result_state.get("solution", {})
                evaluation = result_state.get("evaluation", {})
                
                # テスト結果の形式に変換
                test_results = self._convert_graph_results_to_test_results(result_state)
                
                # 状態を更新
                self.state.update(
                    test_results=test_results,
                    graph_state=result_state,
                    current_step=result_state.get("current_step"),
                    problem_type=result_state.get("problem_type"),
                    is_processing=False,
                    status="completed"
                )
                self._save_agent_state()
                
                return {
                    "status": "success",
                    "message": f"テスト実行が完了しました。品質: {evaluation.get('quality', 'unknown')}",
                    "test_results": test_results
                }
                
            elif status == "waiting_for_info":
                # 情報待ち状態
                checkpoints = result_state.get("checkpoints", [])
                current_checkpoint = checkpoints[-1] if checkpoints else {}
                missing_info = current_checkpoint.get("missing_info", [])
                
                # 状態を更新
                self.state.update(
                    graph_state=result_state,
                    current_step=result_state.get("current_step"),
                    problem_type=result_state.get("problem_type"),
                    checkpoints=checkpoints,
                    is_processing=False,
                    status="waiting_for_info"
                )
                self._save_agent_state()
                
                return {
                    "status": "waiting_for_info",
                    "message": "追加情報が必要です",
                    "missing_info": missing_info,
                    "checkpoint_id": current_checkpoint.get("id")
                }
                
            else:
                # エラー状態
                error_message = result_state.get("error", "不明なエラー")
                
                # 状態を更新
                self.state.update(
                    graph_state=result_state,
                    is_processing=False,
                    status="error"
                )
                self._save_agent_state()
                
                return {
                    "status": "error",
                    "error": error_message
                }
                
        except Exception as e:
            logger.error(f"グラフ実行中にエラー: {e}")
            self.state.update(is_processing=False, status="error")
            return {"status": "error", "error": str(e)}
    
    def _convert_graph_results_to_test_results(self, graph_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        グラフ実行結果をテスト結果形式に変換
        
        Args:
            graph_state: グラフ実行の結果状態
            
        Returns:
            テスト結果
        """
        solution = graph_state.get("solution", {})
        evaluation = graph_state.get("evaluation", {})
        actions = solution.get("actions", [])
        
        # 結果のカウント
        passed = 0
        failed = 0
        
        # 各テスト項目の結果
        results = []
        
        for action in actions:
            # テスト項目の評価（実際の実装ではテスト実行結果に基づく）
            confidence = solution.get("confidence", 0.7)
            is_passed = confidence > 0.6  # シンプルな判定条件
            
            result = {
                "test_item_id": action.get("test_id", ""),
                "test_name": action.get("name", "未定義テスト"),
                "result": "pass" if is_passed else "fail",
                "details": action.get("description", ""),
                "affected_rows": [],  # 実際の実装では影響行を特定
                "timestamp": datetime.now().isoformat()
            }
            
            results.append(result)
            if is_passed:
                passed += 1
            else:
                failed += 1
        
        # サマリーの作成
        summary = {
            "pass": passed,
            "fail": failed,
            "error": 0,
            "skipped": 0,
            "total": len(actions),
            "quality": evaluation.get("quality", "unknown"),
            "recommendation": evaluation.get("recommendation", "")
        }
        
        return {
            "summary": summary,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    async def handle_additional_info(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        追加情報の処理
        
        Args:
            content: メッセージコンテンツ
            
        Returns:
            処理結果
        """
        logger.info(f"追加情報を受信: {content.get('info_type', 'unknown')}")
        
        # 必要なパラメータの検証
        if not self.state.graph_state:
            return {"status": "error", "error": "グラフ状態が初期化されていません"}
        
        if self.state.status != "waiting_for_info":
            return {"status": "error", "error": "エージェントは追加情報待ちではありません"}
        
        # グラフ状態のコピーを作成
        graph_state = self.state.graph_state.copy()
        
        # 追加情報の種類と内容を取得
        info_type = content.get("info_type")
        info_data = content.get("data", {})
        
        if not info_type:
            return {"status": "error", "error": "情報の種類が指定されていません"}
        
        # 収集済み情報に追加
        if "collected_info" not in graph_state:
            graph_state["collected_info"] = {}
        
        graph_state["collected_info"][info_type] = {
            "status": "collected",
            "data": info_data,
            "timestamp": datetime.now().isoformat()
        }
        
        # チェックポイントから復元するための設定
        current_checkpoint_id = self.state.graph_state.get("current_checkpoint_id")
        if current_checkpoint_id:
            graph_state["restore_checkpoint_id"] = current_checkpoint_id
            graph_state["status"] = "resumed_from_checkpoint"
        
        try:
            # グラフを再実行
            logger.info(f"追加情報を適用してグラフを再実行: {info_type}")
            result_state = await self.graph.ainvoke(graph_state)
            
            # 結果の解析と状態更新
            status = result_state.get("status", "error")
            
            # 状態を更新
            self.state.update(
                graph_state=result_state,
                current_step=result_state.get("current_step"),
                status=status
            )
            
            if status == "completed":
                # 完了状態
                test_results = self._convert_graph_results_to_test_results(result_state)
                self.state.update(
                    test_results=test_results,
                    is_processing=False
                )
                self._save_agent_state()
                
                return {
                    "status": "success",
                    "message": "追加情報が適用され、テスト実行が完了しました",
                    "test_results": test_results
                }
                
            elif status == "waiting_for_info":
                # まだ情報が足りない
                checkpoints = result_state.get("checkpoints", [])
                current_checkpoint = checkpoints[-1] if checkpoints else {}
                missing_info = current_checkpoint.get("missing_info", [])
                
                self.state.update(
                    checkpoints=checkpoints,
                    is_processing=False
                )
                self._save_agent_state()
                
                return {
                    "status": "waiting_for_info",
                    "message": "さらに追加情報が必要です",
                    "missing_info": missing_info,
                    "checkpoint_id": current_checkpoint.get("id")
                }
                
            else:
                # エラー状態
                error_message = result_state.get("error", "不明なエラー")
                
                self.state.update(is_processing=False)
                self._save_agent_state()
                
                return {
                    "status": "error",
                    "error": error_message
                }
                
        except Exception as e:
            logger.error(f"追加情報適用中にエラー: {e}")
            self.state.update(is_processing=False, status="error")
            return {"status": "error", "error": str(e)}
    
    async def handle_restore_checkpoint(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        チェックポイント復元処理
        
        Args:
            content: メッセージコンテンツ
            
        Returns:
            処理結果
        """
        checkpoint_id = content.get("checkpoint_id")
        if not checkpoint_id:
            return {"status": "error", "error": "チェックポイントIDが指定されていません"}
        
        if not self.state.graph_state:
            return {"status": "error", "error": "グラフ状態が初期化されていません"}
        
        # グラフ状態のコピーを作成
        graph_state = self.state.graph_state.copy()
        
        # 復元するチェックポイントの指定
        graph_state["restore_checkpoint_id"] = checkpoint_id
        
        try:
            # グラフを再実行
            logger.info(f"チェックポイントから復元: {checkpoint_id}")
            result_state = await self.graph.ainvoke(graph_state)
            
            # 結果の解析
            status = result_state.get("status", "error")
            
            # 状態を更新
            self.state.update(
                graph_state=result_state,
                current_step=result_state.get("current_step"),
                status=status,
                is_processing=(status == "in_progress")
            )
            self._save_agent_state()
            
            return {
                "status": "success",
                "message": f"チェックポイント {checkpoint_id} から復元しました",
                "current_step": result_state.get("current_step"),
                "graph_status": status
            }
            
        except Exception as e:
            logger.error(f"チェックポイント復元中にエラー: {e}")
            return {"status": "error", "error": str(e)}
    
    # イベント駆動型ツール選択・実行メソッド（拡張）
    async def select_and_execute_tools(self, problem_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        問題タイプに基づいて適切なツールを選択し実行
        
        Args:
            problem_type: 問題タイプ
            data: ツール実行に必要なデータ
            
        Returns:
            ツール実行結果
        """
        logger.info(f"問題タイプに基づくツール選択: {problem_type}")
        
        # 問題タイプに基づいてツールを選択
        selected_tools = []
        
        if problem_type == "data_inconsistency":
            selected_tools.append("data_comparison_tool")
        elif problem_type == "approval_verification":
            selected_tools.append("document_analyzer")
        elif problem_type == "threshold_validation":
            selected_tools.append("data_validation_tool")
        
        # 基本的なデータ分析ツールは常に含める
        if "excel_analyzer" not in selected_tools:
            selected_tools.append("excel_analyzer")
        
        # 利用可能なツールをチェック
        available_tools = self.tool_registry.list_available_tools()
        selected_tools = [tool for tool in selected_tools if tool in available_tools]
        
        if not selected_tools:
            return {
                "status": "error",
                "error": f"問題タイプ {problem_type} に適したツールが見つかりません"
            }
        
        # ツールの実行
        results = []
        
        for tool_id in selected_tools:
            try:
                # ツールパラメータの準備
                params = {
                    "data": data,
                    "problem_type": problem_type
                }
                
                # ツール実行
                request_id = f"req-{uuid.uuid4().hex[:8]}"
                tool_result = await self._execute_tool(tool_id, params, request_id)
                
                results.append({
                    "tool_id": tool_id,
                    "request_id": request_id,
                    "result": tool_result,
                    "status": "success",
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"ツール {tool_id} の実行中にエラー: {e}")
                results.append({
                    "tool_id": tool_id,
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        # 結果をまとめる
        return {
            "status": "success",
            "tools_executed": len(results),
            "results": results
        }
    
    async def evaluate_budget_change(self, budget_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        予算変更の評価を実行
        
        Args:
            budget_data: 予算変更データ
            config: 評価設定（オプション）
                - target_agent: データリクエスト先のエージェントID
                - thresholds: リスクレベルの閾値設定
                - custom_rules: カスタム評価ルール
                
        Returns:
            評価結果
        """
        try:
            # 設定のデフォルト値
            evaluation_config = {
                "target_agent": config.get("target_agent", "agent_a"),
                "thresholds": config.get("thresholds", {
                    "medium": 20,
                    "high": 50
                }),
                "custom_rules": config.get("custom_rules", [])
            }
            
            # データリクエストの送信
            request_id = str(uuid.uuid4())
            message_id = await self.message_client.send_message(
                to_agent=evaluation_config["target_agent"],
                message_type=MessageType.DATA_REQUEST,
                content={
                    "request_type": "budget_data",
                    "request_id": request_id,
                    "requesting_agent": self.agent_id,
                    **budget_data
                }
            )
            
            if not message_id:
                raise Exception("データリクエストの送信に失敗しました")
            
            # 応答を待機
            responses = await self.message_client.wait_for_response(message_id, timeout=10)
            if not responses:
                raise Exception("予算データの取得に失敗しました")
            
            response_data = responses[0].content.get("data", {})
            if not response_data:
                raise Exception("応答データが不正です")
            
            # 基本的な評価指標の計算
            evaluation_metrics = self._calculate_evaluation_metrics(response_data)
            
            # リスクレベルの判定
            risk_assessment = self._assess_risk_level(
                evaluation_metrics,
                evaluation_config["thresholds"]
            )
            
            # カスタムルールの適用
            custom_evaluation = self._apply_custom_rules(
                evaluation_metrics,
                evaluation_config["custom_rules"]
            )
            
            # 最終評価結果の生成
            evaluation_result = self._generate_evaluation_result(
                evaluation_metrics,
                risk_assessment,
                custom_evaluation
            )
            
            # 評価結果の通知
            await self._notify_evaluation_result(evaluation_result)
            
            return evaluation_result
            
        except Exception as e:
            logger.error(f"予算変更の評価中にエラーが発生: {str(e)}")
            return {
                "status": "failed",
                "error": str(e)
            }

    def _calculate_evaluation_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """基本的な評価指標を計算"""
        current = data.get("current_budget", 0)
        requested = data.get("requested_budget", 0)
        
        return {
            "change_amount": requested - current,
            "change_percentage": ((requested - current) / current * 100) if current else 0,
            "current_budget": current,
            "requested_budget": requested,
            "department": data.get("department"),
            "reason": data.get("reason"),
            "urgency": data.get("urgency")
        }

    def _assess_risk_level(
        self,
        metrics: Dict[str, Any],
        thresholds: Dict[str, float]
    ) -> Dict[str, Any]:
        """リスクレベルを評価"""
        change_percentage = metrics["change_percentage"]
        
        risk_level = "low"
        if change_percentage > thresholds["high"]:
            risk_level = "high"
        elif change_percentage > thresholds["medium"]:
            risk_level = "medium"
        
        return {
            "level": risk_level,
            "factors": self._identify_risk_factors(metrics)
        }

    def _identify_risk_factors(self, metrics: Dict[str, Any]) -> List[str]:
        """リスク要因を特定"""
        factors = []
        
        if metrics["change_percentage"] < 0:
            factors.append("予算削減")
        if metrics["change_percentage"] > 100:
            factors.append("予算倍増")
        if metrics.get("urgency") == "high":
            factors.append("緊急性が高い")
        
        return factors

    def _apply_custom_rules(
        self,
        metrics: Dict[str, Any],
        rules: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """カスタム評価ルールを適用"""
        results = []
        
        for rule in rules:
            try:
                rule_result = {
                    "rule_id": rule.get("id"),
                    "name": rule.get("name"),
                    "result": self._evaluate_rule(metrics, rule)
                }
                results.append(rule_result)
            except Exception as e:
                logger.warning(f"カスタムルール適用中にエラー: {str(e)}")
            
        return results

    def _evaluate_rule(
        self,
        metrics: Dict[str, Any],
        rule: Dict[str, Any]
    ) -> Dict[str, Any]:
        """個別のルールを評価"""
        condition = rule.get("condition", {})
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")
        
        if not all([field, operator, value]):
            return {"status": "invalid_rule"}
        
        metric_value = metrics.get(field)
        if metric_value is None:
            return {"status": "missing_data"}
        
        result = self._compare_values(metric_value, operator, value)
        return {
            "status": "passed" if result else "failed",
            "details": {
                "actual": metric_value,
                "expected": value,
                "operator": operator
            }
        }

    def _compare_values(self, actual: Any, operator: str, expected: Any) -> bool:
        """値の比較を実行"""
        operators = {
            "eq": lambda x, y: x == y,
            "ne": lambda x, y: x != y,
            "gt": lambda x, y: x > y,
            "lt": lambda x, y: x < y,
            "ge": lambda x, y: x >= y,
            "le": lambda x, y: x <= y,
            "in": lambda x, y: x in y,
            "not_in": lambda x, y: x not in y
        }
        
        compare_func = operators.get(operator)
        if not compare_func:
            raise ValueError(f"未知の比較演算子: {operator}")
        
        return compare_func(actual, expected)

    def _generate_evaluation_result(
        self,
        metrics: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        custom_evaluation: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """最終的な評価結果を生成"""
        # 承認状態の判定
        approval_status = self._determine_approval_status(
            risk_assessment,
            custom_evaluation
        )
        
        return {
            "status": "completed",
            "metrics": metrics,
            "risk_assessment": risk_assessment,
            "custom_evaluation": custom_evaluation,
            "approval": {
                "status": approval_status,
                "recommendations": self._generate_recommendations(
                    metrics,
                    risk_assessment,
                    approval_status
                )
            }
        }

    def _determine_approval_status(
        self,
        risk_assessment: Dict[str, Any],
        custom_evaluation: List[Dict[str, Any]]
    ) -> str:
        """承認状態を判定"""
        if risk_assessment["level"] == "high":
            return "needs_review"
        
        # カスタムルールの失敗をチェック
        failed_rules = [
            rule for rule in custom_evaluation
            if rule.get("result", {}).get("status") == "failed"
        ]
        
        if failed_rules:
            return "needs_review"
        
        return "approved"

    def _generate_recommendations(
        self,
        metrics: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        approval_status: str
    ) -> List[str]:
        """推奨事項を生成"""
        recommendations = [
            f"予算変更額: {metrics['change_amount']:,}円 ({metrics['change_percentage']:.1f}%)",
            f"リスクレベル: {risk_assessment['level']}"
        ]
        
        if risk_assessment["factors"]:
            recommendations.append(
                f"リスク要因: {', '.join(risk_assessment['factors'])}"
            )
        
        if approval_status == "needs_review":
            recommendations.append("詳細なコスト分析が必要です")
        else:
            recommendations.append("標準的な承認プロセスで問題ありません")
        
        return recommendations

    async def _notify_evaluation_result(self, result: Dict[str, Any]) -> None:
        """評価結果を通知"""
        try:
            await self.message_client.send_message(
                to_agent="all",
                message_type=MessageType.WORKFLOW_UPDATE,
                content={
                    "type": "budget_evaluation",
                    "result": result
                }
            )
        except Exception as e:
            logger.error(f"評価結果の通知中にエラー: {str(e)}")

    async def handle_data_request(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        データリクエストメッセージの処理
        
        Args:
            content: メッセージコンテンツ
            
        Returns:
            処理結果
        """
        try:
            request_type = content.get("request_type")
            if request_type == "budget_data":
                # 予算データのリクエストに対する応答
                budget_data = {
                    "department": content.get("department"),
                    "current_budget": content.get("current_budget"),
                    "requested_budget": content.get("requested_budget"),
                    "change_amount": content.get("requested_budget", 0) - content.get("current_budget", 0),
                    "change_percentage": ((content.get("requested_budget", 0) - content.get("current_budget", 0)) / content.get("current_budget", 1)) * 100,
                    "reason": content.get("reason"),
                    "urgency": content.get("urgency"),
                    "submitted_by": content.get("submitted_by"),
                    "submitted_at": content.get("submitted_at")
                }
                
                # データ応答メッセージを送信
                await self.message_client.send_message(
                    to_agent=content.get("requesting_agent", "agent_a"),  # デフォルトでagent_aに送信
                    message_type=MessageType.DATA_RESPONSE,
                    content={
                        "request_id": content.get("request_id"),
                        "data": budget_data,
                        "status": "success",
                        "responding_agent": "agent_b"  # 応答元エージェントの情報を追加
                    }
                )
                
                return {
                    "status": "success",
                    "message": "予算データを送信しました",
                    "data": budget_data
                }
            else:
                return {
                    "status": "error",
                    "message": f"未知のリクエストタイプ: {request_type}"
                }
        except Exception as e:
            logger.error(f"データリクエスト処理中にエラーが発生: {str(e)}")
            return {
                "status": "error",
                "message": f"データリクエスト処理エラー: {str(e)}"
            } 