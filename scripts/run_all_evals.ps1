$ErrorActionPreference = "Stop"

$configs = @(
    @{ Provider = "gemini"; Model = "gemini-2.5-flash" },
    @{ Provider = "grok"; Model = "grok-2-latest" }
)

$datasets = @("validation", "humaneval", "mbpp")
$limit = 2

Write-Host "=== Starting Atlas Round 1 Benchmarking ===" -ForegroundColor Cyan
Write-Host "Limit: $limit questions per dataset" -ForegroundColor Cyan

$log_file = "logs/evaluation_run_log.txt"
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

Clear-Content $log_file -ErrorAction SilentlyContinue

foreach ($dataset in $datasets) {
    foreach ($config in $configs) {
        $provider = $config.Provider
        $model = $config.Model

        Write-Host "-> Running $provider ($model) on $dataset..." -ForegroundColor Yellow
        Add-Content -Path $log_file -Value "========================================="
        Add-Content -Path $log_file -Value "STARTING: Provider=$provider, Dataset=$dataset, Model=$model"
        
        $cmd = "py scripts/run_experiment.py --dataset $dataset --provider $provider --model `"$model`" --limit $limit --prompt v3"
        Write-Host "> $cmd" -ForegroundColor DarkGray
        
        try {
            $output = Invoke-Expression $cmd
            Add-Content -Path $log_file -Value ($output | Out-String)
            Write-Host "[OK] Completed $provider on $dataset." -ForegroundColor Green
        } catch {
            Write-Host "[ERROR] Failed $provider on ${dataset}: $($_)" -ForegroundColor Red
            Add-Content -Path $log_file -Value "ERROR: $($_)"
        }

        Write-Host "Sleeping 15 seconds to respect free tier rate limits..." -ForegroundColor DarkGray
        Start-Sleep -Seconds 15
    }
}

Write-Host "=== Benchmarking Round 1 Complete! ===" -ForegroundColor Cyan
Write-Host "Check $log_file for full output." -ForegroundColor Cyan
