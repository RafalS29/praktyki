FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup -S appgroup \
    && adduser -S -D -H -s /sbin/nologin -G appgroup appuser

# Najpierw zależności - osobna warstwa dla cache Dockera.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiujemy wyłącznie pliki potrzebne aplikacji produkcyjnej.
COPY app.py init_db.py init_db_wallet.py manage_users.py ./
COPY static ./static
COPY templates ./templates

# Kod pozostaje własnością roota i nie jest zapisywalny przez appuser.
# Tylko katalog danych i uploadów jest zapisywalny.
RUN mkdir -p /app/data /app/private_uploads \
    && chown -R appuser:appgroup /app/data /app/private_uploads \
    && chmod 0755 /app \
    && chmod 0555 /app/static /app/templates \
    && chmod 0444 /app/*.py /app/requirements.txt \
    && chmod 0700 /app/data /app/private_uploads

EXPOSE 5000

USER appuser

CMD ["sh", "-c", "python init_db.py && python init_db_wallet.py && exec gunicorn --bind 0.0.0.0:${APP_PORT:-5000} --workers 1 --threads 2 --timeout 30 app:app"]
