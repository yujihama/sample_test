#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
テスト実行とレポート生成を一括で行うスクリプト

使用方法:
python tests/run_tests_and_report.py --test-type integration --report-dir reports
"""

import os
import sys
import json
import time
import datetime
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).parents[1].absolute()
sys.path.append(str(project_root))

from tests.reports.test_report_generator import TestReportGenerator, save_test_results
from loguru import logger


def run_tests(test_type: str = "integration", test_file: Optional[str] = None) -> Dict[str, Any]:
    """
    テストを実行する
    
    Args:
        test_type: テストタイプ (unit/integration/e2e)
        test_file: 特定のテストファイル (省略時は全テスト実行)
        
    Returns:
        テスト結果の辞書
    """
    logger.info(f"{test_type}テストを実行します...")
    start_time = time.time()
    
    # テストコマンドの構築
    cmd = ["pytest", "-v"]
    
    if test_type == "unit":
        cmd.append("tests/unit/")
    elif test_type == "integration":
        cmd.append("tests/integration/")
    elif test_type == "e2e":
        cmd.append("tests/e2e/")
    elif test_type == "all":
        cmd.append("tests/")
    
    if test_file:
        cmd.append(test_file)
    
    # JUnitXML形式で結果を出力
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f"tests/reports/test_results_{timestamp}.xml"
    cmd.extend(["--junitxml", result_file])
    
    # テスト実行
    try:
        process = subprocess.run(cmd, capture_output=True, text=True)
        stdout = process.stdout
        stderr = process.stderr
        return_code = process.returncode
    except Exception as e:
        logger.error(f"テスト実行中にエラーが発生しました: {e}")
        return {
            "status": "error",
            "error": str(e),
            "tests": []
        }
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # 結果の解析
    test_results = {
        "timestamp": datetime.datetime.now().isoformat(),
        "test_type": test_type,
        "execution_time": round(execution_time, 2),
        "return_code": return_code,
        "tests": [],
        "agent_results": {}
    }
    
    # 標準出力から個々のテスト結果を解析
    lines = stdout.split("\n")
    current_test = None
    for line in lines:
        line = line.strip()
        if "PASSED" in line or "FAILED" in line or "ERROR" in line:
            # テスト名と結果を抽出
            parts = line.split(" ")
            test_path = parts[0]
            status = "passed" if "PASSED" in line else "failed" if "FAILED" in line else "error"
            
            # test_agent_collaborationなどのテスト結果をagent_resultsにマッピング
            test_name = test_path.split("::")[-1] if "::" in test_path else test_path
            if test_name.startswith("test_agent_") or "agent" in test_name.lower():
                agent_type = test_name.replace("test_", "").split("_")[0]
                if agent_type not in test_results["agent_results"]:
                    test_results["agent_results"][agent_type] = {}
                test_results["agent_results"][agent_type]["status"] = status
                test_results["agent_results"][agent_type]["execution_time"] = 0.0  # 後で更新
            
            # 一般的なテスト結果を追加
            test_results["tests"].append({
                "name": test_name,
                "path": test_path,
                "status": status,
                "duration": 0.0,  # 後で更新（可能であれば）
                "details": line
            })
    
    # 実行時間の割り当て（簡易的に）
    if test_results["tests"]:
        avg_duration = execution_time / len(test_results["tests"])
        for test in test_results["tests"]:
            test["duration"] = round(avg_duration, 2)
        
        # エージェント結果にも実行時間を割り当て
        for agent_id in test_results["agent_results"]:
            test_results["agent_results"][agent_id]["execution_time"] = round(avg_duration, 2)
    
    logger.info(f"テスト実行完了。所要時間: {execution_time:.2f}秒")
    return test_results


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="テスト実行とレポート生成")
    parser.add_argument("--test-type", default="integration", choices=["unit", "integration", "e2e", "all"],
                        help="実行するテストのタイプ")
    parser.add_argument("--test-file", help="特定のテストファイル（省略時は全テスト実行）")
    parser.add_argument("--report-dir", default="reports", help="レポート出力ディレクトリ")
    
    args = parser.parse_args()
    
    # テスト実行
    test_results = run_tests(args.test_type, args.test_file)
    
    # 結果をJSONファイルに保存
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = Path(project_root) / "tests" / "reports" / f"test_results_{timestamp}.json"
    save_test_results(test_results, results_file)
    
    # レポート生成
    report_dir = Path(project_root) / "tests" / args.report_dir
    generator = TestReportGenerator(results_file, report_dir)
    report_path = generator.generate_html_report()
    
    print(f"テスト結果: 成功={sum(1 for t in test_results['tests'] if t['status'] == 'passed')}, "
          f"失敗={sum(1 for t in test_results['tests'] if t['status'] == 'failed')}, "
          f"エラー={sum(1 for t in test_results['tests'] if t['status'] == 'error')}")
    print(f"レポートが生成されました: {report_path}")


if __name__ == "__main__":
    main() 