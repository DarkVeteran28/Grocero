FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATABASE_URL=sqlite:////data/grocery.db

WORKDIR /app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY frontend/ /app/frontend/
COPY data/ /app/data/
COPY docker/entrypoint.sh /usr/local/bin/grocery-entrypoint

RUN chmod 755 /usr/local/bin/grocery-entrypoint \
    && mkdir -p /data /app/backend/instance \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --home-dir /app app \
    && chown -R app:app /data /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD-SHELL python -c 'import os, urllib.request; urllib.request.urlopen("http://127.0.0.1:" + os.environ.get("PORT", "8000") + "/api/config", timeout=2)' || exit 1

ENTRYPOINT ["/usr/local/bin/grocery-entrypoint"]
CMD ["/bin/sh", "-c", "exec gunicorn --workers 2 --bind 0.0.0.0:${PORT:-8000} --access-logfile - --error-logfile - run:app"]
