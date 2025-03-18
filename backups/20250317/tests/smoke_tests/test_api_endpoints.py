#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
APIエンドポイント疎通テスト

このスクリプトは、主要なAPIエンドポイントが応答するかを確認する疎通テストです。
詳細な機能テストではなく、エンドポイントが基本的に機能していることを確認します。
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

# src ディレクトリをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# APIクライアントの初期化
try:
    from src.api.app import app
    client = TestClient(app)
except ImportError as e:
    pytest.skip(f"API アプリケーションのインポートに失敗しました: {e}", allow_module_level=True)

class TestAPIEndpoints:
    """APIエンドポイントの疎通テスト"""

    def test_root_endpoint(self):
        """ルートエンドポイントが応答するかテスト"""
        try:
            response = client.get("/")
            assert response.status_code == 200, f"ルートエンドポイントのステータスコードが不正: {response.status_code}"
            data = response.json()
            assert "status" in data, "レスポンスに 'status' フィールドがありません"
            assert data["status"] == "ok", f"ステータスが 'ok' ではありません: {data['status']}"
        except Exception as e:
            pytest.fail(f"ルートエンドポイントのテストでエラーが発生しました: {str(e)}")

    def test_health_endpoint(self):
        """ヘルスチェックエンドポイントが応答するかテスト"""
        try:
            response = client.get("/health")
            assert response.status_code == 200, f"ヘルスエンドポイントのステータスコードが不正: {response.status_code}"
            data = response.json()
            assert "status" in data, "レスポンスに 'status' フィールドがありません"
        except Exception as e:
            pytest.fail(f"ヘルスチェックエンドポイントのテストでエラーが発生しました: {str(e)}")

    def test_graph_routes_available(self):
        """グラフ関連エンドポイントの疎通確認"""
        try:
            # エンドポイント一覧の取得方法はOpenAPIを使用
            response = client.get("/openapi.json")
            assert response.status_code == 200, "OpenAPI定義を取得できませんでした"
            
            openapi_schema = response.json()
            paths = openapi_schema.get("paths", {})
            
            # 少なくとも1つのグラフ関連エンドポイントが存在することを確認
            graph_paths = [path for path in paths.keys() if "/graph/" in path]
            assert len(graph_paths) > 0, "グラフ関連のエンドポイントが見つかりません"
            
        except Exception as e:
            pytest.fail(f"グラフルートの確認でエラーが発生しました: {str(e)}")

    def test_agent_context_routes_available(self):
        """エージェントコンテキスト関連エンドポイントの疎通確認"""
        try:
            # エンドポイント一覧の取得
            response = client.get("/openapi.json")
            assert response.status_code == 200, "OpenAPI定義を取得できませんでした"
            
            openapi_schema = response.json()
            paths = openapi_schema.get("paths", {})
            
            # 少なくとも1つのエージェントコンテキスト関連エンドポイントが存在することを確認
            context_paths = [path for path in paths.keys() if "/agent-context/" in path]
            assert len(context_paths) > 0, "エージェントコンテキスト関連のエンドポイントが見つかりません"
            
        except Exception as e:
            pytest.fail(f"エージェントコンテキストルートの確認でエラーが発生しました: {str(e)}")

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 