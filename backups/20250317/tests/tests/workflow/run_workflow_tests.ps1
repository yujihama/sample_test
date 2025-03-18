# ワークフローテスト実行スクリプト
# PowerShell

# スクリプトが存在するディレクトリのパスを取得
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
# プロジェクトのルートパスを取得
$rootPath = (Get-Item $scriptPath).Parent.Parent.FullName

# カレントディレクトリをプロジェクトルートに変更
Set-Location -Path $rootPath

Write-Host "=========================================="
Write-Host "ワークフローテスト実行 - 開始" -ForegroundColor Green
Write-Host "=========================================="

# 必要なディレクトリが存在するか確認
$testDir = Join-Path -Path $rootPath -ChildPath "tests\workflow"
$srcDir = Join-Path -Path $rootPath -ChildPath "src"

if (-not (Test-Path -Path $testDir)) {
    Write-Host "テストディレクトリが見つかりません: $testDir" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -Path $srcDir)) {
    Write-Host "ソースディレクトリが見つかりません: $srcDir" -ForegroundColor Red
    exit 1
}

# Pythonが利用可能か確認
try {
    $pythonVersion = python --version
    Write-Host "Python: $pythonVersion" -ForegroundColor Cyan
} catch {
    Write-Host "Pythonが見つかりません。インストールしてください。" -ForegroundColor Red
    exit 1
}

# 依存ライブラリをチェック
Write-Host "依存関係を確認しています..." -ForegroundColor Cyan
python -c "import unittest, logging, tempfile, json, sys; print('基本モジュールが利用可能です')"

# モックリポジトリの存在確認
$mockRepo = Join-Path -Path $testDir -ChildPath "mock_repositories.py"
if (-not (Test-Path -Path $mockRepo)) {
    Write-Host "モックリポジトリファイルが見つかりません: $mockRepo" -ForegroundColor Red
    exit 1
}

# テストスクリプトの存在確認
$testScript = Join-Path -Path $testDir -ChildPath "test_workflow_state.py"
if (-not (Test-Path -Path $testScript)) {
    Write-Host "テストスクリプトが見つかりません: $testScript" -ForegroundColor Red
    exit 1
}

# テスト実行
Write-Host "ワークフローテストを実行しています..." -ForegroundColor Cyan

# テストスクリプトの実行
python $testScript

if ($LASTEXITCODE -eq 0) {
    Write-Host "=========================================="
    Write-Host "すべてのテストが成功しました" -ForegroundColor Green
    Write-Host "=========================================="
} else {
    Write-Host "=========================================="
    Write-Host "テストに失敗があります" -ForegroundColor Red
    Write-Host "=========================================="
    exit 1
}

exit 0 