# fix_table_names.ps1
# Run with: .\fix_table_names.ps1 -DryRun
# Run for real: .\fix_table_names.ps1

param(
    [switch]$DryRun = $true,
    [string]$ProjectPath = "D:\itender_clean"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PWD/LGED Table Name Fixer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Project Path: $ProjectPath"
if ($DryRun) {
    Write-Host "MODE: DRY RUN (no changes will be made)" -ForegroundColor Yellow
} else {
    Write-Host "MODE: LIVE (changes will be made)" -ForegroundColor Red
}
Write-Host ""

# Define replacements
$replacements = @(
    # PWD table names
    @{Old="pwd_rates"; New="pwd_rates"},
    @{Old="pwd_parent_items"; New="pwd_parents"},
    @{Old="pwd_child_items"; New="pwd_children"},
    @{Old="regional_rates"; New="pwd_rates"},
    
    # Version table names (should use unified rate_versions)
    @{Old="pwd_versions"; New="rate_versions"},
    @{Old="lged_versions"; New="rate_versions"}
)

# File patterns to search
$filePatterns = @("*.py")

# Directories to exclude
$excludeDirs = @("venv", "__pycache__", ".git", "temp", "cache", "logs")

Write-Host "Searching for files..." -ForegroundColor Green

# Find all Python files
$allFiles = Get-ChildItem -Path $ProjectPath -Recurse -Include $filePatterns | Where-Object {
    $shouldExclude = $false
    foreach ($excludeDir in $excludeDirs) {
        if ($_.FullName -like "*\$excludeDir*") {
            $shouldExclude = $true
            break
        }
    }
    -not $shouldExclude
}

Write-Host "Found $($allFiles.Count) Python files to scan" -ForegroundColor Green
Write-Host ""

# Store results
$results = @()

foreach ($file in $allFiles) {
    $content = Get-Content -Path $file.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $content) { continue }
    
    $originalContent = $content
    $changes = @()
    
    foreach ($replacement in $replacements) {
        $oldPattern = $replacement.Old
        $newPattern = $replacement.New
        
        # Count occurrences
        $matches = [regex]::Matches($content, "\b$oldPattern\b")
        if ($matches.Count -gt 0) {
            $changes += @{
                Old = $oldPattern
                New = $newPattern
                Count = $matches.Count
            }
            if (-not $DryRun) {
                $content = $content -replace "\b$oldPattern\b", $newPattern
            }
        }
    }
    
    if ($changes.Count -gt 0) {
        $results += @{
            File = $file.FullName
            Changes = $changes
            RelativePath = $file.FullName.Replace($ProjectPath, "").TrimStart('\')
        }
        
        if (-not $DryRun) {
            Set-Content -Path $file.FullName -Value $content -NoNewline
        }
    }
}

# Display results
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "RESULTS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($results.Count -eq 0) {
    Write-Host "No files need changes!" -ForegroundColor Green
} else {
    Write-Host "Files requiring changes: $($results.Count)" -ForegroundColor Yellow
    Write-Host ""
    
    foreach ($result in $results) {
        Write-Host "📄 $($result.RelativePath)" -ForegroundColor White
        foreach ($change in $result.Changes) {
            Write-Host "   ✏️  '$($change.Old)' → '$($change.New)' ($($change.Count) occurrence(s))" -ForegroundColor Gray
        }
        Write-Host ""
    }
    
    if ($DryRun) {
        Write-Host "========================================" -ForegroundColor Yellow
        Write-Host "DRY RUN COMPLETE" -ForegroundColor Yellow
        Write-Host "To apply changes, run: .\fix_table_names.ps1 -DryRun:`$false" -ForegroundColor White
        Write-Host "========================================" -ForegroundColor Yellow
    } else {
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "LIVE RUN COMPLETE" -ForegroundColor Green
        Write-Host "$($results.Count) files were modified" -ForegroundColor White
        Write-Host "========================================" -ForegroundColor Green
    }
}