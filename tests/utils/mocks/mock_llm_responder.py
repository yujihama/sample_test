"""
モックLLMレスポンダー

テスト環境でLLM呼び出しをシミュレートするためのモックレスポンダー
- 事前に定義された応答パターンに基づいてレスポンスを返す
- プロンプトのキーワードに基づいて応答を選択
- 再現性のあるテストを実現
"""

import json
import re
import random
from typing import Dict, Any, List, Optional, Tuple, Union
from loguru import logger

# デフォルトのモック応答
DEFAULT_RESPONSES = {
    # エージェントA用レスポンス
    "監査手続き分析": {
        "output": {
            "分析結果": "監査手続きを分析しました。この手続きは経費申請プロセスの検証に関するものです。",
            "主要リスク": ["承認なしの経費申請", "上限超過", "不適切なカテゴリ", "重複申請"],
            "必要データ項目": ["従業員ID", "申請日", "金額", "カテゴリ", "承認者", "承認状態", "申請理由"],
            "テスト項目": [
                {
                    "id": "test-001",
                    "名称": "承認状態検証",
                    "内容": "すべての経費申請に適切な承認があるか検証",
                    "検証条件": "承認状態が「承認済」であること",
                    "リスクレベル": "高"
                },
                {
                    "id": "test-002",
                    "名称": "金額上限検証",
                    "内容": "経費申請額が規定の上限を超えていないか検証",
                    "検証条件": "金額が20,000円以下であること",
                    "リスクレベル": "中"
                },
                {
                    "id": "test-003", 
                    "名称": "カテゴリ検証",
                    "内容": "経費申請のカテゴリが適切か検証",
                    "検証条件": "カテゴリが許可リストに含まれること",
                    "リスクレベル": "低"
                }
            ]
        }
    },
    
    # エージェントB用レスポンス
    "データ分析": {
        "output": {
            "分析サマリー": "従業員経費データの分析が完了しました。",
            "レコード数": 152,
            "データ期間": "2023-01-01から2023-12-31",
            "金額統計": {
                "最小": 500,
                "最大": 35000,
                "平均": 12500,
                "中央値": 9800
            },
            "カテゴリ分布": {
                "交通費": 45,
                "宿泊費": 25,
                "飲食費": 38,
                "備品": 28,
                "その他": 16
            },
            "異常検出": [
                {"従業員ID": "EMP005", "申請番号": "EXP-2023-042", "問題": "上限超過", "金額": 35000},
                {"従業員ID": "EMP012", "申請番号": "EXP-2023-078", "問題": "未承認処理", "金額": 18500},
                {"従業員ID": "EMP008", "申請番号": "EXP-2023-103", "問題": "重複申請の疑い", "金額": 12800}
            ]
        }
    },
    
    # エージェントC用レスポンス
    "テスト実行": {
        "output": {
            "実行結果": "テスト計画に基づくテストが完了しました。",
            "テスト実行日時": "2025-03-15T12:00:00",
            "実行テスト数": 3,
            "合格": 1,
            "不合格": 2,
            "詳細結果": [
                {
                    "テストID": "test-001",
                    "結果": "不合格",
                    "詳細": "10件の承認がないケースを検出",
                    "対象レコード": ["EXP-2023-042", "EXP-2023-078"]
                },
                {
                    "テストID": "test-002",
                    "結果": "不合格",
                    "詳細": "5件の上限超過を検出",
                    "対象レコード": ["EXP-2023-042", "EXP-2023-091"]
                },
                {
                    "テストID": "test-003",
                    "結果": "合格",
                    "詳細": "すべてのカテゴリが適切",
                    "対象レコード": []
                }
            ]
        }
    },
    
    # エージェントD用レスポンス
    "報告書作成": {
        "output": {
            "報告タイトル": "経費申請プロセス監査報告書",
            "作成日": "2025-03-15",
            "概要": "監査の結果、経費申請プロセスに複数の問題が発見されました。承認プロセスと金額上限管理に改善が必要です。",
            "主要発見事項": [
                {
                    "タイトル": "承認プロセスの不備",
                    "内容": "10件の経費申請で適切な承認手続きが行われていません。",
                    "リスク評価": "高",
                    "改善提案": "承認フローの自動リマインダーと二次承認プロセスの導入を推奨します。"
                },
                {
                    "タイトル": "上限金額超過",
                    "内容": "5件の経費申請で規定の上限金額を超過していました。",
                    "リスク評価": "中",
                    "改善提案": "経費申請システムに上限金額チェック機能を実装することを推奨します。"
                }
            ],
            "結論": "経費申請プロセスは部分的に機能していますが、重要な改善点があります。特に承認プロセスの強化が必要です。"
        }
    },
    
    # 質問応答用レスポンス
    "質問応答": {
        "output": {
            "回答": "ご質問にお答えします。経費申請プロセスの監査では、主に承認プロセスと金額上限の問題が発見されました。詳細はレポートをご確認ください。"
        }
    },
    
    # デフォルトレスポンス
    "default": {
        "output": {
            "結果": "リクエストを処理しました。",
            "詳細": "特に問題は検出されませんでした。",
            "タイムスタンプ": "2025-03-15T14:30:00"
        }
    }
}


