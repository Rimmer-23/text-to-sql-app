# Text-to-SQL App

Upload CSV / Excel files, ask a question in plain English, and the app generates the SQL and shows the result.

## Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows; on Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # then set AI_API_KEY and AI_MODEL
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

Tests: `pytest`

Architecture details are in [CLAUDE.md](CLAUDE.md).
