# シンプルテスト実行スクリプト
Write-Host "テストを実行します..."
python test_workflow_state.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "テスト成功" -ForegroundColor Green
} else {
    Write-Host "テスト失敗" -ForegroundColor Red
} 