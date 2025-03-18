"""
backup_manager.pyのテストモジュール

このモジュールは、src.utils.backup_managerの機能をテストします。
"""

import os
import sys
import shutil
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from datetime import datetime

import pytest

# テスト対象のモジュールをインポート
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.backup_manager import (
    backup_database,
    restore_database_from_backup,
    list_backups,
    create_full_backup,
    DEFAULT_BACKUP_DIR
)

class TestBackupManager(unittest.TestCase):
    """backup_manager.pyのテストクラス"""
    
    def setUp(self):
        """テスト前の準備"""
        # テスト用の一時ディレクトリを作成
        self.temp_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.temp_dir, "test_db.sqlite")
        
        # テスト用のデータベースファイルを作成
        with open(self.test_db_path, 'w') as f:
            f.write("テスト用データベース")
        
        # バックアップディレクトリのパスを一時ディレクトリに変更（モック）
        self.original_backup_dir = DEFAULT_BACKUP_DIR
        self.backup_dir_patcher = mock.patch(
            'src.utils.backup_manager.DEFAULT_BACKUP_DIR', 
            os.path.join(self.temp_dir, "backups")
        )
        self.backup_dir_mock = self.backup_dir_patcher.start()
        
        # バックアップディレクトリを作成
        os.makedirs(os.path.join(self.temp_dir, "backups"), exist_ok=True)
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        # モックを停止
        self.backup_dir_patcher.stop()
        
        # 一時ディレクトリを削除
        shutil.rmtree(self.temp_dir)
    
    def test_backup_database(self):
        """backup_database関数のテスト"""
        # バックアップの実行
        result = backup_database(db_path=self.test_db_path)
        
        # 結果の検証
        self.assertTrue(result['success'])
        self.assertEqual(result['source'], self.test_db_path)
        
        # バックアップファイルが作成されたか確認
        backup_path = result['destination']
        self.assertTrue(os.path.exists(backup_path))
        
        # バックアップファイルの内容を確認
        with open(backup_path, 'r') as f:
            content = f.read()
            self.assertEqual(content, "テスト用データベース")
    
    def test_backup_database_with_timestamp(self):
        """タイムスタンプ付きのバックアップのテスト"""
        # タイムスタンプ付きバックアップの実行
        result = backup_database(db_path=self.test_db_path, add_timestamp=True)
        
        # 結果の検証
        self.assertTrue(result['success'])
        
        # ファイル名にタイムスタンプが含まれているか確認
        backup_filename = os.path.basename(result['destination'])
        self.assertIn("test_db_", backup_filename)  # タイムスタンプ形式の確認
    
    def test_backup_nonexistent_database(self):
        """存在しないデータベースのバックアップテスト"""
        nonexistent_path = os.path.join(self.temp_dir, "nonexistent.db")
        
        # 存在しないデータベースのバックアップ実行
        result = backup_database(db_path=nonexistent_path)
        
        # 結果の検証
        self.assertFalse(result['success'])
        self.assertIsNotNone(result['error'])
    
    def test_restore_database(self):
        """restore_database_from_backup関数のテスト"""
        # まずバックアップを作成
        backup_result = backup_database(db_path=self.test_db_path)
        backup_path = backup_result['destination']
        
        # 元のDBを変更
        with open(self.test_db_path, 'w') as f:
            f.write("変更後のデータ")
        
        # バックアップから復元
        restore_result = restore_database_from_backup(
            backup_path=backup_path,
            target_path=self.test_db_path
        )
        
        # 結果の検証
        self.assertTrue(restore_result['success'])
        
        # 復元されたファイルの内容を確認
        with open(self.test_db_path, 'r') as f:
            content = f.read()
            self.assertEqual(content, "テスト用データベース")
    
    def test_list_backups(self):
        """list_backups関数のテスト"""
        # 複数のバックアップを作成
        backup_database(db_path=self.test_db_path)
        backup_database(db_path=self.test_db_path, add_timestamp=True)
        
        # バックアップリストの取得
        backups = list_backups()
        
        # 結果の検証
        self.assertGreaterEqual(len(backups), 2)
        self.assertIn("filename", backups[0])
        self.assertIn("path", backups[0])
        self.assertIn("size", backups[0])
        self.assertIn("created", backups[0])
    
    def test_create_full_backup(self):
        """create_full_backup関数のテスト"""
        # テスト用のアップロードディレクトリとログディレクトリを作成
        uploads_dir = os.path.join(self.temp_dir, "uploads")
        logs_dir = os.path.join(self.temp_dir, "logs")
        os.makedirs(uploads_dir, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)
        
        # テスト用のファイルを作成
        with open(os.path.join(uploads_dir, "test_upload.txt"), 'w') as f:
            f.write("テスト用アップロードファイル")
        
        with open(os.path.join(logs_dir, "test.log"), 'w') as f:
            f.write("テスト用ログファイル")
        
        # シミュレーション用のモック設定
        with mock.patch('src.utils.backup_manager.root_dir', self.temp_dir):
            with mock.patch('src.utils.backup_manager.settings') as settings_mock:
                settings_mock.DB_PATH = self.test_db_path
                
                # フルバックアップの作成
                output_path = os.path.join(self.temp_dir, "fullbackup_test.zip")
                result = create_full_backup(
                    output_path=output_path,
                    include_db=True,
                    include_uploads=True,
                    include_logs=True
                )
                
                # 結果の検証
                self.assertTrue(result['success'])
                self.assertTrue(os.path.exists(output_path))
                self.assertGreater(len(result['included_files']), 0)

if __name__ == "__main__":
    unittest.main() 