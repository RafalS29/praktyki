# Zadanie 17 – aplikacja kontenerowa

Dokumentacja architektury, uruchomienia, zabezpieczeń i bazy jest w pliku [`../README.md`](../README.md).

Szybki start w PowerShellu (z tego folderu):

```powershell
.\run.ps1 -NumerDziennika 12
```

Uwaga: `SEED_DEMO_DATA=0` domyślnie. Konta można tworzyć przez `docker exec -it sklep17 python manage_users.py --username <login> --role user`.
