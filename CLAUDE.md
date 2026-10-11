# Text-to-SQL App

Веб-приложение: пользователь загружает свои файлы (CSV / Excel), затем пишет вопрос обычным текстом
("show the top 5 cities by total sales"), AI переводит вопрос в SQL, сервер выполняет его
и фронт показывает результат в универсальной таблице.

## Язык

- **Продукт полностью на английском**: интерфейс, сообщения об ошибках, промпт для AI, данные
  пользователей, вопросы пользователей, README, тестовые данные, коммиты.
- Разработчик общается с Claude по-русски — это только язык переписки, в продукт русский не попадает.

## Стек

- **Backend:** Python 3.11+, FastAPI, Uvicorn, Pydantic v2
- **Хранилище данных пользователя:** SQLite (один файл БД на workspace)
- **Парсинг файлов:** pandas, openpyxl
- **Проверка SQL:** sqlglot
- **AI:** через абстракцию провайдера (по умолчанию Gemini, легко заменить на OpenAI / Claude)
- **Frontend:** React + TypeScript + Vite
- **HTTP-клиент на фронте:** fetch (обёртка в `src/api/client.ts`)

## Ключевые понятия

- **Workspace** — набор данных пользователя. Внутри — своя SQLite БД.
  Авторизации пока нет: workspace идентифицируется по `workspace_id` (UUID).
  Авторизация планируется позже — не закладывать сложную логику, но держать `workspace_id` везде, где нужна изоляция данных.
- **Каждый загруженный файл = отдельная таблица** в БД workspace'а.
  Excel с несколькими листами → одна таблица на лист.
- **Схема** — список таблиц, колонок, типов и 3 примера строк. Строится на сервере после загрузки
  и передаётся AI в каждом запросе.

## Структура проекта

```
text-to-sql/
├── CLAUDE.md
├── README.md
├── .gitignore
├── backend/
│   ├── pyproject.toml          # или requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── main.py             # создание FastAPI app, CORS, подключение роутеров
│   │   ├── config.py           # настройки из env (pydantic-settings)
│   │   ├── api/
│   │   │   ├── workspaces.py   # создание workspace, список таблиц, схема
│   │   │   ├── files.py        # загрузка файлов
│   │   │   └── query.py        # вопрос → SQL → результат
│   │   ├── models/
│   │   │   └── schemas.py      # Pydantic-модели запросов/ответов
│   │   ├── services/
│   │   │   ├── workspace_service.py  # создание папки/БД workspace'а
│   │   │   ├── ingest_service.py     # CSV/Excel → pandas → SQLite
│   │   │   ├── schema_service.py     # извлечение схемы для промпта
│   │   │   ├── sql_guard.py          # валидация SQL (только SELECT)
│   │   │   └── query_service.py      # выполнение SQL, лимиты, таймаут
│   │   ├── ai/
│   │   │   ├── base.py         # интерфейс AIProvider.generate_sql(schema, question) -> str
│   │   │   ├── gemini.py
│   │   │   ├── openai_provider.py
│   │   │   ├── prompts.py      # шаблон промпта
│   │   │   └── factory.py      # выбор провайдера по AI_PROVIDER из env
│   │   └── utils/
│   │       └── naming.py       # нормализация имён таблиц и колонок
│   ├── data/                   # здесь лежат БД workspace'ов (в .gitignore)
│   └── tests/
│       ├── test_ingest.py
│       ├── test_sql_guard.py
│       └── test_query.py
└── frontend/
    ├── package.json
    ├── vite.config.ts          # proxy /api → http://localhost:8000
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── api/
        │   └── client.ts       # все вызовы бэкенда
        ├── types/
        │   └── index.ts        # типы ответов API
        ├── hooks/
        │   └── useWorkspace.ts # workspace_id в localStorage, загрузка схемы
        └── components/
            ├── FileUpload.tsx  # drag&drop, несколько файлов сразу
            ├── TableList.tsx   # список загруженных таблиц и их колонок
            ├── QueryInput.tsx  # поле ввода вопроса
            ├── SqlPreview.tsx  # показывает сгенерированный SQL
            └── ResultTable.tsx # универсальная таблица: колонки из ответа API
```

## API

| Метод | Путь | Описание |
|---|---|---|
| POST | `/api/workspaces` | Создать workspace → `{ workspace_id }` |
| POST | `/api/workspaces/{id}/files` | Загрузить один или несколько файлов (multipart) → список созданных таблиц |
| GET | `/api/workspaces/{id}/schema` | Таблицы, колонки, типы, число строк |
| DELETE | `/api/workspaces/{id}/tables/{table}` | Удалить таблицу |
| POST | `/api/workspaces/{id}/query` | `{ question }` → `{ sql, columns, rows, row_count, truncated }` |

Формат результата запроса — колонки отдельно от строк, чтобы порядок колонок был стабильным:

```json
{
  "sql": "SELECT city, SUM(amount) AS total FROM sales GROUP BY city ORDER BY total DESC LIMIT 5",
  "columns": ["city", "total"],
  "rows": [["Praha", 12000], ["Brno", 8000]],
  "row_count": 2,
  "truncated": false
}
```

