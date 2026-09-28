param(
    [string]$Repository = 'https://github.com/RafalS29/praktyki.git'
)
$ErrorActionPreference = 'Stop'
git filter-repo --version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Zainstaluj narzedzie: python -m pip install git-filter-repo'
    exit 1
}
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backup = "praktyki-backup-$stamp.git"
$clean = "praktyki-clean-$stamp.git"

git clone --mirror $Repository $backup
if ($LASTEXITCODE -ne 0) { throw 'Tworzenie lokalnej kopii nie powiodlo sie.' }
git clone --mirror $Repository $clean
if ($LASTEXITCODE -ne 0) { throw 'Tworzenie roboczej kopii nie powiodlo sie.' }
$expected = git -C $clean rev-parse refs/heads/master

# Filtruje WYŁĄCZNIE pliki robocze starego zadania i lokalne artefakty.
git -C $clean filter-repo --force `
  --path zadanie13/app_wallet_vuln.py `
  --path zadanie13/audit_race_condition.py `
  --path zadanie13/exploit.py `
  --path zadanie13/exploit_audit.py `
  --path-regex '(^|/)(\.env($|\.(?!example$)[^/]+$)|[^/]+\.(db|sqlite|sqlite3|pyc)$|__pycache__/|\.venv/|private_uploads/|uploads_private/)' `
  --invert-paths
if ($LASTEXITCODE -ne 0) { throw 'git filter-repo nie powiodl sie.' }

Write-Host "`nKopia przed zmianami: $backup"
Write-Host "Kopia oczyszczona:    $clean"
Write-Host "Stary SHA master:     $expected"
Write-Host "`nSPRAWDZ WYNIKI przed jakimkolwiek wypchnieciem:"
Write-Host "  git -C $clean rev-list --objects --all"
Write-Host "  git -C $clean log --oneline --all"
Write-Host "`nNie wykonano force push. Po sprawdzeniu i uzgodnieniu ze wspolpracownikami:"
Write-Host "  git -C $clean remote add origin $Repository"
Write-Host "  git -C $clean push --force-with-lease=refs/heads/master:$expected origin refs/heads/master:refs/heads/master"
Write-Host "`nUWAGA: usuniecie z refow nie gwarantuje usuniecia z cache GitHub lub klonow. Ujawnione sekrety trzeba zmienic."
