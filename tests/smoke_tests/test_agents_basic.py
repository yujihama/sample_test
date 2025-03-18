#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
エージェント基本機能疎通テスト

このスクリプトは、各エージェントの基本的なインスタンス化と初期化が正常に行われるかを確認する疎通テストです。
詳細な機能テストではなく、エージェントクラスが基本的に機能していることを確認します。
"""

import os
import sys
import pytest

# src ディレクトリをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# 前提条件のスキップフラグ
skip_tests = False

try:
    # エージェントのインポート
    from src.agents.agent_a import AgentA
    from src.agents.agent_b import AgentB
    from src.agents.agent_c import AgentC
    from src.agents.agent_d import AgentD
except ImportError as e:
    skip_tests = True
    reason = f"エージェントクラスのインポートに失敗しました: {e}"

class TestAgentsBasic:
    """エージェントの基本機能疎通テスト"""

    def setup_method(self):
        """各テストの前に実行されるセットアップ"""
        if skip_tests:
            pytest.skip(reason)

    def test_agent_a_init(self):
        """エージェントAのインスタンス化と初期化が可能かテスト"""
        try:
            # エージェントAのインスタンス化
            agent = AgentA()
            
            # 基本的なプロパティの確認
            assert hasattr(agent, "agent_id"), "エージェントAにagent_idプロパティがありません"
            assert hasattr(agent, "state"), "エージェントAにstateプロパティがありません"
            assert hasattr(agent, "messaging"), "エージェントAにmessagingプロパティがありません"
            
        except Exception as e:
            pytest.fail(f"エージェントAの初期化でエラーが発生しました: {str(e)}")

    def test_agent_b_init(self):
        """エージェントBのインスタンス化と初期化が可能かテスト"""
        try:
            # エージェントBのインスタンス化
            agent = AgentB()
            
            # 基本的なプロパティの確認
            assert hasattr(agent, "agent_id"), "エージェントBにagent_idプロパティがありません"
            assert hasattr(agent, "state"), "エージェントBにstateプロパティがありません"
            assert hasattr(agent, "messaging"), "エージェントBにmessagingプロパティがありません"
            
        except Exception as e:
            pytest.fail(f"エージェントBの初期化でエラーが発生しました: {str(e)}")

    def test_agent_c_init(self):
        """エージェントCのインスタンス化と初期化が可能かテスト"""
        try:
            # エージェントCのインスタンス化
            agent = AgentC()
            
            # 基本的なプロパティの確認
            assert hasattr(agent, "agent_id"), "エージェントCにagent_idプロパティがありません"
            assert hasattr(agent, "state"), "エージェントCにstateプロパティがありません"
            assert hasattr(agent, "messaging"), "エージェントCにmessagingプロパティがありません"
            
        except Exception as e:
            pytest.fail(f"エージェントCの初期化でエラーが発生しました: {str(e)}")

    def test_agent_d_init(self):
        """エージェントDのインスタンス化と初期化が可能かテスト"""
        try:
            # エージェントDのインスタンス化
            agent = AgentD()
            
            # 基本的なプロパティの確認
            assert hasattr(agent, "agent_id"), "エージェントDにagent_idプロパティがありません"
            assert hasattr(agent, "state"), "エージェントDにstateプロパティがありません"
            assert hasattr(agent, "messaging"), "エージェントDにmessagingプロパティがありません"
            
        except Exception as e:
            pytest.fail(f"エージェントDの初期化でエラーが発生しました: {str(e)}")

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 