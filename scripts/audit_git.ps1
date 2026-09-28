$ErrorActionPreference = "Stop"
Write-Host "=== Sledzone pliki niedozwolone ==="
$patterns = '(?i)(^|/)(\.env($|\.)|.*\.(db|sqlite|sqlite3|pyc)$|__pycache__|\.venv|private_uploads|uploads_private)'
$tracked = git ls-files
$bad = $tracked | Where-Object { $_ -match $patterns -and $_ -notmatch '(^|/)\.env\.example$' }
if ($bad) { $bad | ForEach-Object { Write-Host "BLAD: $_" }; exit 1 }
Write-Host "OK: Drzewo HEAD nie zawiera zabronionych plikow."
Write-Host "`n=== Podejrzane sciezki w historii wszystkich dostepnych refow ==="
$history = git rev-list --objects --all
$history | Where-Object { $_ -match $patterns -and $_ -notmatch '(^|/)\.env\.example$' }
Write-Host "`nUWAGA: sprawdzenie nazw nie wykrywa sekretow wpisanych w kodzie."
