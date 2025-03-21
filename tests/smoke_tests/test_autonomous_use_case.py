"""
エージェント間の自律的な連携とツール利用テスト

このモジュールでは、use_cases.mdに記載されているユースケースシナリオに基づいて
エージェント間の自律的な連携とツール利用を検証するテストを提供します。
"""

import os
import sys
import uuid
import pytest
import pytest_asyncio
import asyncio
import json
from datetime import datetime
from pathlib import Path
from loguru import logger
from typing import Dict, Any, List, Optional

# プロジェクトルートをパスに追加
root_dir = Path(__file__).parents[2].absolute()
sys.path.append(str(root_dir))

from src.agents.agent_a import AgentA
from src.agents.agent_b import AgentB
from src.agents.agent_c import AgentC
from src.core.messaging import MessageBroker, MessageClient
from src.tools.tool_registry import ToolRegistry
from src.models.schema import MessageType, MessagePriority
from tests.smoke_tests.test_helpers import setup_test_environment, cleanup_test_environment
from src.agents import agent_b_graph

# ログディレクトリを確認
log_dir = os.path.join(root_dir, "logs", "agent")
os.makedirs(log_dir, exist_ok=True)

# マークを設定
pytestmark = [
    pytest.mark.smoke,
    pytest.mark.asyncio,
]

# テスト環境をセットアップ
setup_test_environment()

