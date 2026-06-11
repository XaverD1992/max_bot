# TOS MVP — Технический обзор

## A. Назначение

Бот для мессенджера MAX (max.ru) для подачи, модерации и голосования за инициативы жителей (Town of Suggestions / TOS). Пользователи подают заявки через многошаговый диалог, модераторы approve/reject с причиной отклонения, жители голосуют за одобренные.

## B. Технологический стек

- **Python 3.11+** (Hatchling packaging)
- **maxapi** — SDK для мессенджера MAX (Polling + Webhook, MemoryContext для FSM, ButtonsPayload для inline-клавиатур)
- **SQLAlchemy 2.0 (asyncio)** — ORM + asyncpg драйвер
- **Alembic** — миграции схемы
- **Pydantic Settings** — конфигурация через `.env`
- **FastAPI + Uvicorn** (опционально) — webhook-режим
- **Docker + Docker Compose** — развёртывание (PostgreSQL 15 + бот)
- **uv** — менеджер зависимостей

## C. Структура файлов

```
.
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions/
│       └── 36cc78853d5b_init.py          # Миграция: users, initiatives, votes
├── docker-compose.yml                     # PostgreSQL 15 + бот
├── docker-entrypoint.sh                   # alembic upgrade head → python -m src.main
├── Dockerfile                             # python:3.11-slim, uv, hatchling
├── pyproject.toml                         # Зависимости, dev-окружение, ruff, hatch
├── uv.lock
├── scripts/
│   └── seed_db.py                         # seed / clear тестовых данных
├── src/
│   ├── __init__.py
│   ├── main.py                            # Точка входа, регистрация всех handlers
│   ├── config.py                          # Settings (BOT_TOKEN, DB_URL, RUN_MODE, ...)
│   ├── logging_config.py                  # Настройка логгера (stdout + bot.log)
│   ├── database/
│   │   ├── __init__.py
│   │   ├── session.py                     # async_engine, async_session_factory, get_db
│   │   └── crud.py                        # Асинхронные CRUD-функции
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                        # declarative_base()
│   │   ├── user.py                        # User, UserRole (RESIDENT/MODERATOR/ADMIN)
│   │   ├── initiative.py                  # Initiative, InitiativeStatus, InitiativeCategory
│   │   └── vote.py                        # Vote (unique: user_id + initiative_id)
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── states.py                      # IdeaStates, StartStates, ModerationStates
│   │   └── keyboards.py                   # Inline-клавиатуры (модерация, категории, confirm, back)
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py                       # /start, привязка телефона (+7XXXXXXXXXX)
│   │   ├── idea.py                        # Пошаговый диалог подачи инициативы
│   │   ├── moderation.py                  # Отклонение с причиной, timeout-заглушка
│   │   ├── callback.py                    # Единый обработчик callback-кнопок
│   │   ├── vote.py                        # /vote [id], проверки дубликатов
│   │   ├── list.py                        # /list, вывод APPROVED инициатив
│   │   └── admin.py                       # /set_role <chat_id> <role> (только ADMIN_USER_IDS)
│   └── services/
│       ├── __init__.py
│       └── notification.py                # Уведомление модераторов о новых инициативах
├── .env                                    # Токены, DB_URL, режим, админы
└── .gitignore
```

## D. Входные точки и основные компоненты

### Входная точка
- **`src/main.py:181`** — `main()` создаёт `Bot` + `Dispatcher`, регистрирует handlers, запускает polling или webhook.
- **`docker-entrypoint.sh`** — запускает `alembic upgrade head`, затем `python -m src.main`.

### Конфигурация
- **`src/config.py`** — `Settings` на основе `pydantic-settings`, загружает `.env`. Поля: `BOT_TOKEN`, `DB_URL`, `RUN_MODE` (`polling` | `webhook`), `WEBHOOK_URL`, `ADMIN_USER_IDS` (список через запятую), `LOG_LEVEL`.

### Основные модули-обработчики
| Модуль | Ответственность |
|---|---|
| `handlers/start.py` | `/start`, создание User, запрос телефона, авторизация |
| `handlers/idea.py` | Пошаговый FSM-диалог подачи инициативы (title → description → category → location → confirm) |
| `handlers/callback.py` | Callback-кнопки: модерация (approve/reject), выбор категории, подтверждение подачи, "Назад" |
| `handlers/moderation.py` | Ввод причины отклонения, уведомление автора |
| `handlers/vote.py` | `/vote [id]`, проверка статуса инициативы, уникальность голоса |
| `handlers/list.py` | `/list`, вывод APPROVED инициатив с счётом голосов |
| `handlers/admin.py` | `/set_role`, назначение ролей (только для `ADMIN_USER_IDS`) |

