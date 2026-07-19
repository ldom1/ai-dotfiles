import unittest

from validate_sop import validate_sop

VALID = """---
title: SOP — Example
tags: [sop]
owner: alice
last-updated: 2026-07-19
---

# SOP — Example

## Purpose
Keep the example service running.

## Scope
Applies to the example service on host X.

## Prerequisites
N/A

## Steps
1. Do the thing.

## Verification
Run `curl` and check for 200.

## Rollback
N/A

## Owner / Last updated
alice, 2026-07-19
"""


class TestValidateSop(unittest.TestCase):
    def test_valid_document_has_no_errors(self):
        self.assertEqual(validate_sop(VALID), [])

    def test_missing_section_is_reported(self):
        broken = VALID.replace("## Rollback\nN/A\n\n", "")
        errors = validate_sop(broken)
        self.assertTrue(any("Rollback" in e for e in errors))

    def test_wrong_order_is_reported(self):
        broken = VALID.replace(
            "## Prerequisites\nN/A\n\n## Steps\n1. Do the thing.\n\n",
            "## Steps\n1. Do the thing.\n\n## Prerequisites\nN/A\n\n",
        )
        errors = validate_sop(broken)
        self.assertTrue(any("order" in e.lower() for e in errors))

    def test_empty_section_body_is_reported(self):
        broken = VALID.replace("## Rollback\nN/A\n\n", "## Rollback\n\n")
        errors = validate_sop(broken)
        self.assertTrue(any("Rollback" in e and "empty" in e.lower() for e in errors))


if __name__ == "__main__":
    unittest.main()
