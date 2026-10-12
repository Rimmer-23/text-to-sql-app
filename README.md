# Text-to-SQL App

Upload CSV / Excel files, ask a question in plain English, and the app generates the SQL and shows the result.

## Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows; on Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # then set AI_API_KEY (see "AI setup" below)
uvicorn app.main:app --reload --port 8000
```

Run `uvicorn` from `backend/`: that is where it looks for `.env`. Restart it after editing `.env`.

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

## AI setup (Gemini)

1. Create an API key in [Google AI Studio](https://aistudio.google.com) (Get API key → Create API key).
2. Put it in `backend/.env`:

   ```
   AI_PROVIDER=gemini
   AI_MODEL=gemini-3.5-flash-lite
   AI_API_KEY=your-key
   ```

`gemini-3.5-flash-lite` is the recommended model: it is fast, answers the sample questions
(joins included) correctly, and its free tier allows 15 requests a minute and 500 a day.
Larger models can have much smaller free limits (Gemini 3.8 Flash: 5 a minute, 20 a day).
Current limits for your project are on the [Rate Limit](https://aistudio.google.com/rate-limit)
page in AI Studio; daily limits reset at midnight Pacific time.

Overloaded-model errors (503) are retried once; set `AI_MAX_ATTEMPTS` in `.env` to change that
(`1` disables retries). Failed requests count toward the quota too.

Never commit `.env`: it holds your key, and it is in `.gitignore`.

## Try it

[`sample-data/`](sample-data/) has three related CSV files and 12 questions with known answers.
Upload all three files at once, then compare the app's answers with the table in its README.
