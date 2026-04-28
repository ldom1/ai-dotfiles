---
name: Fix e2e container startup
overview: Stabilize GitLab e2e startup by preventing empty persistence directory handling and ensuring the e2e job passes the expected environment variable into the runtime container.
todos:
  - id: harden-entrypoint
    content: Add safe default/guard for HESABU_PERSISTENCE_DIR in docker entrypoint
    status: completed
  - id: pass-env-in-e2e-job
    content: Propagate HESABU_PERSISTENCE_DIR in test:e2e docker run environment
    status: completed
  - id: record-fix
    content: Document the CI/e2e startup fix in CHANGELOG.md
    status: completed
  - id: validate-startup
    content: Verify container startup and e2e CI progression after changes
    status: completed
isProject: false
---

# Fix GitLab E2E Startup Crash

## Diagnosis
The e2e job fails before tests execute because the runtime container exits during startup:
- Log evidence: `mkdir: cannot create directory ''` in `docker-entrypoint.sh`
- In [`docker/docker-entrypoint.sh`](/home/lgiron/acsg_coe_lab/coe-kpi-hesabu-server/docker/docker-entrypoint.sh), dynamic mode always runs:
  - `mkdir -p ... "$HESABU_PERSISTENCE_DIR"`
  - `chown -R ... "$HESABU_PERSISTENCE_DIR"`
- In [`/.gitlab-ci.yml`](/home/lgiron/acsg_coe_lab/coe-kpi-hesabu-server/.gitlab-ci.yml), `test:e2e` starts the app container without explicitly passing `HESABU_PERSISTENCE_DIR`, so the entrypoint can receive an empty value in this path.

## Implementation
- Update [`docker/docker-entrypoint.sh`](/home/lgiron/acsg_coe_lab/coe-kpi-hesabu-server/docker/docker-entrypoint.sh):
  - Normalize `HESABU_PERSISTENCE_DIR` with a safe default matching app behavior (same default as codebase constant).
  - Guard `mkdir/chown` so no empty path can be evaluated.
- Update [`/.gitlab-ci.yml`](/home/lgiron/acsg_coe_lab/coe-kpi-hesabu-server/.gitlab-ci.yml) in `test:e2e` docker run env block:
  - Add explicit `-e HESABU_PERSISTENCE_DIR` pass-through for consistency with other paths.
- Update [`CHANGELOG.md`](/home/lgiron/acsg_coe_lab/coe-kpi-hesabu-server/CHANGELOG.md):
  - Add a short entry about fixing e2e startup crash due to persistence dir handling.

## Verification
- Run targeted shell validation locally (or CI job replay) to confirm container no longer exits at startup:
  - Build e2e image.
  - Run container in dynamic mode without manually setting `HESABU_PERSISTENCE_DIR` and confirm entrypoint starts service instead of failing.
- Run `test:e2e` pipeline job and verify it reaches health check / test execution steps.
- Quick regression check: ensure runtime still honors explicit `HESABU_PERSISTENCE_DIR` when provided.