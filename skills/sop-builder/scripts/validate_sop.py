"""Validate an SOP document against the fixed sop-builder template shape."""
import re
import sys

REQUIRED_SECTIONS = [
    "Purpose",
    "Scope",
    "Prerequisites",
    "Steps",
    "Verification",
    "Rollback",
    "Owner / Last updated",
]


def validate_sop(text: str) -> list[str]:
    errors: list[str] = []

    heading_re = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
    found = [(m.start(), m.group(1).strip()) for m in heading_re.finditer(text)]
    found_names = [name for _, name in found]

    for section in REQUIRED_SECTIONS:
        if section not in found_names:
            errors.append(f"Missing required section: {section!r}")

    if not errors:
        # only check ordering once we know all sections are present
        positions = [found_names.index(s) for s in REQUIRED_SECTIONS]
        if positions != sorted(positions):
            errors.append(
                f"Sections out of order: expected {REQUIRED_SECTIONS}, "
                f"found {found_names}"
            )

    # body-emptiness check, independent of ordering result
    for i, (start, name) in enumerate(found):
        if name not in REQUIRED_SECTIONS:
            continue
        body_start = start + len(text[start:].split("\n", 1)[0]) + 1
        body_end = found[i + 1][0] if i + 1 < len(found) else len(text)
        body = text[body_start:body_end].strip()
        if not body:
            errors.append(f"Section {name!r} has an empty body (use 'N/A' if not applicable)")

    return errors


def main() -> None:
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        text = f.read()
    errors = validate_sop(text)
    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
