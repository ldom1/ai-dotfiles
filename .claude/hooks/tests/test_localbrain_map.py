"""LocalBrain.md is the one vault map: every path it names must exist in the vault."""
import os
import re
from pathlib import Path

import pytest

MAP = Path(__file__).resolve().parents[3] / "LocalBrain.md"
SPAN = re.compile(r"`([^`]+)`")
BRACES = re.compile(r"\{([^{}]+)\}")


def table_paths():
    """Backticked paths of the first column, braces expanded, cut at the first placeholder."""
    paths = []
    for line in MAP.read_text().splitlines():
        if not line.startswith("| `"):
            continue
        for span in SPAN.findall(line.split("|")[1]):
            if "/" not in span and not span.endswith((".md", ".base")):
                continue
            paths += expand(span)
    return paths


def expand(span):
    m = BRACES.search(span)
    if m:
        return [p for alt in m.group(1).split(",")
                for p in expand(span[:m.start()] + alt + span[m.end():])]
    kept = []
    for seg in span.split("/"):
        if "<" in seg or "YYYY" in seg or "…" in seg:
            break
        kept.append(seg)
    path = "/".join(kept).rstrip("/")
    return [path] if path else []


def test_every_mapped_path_exists():
    brain = os.environ.get("BRAIN_PATH")
    if not brain:
        pytest.skip("BRAIN_PATH is unset: no vault to check")
    missing = [p for p in table_paths() if not (Path(brain) / p).exists()]
    assert not missing, f"paths in LocalBrain.md missing from the vault: {missing}"


def test_table_names_current_paths():
    paths = table_paths()
    for want in ["TASKS_REVIEW.base", "VEILLE.base", "inbox/review", "inbox/sensors",
                 "inbox/insights", "inbox/daily/products", "inbox/daily/prompts",
                 "resources/knowledge/veille", "resources/queries/archive",
                 "meta/harness-sessions", "raw", "archive"]:
        assert want in paths, want
    for gone in ["inbox/connections", "inbox/qa", "inbox/drafts"]:
        assert gone not in paths, gone


def test_map_states_the_three_rules():
    text = MAP.read_text()
    assert "Order of truth" in text
    assert "never `[[name]]`" in text
    for tool in ["cursor-agent-brain", "bootstrap.md", "Cursor IDE"]:
        assert tool in text, tool
