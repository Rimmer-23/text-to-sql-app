# Text-to-SQL App

Загрузите CSV / Excel, задайте вопрос обычным текстом — приложение сгенерирует SQL и покажет результат.

## Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows; на Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Тесты: `pytest`

Подробности архитектуры — в [CLAUDE.md](CLAUDE.md).
