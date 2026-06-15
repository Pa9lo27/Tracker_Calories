FROM python:3.14-slim

WORKDIR /app
# Встановлюємо залежності для мережі, якщо потрібно
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt || echo "No requirements.txt found, skipping..."

COPY . .