param(
    [Parameter(Mandatory=$true)]
    [ValidateRange(1, 99)]
    [int]$NumerDziennika
)

$Port = 8000 + $NumerDziennika
$Image = "sklep-zadanie17"
$Container = "sklep17"

Write-Host "=== 1. Tozsamosc procesu ==="
docker exec $Container whoami
docker exec $Container id

Write-Host "`n=== 2. USER zadeklarowany w obrazie ==="
docker inspect $Container --format "{{.Config.User}}"

Write-Host "`n=== 3. Limit pamieci (256 MB = 268435456 bajtow) ==="
docker inspect $Container --format "{{.HostConfig.Memory}}"

Write-Host "`n=== 4. Rzeczywiste zuzycie zasobow ==="
docker stats --no-stream $Container

Write-Host "`n=== 5. Uprawnienia katalogow ==="
docker exec $Container sh -c "ls -ld /app /app/data /app/private_uploads"

Write-Host "`n=== 6. Proba zapisu do kodu /app - ma sie NIE udac ==="
docker exec $Container sh -c "touch /app/PROBA_ZAPISU 2>/dev/null && echo BLAD: zapis mozliwy || echo OK: /app jest niezapisywalne"

Write-Host "`n=== 7. Proba zapisu do /app/data - ma sie udac ==="
docker exec $Container sh -c "touch /app/data/proba && rm /app/data/proba && echo OK: zapis do data dziala"

Write-Host "`n=== 8. Proba zapisu do /app/private_uploads - ma sie udac ==="
docker exec $Container sh -c "touch /app/private_uploads/proba && rm /app/private_uploads/proba && echo OK: zapis do private_uploads dziala"

Write-Host "`n=== 9. Wrazliwe pliki w CZYSTYM obrazie ==="
Write-Host "Oczekiwany wynik: brak .env, *.db, .git oraz .venv."
docker run --rm --entrypoint sh $Image -c "find /app -maxdepth 3 \( -name '.env' -o -name '*.db' -o -name '.git' -o -name '.venv' \) -print"

Write-Host "`n=== 10. Historia warstw obrazu ==="
docker history --no-trunc $Image

Write-Host "`n=== 11. Port aplikacji ==="
Write-Host "http://localhost:$Port"
