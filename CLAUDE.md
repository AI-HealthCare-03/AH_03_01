# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AI-driven chronic-disease (hypertension/diabetes) lifestyle-challenge web service. Two Python services share one repo and one `pyproject.toml`:

- **`app/`** — FastAPI HTTP server (auth, users, business logic). Async, Tortoise ORM on MySQL.
- **`ai_worker/`** — separate process for ML inference/training (PyTorch, scikit-learn, sentence-transformers). Currently scaffolded; tasks live under `ai_worker/tasks/`.

Both run together via `docker-compose.yml` with MySQL, Redis, and Nginx (reverse proxy on `:80` → `fastapi:8000`).

## Commands

Dependencies are managed by **uv**; Python 3.13+ required. The `.env` symlink points to `envs/.local.env`.

```bash
# Install deps (dependency groups: app, ai, dev)
uv sync                       # everything
uv sync --group app           # API server only
uv sync --group ai            # AI worker only

# Run locally
uv run uvicorn app.main:app --reload          # FastAPI (docs at /api/docs)
uv run python -m ai_worker.main               # AI worker

# Full stack
docker-compose up -d --build

# Quality gates (also run in CI – .github/workflows/checks.yml)
./scripts/ci/code_fommatting.sh   # ruff check --fix + ruff format
./scripts/ci/check_mypy.sh        # mypy .
./scripts/ci/run_test.sh          # pytest + coverage; REQUIRES running mysql container

# Single test
uv run pytest app/tests/auth_apis/test_login_api.py::test_name -v

# DB migrations (aerich, config in pyproject.toml [tool.aerich])
uv run aerich migrate
uv run aerich upgrade
```

`run_test.sh` grants privileges inside the `mysql` Docker container before running pytest — tests will not work without `docker compose up mysql` first.

## Architecture notes

**FastAPI app layering** (`app/`):
- `apis/v1/` — routers; new routers must be registered in `apis/v1/__init__.py` under the `v1_routers` `APIRouter(prefix="/api/v1")`.
- `services/` — business logic, called from routers.
- `repositories/` — DB access via Tortoise models.
- `models/` — Tortoise ORM models. **New model files must be appended to `TORTOISE_APP_MODELS` in `app/core/db/databases.py`** or they won't be registered or migrated.
- `dtos/` — Pydantic request/response schemas.
- `dependencies/` — FastAPI `Depends` providers (e.g. `security.py` for auth).
- `core/` — cross-cutting: `config.py` (pydantic-settings, reads `.env`), `db/`, `jwt/` (custom token backend wrapping PyJWT, see `core/jwt/backends.py` + `tokens.py`), `utils/`, `validators/`.

**Config**: `app/core/config.py` exposes settings as module-level attributes via a `Config()` instance — import as `from app.core import config; config.DB_HOST`. Same pattern in `ai_worker/core/config.py`.

**Migrations**: aerich config lives in `pyproject.toml`; migration files in `app/core/db/migrations/models/`. The `db/migrations/*` path is ALL-ignored by ruff (`per-file-ignores`).

**Tests**: `app/tests/conftest.py` uses Tortoise's test initializer against a `test` database on the same MySQL instance — it patches `getDBConfig`. `asyncio_mode = "auto"`, session-scoped event loop. Test files mirror the API tree: `app/tests/auth_apis/`, `app/tests/user_apis/`.

**Lint/format**: ruff with line-length 120, target `py312`; selects E/W/F/I/C90/B/UP/N. `UP046` and `E501` are globally ignored. `__init__.py` ignores `F401` (re-exports allowed).

## Conventions observed

- Commit messages follow gitmoji + Korean style (see `.github/commit_template.txt` and recent log). Mixed Korean/English is normal.
- The two Dockerfiles (`app/Dockerfile`, `ai_worker/Dockerfile`) are built from the **project root** as context — paths in them are relative to repo root, not the service dir.
- `envs/.local.env` is the active env (symlinked to `.env`). `envs/.prod.env` is for the `scripts/deployment.sh` EC2 flow.