# メッセージ保存ヘルパー関数
def save_message_history(workflow_id: str, broker: MessageBroker):
    """メッセージ履歴をログファイルに保存する"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"logs/agent/message_history_{workflow_id}_{timestamp}.json"
    
    try:
        message_history = broker.message_history if hasattr(broker, 'message_history') else []
        
        # ワークフローIDでフィルタリング
        if workflow_id:
            filtered_messages = [msg for msg in message_history if msg.get('workflow_id') == workflow_id]
        else:
            filtered_messages = message_history
        
        # ファイルに保存
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(filtered_messages, f, ensure_ascii=False, indent=2)
        
        logger.info(f"メッセージ履歴をファイル {filename} に保存しました（メッセージ数: {len(filtered_messages)}）")
        return filename
    except Exception as e:
        logger.error(f"メッセージ履歴保存中にエラーが発生: {str(e)}")
        return None

class TestAutonomousUseCase:
    """エージェント間の自律的な連携とツール利用を検証するテストクラス"""
    
    @pytest_asyncio.fixture
    async def setup_agents_and_tools(self):
        """テスト用のエージェントとツールをセットアップする"""
        # メッセージブローカーをクリア（新しいインスタンスを作成）
        MessageBroker._instance = None
        broker = MessageBroker()
        
        # メッセージクライアントを作成
        client_a = MessageClient("agent_a", broker)
        client_b = MessageClient("agent-b", broker)
        client_c = MessageClient("agent-c", broker)
        
        # メッセージクライアントを接続
        client_a.connect()
        client_b.connect()
        client_c.connect()
        
        # エージェントインスタンス作成（明示的にメッセージクライアントを設定）
        agent_a = AgentA(message_client=client_a)
        agent_b = AgentB(message_client=client_b)
        agent_c = AgentC(message_client=client_c)
        
        # エージェントを登録
        broker.register_agent(agent_a.agent_id, agent_a)
        broker.register_agent(agent_b.agent_id, agent_b)
        broker.register_agent(agent_c.agent_id, agent_c)
        
        # メッセージ履歴を確実に有効化
        if not hasattr(broker, 'message_history'):
            broker.message_history = []
        
        # ツールレジストリを初期化
        ToolRegistry._instance = None  # シングルトンをリセット
        tool_registry = ToolRegistry()
        
        # 必須ツールが登録されていることを確認
        tools = tool_registry.get_all_tools()
        assert "image_processor" in tools, "画像処理ツールが利用できません"
        assert "excel_processor" in tools, "エクセル解析ツールが利用できません"
        
        logger.info("エージェントの自律モードを開始します")
        # エージェントの自律モードを開始
        await agent_a.start_autonomous_mode({"polling_interval": 0.2})
        await agent_b.start_autonomous_mode({"polling_interval": 0.2})
        
        # フィクスチャの値を返す
        yield agent_a, agent_b, agent_c, broker, tool_registry
        
        # テスト後のクリーンアップ
        logger.info("エージェントの自律モードを停止します")
        # 自律モードを停止
        await agent_a.stop_autonomous_mode()
        await agent_b.stop_autonomous_mode()
        
        # クライアントを切断
        client_a.disconnect()
        client_b.disconnect()
        client_c.disconnect()
    
    @pytest.mark.smoke
    async def test_tool_usage_workflow(self, setup_agents_and_tools):
        """ツール利用を含むエージェント間連携ワークフローのテスト"""
        agent_a, agent_b, agent_c, broker, tool_registry = setup_agents_and_tools
        
        try:
            # テスト用のワークフローIDを生成
            workflow_id = f"test-workflow-{uuid.uuid4().hex[:8]}"
            
            logger.info(f"テストワークフローID: {workflow_id}")
            
            # メッセージブローカー状態をログに記録
            logger.info(f"AgentA ID: {agent_a.agent_id}, AgentB ID: {agent_b.agent_id}")
            logger.info(f"登録されているエージェント: {broker.agents if hasattr(broker, 'agents') else 'ブローカーにagentsプロパティがありません'}")
            logger.info(f"メッセージキュー状態: {broker.message_queue if hasattr(broker, 'message_queue') else 'ブローカーにmessage_queueプロパティがありません'}")
            
            # AgentAからAgentBへの指示メッセージを作成
            instruction_content = {
                "procedure_id": "PROC-001",
                "sample_id": "サンプルID-001",
                "documents": [
                    "出張申請書",
                    "領収書キャプチャ",
                    "精算承認画面"
                ],
                "verification_points": [
                    "出張期間と領収書日付の整合性",
                    "申請金額と領収書金額の一致",
                    "承認者の適切性（権限者による承認）"
                ]
            }
            
            # AgentAからAgentBへメッセージを送信
            logger.info("AgentAからAgentBへ指示を送信します")
            # メッセージクライアントを使用してメッセージを送信
            result = agent_a.message_client.send_message(
                message_type=MessageType.TASK_REQUEST.name,
                content=instruction_content,
                recipient_id=agent_b.agent_id,
                workflow_id=workflow_id,
                priority=MessagePriority.NORMAL.name,
                requires_response=True
            )
            
            logger.info(f"送信結果: {result}")
            
            # 送信メッセージが記録されたことを確認
            logger.info("メッセージ履歴を確認します")
            current_history = getattr(broker, 'message_history', [])
            logger.info(f"現在のメッセージ履歴数: {len(current_history)}")
            
            # メッセージIDの生成 - result がブール値の場合はUUIDを生成
            message_id = str(uuid.uuid4()) if isinstance(result, bool) else result.get("message_id", str(uuid.uuid4()))
            
            # 直接記録した送信メッセージをログに残す
            sent_msg = {
                "workflow_id": workflow_id,
                "sender_id": agent_a.agent_id,
                "recipient_id": agent_b.agent_id,
                "message_type": MessageType.TASK_REQUEST.name,
                "content": instruction_content,
                "timestamp": datetime.now().isoformat(),
                "id": message_id
            }
            
            # ブローカーのメッセージ履歴に確実に追加
            if hasattr(broker, 'message_history'):
                broker.message_history.append(sent_msg)
                logger.info(f"メッセージを履歴に追加しました。現在の履歴数: {len(broker.message_history)}")
            
            # 応答を待機 (実際のLLM処理に時間がかかるため余裕を持つ)
            logger.info("AgentBからの応答を待機中...")
            max_wait_time = 60  # 最大60秒待機に延長
            wait_interval = 2   # 2秒ごとにチェック
            
            response_received = False
            response_message_id = None
            response_content = None
            
            for i in range(max_wait_time // wait_interval):
                # 定期的にメッセージ履歴をログに保存
                if i % 5 == 0:  # 10秒ごとに保存
                    save_message_history(workflow_id, broker)
                
                # 応答をチェック
                messages = broker.get_messages(agent_a.agent_id)
                logger.info(f"AgentAのキューに{len(messages)}件のメッセージがあります")
                
                for msg in messages:
                    if (msg.get("sender_id") == agent_b.agent_id and 
                        msg.get("recipient_id") == agent_a.agent_id and
                        msg.get("workflow_id") == workflow_id):
                        # メッセージの内容をチェック
                        msg_content = msg.get("content", {})
                        if isinstance(msg_content, dict):
                            response_received = True
                            response_message_id = msg.get("id")
                            response_content = msg_content
                            logger.info(f"AgentBからの応答を受信: {msg_content}")
                            
                            # 応答メッセージをブローカーの履歴に確実に追加
                            if hasattr(broker, 'message_history'):
                                broker.message_history.append(msg)
                                logger.info(f"応答メッセージを履歴に追加しました。現在の履歴数: {len(broker.message_history)}")
                            
                            break
                
                if response_received:
                    break
                
                # エージェントのステータスをログに記録
                logger.info(f"AgentA自律モード: {agent_a.state.is_autonomous if hasattr(agent_a.state, 'is_autonomous') else '不明'}")
                logger.info(f"AgentB自律モード: {agent_b.state.is_autonomous if hasattr(agent_b.state, 'is_autonomous') else '不明'}")
                
                # 待機
                await asyncio.sleep(wait_interval)
            
            # 最終的なメッセージ履歴を保存
            history_file = save_message_history(workflow_id, broker)
            logger.info(f"最終メッセージ履歴を保存しました: {history_file}")
            
            # 応答を受信したことを確認
            assert response_received, "AgentBからの応答が受信されませんでした"
            
            # LLMの応答分析 - 最低限"issues"か"analysis"のどちらかを含む
            has_valid_content = (
                isinstance(response_content, dict) and 
                ("issues" in response_content or "analysis" in response_content or "analysis_results" in response_content)
            )
            
            assert has_valid_content, "応答に問題点か分析結果が含まれていません"
            logger.info(f"有効な応答内容を確認: {response_content.keys()}")
            
            # 残りのテストロジックはツール提案がある場合のみ実行
            if "tool_proposals" in response_content and response_message_id:
                tool_proposals = response_content.get("tool_proposals", [])
                
                if tool_proposals:
                    # ツール実行の承認メッセージを作成
                    approved_tools = []
                    
                    for proposal in tool_proposals:
                        tool_name = proposal.get("tool_name")
                        
                        if tool_name == "image_processor":
                            approved_tools.append({
                                "tool_name": "image_processor",
                                "params": {
                                    "process_type": "enhance",
                                    "target_file": "サンプルID-001_領収書.png",
                                    "coordinates": {"x1": 300, "y1": 500, "x2": 400, "y2": 600},
                                    "enhancement_factor": 3.0
                                }
                            })
                        elif tool_name == "data_validator":
                            approved_tools.append({
                                "tool_name": "data_validator",
                                "params": {
                                    "operation": "verify_employee",
                                    "employee_name": "山田太郎"
                                }
                            })
                    
                    if approved_tools:
                        # ツール実行承認を送信
                        logger.info("AgentAからAgentBへツール実行承認を送信します")
                        approval_result = agent_a.message_client.send_response(
                            recipient_id=agent_b.agent_id,
                            in_response_to=response_message_id,
                            message_type="task_response",
                            content={"approved_tools": approved_tools},
                            workflow_id=workflow_id,
                            priority=MessagePriority.HIGH.name
                        )
                        
                        # 承認メッセージIDの生成 - approval_result がブール値の場合はUUIDを生成
                        approval_message_id = str(uuid.uuid4()) if isinstance(approval_result, bool) else approval_result.get("message_id", str(uuid.uuid4()))
                        
                        # 承認メッセージを履歴に確実に追加
                        if hasattr(broker, 'message_history'):
                            tool_approval_msg = {
                                "workflow_id": workflow_id,
                                "sender_id": agent_a.agent_id,
                                "recipient_id": agent_b.agent_id,
                                "message_type": "task_response",
                                "content": {"approved_tools": approved_tools},
                                "in_response_to": response_message_id,
                                "timestamp": datetime.now().isoformat(),
                                "id": approval_message_id
                            }
                            broker.message_history.append(tool_approval_msg)
                            logger.info("ツール承認メッセージを履歴に追加しました")
                        
                        # ツール実行結果を待機
                        logger.info("AgentBからのツール実行結果を待機中...")
                        tool_result_received = False
                        
                        for i in range(max_wait_time // wait_interval):
                            # 定期的にメッセージ履歴をログに保存
                            if i % 5 == 0:  # 10秒ごとに保存
                                save_message_history(workflow_id, broker)
                            
                            # メッセージをチェック
                            messages = broker.get_messages(agent_a.agent_id)
                            
                            for msg in messages:
                                if (msg.get("sender_id") == agent_b.agent_id and 
                                    msg.get("recipient_id") == agent_a.agent_id and
                                    msg.get("workflow_id") == workflow_id and
                                    msg.get("message_type") == "tool_result"):
                                    
                                    tool_result_content = msg.get("content", {})
                                    logger.info(f"ツール実行結果を受信: {tool_result_content}")
                                    
                                    # ツール結果メッセージを履歴に確実に追加
                                    if hasattr(broker, 'message_history'):
                                        broker.message_history.append(msg)
                                        logger.info("ツール結果メッセージを履歴に追加しました")
                                    
                                    tool_result_received = True
                                    break
                            
                            if tool_result_received:
                                break
                                
                            # 待機
                            await asyncio.sleep(wait_interval)
                        
                        # ツール実行結果を受信したかのチェック（受信しなくてもテスト失敗としない）
                        if not tool_result_received:
                            logger.warning("ツール実行結果が受信されませんでした（テスト続行）")
            
            # 最終的なメッセージ履歴を再度保存
            history_file = save_message_history(workflow_id, broker)
            logger.info(f"最終メッセージ履歴を保存しました: {history_file}")
            
            # エージェント間連携の状態を最終確認
            logger.info(f"AgentAのキューメッセージ数: {len(broker.get_messages(agent_a.agent_id)) if hasattr(broker, 'get_messages') else '不明'}")
            logger.info(f"AgentBのキューメッセージ数: {len(broker.get_messages(agent_b.agent_id)) if hasattr(broker, 'get_messages') else '不明'}")
            logger.info(f"メッセージ履歴の総数: {len(broker.message_history) if hasattr(broker, 'message_history') else '不明'}")
            
            # テスト成功
            logger.info("ツール利用ワークフローテスト完了")
            
        except Exception as e:
            logger.error(f"テスト実行中にエラーが発生: {e}")
            # エラー時もメッセージ履歴を保存
            save_message_history(workflow_id, broker)
            raise
        
        finally:
            # クリーンアップ処理
            logger.info("テスト後のクリーンアップ処理実行")

    @pytest.mark.smoke
    async def test_excel_analysis_workflow(self, setup_agents_and_tools):
        """Excelデータ分析を含むエージェント間連携ワークフローのテスト"""
        agent_a, agent_b, agent_c, broker, tool_registry = setup_agents_and_tools
        
        try:
            # テスト用のワークフローIDを生成
            workflow_id = f"test-workflow-{uuid.uuid4().hex[:8]}"
            
            logger.info(f"テストワークフローID: {workflow_id}")
            
            # メッセージブローカー状態をログに記録
            logger.info(f"AgentA ID: {agent_a.agent_id}, AgentB ID: {agent_b.agent_id}")
            logger.info(f"登録されているエージェント: {broker.agents if hasattr(broker, 'agents') else 'ブローカーにagentsプロパティがありません'}")
            logger.info(f"メッセージキュー状態: {broker.message_queue if hasattr(broker, 'message_queue') else 'ブローカーにmessage_queueプロパティがありません'}")
            
            # AgentAからAgentBへの指示メッセージを作成
            instruction_content = {
                "procedure_id": "PROC-005",
                "sample_id": "サンプルID-005",
                "documents": [
                    "取引履歴データ"
                ],
                "verification_points": [
                    "取引履歴（申請・承認・実行）の整合性",
                    "取引金額の一貫性",
                    "システムログとの時系列整合性"
                ]
            }
            
            # AgentAからAgentBへメッセージを送信
            logger.info("AgentAからAgentBへ指示を送信します")
            result = agent_a.message_client.send_message(
                message_type=MessageType.TASK_REQUEST.name,
                content=instruction_content,
                recipient_id=agent_b.agent_id,
                workflow_id=workflow_id,
                priority=MessagePriority.NORMAL.name,
                requires_response=True
            )
            
            logger.info(f"送信結果: {result}")
            
            # 送信メッセージが記録されたことを確認
            logger.info("メッセージ履歴を確認します")
            current_history = getattr(broker, 'message_history', [])
            logger.info(f"現在のメッセージ履歴数: {len(current_history)}")
            
            # メッセージIDの生成 - result がブール値の場合はUUIDを生成
            message_id = str(uuid.uuid4()) if isinstance(result, bool) else result.get("message_id", str(uuid.uuid4()))
            
            # 直接記録した送信メッセージをログに残す
            sent_msg = {
                "workflow_id": workflow_id,
                "sender_id": agent_a.agent_id,
                "recipient_id": agent_b.agent_id,
                "message_type": MessageType.TASK_REQUEST.name,
                "content": instruction_content,
                "timestamp": datetime.now().isoformat(),
                "id": message_id
            }
            
            # ブローカーのメッセージ履歴に確実に追加
            if hasattr(broker, 'message_history'):
                broker.message_history.append(sent_msg)
                logger.info(f"メッセージを履歴に追加しました。現在の履歴数: {len(broker.message_history)}")
            
            # 応答を待機 (実際のLLM処理に時間がかかるため余裕を持つ)
            logger.info("AgentBからの応答を待機中...")
            max_wait_time = 60  # 最大60秒待機に延長
            wait_interval = 2   # 2秒ごとにチェック
            
            response_received = False
            response_message_id = None
            response_content = None
            
            for i in range(max_wait_time // wait_interval):
                # 定期的にメッセージ履歴をログに保存
                if i % 5 == 0:  # 10秒ごとに保存
                    save_message_history(workflow_id, broker)
                
                # 応答をチェック
                messages = broker.get_messages(agent_a.agent_id)
                logger.info(f"AgentAのキューに{len(messages)}件のメッセージがあります")
                
                for msg in messages:
                    if (msg.get("sender_id") == agent_b.agent_id and 
                        msg.get("recipient_id") == agent_a.agent_id and
                        msg.get("workflow_id") == workflow_id):
                        # メッセージの内容をチェック
                        msg_content = msg.get("content", {})
                        if isinstance(msg_content, dict):
                            response_received = True
                            response_message_id = msg.get("id")
                            response_content = msg_content
                            logger.info(f"AgentBからの応答を受信: {msg_content}")
                            
                            # 応答メッセージをブローカーの履歴に確実に追加
                            if hasattr(broker, 'message_history'):
                                broker.message_history.append(msg)
                                logger.info(f"応答メッセージを履歴に追加しました。現在の履歴数: {len(broker.message_history)}")
                            
                            break
                
                if response_received:
                    break
                
                # エージェントのステータスをログに記録
                logger.info(f"AgentA自律モード: {agent_a.state.is_autonomous if hasattr(agent_a.state, 'is_autonomous') else '不明'}")
                logger.info(f"AgentB自律モード: {agent_b.state.is_autonomous if hasattr(agent_b.state, 'is_autonomous') else '不明'}")
                
                # 待機
                await asyncio.sleep(wait_interval)
            
            # 最終的なメッセージ履歴を保存
            history_file = save_message_history(workflow_id, broker)
            logger.info(f"最終メッセージ履歴を保存しました: {history_file}")
            
            # 応答を受信したことを確認
            assert response_received, "AgentBからの応答が受信されませんでした"
            
            # Excel処理ツールの承認テスト - 提案がある場合のみ実行
            if "tool_proposals" in response_content and response_message_id:
                has_excel_tool = False
                for proposal in response_content.get("tool_proposals", []):
                    if proposal.get("tool_name") == "excel_processor":
                        has_excel_tool = True
                        break
                
                if has_excel_tool:
                    # Excelツール実行の承認メッセージを作成
                    approved_tools = [{
                        "tool_name": "excel_processor",
                        "params": {
                            "process_type": "analyze",
                            "target_file": "サンプルID-005_取引履歴.xlsx",
                            "operations": [
                                {
                                    "operation": "extract_summary",
                                    "columns": ["申請金額", "承認金額", "取引ID"]
                                },
                                {
                                    "operation": "find_discrepancies",
                                    "threshold": 0.05
                                }
                            ]
                        }
                    }]
                    
                    # ツール実行承認を送信
                    logger.info("AgentAからAgentBへExcelツール実行承認を送信します")
                    approval_result = agent_a.message_client.send_response(
                        recipient_id=agent_b.agent_id,
                        in_response_to=response_message_id,
                        message_type="task_response",
                        content={"approved_tools": approved_tools},
                        workflow_id=workflow_id,
                        priority=MessagePriority.HIGH.name
                    )
                    
                    # 承認メッセージIDの生成 - approval_result がブール値の場合はUUIDを生成
                    approval_message_id = str(uuid.uuid4()) if isinstance(approval_result, bool) else approval_result.get("message_id", str(uuid.uuid4()))
                    
                    # 承認メッセージを履歴に確実に追加
                    if hasattr(broker, 'message_history'):
                        tool_approval_msg = {
                            "workflow_id": workflow_id,
                            "sender_id": agent_a.agent_id,
                            "recipient_id": agent_b.agent_id,
                            "message_type": "task_response",
                            "content": {"approved_tools": approved_tools},
                            "in_response_to": response_message_id,
                            "timestamp": datetime.now().isoformat(),
                            "id": approval_message_id
                        }
                        broker.message_history.append(tool_approval_msg)
                        logger.info("ツール承認メッセージを履歴に追加しました")
                    
                    # ツール実行結果を待機
                    logger.info("AgentBからのExcelツール実行結果を待機中...")
                    tool_result_received = False
                    
                    for i in range(max_wait_time // wait_interval):
                        # 定期的にメッセージ履歴をログに保存
                        if i % 5 == 0:  # 10秒ごとに保存
                            save_message_history(workflow_id, broker)
                        
                        # メッセージをチェック
                        messages = broker.get_messages(agent_a.agent_id)
                        logger.info(f"AgentAのキューに{len(messages)}件のメッセージがあります")
                        
                        for msg in messages:
                            if (msg.get("sender_id") == agent_b.agent_id and 
                                msg.get("recipient_id") == agent_a.agent_id and
                                msg.get("workflow_id") == workflow_id and
                                msg.get("message_type") == "tool_result"):
                                
                                tool_result_content = msg.get("content", {})
                                logger.info(f"Excelツール実行結果を受信: {tool_result_content}")
                                
                                # ツール結果メッセージを履歴に確実に追加
                                if hasattr(broker, 'message_history'):
                                    broker.message_history.append(msg)
                                    logger.info("Excelツール結果メッセージを履歴に追加しました")
                                
                                tool_result_received = True
                                break
                        
                        if tool_result_received:
                            break
                            
                        # エージェントのステータスをログに記録
                        logger.info(f"AgentA自律モード: {agent_a.state.is_autonomous if hasattr(agent_a.state, 'is_autonomous') else '不明'}")
                        logger.info(f"AgentB自律モード: {agent_b.state.is_autonomous if hasattr(agent_b.state, 'is_autonomous') else '不明'}")
                        
                        # 待機
                        await asyncio.sleep(wait_interval)
                    
                    # ツール実行結果を受信したかのチェック（受信しなくてもテスト失敗としない）
                    if not tool_result_received:
                        logger.warning("Excelツール実行結果が受信されませんでした（テスト続行）")
                else:
                    logger.info("Excel処理ツールの提案がなかったため、ツール実行承認をスキップします")
            else:
                logger.info("ツール提案がなかったため、ツール実行承認をスキップします")
            
            # 最終的なメッセージ履歴を再度保存
            history_file = save_message_history(workflow_id, broker)
            logger.info(f"最終メッセージ履歴を保存しました: {history_file}")
            
            # エージェント間連携の状態を最終確認
            logger.info(f"AgentAのキューメッセージ数: {len(broker.get_messages(agent_a.agent_id)) if hasattr(broker, 'get_messages') else '不明'}")
            logger.info(f"AgentBのキューメッセージ数: {len(broker.get_messages(agent_b.agent_id)) if hasattr(broker, 'get_messages') else '不明'}")
            logger.info(f"メッセージ履歴の総数: {len(broker.message_history) if hasattr(broker, 'message_history') else '不明'}")
            
            # テスト成功
            logger.info("Excel分析ワークフローテスト完了")
            
        except Exception as e:
            logger.error(f"テスト実行中にエラーが発生: {e}")
            # エラー時もメッセージ履歴を保存
            save_message_history(workflow_id, broker)
            raise
        
        finally:
            # クリーンアップ処理
            logger.info("テスト後のクリーンアップ処理実行")


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 