### Модели БД
| Модель | Таблица | Ключевые поля |
|---|---|---|
| `User` | `users` | `id` (chat_id, PK), `phone`, `name`, `role` (Enum) |
| `Initiative` | `initiatives` | `id`, `title`, `description`, `category` (Enum), `location`, `status` (Enum), `author_id` (FK), `created_at` |
| `Vote` | `votes` | `id`, `user_id` (FK), `initiative_id` (FK), `created_at`, `UniqueConstraint(user_id, initiative_id)` |

## E. Зависимости и конфигурация

### Управление зависимостями
- **`pyproject.toml`** — основной файл зависимостей (hatchling build-backend).
- **`uv.lock`** — lock-файл для `uv`.
- Основные зависимости: `sqlalchemy[asyncio]`, `asyncpg`, `python-dotenv`, `pydantic-settings`, `alembic`, `maxapi` (из git: `https://github.com/XaverD1992/max-botapi-python.git`).
- Опциональная группа `webhook`: `fastapi`, `uvicorn`.
- Dev-группа: `pytest`, `ruff`.

### Конфигурация
- **`.env`** — переменные окружения (`BOT_TOKEN`, `DB_URL`, `RUN_MODE`, `WEBHOOK_URL`, `ADMIN_USER_IDS`, `LOG_LEVEL`).
- **`alembic.ini`** — конфиг Alembic.
- **`Dockerfile`** / **`docker-compose.yml`** — развёртывание через Docker.

## F. Специфические особенности

### CLI-аргументы / Команды бота
| Команда | Описание |
|---|---|
| `/start` | Регистрация, привязка телефона |
| `/idea` | Многошаговый диалог подачи инициативы |
| `/list` | Показ одобренных инициатив |
| `/vote [id]` | Голосование за инициативу |
| `/set_role <id> <role>` | Назначение роли (админ) |
| `/test_idea` | Создание тестовой инициативы + уведомление модераторов (debug) |

### Паттерны и соглашения
- **FSM через MemoryContext** — состояние диалога хранится в памяти (не персистентно). При перезапуске бота контекст теряется.
- **Единый обработчик callback** — `handlers/callback.py:handle_callback` маршрутизирует по префиксу payload (`mod_approve:`, `cat_select:`, `idea_confirm:`, `cmd_back`).
- **Валидация телефона** — строгий regex `^\+7\d{10}$` в `handlers/start.py:57` и в `main.py:142`.
- **Ролевая модель** — проверка роли в каждом хендлере перед выполнением действий модератора/админа. `ADMIN_USER_IDS` — белый список из `.env` для `/set_role`.
- **Асинхронный контекстный менеджер сессии** — `database/session.py:get_db` с `commit/rollback/close`.
- **Логирование** — единый логгер `src.logging_config.logger`, вывод в stdout + `bot.log`, подавление шумных логов `asyncpg` и `sqlalchemy.engine`.
- **Уведомления** — `services/notification.py` отправляет всем модераторам (broadcast) при создании инициативы; ошибки отправки одному пользователю не прерывают рассылку остальным.
- **Alembic миграции** — единая миграция `36cc78853d5b` создаёт все три таблицы. Запуск через docker-entrypoint перед стартом бота.
- **Неочевидное**: `handlers/callback.py` содержит две логические ветки — approve (сразу меняет статус) и reject (переводит FSM в `WAITING_REJECT_REASON`, причина вводится текстом в следующем сообщении). При approve модератору отправляется подтверждение, автору — отдельное уведомление. При reject причина ограничена 500 символами.

## Машинно-ориентированный блок (YAML)

```yaml
project_type: cli_tool
primary_language: Python 3.11
entrypoint: src/main.py::main()
core_files:
  - src/main.py
  - src/config.py
  - src/database/session.py
  - src/database/crud.py
  - src/models/user.py
  - src/models/initiative.py
  - src/models/vote.py
  - src/handlers/start.py
  - src/handlers/idea.py
  - src/handlers/callback.py
  - src/handlers/moderation.py
  - src/handlers/vote.py
  - src/handlers/list.py
  - src/handlers/admin.py
  - src/bot/states.py
  - src/bot/keyboards.py
  - src/services/notification.py
dependencies_file: pyproject.toml
config_sources:
  - .env
  - src/config.py (pydantic-settings)
  - alembic.ini
  - docker-compose.yml
conventions:
  - FSM states defined in src/bot/states.py as StatesGroup subclasses
  - Callback payloads use "prefix:payload" format (mod_approve:, cat_select:, idea_confirm:, cmd_back)
  - Phone regex: ^\+7\d{10}$
  - Database access via async_session_factory context manager
  - All handlers are async functions receiving (event, db, context)
  - User chat_id used as primary key (BigInteger)
  - Role checks via UserRole enum comparison before moderator/admin actions
  - Logging via src.logging_config.logger with structured prefix tags like [idea], [list], [main]
  - Alembic migrations run automatically in docker-entrypoint.sh before bot start
```
