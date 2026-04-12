---
name: fix launch detection
overview: Fix project launch detection by replacing the current URL-only probe with a backend launch-status resolver, add a `Build & Launch` path for buildable apps, verify the updated workspace `projects_root` at `/home/lgiron/lab/projects` is honored for launch resolution, and remove GitNexus references from the repo and generated project artifacts.
todos:
  - id: repo-cleanup-scope
    content: Remove GitNexus references from repo docs/config and generated `graphify-out/` artifacts.
    status: completed
  - id: projects-root-verification
    content: Verify the workspace `projects_root` change to `/home/lgiron/lab/projects` is used as the source of truth for launch resolution and build detection.
    status: pending
  - id: backend-launch-status
    content: Add launch-status and build helpers in the Kanban API using repo_path/filesystem as source of truth.
    status: in_progress
  - id: hub-project-cta
    content: Update the project page CTA to use launch status and support Build & Launch.
    status: pending
  - id: tests-launch-flow
    content: Add focused backend and Playwright coverage for launchable, buildable, and missing project states.
    status: in_progress
  - id: docs-sync
    content: Update CHANGELOG, docs/PITFALLS, and required Local Brain notes after implementation.
    status: pending
isProject: false
---

# Fix Launch Detection And Remove GitNexus

## Root Cause
- `hub/src/main.js` currently decides launchability by calling `fetch('/apps/<slug>/', { method: 'HEAD' })` inside `wireProjectPage()`.
- `hub/nginx.conf` serves `/apps/<slug>/` via `try_files $uri $uri/dist/index.html $uri/index.html @app_not_found;`, so a missing app can still resolve to the placeholder page rather than reflecting real project state.
- The launch URL is hardcoded from the project `slug`, while the backend already knows the real `repo_path`; if metadata `slug` drifts from the repo directory basename, the hub can point at the wrong `/apps/...` folder.
- The launch fix must be validated against the updated workspace setting where the projects root is now `/home/lgiron/lab/projects`, so project discovery and launch resolution both read from the expected directory.
- GitNexus is still documented as a required project workflow in repo-owned files like `AGENTS.md`, `CLAUDE.md`, `docs/CLAUDE-REFERENCE.md`, `docs/README.md`, `.gitignore`, and is then re-exported into generated `graphify-out/` artifacts.

## Files To Modify
- [AGENTS.md](AGENTS.md)
  - Remove the GitNexus guidance block entirely.
- [CLAUDE.md](CLAUDE.md)
  - Remove the GitNexus section and the pointer to `AGENTS.md`.
- [docs/CLAUDE-REFERENCE.md](docs/CLAUDE-REFERENCE.md)
  - Remove the remaining GitNexus references from the agent guidance index.
- [docs/README.md](docs/README.md)
  - Remove GitNexus from the documentation summary.
- [.gitignore](.gitignore)
  - Remove the `.gitnexus` ignore entry if GitNexus is being removed from the project entirely.
- [graphify-out](graphify-out)
  - Remove or regenerate generated graph artifacts that currently embed GitNexus nodes extracted from repo docs.
- [hub/src/main.js](hub/src/main.js)
  - Replace the current `HEAD /apps/<slug>/` probe with an API-backed launch-state fetch.
  - Render the project CTA from explicit states: `launchable`, `buildable`, `missing`.
- [kanban/kanban_api/core.py](kanban/kanban_api/core.py)
  - Add a launch-status resolver that inspects `repo_path`, the repo directory name, and deployable artifacts like `dist/index.html` or `index.html`.
  - Add a build helper for static/buildable projects only, derived from existing metadata/filesystem (`template`, `package.json`, build script), without changing the registry schema.
  - Normalize the served app path from the real repo directory basename so slug/dirname drift does not break launch routing.
  - Confirm the resolver uses the effective workspace `projects_root`, including the updated `/home/lgiron/lab/projects` setting.
