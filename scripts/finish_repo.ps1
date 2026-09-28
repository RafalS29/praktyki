param(
    [Parameter(Mandatory=$true)]
    [string]$RepoPath
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path $RepoPath).Path
if (-not (Test-Path (Join-Path $repo '.git'))) {
    throw "Podana sciezka nie jest katalogiem roboczym Git: $repo"
}
$bundleRoot = Split-Path -Parent $PSScriptRoot

Write-Host "Kopia plikow porzadkowych do: $repo"
Copy-Item (Join-Path $bundleRoot 'README.md') (Join-Path $repo 'README.md') -Force
Copy-Item (Join-Path $bundleRoot '.gitignore') (Join-Path $repo '.gitignore') -Force
Copy-Item (Join-Path $bundleRoot '.dockerignore') (Join-Path $repo '.dockerignore') -Force

$dstApp = Join-Path $repo 'zadanie17'
if (Test-Path $dstApp) {
    Write-Host 'Katalog zadanie17 juz istnieje. Pliki z paczki zostana scalone/nadpisane, ale nie usuwam lokalnych danych.'
}
Copy-Item (Join-Path $bundleRoot 'zadanie17') $repo -Recurse -Force
Copy-Item (Join-Path $bundleRoot 'scripts') $repo -Recurse -Force

Push-Location $repo
try {
    git rm -f --ignore-unmatch -- `
      zadanie13/app_wallet_vuln.py `
      zadanie13/audit_race_condition.py `
      zadanie13/exploit.py `
      zadanie13/exploit_audit.py

    # Jeśli plik wrażliwy był już śledzony, usuń go TYLKO z indeksu.
    # Lokalnej kopii nie kasujemy automatycznie, bo może zawierać potrzebne dane.
    $tracked = git ls-files
    $sensitive = $tracked | Where-Object {
        $_ -match '(?i)(^|/)(\.env($|\.)|.*\.(db|sqlite|sqlite3)$|private_uploads/|uploads_private/)' -and
        $_ -notmatch '(^|/)\.env\.example$'
    }
    foreach ($path in $sensitive) {
        Write-Host "Usuwam z indeksu (lokalny plik zostaje): $path"
        git rm --cached --ignore-unmatch -- $path
    }

    git add -- README.md .gitignore .dockerignore zadanie17 scripts
    Write-Host "`n=== Stan do weryfikacji ==="
    git status --short
    Write-Host "`nNie wykonano commit ani push automatycznie. Po sprawdzeniu:"
    Write-Host '  git commit -m "Zadanie 19: uporzadkowanie repozytorium i dokumentacja"'
    Write-Host '  git push'
} finally {
    Pop-Location
}
