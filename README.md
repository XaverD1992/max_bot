# TOS MVP — Бот для инициатив жителей

## 🚀 Быстрый старт

```bash
# 1. Установите зависимости
uv sync

# 2. Для webhook-режима (опционально)
uv sync --extra webhook

# 3. Настройте .env
cp .env.example .env

# 4. Запустите PostgreSQL (опционально)
docker-compose up -d db

# 5. Запустите бота
uv run src/main.py