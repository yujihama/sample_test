#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
テスト結果レポート生成ツール

テスト実行結果から包括的なレポートを生成します。
以下の情報を含みます：
- 実行されたテストの概要
- 成功したテスト数 / 失敗したテスト数
- 各テストのステータスとエラー情報
- グラフによる視覚化
- パフォーマンス指標
"""

import os
import sys
import json
import datetime
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from jinja2 import Environment, FileSystemLoader

# プロジェクトルートをパスに追加
project_root = Path(__file__).parents[2].absolute()
sys.path.append(str(project_root))

from loguru import logger


class TestResultProcessor:
    """テスト結果の処理と分析を行うクラス"""
    
    def __init__(self, results_file: Union[str, Path]):
        """
        初期化
        
        Args:
            results_file: テスト結果が保存されたJSONファイルのパス
        """
        self.results_file = Path(results_file)
        self.results = self._load_results()
        
    def _load_results(self) -> Dict[str, Any]:
        """
        テスト結果ファイルを読み込む
        
        Returns:
            テスト結果の辞書
        """
        try:
            with open(self.results_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"テスト結果ファイルの読み込みに失敗しました: {e}")
            return {}
    
    def get_test_summary(self) -> Dict[str, Any]:
        """
        テスト結果の概要を取得
        
        Returns:
            テスト概要の辞書
        """
        if not self.results:
            return {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "error_tests": 0,
                "success_rate": 0.0
            }
        
        test_results = self.results.get("tests", [])
        total_tests = len(test_results)
        passed_tests = sum(1 for test in test_results if test.get("status") == "passed")
        failed_tests = sum(1 for test in test_results if test.get("status") == "failed")
        error_tests = sum(1 for test in test_results if test.get("status") == "error")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0.0
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "error_tests": error_tests,
            "success_rate": round(success_rate, 2)
        }
    
    def get_agent_performance(self) -> Dict[str, Any]:
        """
        各エージェントのパフォーマンス情報を取得
        
        Returns:
            エージェントパフォーマンスの辞書
        """
        if not self.results:
            return {}
        
        agent_results = self.results.get("agent_results", {})
        performance = {}
        
        for agent_id, results in agent_results.items():
            if "execution_time" in results:
                performance[agent_id] = {
                    "execution_time": results["execution_time"],
                    "status": results.get("status", "unknown"),
                    "error": results.get("error", None)
                }
        
        return performance
    
    def generate_performance_chart(self, output_dir: Union[str, Path]) -> Optional[str]:
        """
        パフォーマンスチャートを生成
        
        Args:
            output_dir: チャート画像の出力ディレクトリ
            
        Returns:
            生成されたチャートファイルのパス
        """
        if not self.results:
            return None
        
        performance = self.get_agent_performance()
        if not performance:
            return None
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # エージェントとその実行時間のデータを準備
            agents = []
            times = []
            for agent_id, data in performance.items():
                agents.append(agent_id)
                times.append(data["execution_time"])
            
            # グラフの作成
            plt.figure(figsize=(10, 6))
            bars = plt.bar(agents, times, color='skyblue')
            
            # バーの上に値を表示
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.2f}s',
                        ha='center', va='bottom')
                
            plt.xlabel('エージェント')
            plt.ylabel('実行時間 (秒)')
            plt.title('エージェント別実行時間')
            plt.grid(axis='y', linestyle='--', alpha=0.7)
            
            # ファイル保存
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            chart_path = output_dir / f"agent_performance_{timestamp}.png"
            plt.savefig(chart_path)
            plt.close()
            
            return str(chart_path)
            
        except Exception as e:
            logger.error(f"パフォーマンスチャートの生成に失敗しました: {e}")
            return None


class TestReportGenerator:
    """テストレポート生成クラス"""
    
    def __init__(self, results_file: Union[str, Path], output_dir: Union[str, Path]):
        """
        初期化
        
        Args:
            results_file: テスト結果ファイルのパス
            output_dir: レポート出力ディレクトリ
        """
        self.results_file = Path(results_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.processor = TestResultProcessor(results_file)
        
        # テンプレートエンジンの設定
        template_dir = project_root / "tests" / "templates"
        if not template_dir.exists():
            template_dir = project_root / "templates"
            if not template_dir.exists():
                template_dir.mkdir(parents=True, exist_ok=True)
                self._create_default_template(template_dir)
        
        self.env = Environment(loader=FileSystemLoader(template_dir))
    
    def _create_default_template(self, template_dir: Path):
        """
        デフォルトのHTMLテンプレートを作成
        
        Args:
            template_dir: テンプレートディレクトリ
        """
        default_template = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>テスト実行結果レポート</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .summary { display: flex; justify-content: space-between; margin-bottom: 30px; }
        .summary-card { background-color: #fff; border: 1px solid #ddd; border-radius: 5px; padding: 15px; width: 23%; }
        .summary-card h3 { margin-top: 0; color: #555; }
        .summary-card.success { border-left: 5px solid #4caf50; }
        .summary-card.failure { border-left: 5px solid #f44336; }
        .summary-card.error { border-left: 5px solid #ff9800; }
        .summary-card.rate { border-left: 5px solid #2196f3; }
        .big-number { font-size: 2em; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f8f8; }
        tr:hover { background-color: #f1f1f1; }
        .status-passed { color: #4caf50; font-weight: bold; }
        .status-failed { color: #f44336; font-weight: bold; }
        .status-error { color: #ff9800; font-weight: bold; }
        .performance-chart { margin: 30px 0; text-align: center; }
        .performance-chart img { max-width: 100%; height: auto; }
        pre { background-color: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }
        .agent-section { margin-bottom: 40px; }
        h2 { color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>テスト実行結果レポート</h1>
            <p>生成日時: {{ timestamp }}</p>
        </div>

        <h2>実行概要</h2>
        <div class="summary">
            <div class="summary-card success">
                <h3>成功</h3>
                <div class="big-number">{{ summary.passed_tests }}</div>
            </div>
            <div class="summary-card failure">
                <h3>失敗</h3>
                <div class="big-number">{{ summary.failed_tests }}</div>
            </div>
            <div class="summary-card error">
                <h3>エラー</h3>
                <div class="big-number">{{ summary.error_tests }}</div>
            </div>
            <div class="summary-card rate">
                <h3>成功率</h3>
                <div class="big-number">{{ summary.success_rate }}%</div>
            </div>
        </div>

        {% if performance_chart %}
        <div class="performance-chart">
            <h2>エージェントパフォーマンス</h2>
            <img src="{{ performance_chart }}" alt="エージェントパフォーマンスチャート">
        </div>
        {% endif %}

        {% if tests %}
        <h2>テスト詳細</h2>
        <table>
            <thead>
                <tr>
                    <th>テスト名</th>
                    <th>ステータス</th>
                    <th>実行時間</th>
                    <th>詳細</th>
                </tr>
            </thead>
            <tbody>
                {% for test in tests %}
                <tr>
                    <td>{{ test.name }}</td>
                    <td class="status-{{ test.status }}">{{ test.status }}</td>
                    <td>{{ test.duration }}秒</td>
                    <td>{{ test.details }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}

        {% if agent_performance %}
        <h2>エージェント詳細</h2>
        {% for agent_id, data in agent_performance.items() %}
        <div class="agent-section">
            <h3>{{ agent_id }}</h3>
            <p><strong>実行時間:</strong> {{ data.execution_time }}秒</p>
            <p><strong>ステータス:</strong> {{ data.status }}</p>
            {% if data.error %}
            <p><strong>エラー:</strong></p>
            <pre>{{ data.error }}</pre>
            {% endif %}
        </div>
        {% endfor %}
        {% endif %}
    </div>
</body>
</html>"""
        
        template_path = template_dir / "report_template.html"
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(default_template)
    
    def generate_html_report(self) -> str:
        """
        HTMLレポートを生成
        
        Returns:
            生成されたレポートファイルのパス
        """
        # テンプレートの読み込み
        template = self.env.get_template("report_template.html")
        
        # データの準備
        summary = self.processor.get_test_summary()
        agent_performance = self.processor.get_agent_performance()
        
        # パフォーマンスチャートの生成
        performance_chart_path = self.processor.generate_performance_chart(self.output_dir)
        if performance_chart_path:
            # パスを相対パスに変換
            performance_chart = os.path.basename(performance_chart_path)
        else:
            performance_chart = None
        
        # 元のテスト結果からテスト詳細を取得
        tests = self.processor.results.get("tests", [])
        
        # HTMLの生成
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html_content = template.render(
            timestamp=timestamp,
            summary=summary,
            tests=tests,
            agent_performance=agent_performance,
            performance_chart=performance_chart
        )
        
        # ファイルに保存
        timestamp_file = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"test_report_{timestamp_file}.html"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTMLレポートを生成しました: {report_file}")
        return str(report_file)


def save_test_results(results: Dict[str, Any], output_file: Union[str, Path]):
    """
    テスト結果をJSONファイルに保存
    
    Args:
        results: テスト結果の辞書
        output_file: 出力ファイルパス
    """
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"テスト結果をJSONファイルに保存しました: {output_file}")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="テスト結果レポート生成ツール")
    parser.add_argument("--results", required=True, help="テスト結果JSONファイルのパス")
    parser.add_argument("--output-dir", default="reports", help="レポート出力ディレクトリ")
    
    args = parser.parse_args()
    
    # レポート生成
    generator = TestReportGenerator(args.results, args.output_dir)
    report_path = generator.generate_html_report()
    
    print(f"レポートが生成されました: {report_path}")


if __name__ == "__main__":
    main() 