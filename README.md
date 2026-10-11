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

## Frontend

Requires Node.js 22.22+ (or 24.15+). Start the backend first.

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173, /api is proxied to :8000
```

Checks: `npm test`, `npm run lint`, `npm run build`

Architecture details are in [CLAUDE.md](CLAUDE.md).
