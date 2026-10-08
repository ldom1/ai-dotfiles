"""docker/ci-runner.manifest drives the Dockerfile build args and the build-time version checks."""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MANIFEST = REPO / "docker" / "ci-runner.manifest"
DOCKERFILE = REPO / "docker" / "ci-runner.Dockerfile"
BUILD = REPO / "scripts" / "build-ci-runner.sh"


def manifest():
    return dict(l.split("=", 1) for l in MANIFEST.read_text().splitlines() if l and not l.startswith("#"))


def test_manifest_pins_the_reference_runner_image():
    m = manifest()
    assert m["RUNNER_IMAGE_TAG"] == "ubuntu24/20261004.327"
    assert m == {"RUNNER_IMAGE_TAG": "ubuntu24/20261004.327", "NODE_VERSION": "22.23.3", "GIT_VERSION": "2.55.0",
                 "GIT_LFS_VERSION": "3.8.0", "GH_VERSION": "2.102.0", "JQ_VERSION": "1.7",
                 "PYTHON_VERSION": "3.12.3", "SHELLCHECK_VERSION": "0.9.0"}


def test_every_dockerfile_arg_is_in_the_manifest():
    args = re.findall(r"^ARG (\w+)", DOCKERFILE.read_text(), re.M)
    assert args and set(args) <= set(manifest())


def test_build_script_checks_every_tool_version():
    body = BUILD.read_text()
    for key in ("NODE_VERSION", "GIT_VERSION", "GIT_LFS_VERSION", "GH_VERSION", "JQ_VERSION", "PYTHON_VERSION",
                "SHELLCHECK_VERSION"):
        assert f"${key}" in body or f"${{{key}}}" in body, key
    assert "id -u" in body and "sudo -n true" in body
    assert "apt-get install -s shellcheck" in body  # apt lists kept: CI installs without `apt-get update`
