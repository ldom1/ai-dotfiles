---
name: spendlens-openrouter-claude-panels
overview: Add OpenRouter and Claude integrations end-to-end (FastAPI routers, schemas, React panels, tests, and GitHub CI) following your literal path/prefix requirement.
todos:
  - id: backend-routers
    content: Create OpenRouter and Claude routers under backend/spendlens_api/routers and mount them in main.py with /SpendLens/api prefix
    status: completed
  - id: schemas-env
    content: Add required Pydantic schemas and update backend/.env.example variables
    status: completed
  - id: frontend-panels
    content: Implement OpenRouterPanel and ClaudePanel and wire into App integration flow
    status: completed
  - id: backend-tests
    content: Add backend tests for OpenRouter and Claude endpoints including graceful fallback scenarios
    status: completed
  - id: github-ci
    content: Add .github/workflows/ci.yml for backend lint/tests and frontend build checks
    status: completed
  - id: docs-update
    content: Update README.md and CHANGELOG.md to reflect new integrations and CI workflow
    status: completed
isProject: false
---

# Add OpenRouter & Claude Panels

## Scope
Implement two new integrations in SpendLens with backend proxying, frontend panels, tests, and GitHub Actions CI. Follow your selected convention: create `backend/spendlens_api/routers/*` and expose `/SpendLens/api/...` directly from FastAPI.

## Implementation Plan
- Backend API layer
  - Create new package files under `backend/spendlens_api/routers/`:
    - `openrouter.py` with `GET /openrouter`
    - `claude.py` with `GET /claude` and `GET /claude/audit`
  - Add robust env-based config handling and graceful fallbacks:
    - OpenRouter key via `OPENROUTER_API_KEY`
    - Claude audit paths via `CLAUDE_FINOPS_SKILL_PATH` and `CLAUDE_REPORT_PATH`
    - Audit endpoint never fails hard on missing files/permissions; returns `{ installed: false, report: null }`.
  - Wire both routers in `backend/spendlens_api/main.py` with a FastAPI prefix `/SpendLens/api` so endpoints become:
    - `/SpendLens/api/openrouter`
    - `/SpendLens/api/claude`
    - `/SpendLens/api/claude/audit`

- Backend schemas and env docs
  - Extend `backend/spendlens_api/schemas.py` with:
    - `OpenRouterUsage`, `OpenRouterModelStat`, `OpenRouterResponse`
    - `ClaudeUsageResponse`, `ClaudeAuditResponse`
  - Update `backend/.env.example` with the required OpenRouter/Anthropic/skill/report variables.

- Frontend components
  - Add `frontend/src/components/OpenRouterPanel.tsx`:
    - Fetch `/SpendLens/api/openrouter` on mount
    - Render balance, total usage USD, top models table, and loading/error/empty states
    - Match current modal/panel Tailwind patterns from existing panels.
  - Add `frontend/src/components/ClaudePanel.tsx`:
    - Parallel fetch of `/SpendLens/api/claude` and `/SpendLens/api/claude/audit`
    - Render usage summary + `finops-audit` block
    - If installed: show report in `<details>`
    - If not installed: show install callout text requested
    - Include loading/error/empty states.

- App integration (no layout redesign)
  - Update `frontend/src/App.tsx` to import and conditionally render new panels alongside existing integration panel handling.
  - Update `frontend/src/types.ts` and any integration-normalization logic (e.g. `frontend/src/ensureIntegrations.ts`) only as needed to support new integration keys without changing existing behavior.

- Tests
  - Add backend tests:
    - `backend/tests/test_openrouter.py`
    - `backend/tests/test_claude.py`
  - Cover success + graceful-failure paths (missing keys, upstream failure, missing audit directory/report, unreadable report).

- GitHub CI
  - Create `.github/workflows/ci.yml` with jobs for:
    - Backend: install deps, run lint (`ruff`) and tests (`pytest`)
    - Frontend: install deps and run build/typecheck (and lint if script exists)
  - Ensure workflow commands align with existing project tooling and lockfiles.

## Files To Touch
- Backend
  - `backend/spendlens_api/main.py`
  - `backend/spendlens_api/schemas.py`
  - `backend/spendlens_api/routers/openrouter.py` (new)
  - `backend/spendlens_api/routers/claude.py` (new)
  - `backend/.env.example`
  - `backend/tests/test_openrouter.py` (new)
  - `backend/tests/test_claude.py` (new)
- Frontend
  - `frontend/src/components/OpenRouterPanel.tsx` (new)
  - `frontend/src/components/ClaudePanel.tsx` (new)
  - `frontend/src/App.tsx`
  - `frontend/src/types.ts` (if integration union extension is required)
  - `frontend/src/ensureIntegrations.ts` (if defaults/normalization must include new integration keys)
- CI
  - `.github/workflows/ci.yml` (new)
- Docs hygiene
  - `README.md`
  - `CHANGELOG.md`

## Verification Plan
- Backend: run `pytest` and lint checks locally for changed backend files.
- Frontend: run build/typecheck to validate strict TypeScript for new panels.
- Endpoints sanity:
  - `/SpendLens/api/openrouter`
  - `/SpendLens/api/claude`
  - `/SpendLens/api/claude/audit`
- Confirm no API secrets are exposed in frontend or response payloads.