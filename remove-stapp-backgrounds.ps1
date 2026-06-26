# Remove .stApp background declarations from all Python files
param(
    [switch]$DryRun = $true,
    [string]$SearchPath = "D:\itender_clean"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  .stApp Background Remover" -ForegroundColor Cyan
Write-Host "  Mode: $(if ($DryRun) { 'DRY RUN' } else { 'LIVE' })" -ForegroundColor $(if ($DryRun) { 'Yellow' } else { 'Red' })
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$files = Get-ChildItem -Path $SearchPath -Filter *.py -Recurse | 
    Where-Object { $_.FullName -notmatch '\\venv\\' -and $_.FullName -notmatch '\\__pycache__\\' }

$totalFiles = 0
$modifiedFiles = 0

foreach ($file in $files) {
    $totalFiles++
    $content = Get-Content $file.FullName -Raw
    
    $pattern = '(?ms)\.stApp\s*\{\s*background:[^}]+\}'
    $matches = [regex]::Matches($content, $pattern)
    
    if ($matches.Count -gt 0) {
        $modifiedFiles++
        Write-Host "`nFile: $($file.FullName)" -ForegroundColor Green
        Write-Host "Found $($matches.Count) .stApp background(s)" -ForegroundColor White
        
        if ($DryRun) {
            Write-Host "Preview:" -ForegroundColor Yellow
            foreach ($match in $matches) {
                $preview = $match.Value -replace "`r`n", " "
                $preview = $preview.Substring(0, [Math]::Min(150, $preview.Length))
                Write-Host "  $preview..." -ForegroundColor Gray
            }
        } else {
            $backupPath = "$($file.FullName).stapp_backup"
            Copy-Item $file.FullName $backupPath -Force
            Write-Host "Backup: $backupPath" -ForegroundColor Cyan
            
            $newContent = [regex]::Replace($content, $pattern, '')
            $newContent = $newContent -replace '\n\s*\n\s*\n', "`n`n"
            
            Set-Content -Path $file.FullName -Value $newContent -NoNewline
            Write-Host "Removed and saved" -ForegroundColor Green
        }
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Total files scanned: $totalFiles"
Write-Host "Files with .stApp backgrounds: $modifiedFiles"

if ($DryRun) {
    Write-Host "`nDRY RUN - No files modified" -ForegroundColor Yellow
    Write-Host "To apply: .\remove-stapp-backgrounds.ps1 -DryRun:`$false" -ForegroundColor Yellow
} else {
    Write-Host "`nAll .stApp backgrounds removed!" -ForegroundColor Green
    Write-Host "Backups created with .stapp_backup extension" -ForegroundColor Cyan
}

Write-Host ""