class MockLLMResponder:
    """
    モックLLMレスポンダークラス
    プロンプトに基づいて事前定義された応答を返す
    """
    
    def __init__(self, custom_responses: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            custom_responses: カスタム応答辞書（オプション）
        """
        self.responses = DEFAULT_RESPONSES.copy()
        if custom_responses:
            self.responses.update(custom_responses)
        
        # リクエスト履歴
        self.request_history: List[Dict[str, Any]] = []
        logger.info("モックLLMレスポンダーを初期化しました")
    
    def add_response(self, key: str, response_data: Dict[str, Any]) -> None:
        """
        応答を追加または更新
        
        Args:
            key: 応答キー
            response_data: 応答データ
        """
        self.responses[key] = response_data
    
    async def generate_response(self, 
                          prompt: str, 
                          temperature: float = 0.0,
                          max_tokens: Optional[int] = None,
                          model: Optional[str] = None) -> Dict[str, Any]:
        """
        プロンプトに基づいて応答を生成
        
        Args:
            prompt: 入力プロンプト
            temperature: 温度パラメータ（未使用）
            max_tokens: 最大トークン数（未使用）
            model: モデル名（未使用）
            
        Returns:
            モック応答
        """
        # リクエストを記録
        request = {
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "model": model,
            "timestamp": "2025-03-15T15:00:00"
        }
        self.request_history.append(request)
        
        # プロンプトのキーワードに基づいて応答を選択
        response_key = self._select_response_key(prompt)
        response = self.responses.get(response_key, self.responses["default"])
        
        # 特定のバリエーションを加える（テスト目的）
        response_copy = self._add_variation_to_response(response.copy(), prompt)
        
        logger.debug(f"モックLLMレスポンダー: '{response_key}' に基づく応答を生成")
        
        # 遅延をシミュレート（オプション）
        # await asyncio.sleep(random.uniform(0.5, 2.0))
        
        return response_copy
    
    def _select_response_key(self, prompt: str) -> str:
        """
        プロンプトに基づいて適切な応答キーを選択
        
        Args:
            prompt: 入力プロンプト
            
        Returns:
            応答キー
        """
        # キーワードマッピング
        keyword_mapping = {
            "監査手続き分析": ["監査手続", "監査プロセス", "手続き分析", "リスク評価"],
            "データ分析": ["データ分析", "サンプルデータ", "データセット", "検証データ"],
            "テスト実行": ["テスト実行", "テスト計画", "検証実施", "監査テスト"],
            "報告書作成": ["報告書", "監査報告", "レポート作成", "調査結果"],
            "質問応答": ["質問", "回答", "教えて", "疑問", "どうして"]
        }
        
        for key, keywords in keyword_mapping.items():
            for keyword in keywords:
                if keyword.lower() in prompt.lower():
                    return key
        
        return "default"
    
    def _add_variation_to_response(self, response: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        """
        応答にわずかなバリエーションを加える
        
        Args:
            response: 元の応答
            prompt: 入力プロンプト
            
        Returns:
            バリエーションを加えた応答
        """
        # 出力がある場合のみ処理
        if "output" not in response:
            return response
            
        # プロンプトの一部を応答に反映（例：プロンプトから特定の単語を抽出）
        if "概要" in response["output"] and len(prompt) > 20:
            # プロンプトの一部を概要に組み込む
            words = re.findall(r'\b\w{5,}\b', prompt)
            if words:
                random_word = random.choice(words)
                if isinstance(response["output"]["概要"], str):
                    response["output"]["概要"] = response["output"]["概要"].replace(
                        "監査の結果", f"「{random_word}」に関する監査の結果"
                    )
        
        return response
    
    def get_request_history(self) -> List[Dict[str, Any]]:
        """
        リクエスト履歴を取得
        
        Returns:
            リクエスト履歴リスト
        """
        return self.request_history
    
    def clear_history(self) -> None:
        """リクエスト履歴をクリア"""
        self.request_history = []


# シングルトンインスタンス
mock_llm_responder = MockLLMResponder() 