## Change scope discipline

When the user gives an instruction, preserve the existing codebase as much as possible and modify **only** what is strictly required to fulfill that instruction. Avoid sweeping rewrites.

Rules:
- **Minimal diff**: change the smallest set of lines/files needed. Do not reformat, rename, reorder imports, or "clean up" surrounding code that is unrelated to the request.
- **No opportunistic refactors**: do not refactor, restructure folders, extract helpers, or introduce abstractions unless the user explicitly asked for it.
- **No style churn**: do not rewrite working code into a different but equivalent style (e.g. swapping `if/else` chains for match, switching loop styles, re-ordering function arguments).
- **No incidental dependency / config changes**: do not bump versions, add packages, edit `pyproject.toml`, `docker-compose.yml`, CI configs, or env files unless the task requires it.
- **Preserve public surface**: keep existing function signatures, class names, route paths, DB column names, and response schemas unless the change is the point of the task.
- **Edit, don't rewrite**: prefer `Edit` over `Write`. Never overwrite a whole file when a localized edit suffices.
- **Touch only relevant files**: if a task is about file A, do not also modify file B "while you're at it." If you discover a separate issue, surface it to the user instead of silently fixing it.
- **Same applies to sub-agents**: when delegating, instruct each agent to follow this minimal-diff rule and to limit edits to the files/areas specified.

If a wider change genuinely seems necessary (e.g. the requested change cannot be done without touching adjacent code), explain why and get user confirmation **before** making the broader edit.

## Agent team orchestration

This project ships with 10 specialized sub-agents. When the user gives a work instruction, you MUST:

1. **Assemble a task-fit team** — pick only the agents whose domain is actually required by the request. Do NOT spawn agents whose role is unrelated to the task (e.g. don't spawn the pet-game agent for an auth API task, don't spawn the ML agent when there's no prediction involvement).
2. **Run the selected agents in parallel** — issue all selected `Agent` tool calls in a single message (multiple tool-use blocks in one assistant turn), not sequentially, unless there is a real data dependency between them.
3. **Never spawn the full roster by default** — unused roles must be omitted. Briefly state which agents you selected and why before launching them.

Available specialized agents and their trigger conditions:

| Agent | Use when the task involves… |
|---|---|
| `requirements-organizer` | Raw ideas, meeting notes, or feature requests that need to be turned into structured requirements / user scenarios / MVP scope. |
| `api-contract-designer` | Designing or documenting REST API contracts (endpoints, request/response schemas, auth, pagination) **before** implementation. |
| `db-schema-architect` | Designing/modifying Tortoise models, tables, relationships, indexes, constraints, or planning migration order. |
| `fastapi-backend-implementer` | Writing FastAPI router/service/repository/model/dto/dependency code from an already-defined spec. |
| `frontend-ui-architect` | UI/UX design, React/Next.js components, frontend API integration, state management, forms/validation. |
| `ml-prediction-integrator` | Contract between `app/` and `ai_worker/` (model I/O, feature mapping, prediction persistence, failure handling, result messaging). |
| `pet-game-designer` | Pet-raising gamification: growth logic, rewards, pet APIs/screens/models. **Pet feature only.** |
| `security-stability-reviewer` | Reviewing code for security vulnerabilities and stability (auth, permissions, file upload, PII/PHI, reward/transaction logic). |
| `qa-test-designer` | Designing QA test scenarios, API/flow test cases, edge cases, regression checklists. |
| `chronic-disease-docs-writer` | Writing/updating README, API docs, setup guides, troubleshooting, or portfolio/presentation materials. |

Selection rules:
- If the request is a pure question, code lookup, or trivial edit, do NOT spawn any agent — handle inline.
- Reuse agent outputs across the team rather than asking multiple agents to redo the same analysis.
- After the parallel team returns, synthesize results yourself; do not delegate synthesis.
