FROM python:3.11-slim

WORKDIR /app

# System dependencies for dnspython, lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

# Persistent volume for SQLite DB
VOLUME ["/app/data"]
ENV DB_PATH=/app/data/scans.db

EXPOSE 5000

CMD ["sh", "-c", "gunicorn app:create_app() --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT"]