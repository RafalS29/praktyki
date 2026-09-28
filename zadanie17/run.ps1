param(
    [Parameter(Mandatory=$true)]
    [ValidateRange(1, 99)]
    [int]$NumerDziennika
)

$ErrorActionPreference = "Stop"

$Port = 8000 + $NumerDziennika
$Image = "sklep-zadanie17"
$Container = "sklep17"

Write-Host "Port hosta: $Port"

if (-not (Test-Path ".env")) {
    $secret = ([guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N"))
    @"
JWT_SECRET=$secret
APP_PORT=5000
SEED_DEMO_DATA=0
"@ | Set-Content -Encoding ASCII ".env"

    Write-Host "Utworzono .env z losowym JWT_SECRET."
}

docker build -t $Image .

$existing = docker ps -a --filter "name=^/$Container$" --format "{{.Names}}"
if ($existing -eq $Container) {
    docker rm -f $Container | Out-Null
}

docker run -d `
    --name $Container `
    --memory=256m `
    --memory-swap=256m `
    --env-file .env `
    --cap-drop=ALL `
    --security-opt no-new-privileges:true `
    --mount type=volume,src=sklep17_data,dst=/app/data `
    --mount type=volume,src=sklep17_uploads,dst=/app/private_uploads `
    -p "127.0.0.1:${Port}:5000" `
    $Image

Write-Host ""
Write-Host "Kontener uruchomiony."
Write-Host "Adres: http://localhost:$Port"
Write-Host "Testy:"
Write-Host "  python tests/test_security_headers.py --url http://localhost:$Port"
Write-Host "  python tests/test_auth_isolation.py --url http://localhost:$Port"
Write-Host "  python tests/test_upload.py --url http://localhost:$Port"
Write-Host "  python tests/test_race_condition.py --url http://localhost:$Port"