Ошибки — единый формат: `{ "error": { "code": "...", "message": "..." } }`
Коды: `INVALID_FILE`, `SQL_NOT_ALLOWED`, `SQL_EXECUTION_ERROR`, `AI_ERROR`, `WORKSPACE_NOT_FOUND`.

## Загрузка файлов (ingest)

- Поддержка: `.csv`, `.xlsx`, `.xls`. Лимит размера — из env (`MAX_UPLOAD_MB`, по умолчанию 50).
- CSV: определять разделитель и кодировку (utf-8, затем cp1251 как fallback).
- Имя таблицы = имя файла, нормализованное: латиница/цифры/`_`, нижний регистр, не начинается с цифры.
  Если таблица с таким именем уже есть — добавить суффикс `_2`, `_3`.
- Имена колонок нормализовать так же. Оригинальные имена сохранять в служебной таблице `_columns_meta`
  (table, column, original_name) — чтобы фронт мог показывать исходные названия.
- Кириллицу в именах транслитерировать (например, через `unidecode`).
- Пустые колонки и полностью пустые строки отбрасывать.
- Пытаться привести типы: числа, даты (ISO-строки в SQLite).

## Генерация SQL

Промпт содержит:
1. Роль: эксперт по SQLite.
2. Схему: для каждой таблицы — колонки с типами + 3 примера строк + оригинальные имена колонок.
3. Правила: только SELECT, только существующие таблицы/колонки, всегда `LIMIT` (не больше 1000),
   использовать диалект SQLite.
4. Вопрос пользователя.
5. Формат ответа: только SQL, без markdown и пояснений.

После ответа AI: убрать ```` ```sql ```` обёртку, если она есть, затем — проверка через `sql_guard`.

Модель и провайдер — только через env (`AI_PROVIDER`, `AI_MODEL`, `AI_API_KEY`). Названия моделей в коде не хардкодить.

## Безопасность выполнения SQL (обязательно)

SQL от AI считается недоверенным вводом.
- `sql_guard` парсит запрос через `sqlglot`: разрешён ровно один statement, тип — SELECT (включая WITH ... SELECT).
  Запрещены: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, ATTACH, PRAGMA и т.п.
- Соединение для запросов пользователя открывается в режиме **read-only**: `sqlite3.connect(f"file:{path}?mode=ro", uri=True)`.
- Принудительный лимит строк (`MAX_RESULT_ROWS`, по умолчанию 1000): если в запросе нет LIMIT — добавить.
- Таймаут выполнения (через `conn.set_progress_handler`).
- Служебные таблицы (`_columns_meta` и любые с префиксом `_`) не показывать AI и не давать запрашивать.

## Фронтенд

- `workspace_id` хранится в localStorage; если его нет — создаётся при первой загрузке файла.
- `ResultTable` строит колонки из `columns` ответа — никакой генерации HTML через AI.
- Показывать сгенерированный SQL (свёрнуто по умолчанию) — для доверия и отладки.
- Состояния: загрузка, пустой результат, ошибка (показывать `message`).
- Длинные таблицы: простая клиентская пагинация.

## Окружение

`backend/.env.example`:
```
AI_PROVIDER=gemini
AI_MODEL=
AI_API_KEY=
AI_TIMEOUT_SECONDS=30
DATA_DIR=./data
MAX_UPLOAD_MB=50
MAX_RESULT_ROWS=1000
QUERY_TIMEOUT_SECONDS=5
CORS_ORIGINS=http://localhost:5173
```

Запуск:
- Backend: `cd backend && uvicorn app.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev`

## Порядок разработки (MVP)

1. Каркас backend: FastAPI, config, CORS, health-check `GET /api/health`.
2. Workspace + загрузка CSV → SQLite + `GET /schema`. Тесты на ingest.
3. `sql_guard` + выполнение запроса в read-only режиме. Тесты на guard (позитивные и вредоносные запросы).
4. AI-абстракция + один провайдер (Gemini) + endpoint `/query`.
5. Каркас frontend: загрузка файлов, список таблиц.
6. Ввод вопроса, `ResultTable`, `SqlPreview`, обработка ошибок.
7. Поддержка Excel (несколько листов).
8. Второй AI-провайдер, проверка переключения через env.

## Позже (не делать сейчас)

- Авторизация и привязка workspace'ов к пользователям
- История запросов
- Графики по результату (AI выбирает тип графика)
- Повторная попытка: если SQL упал с ошибкой — отправить ошибку обратно AI и попросить исправить (1 retry)
- Переход с SQLite на PostgreSQL / DuckDB при больших объёмах

## Соглашения

- Python: type hints везде, бизнес-логика в `services/`, роутеры тонкие.
- Форматирование: ruff + black (backend), eslint + prettier (frontend).
- Новый endpoint → Pydantic-модели в `models/schemas.py` + тип в `frontend/src/types`.
- Любое изменение в `sql_guard` — сопровождать тестом.
