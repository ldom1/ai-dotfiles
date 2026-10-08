"""check-ci-runner-drift.sh reports a newer ubuntu24 runner release and never edits the manifest."""
import os
import stat
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "check-ci-runner-drift.sh"


def run(tmp_path, latest):
    gh = tmp_path / "gh"
    gh.write_text(f"#!/usr/bin/env bash\necho '{latest}'\n")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    before = (REPO / "docker" / "ci-runner.manifest").read_text()
    r = subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True,
                       env={**os.environ, "LOCAL_CI_GH": str(gh), "LOCAL_CI_HOME": str(tmp_path)})
    assert (REPO / "docker" / "ci-runner.manifest").read_text() == before
    return r.stdout


def test_newer_release_is_reported(tmp_path):
    assert "latest ubuntu24 release is ubuntu24/20261011.330" in run(tmp_path, "ubuntu24/20261011.330")


def test_same_release_prints_nothing(tmp_path):
    assert run(tmp_path, "ubuntu24/20261004.327") == ""