- [kanban/kanban_api/api.py](kanban/kanban_api/api.py)
  - Expose `GET /hub/projects/{project_slug}/launch-status`.
  - Expose `POST /hub/projects/{project_slug}/build-launch` to trigger a build when the project is present but not yet deployed.
- [tests/playwright/tests/personas/projects.spec.ts](tests/playwright/tests/personas/projects.spec.ts) or a dedicated new persona spec
  - Cover: existing deployed app launches, present-but-not-built app shows `Build & Launch`, genuinely absent app still shows the fallback state.
- [kanban/tests](kanban/tests)
  - Add a focused unit test for the launch-status resolver so slug-vs-dir and dist-vs-index cases are locked down.
- [CHANGELOG.md](CHANGELOG.md)
  - Document the launch-state fix and new `Build & Launch` behavior.
- [docs/PITFALLS.md](docs/PITFALLS.md)
  - Add the deployment-detection pitfall and the corrected source of truth.
- [CHANGELOG.md](CHANGELOG.md)
  - Document both the launch-state fix and the GitNexus removal.

## Implementation Steps
1. Remove GitNexus from the repo surface
- Delete the GitNexus workflow block from `AGENTS.md`.
- Remove all GitNexus mentions from `CLAUDE.md`, `docs/CLAUDE-REFERENCE.md`, and `docs/README.md`.
- Drop `.gitnexus` from `.gitignore` if no remaining project-owned files depend on it.
- Clean `graphify-out/` so generated graphs no longer publish GitNexus-derived nodes sourced from repo docs.

2. Backend launch-state source of truth
- Implement a helper in `kanban/kanban_api/core.py` that returns, for one project:
  - canonical app path basename from `Path(repo_path).name`
  - whether the repo exists on disk
  - whether `dist/index.html` or `index.html` exists
  - whether the project is buildable from existing metadata/files (`package.json` with `build`, supported template)
  - the public launch URL to use
- Treat brain-only projects or projects with no repo path as genuinely non-launchable.
- Validate the helper against the effective workspace configuration where `projects_root` has been changed to `/home/lgiron/lab/projects`.

3. Optional build path
- Add a minimal build executor in `kanban/kanban_api/core.py` for buildable static apps only.
- Prefer filesystem-derived commands over schema changes:
  - Vite/static Node apps: install deps if needed, then `npm run build`
  - Do not try to auto-build templates that are not served by `/apps/<slug>/` under current nginx semantics.
- Return structured status so the UI can immediately open the launched app after success.

4. Hub UI behavior
- In `hub/src/main.js`, fetch project details plus the new launch status in `wireProjectPage()`.
- Replace the current hidden/visible button logic with three clear states:
  - `Launch Project` when deployable artifact already exists
  - `Build & Launch` when the repo is present/buildable but not yet deployed
  - existing unavailable/error copy only when the project is genuinely absent or unsupported
- Preserve all existing non-project routes and navigation (`/memory`, `/kanban`, `/chat`, `/settings`, etc.).

5. Verification
- Verify there are no remaining `gitnexus` references in tracked repo files, including `graphify-out/`.
- Verify project discovery and launch-state resolution with `projects_root = /home/lgiron/lab/projects`, confirming the hub resolves launchable/buildable apps from that directory rather than a stale or hardcoded path.
- Add a backend unit test for launch-state resolution.
- Add/update one Playwright persona flow for project page CTA behavior.
- Run the existing hub and kanban checks relevant to touched files.

## Notes
- Prefer the backend resolver over nginx `HEAD` probing; it is the only place that has both `repo_path` and filesystem access.
- Keep the existing `App not deployed` fallback page for genuinely missing apps; the fix is to stop routing buildable/local projects into that state prematurely.
- `graphify-out/` is not the source of truth for GitNexus references here; it mirrors repo documentation, so cleaning source files first prevents regeneration of the same stale context.