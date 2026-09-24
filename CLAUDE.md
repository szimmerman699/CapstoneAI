# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Meeting-to-workflow builder: reads Fathom meeting transcripts and is meant to auto-deploy Make scenarios, MailerLite lists, and WordPress plugins/webhooks. Currently at an early capstone/lab stage — the FastAPI server and `AIClient` wrapper around the Anthropic SDK are built; the transcript extraction/build-planning/payload-generation pipeline described in [docs/model-selection.md](docs/model-selection.md) is not yet implemented (`src/capstone_ai/rag/` is a stub).

## Commands

```bash
# Install deps (base only)
uv sync --locked

# Install deps including the FastAPI server extra (fastapi, uvicorn, etc.)
uv sync --locked --extra server

# Run the API server
uv run uvicorn capstone_ai.api.main:app --reload

# Run all tests
uv run pytest

# Run a single test
uv run pytest tests/unit/test_setup.py::test_own_package_is_installed

# Lint
uv run ruff check .
```

The `server` group (fastapi, uvicorn, watchfiles, websockets, ...) is declared under `[project.optional-dependencies].server` in [pyproject.toml](pyproject.toml), not in the base `dependencies` list — `uv sync --locked` alone will not install it. If `uvicorn` or `fastapi` imports are missing, re-sync with `--extra server`.

On Windows, if `uv sync` fails with a file-in-use error on `uvicorn.exe`/`watchfiles`/`websockets`, a running `uvicorn` dev server process is holding the venv's `Scripts/` files open — stop it before re-syncing.

## Architecture

- **src layout**: the package is `capstone_ai`, installed in editable mode via `uv`; tests import it as an installed package, not via `sys.path` tricks (see `test_own_package_is_installed` in [tests/unit/test_setup.py](tests/unit/test_setup.py)).
- **`core/ai_client.py`**: the single wrapper around `anthropic.AsyncAnthropic`. All Claude calls in the app should go through `AIClient`, not construct their own Anthropic client. It exposes several call shapes on top of one underlying client instance:
  - `message` / `stream_message` — plain text in/out (streaming and non-streaming)
  - `conversation` — raw multi-turn `Message` passthrough
  - `tool_conversation` — hand-rolled agentic tool-use loop (loops while `stop_reason == "tool_use"`, dispatching to a `tool_handler` dict of `name -> async fn`, capped by `max_tool_rounds`)
  - `extract_structured` — forces a single tool call and validates the result into a given Pydantic model (used for structured extraction, e.g. `MeetingSummary`)
- **`core/config.py`**: single `Settings` (pydantic-settings) instance loaded from `.env`, exported as the module-level `settings` singleton. `model_name` defaults to `claude-sonnet-5`.
- **`core/prompt_loader.py`**: loads system prompts by filename from `src/capstone_ai/prompts/`.
- **`core/http_client.py` / `core/retry.py`**: generic async HTTP helpers (`AsyncHTTPClient`, `with_retry`) for calling non-Anthropic APIs (Make, MailerLite, WordPress, etc.) with bounded concurrency (semaphore) and retry/backoff on 429/5xx — independent of `AIClient`, for the downstream platform-integration work.
- **`api/main.py`**: the FastAPI app.
  - `AIClient` is created once in the `lifespan` context manager and stored on `app.state.ai_client` — not constructed per-request — so the underlying `httpx`/Anthropic connection pool is reused across requests.
  - Routes (`/health`, `/chat`, `/chat/stream`, `/chat/tools`) are all API-key gated via `Depends(verify_api_key)` except `/health`; the dev API key is hardcoded (`dev-key-change-in-production`) and must be replaced before any real deployment.
  - `/chat/stream` returns SSE (`text/event-stream`) with `Cache-Control: no-cache` — required so intermediary proxies/browsers don't buffer the stream.
  - `RequestLoggingMiddleware` and `CORSMiddleware` are registered on `app`; CORS currently allows all origins/methods/headers (`"*"`) and is flagged in-code to restrict before production.
  - Anthropic `APIError` is caught via a dedicated `@app.exception_handler` and turned into a structured 502 `ErrorResponse`.
- **`api/models.py`**: request/response Pydantic models (`ChatRequest`, `ChatResponse`, `ToolRequest`, `ErrorResponse`).
- **`data/documents/`**: local storage for source meeting transcripts/notes (Fathom exports, roadmap docs) used as pipeline input.
- **Model selection**: task-to-model routing decisions (which Claude/other model for extraction vs. build planning vs. payload generation vs. error recovery vs. verification) are documented with experimental rationale in [docs/model-selection.md](docs/model-selection.md) — read this before wiring up new pipeline stages, since it encodes deliberate cost/quality tradeoffs per task, not arbitrary defaults.

## Tests

`tests/` is split into `unit/`, `integration/`, and `eval/` (eval currently empty/stubbed). `pytest` is configured with `asyncio_mode = "auto"` in [pyproject.toml](pyproject.toml), so `async def test_*` functions run without extra decorators.

## RAG stack decisions

- **Anthropic SDK** for generation (via `AIClient`, see above).
- **Chroma** for local/dev vector storage, **Pinecone** for production — `pinecone_api_key` is already present on `Settings` in [config.py](src/capstone_ai/core/config.py) for this.
- **LangChain** for document loading (splitting/loading transcripts and notes out of `data/documents/` ahead of embedding).

## Quality rules

- Always validate retrieval results before passing them to generation.
- Every pipeline stage (load, chunk, embed, retrieve, generate) must be independently testable.
- Log chunk counts and token usage at each stage.

## Constraints

- Do not hardcode API keys — load them through `Settings`/`.env`, following the existing `anthropic_api_key` / `pinecone_api_key` pattern.
- Do not skip the embedding step by passing raw text to the LLM.

## Production Constraints

- **Deployment:** Docker container deployed to AWS ECS. Environment variables injected at runtime.
- **Secrets management:** Never hardcode API keys, tokens, or credentials. Load from environment variables via `python-dotenv`. Never commit `.env` files—use `.env.example` as template.
- **API integrations:** All external API calls must have timeout (30s default), retry logic (3 attempts), and explicit error handling. Log failures with request/response data (no sensitive values).
- **File uploads:** Limit document file size to 50MB. Validate MIME types against whitelist (application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, text/plain). Scan for malicious content before processing.
- **Logging in production:** Use structured logging (structlog). Include request IDs and correlation IDs for traceability. Never log PII (personal identifiable information) or sensitive document content.

## Read These Files

- @constraints.md
