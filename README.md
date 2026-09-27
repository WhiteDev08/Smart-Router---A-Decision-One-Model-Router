# JEV Router

A small task-routing pipeline that classifies an incoming question before generating an answer, so the "thinking about what to do" step is as fast and cheap as possible, before the "actually do it" step runs.

The flow is a simple two-stage pipeline:

1. **Route** — [JEV](#what-is-jev) looks at the question and decides which category it belongs to: `coding`, `general_query`, or `summarization`.
2. **Generate** — Based on the winning category, a tailored prompt is sent to Gemini (via LangChain) to actually produce the answer.

The user's state (question, chosen genre, JEV scores, final answer) is persisted in MongoDB between the two steps, keyed by `user_id`, so routing and generation can happen as two independent API calls.

## Why route at all?

Instead of sending every question to one generic prompt, JEV first figures out *what kind* of question it is, so the generation step can use a prompt that's actually written for that kind of task (see `src/prompts.py`) — a coding question gets a prompt tuned for producing code with explanations, a summarization request gets a prompt tuned for condensing content faithfully, and so on. Classifying first and generating second keeps each generation prompt focused, instead of one bloated do-everything prompt.

## What is JEV?

**JEV** is a decision model built by **typesafe**, used here purely for classification/routing — not for generating the final answer. It's designed to make routing decisions extremely fast, which matters because it sits in the critical path of every single request: every question has to pass through JEV before generation can even begin.

In this project, JEV is called via OpenRouter's decisions API (`https://openrouter.ai/api/alpha/decisions`, model `typesafe/jev-1.13`). It's given the user's message plus three yes/no-style questions ("how strongly is this related to coding?", "...a general query?", "...summarization?"), and it returns a numerical strength score (`noul`) for each one. The category with the highest score is picked as the `genre`.

The API response's `jev_time` field (returned by `/route_state`) is exactly this: how long that classification call took, measured with `time.perf_counter()`. It's surfaced in the UI because keeping this number low is the whole point — JEV is meant to be a lightweight gate, not a bottleneck before the real (and much slower) generation step.

## Architecture

```
Browser (frontend/web.html)
        │
        │ POST /route_state  { user_id, ques }
        ▼
FastAPI (src/main.py)
        │
        │ classify_question()  →  JEV (OpenRouter)
        ▼
   genre + scores + jev_time
        │
        │ saved to MongoDB (src/database.py)
        │
        │ POST /generate?user_id=...
        ▼
FastAPI loads saved state, picks a prompt (src/prompts.py)
based on genre, calls Gemini via LangChain (src/models.py)
        ▼
   Markdown answer  →  rendered in the browser
```

### Backend (`ai_task_router/src`)

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app. Exposes `POST /route_state` (runs JEV, stores the result) and `POST /generate` (loads the stored state, calls the matching Gemini prompt). |
| `jev.py` | Talks to the JEV model on OpenRouter and returns per-category scores. |
| `models.py` | Wraps `gemini-2.5-flash` (via `langchain.chat_models.init_chat_model`) with three async helper functions, one per genre. |
| `prompts.py` | The three genre-specific prompt templates (coding / general query / summarization) that shape how Gemini responds. |
| `database.py` | Async MongoDB access (`pymongo`'s `AsyncMongoClient`) — upserts a `user_states` document per `user_id`. |

### Frontend (`ai_task_router/frontend/web.html`)

A single static HTML page (no build step) with a retro black/pixel-CRT theme. It:

1. Takes a `user_id` and a question.
2. Calls `/route_state`, then displays the chosen genre, the JEV per-category scores as bars, and the JEV routing time.
3. Calls `/generate`, then renders the Markdown answer (via `marked`, sanitized with `DOMPurify`).

## Prerequisites

- Python 3.12+
- A MongoDB instance (local or Atlas) reachable via a connection string
- An OpenRouter API key with access to `typesafe/jev-1.13`
- A Google API key with access to Gemini (`gemini-2.5-flash`)

## Setup

1. **Install dependencies**

   ```bash
   cd ai_task_router
   pip install -r requirements.txt
   ```

2. **Configure environment variables**

   Create a `.env` file in `ai_task_router/` with:

   ```env
   OPENROUTER_API_KEY=your_openrouter_key
   GOOGLE_API_KEY=your_google_genai_key
   MONGO_URI=your_mongodb_connection_string
   ```

3. **Run the backend**

   From the `ai_task_router` directory:

   ```bash
   uvicorn src.main:app --reload --port 8000
   ```

   The API will be live at `http://localhost:8000`. A health check is available at `GET /`.

4. **Open the frontend**

   Open `frontend/web.html` directly in a browser (it talks to `http://localhost:8000`, so no separate frontend server is required). Enter a user ID and a question, and hit **Route & Generate**.

## API reference

### `POST /route_state`

```json
{
  "user_id": "9292",
  "ques": "What's FastAPI? Explain with a code snippet."
}
```

Returns:

```json
{
  "genre": "coding",
  "jev_output": {
    "coding": 0.91,
    "general_query": 0.06,
    "summarization": 0.03
  },
  "jev_time": 0.184
}
```

### `POST /generate?user_id=9292`

Uses the state saved by the previous call to pick the right prompt and generate the answer.

```json
{
  "answer": "## FastAPI\n\nFastAPI is a modern, high-performance web framework...",
  "message": "Answer inserted successfully!"
}
```

## Notes

- `/generate` depends on `/route_state` having been called first for that `user_id` — it reads the previously saved `genre`/`ques` from MongoDB rather than taking a fresh question as input.
- CORS is wide open (`allow_origins=["*"]`) for local development convenience; tighten this before deploying anywhere public.
