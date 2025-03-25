#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ファイル管理API機能の疎通テスト

このスクリプトは、ファイル管理APIの基本機能（アップロード、一覧取得、ダウンロードなど）の
疎通確認と動作テストを行います。
"""

import os
import sys
import pytest
import tempfile
import json
import requests
from io import BytesIO
from pathlib import Path

# src ディレクトリをパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# サーバーのURL
API_BASE_URL = "http://localhost:8000"


class TestFileAPI:
    """ファイル管理APIの疎通テストと基本機能テスト"""
    
    def setup_method(self):
        """テストメソッド実行前の準備"""
        self.test_file_path = None
        self.simple_test_file_path = None
        self.uploaded_file_id = None
        
        # テスト用ファイルの作成
        self.test_file_path = "test_upload.txt"
        with open(self.test_file_path, "w") as f:
            f.write("This is a test file for upload API")
            
        self.simple_test_file_path = "test_simple_upload.txt"
        with open(self.simple_test_file_path, "w") as f:
            f.write("This is a test file for simple upload API")
    
    def teardown_method(self):
        """テストメソッド実行後のクリーンアップ"""
        # テスト用ファイルの削除
        for file_path in [self.test_file_path, self.simple_test_file_path]:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"ファイル削除中にエラーが発生: {str(e)}")
    
    @pytest.mark.smoke
    @pytest.mark.api
    @pytest.mark.files
    def test_upload_file(self):
        """ファイルアップロード機能のテスト"""
        with open(self.test_file_path, 'rb') as file_handle:
            files = {'file': file_handle}
            response = requests.post(f"{API_BASE_URL}/api/files/upload", files=files)
            
            assert response.status_code == 200, f"アップロード失敗: {response.text}"
            result = response.json()
            assert "id" in result or "file_id" in result, "レスポンスにファイルIDがありません"
            self.uploaded_file_id = result.get("id") or result.get("file_id")
    
    @pytest.mark.smoke
    @pytest.mark.api
    @pytest.mark.files
    def test_upload_simple(self):
        """シンプルなファイルアップロード機能のテスト"""
        with open(self.simple_test_file_path, 'rb') as file_handle:
            files = {'file': file_handle}
            data = {'file_type': 'document', 'description': 'テスト用ファイル'}
            response = requests.post(f"{API_BASE_URL}/api/upload-simple", files=files, data=data)
            
            assert response.status_code == 200, f"シンプルアップロード失敗: {response.text}"
            result = response.json()
            assert "file_id" in result, "レスポンスにファイルIDがありません"
    
    @pytest.mark.smoke
    @pytest.mark.api
    @pytest.mark.files
    def test_get_files(self):
        """ファイル一覧取得機能のテスト"""
        # まずファイルを一つアップロードする
        self.test_upload_file()
        
        # 複数のURLを試す
        urls = [
            f"{API_BASE_URL}/api/files",  # メインのルートURL
            f"{API_BASE_URL}/api/files/files",  # 代替URL
        ]
        
        for url in urls:
            response = requests.get(url)
            if response.status_code == 200:
                files = response.json()
                assert isinstance(files, list), "ファイル一覧が配列ではありません"
                assert len(files) > 0, "ファイル一覧が空です"
                file_found = False
                for file in files:
                    if self.uploaded_file_id and (file.get("id") == self.uploaded_file_id or file.get("file_id") == self.uploaded_file_id):
                        file_found = True
                        break
                assert file_found, "アップロードしたファイルが一覧に見つかりません"
                break
        else:
            pytest.fail("すべてのURLでファイル一覧の取得に失敗しました")
    
    @pytest.mark.smoke
    @pytest.mark.api
    @pytest.mark.files
    def test_get_file_details(self):
        """ファイル詳細取得機能のテスト"""
        # まずファイルを一つアップロードする
        if not self.uploaded_file_id:
            self.test_upload_file()
        
        response = requests.get(f"{API_BASE_URL}/api/files/{self.uploaded_file_id}")
        assert response.status_code == 200, f"ファイル詳細取得失敗: {response.text}"
        file_info = response.json()
        assert file_info.get("id") == self.uploaded_file_id, "取得したファイルIDが一致しません"
        assert "filename" in file_info, "ファイル名が含まれていません"
        assert "file_path" in file_info, "ファイルパスが含まれていません"
    
    @pytest.mark.smoke
    @pytest.mark.api
    @pytest.mark.files
    def test_download_file(self):
        """ファイルダウンロード機能のテスト"""
        # まずファイルを一つアップロードする
        if not self.uploaded_file_id:
            self.test_upload_file()
        
        response = requests.get(f"{API_BASE_URL}/api/files/{self.uploaded_file_id}/download")
        assert response.status_code == 200, f"ファイルダウンロード失敗: {response.text}"
        
        # ダウンロードしたコンテンツの検証
        content = response.content
        assert len(content) > 0, "ダウンロードしたファイルが空です"
        
        # ダウンロードしたファイルを一時保存して内容を確認
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as tmp:
            tmp.write(content)
            download_path = tmp.name
        
        try:
            with open(download_path, 'rb') as f:
                downloaded_content = f.read()
                assert b"This is a test file" in downloaded_content, "ダウンロードしたファイルの内容が正しくありません"
        finally:
            # クリーンアップ
            if os.path.exists(download_path):
                os.remove(download_path)


# スタンドアロンで実行する場合はこちらを使用
if __name__ == "__main__":
    test_instance = TestFileAPI()
    try:
        test_instance.setup_method()
        print("ファイルアップロードテスト開始...")
        test_instance.test_upload_file()
        
        print("\nシンプルなファイルアップロードテスト開始...")
        test_instance.test_upload_simple()
        
        print("\nファイル一覧取得テスト開始...")
        test_instance.test_get_files()
        
        print("\nファイル詳細取得テスト開始...")
        test_instance.test_get_file_details()
        
        print("\nファイルダウンロードテスト開始...")
        test_instance.test_download_file()
        
        print("\nすべてのテストが完了しました")
    finally:
        test_instance.teardown_method() 