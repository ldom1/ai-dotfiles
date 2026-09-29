import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from versioning import (
    CommitTypeSummary,
    Version,
    changelog_section,
    compute_candidate_version,
    highest_alpha_tag,
    highest_final_tag,
    highest_prerelease_for_candidate,
    next_prerelease_version,
    next_release_version,
    parse_tag,
    summarize_commits,
)

FIX = CommitTypeSummary(has_feat=False, has_fix_or_enh=True, has_breaking=False, has_versionable=True)
FEAT = CommitTypeSummary(has_feat=True, has_fix_or_enh=False, has_breaking=False, has_versionable=True)
BREAKING = CommitTypeSummary(has_feat=False, has_fix_or_enh=True, has_breaking=True, has_versionable=True)
NOTHING = CommitTypeSummary(has_feat=False, has_fix_or_enh=False, has_breaking=False, has_versionable=False)


def test_parse_tag_with_and_without_prefix():
    assert parse_tag("v0.6.0", "v") == Version(0, 6, 0)
    assert parse_tag("0.3.0a2", "") == Version(0, 3, 0, 2)
    assert parse_tag("0.6.0", "v") is None
    assert parse_tag("v0.6", "v") is None


def test_release_sorts_after_its_alphas_and_alphas_by_number():
    assert Version(0, 3, 0) > Version(0, 3, 0, 10)
    assert Version(0, 3, 0, 10) > Version(0, 3, 0, 9)


def test_summarize_commits_detects_fix_and_enh_as_versionable_not_feat():
    assert summarize_commits(["fix(core): repair", "enh(core): tidy"]) == FIX


def test_summarize_commits_detects_feat():
    assert summarize_commits(["feat(core): add the thing"]).has_feat is True


def test_summarize_commits_detects_breaking_footer_and_bang():
    assert summarize_commits(["fix(core): x\n\nBREAKING CHANGE: gone"]).has_breaking is True
    assert summarize_commits(["feat(api)!: drop v1"]).has_breaking is True


def test_summarize_commits_doc_ci_only_or_empty_is_not_versionable():
    assert summarize_commits(["doc(docs): readme", "ci(core): workflow"]).has_versionable is False
    assert summarize_commits([]).has_versionable is False


def test_bump_rule():
    assert compute_candidate_version(Version(0, 2, 1), FIX) == Version(0, 2, 2)
    assert compute_candidate_version(Version(0, 2, 1), FEAT) == Version(0, 3, 0)
    assert compute_candidate_version(Version(0, 2, 1), BREAKING) == Version(0, 3, 0)
    assert compute_candidate_version(Version(1, 2, 1), BREAKING) == Version(2, 0, 0)
    assert compute_candidate_version(Version(0, 2, 1), NOTHING) is None


def test_highest_final_tag_ignores_prereleases_other_prefixes_and_junk():
    tags = ["v0.2.1", "v0.3.0a1", "v0.2.9", "0.9.0", "not-a-version"]
    assert highest_final_tag(tags, "v") == Version(0, 2, 9)
    assert highest_final_tag([], "v") is None


def test_highest_prerelease_for_candidate_uses_real_precedence_and_own_line_only():
    assert highest_prerelease_for_candidate(["0.3.0a9", "0.3.0a10", "0.3.0a2"], Version(0, 3, 0), "") == 10
    assert highest_prerelease_for_candidate(["0.2.2a1", "0.2.2a2"], Version(0, 3, 0), "") == 0


def test_next_prerelease_version():
    assert next_prerelease_version(Version(0, 2, 1), FIX, [], "") == Version(0, 2, 2, 1)
    assert next_prerelease_version(Version(0, 2, 1), FIX, ["0.2.2a1"], "") == Version(0, 2, 2, 2)
    # a feat after 0.2.2a1 moves to a new candidate line, which starts at a1
    assert next_prerelease_version(Version(0, 2, 1), FEAT, ["0.2.2a1"], "") == Version(0, 3, 0, 1)
    assert next_prerelease_version(Version(0, 2, 1), NOTHING, [], "") is None


def test_highest_alpha_tag():
    assert highest_alpha_tag(["0.3.0a9", "0.3.0a10", "0.2.2a1"], "") == Version(0, 3, 0, 10)
    assert highest_alpha_tag(["0.2.1"], "") is None


def test_next_release_version_is_the_base_of_an_unreleased_alpha():
    assert next_release_version(Version(0, 2, 1), FIX, ["0.3.0a1", "0.3.0a2"], "") == Version(0, 3, 0)


def test_next_release_version_ignores_an_already_released_alpha():
    """Docs-only advance after 0.2.2 shipped: 0.2.2a1 is still the highest alpha,
    but it is released already -- nothing new to tag."""
    assert next_release_version(Version(0, 2, 2), NOTHING, ["0.2.2a1", "0.2.2"], "") is None


def test_next_release_version_without_intermediate_stage_bumps_from_commits():
    assert next_release_version(Version(0, 6, 0), FEAT, [], "v") == Version(0, 7, 0)


def test_changelog_section():
    changelog = "# Changelog\n\n## [Unreleased]\n\n## [0.7.0] - 2026-09-29\n\n### Added\n- x\n\n## [0.6.0] - 2026-09-10\n- y\n"
    assert changelog_section(changelog, Version(0, 7, 0)) == "### Added\n- x"
    assert changelog_section(changelog, Version(0, 6, 0)) == "- y"
    assert changelog_section(changelog, Version(0, 8, 0)) is None
