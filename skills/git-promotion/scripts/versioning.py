"""Pure version math for git-promotion -- no git subprocess calls in this module,
so every function here is testable with plain Python data.

Tags are `<prefix>X.Y.Z` (a release) or `<prefix>X.Y.ZaN` (an alpha on an
intermediate stage such as preprod). Any other tag name is ignored.
"""

from __future__ import annotations

import functools
import math
import re
from dataclasses import dataclass

_CONVENTIONAL_COMMIT_RE = re.compile(r"^(feat|fix|enh|doc|ci)(\([^)]+\))?(!)?: ")
_BREAKING_FOOTER_RE = re.compile(r"^BREAKING CHANGE:", re.MULTILINE)
_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)(?:a(\d+))?")


@functools.total_ordering
@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    micro: int
    alpha: int | None = None

    @property
    def base(self) -> Version:
        return Version(self.major, self.minor, self.micro)

    def _key(self) -> tuple:
        # A release sorts after every alpha of the same X.Y.Z.
        alpha = math.inf if self.alpha is None else self.alpha
        return (self.major, self.minor, self.micro, alpha)

    def __lt__(self, other: Version) -> bool:
        return self._key() < other._key()

    def __str__(self) -> str:
        suffix = f"a{self.alpha}" if self.alpha is not None else ""
        return f"{self.major}.{self.minor}.{self.micro}{suffix}"


ZERO = Version(0, 0, 0)


def parse_tag(name: str, prefix: str) -> Version | None:
    if not name.startswith(prefix):
        return None
    match = _VERSION_RE.fullmatch(name[len(prefix) :])
    if not match:
        return None
    major, minor, micro, alpha = match.groups()
    return Version(int(major), int(minor), int(micro), int(alpha) if alpha else None)


def _versions(tag_names: list[str], prefix: str) -> list[Version]:
    return [v for v in (parse_tag(n, prefix) for n in tag_names) if v is not None]


@dataclass(frozen=True)
class CommitTypeSummary:
    has_feat: bool
    has_fix_or_enh: bool
    has_breaking: bool
    has_versionable: bool


def summarize_commits(commit_messages: list[str]) -> CommitTypeSummary:
    """commit_messages: one full commit message (subject + body/footers) per commit."""
    has_feat = False
    has_fix_or_enh = False
    has_breaking = False
    for message in commit_messages:
        subject = message.splitlines()[0] if message else ""
        match = _CONVENTIONAL_COMMIT_RE.match(subject)
        if match:
            commit_type = match.group(1)
            if commit_type == "feat":
                has_feat = True
            elif commit_type in ("fix", "enh"):
                has_fix_or_enh = True
            if match.group(3):
                has_breaking = True
        if _BREAKING_FOOTER_RE.search(message):
            has_breaking = True
    return CommitTypeSummary(
        has_feat=has_feat,
        has_fix_or_enh=has_fix_or_enh,
        has_breaking=has_breaking,
        has_versionable=has_feat or has_fix_or_enh or has_breaking,
    )


def compute_candidate_version(
    current_final: Version, summary: CommitTypeSummary
) -> Version | None:
    """fix/enh -> patch; feat -> minor; breaking -> major, or minor while X is 0.
    Nothing versionable -> None (the caller skips tag creation)."""
    if not summary.has_versionable:
        return None
    major, minor, micro = current_final.major, current_final.minor, current_final.micro
    if summary.has_breaking and major > 0:
        return Version(major + 1, 0, 0)
    if summary.has_feat or summary.has_breaking:
        return Version(major, minor + 1, 0)
    return Version(major, minor, micro + 1)


def highest_final_tag(tag_names: list[str], prefix: str) -> Version | None:
    finals = [v for v in _versions(tag_names, prefix) if v.alpha is None]
    return max(finals) if finals else None


def highest_alpha_tag(tag_names: list[str], prefix: str) -> Version | None:
    alphas = [v for v in _versions(tag_names, prefix) if v.alpha is not None]
    return max(alphas) if alphas else None


def highest_prerelease_for_candidate(
    tag_names: list[str], candidate: Version, prefix: str
) -> int:
    """Highest existing alpha N for this exact X.Y.Z (0 if none). A tag for a
    different X.Y.Z line is not consulted, so a new candidate line starts at a1."""
    return max(
        (
            v.alpha
            for v in _versions(tag_names, prefix)
            if v.alpha is not None and v.base == candidate
        ),
        default=0,
    )


def next_prerelease_version(
    current_final: Version,
    summary: CommitTypeSummary,
    existing_tag_names: list[str],
    prefix: str,
) -> Version | None:
    candidate = compute_candidate_version(current_final, summary)
    if candidate is None:
        return None
    alpha = highest_prerelease_for_candidate(existing_tag_names, candidate, prefix) + 1
    return Version(candidate.major, candidate.minor, candidate.micro, alpha)


def next_release_version(
    current_final: Version,
    summary: CommitTypeSummary,
    source_tag_names: list[str],
    prefix: str,
) -> Version | None:
    """With an intermediate stage, the release is the base of the source's highest
    alpha -- the version that stage already tested. Without one (or once that alpha
    is released), bump from the commit types since the last release."""
    alpha = highest_alpha_tag(source_tag_names, prefix)
    if alpha is not None and alpha.base > current_final:
        return alpha.base
    return compute_candidate_version(current_final, summary)


def changelog_section(changelog: str, version: Version) -> str | None:
    """Body of the `## [X.Y.Z]` section (Keep a Changelog), or None if absent."""
    heading = re.compile(rf"^## \[{re.escape(str(version))}\].*$", re.MULTILINE)
    match = heading.search(changelog)
    if not match:
        return None
    rest = changelog[match.end() :]
    next_heading = re.search(r"^## ", rest, re.MULTILINE)
    return (rest[: next_heading.start()] if next_heading else rest).strip()
