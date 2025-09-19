# Email to Notion Summary - Fetch since 2025-09-15
Write-Host "=== Email to Notion Summary - Fetch since 2025-09-15 ===" -ForegroundColor Green

# 1. Backup DB
Write-Host "`n1. Creating database backup..." -ForegroundColor Yellow
if (Test-Path ".\emails.db") {
    Copy-Item -Path ".\emails.db" -Destination ".\emails.db.bak" -Force
    Write-Host "Backup created: emails.db.bak" -ForegroundColor Green
} else {
    Write-Host "No existing database found to backup" -ForegroundColor Yellow
}

# 2. Create feature branch
Write-Host "`n2. Creating feature branch..." -ForegroundColor Yellow
git checkout -b oneoff/fetch-since-2025-09-15
Write-Host "Feature branch created" -ForegroundColor Green

# 3. Install dateparser
Write-Host "`n3. Installing dateparser..." -ForegroundColor Yellow
pip install dateparser
Write-Host "dateparser installation completed" -ForegroundColor Green

# 4. DRY-RUN
Write-Host "`n4. Running DRY-RUN..." -ForegroundColor Yellow
Write-Host "This will fetch messages AFTER 2025-09-15 from BMU and Classroom" -ForegroundColor Cyan
Write-Host "It will NOT write to Notion (dry-run mode)" -ForegroundColor Cyan

Write-Host "`nRunning DRY-RUN command..." -ForegroundColor Gray
python src/main.py --dry-run --query "after:2025/09/15 (from:@bmu.edu.in OR from:@classroom.google.com)" --limit 1000 --order recent

Write-Host "`n--- DRY-RUN COMPLETED ---" -ForegroundColor Magenta
Write-Host "Review the output above. If it looks good, run the live command:" -ForegroundColor Magenta
Write-Host "python src/main.py --notion --query `"after:2025/09/15 (from:@bmu.edu.in OR from:@classroom.google.com)`" --limit 1000 --order recent" -ForegroundColor White

Write-Host "`n=== Script completed ===" -ForegroundColor Green