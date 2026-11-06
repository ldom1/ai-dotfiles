# Local CI

Run the GitHub workflows of a repo on your machine before you push. Back to the [README](../README.md).

Run a repo's GitHub workflows locally with `act`, in a clean clone of one commit.

```bash
bash scripts/install-act.sh
bash scripts/build-ci-runner.sh
bin/local-ci install --repo <path> --workflows ci.yml
bin/local-ci run --repo <path> --ref refs/heads/<branch> --record-baseline <sha>
bin/local-ci run --event pull_request --pr <N>
```

First run: record the skip baseline once, after a parity check against the GitHub run of `<sha>`. The baseline key is `<workflow>/<job>@<ref>`. One `--record-baseline` on any feature branch also writes `<workflow>/<job>@branch`, which covers all feature branches. Deploy branches (`local-ci.deploy-branches`, default `main preprod`) and pull requests need their own baseline. A `pull_request` run uses the key `<workflow>/<job>@pull_request`: record it once with `--event pull_request --pr <N> --record-baseline`. The lookup order is `@<ref>`, then `@branch` (feature-branch push runs only), then a key without `@<ref>`. Until a baseline matches, the run fails with "no skip baseline". A push run always needs `--ref`; the `pre-push` hook passes it.

The job gets an empty `GITHUB_TOKEN`: your `gh` token never reaches the workflow. Logs are in `~/.cache/local-ci/<owner>__<repo>/<sha>-<ref>-<event>-<tier>/`, with `/` in the ref replaced by `_`.

The merge guard is off until `git config local-ci.guard true`. In every directory, it denies a `gh pr merge` with `-R`, `GH_REPO`, `cd`, `env -C` or a PR URL for another repo, and a merge through `gh api`. A command made only of data commands (`grep`, `echo`, `cat > file <<'EOF'`, `gh pr view|edit|create`, `git commit -m`) passes, even when it names a merge as text. Run such a command in its own Bash call: one non-data command in the line brings back the full check.
