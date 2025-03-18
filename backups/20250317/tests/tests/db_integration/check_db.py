#!/usr/bin/env python
"""
データベースの状態を確認するスクリプト
"""

import sqlite3
import json

# データベースに接続
conn = sqlite3.connect('data/app.db')
cursor = conn.cursor()

# テーブル一覧を取得
print("=== データベーステーブル一覧 ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
for table in tables:
    print(f"- {table}")

# 人間監査人介入リクエストテーブルの内容を確認
print("\n=== 人間監査人介入リクエスト ===")
try:
    cursor.execute("SELECT * FROM human_intervention_requests")
    rows = cursor.fetchall()
    
    # カラム名を取得
    column_names = [description[0] for description in cursor.description]
    
    if rows:
        for row in rows:
            print("\n--- リクエスト詳細 ---")
            for i, col in enumerate(column_names):
                # JSONフィールドの場合は整形して表示
                if col in ['options', 'context_data'] and row[i]:
                    try:
                        value = json.loads(row[i])
                        print(f"{col}: {json.dumps(value, ensure_ascii=False, indent=2)}")
                    except:
                        print(f"{col}: {row[i]}")
                else:
                    print(f"{col}: {row[i]}")
    else:
        print("リクエストが見つかりませんでした")
except Exception as e:
    print(f"エラー: {e}")

# データベース接続を閉じる
conn.close() 