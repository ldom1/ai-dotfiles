#!/usr/bin/env python3
import json
import sys
from pathlib import Path

SEV_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def norm_sev(value: str) -> str:
    value = (value or "info").lower()
    return value if value in SEV_ORDER else "info"


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: aggregate.py <checks_dir> <report_path>", file=sys.stderr)
        return 2

    checks_dir = Path(sys.argv[1])
    report_path = Path(sys.argv[2])
    checks = []
    for p in sorted(checks_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            data["severity"] = norm_sev(data.get("severity"))
            checks.append(data)
        except Exception as exc:
            checks.append(
                {
                    "check": p.stem,
                    "status": "error",
                    "severity": "high",
                    "findings": [f"Invalid JSON in {p.name}: {exc}"],
                    "evidence": [],
                    "suggested_fixes": ["Fix check output format and rerun."],
                    "meta": {},
                }
            )

    checks.sort(key=lambda c: SEV_ORDER[norm_sev(c.get("severity"))], reverse=True)

    severity_counts = {k: 0 for k in ["critical", "high", "medium", "low", "info"]}
    for c in checks:
        severity_counts[norm_sev(c.get("severity"))] += 1

    issues = []
    fixes = []
    for c in checks:
        sev = norm_sev(c.get("severity"))
        for f in c.get("findings", []):
            issues.append({"check": c.get("check"), "severity": sev, "message": f})
        for fx in c.get("suggested_fixes", []):
            fixes.append({"check": c.get("check"), "severity": sev, "fix": fx})

    fixes.sort(key=lambda x: SEV_ORDER[x["severity"]], reverse=True)
    unique_fixes = []
    seen = set()
    for f in fixes:
        key = (f["check"], f["fix"])
        if key not in seen:
            seen.add(key)
            unique_fixes.append(f)

    report = {
        "summary": {
            "total_checks": len(checks),
            "severity_counts": severity_counts,
            "top_severity": next((k for k, v in severity_counts.items() if v > 0), "info"),
        },
        "checks": checks,
        "issues": issues,
        "suggested_fixes": unique_fixes,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Infrastructure audit summary")
    print(
        "Severity: "
        + " ".join(f"{k.upper()}={severity_counts[k]}" for k in ["critical", "high", "medium", "low", "info"])
    )
    rank = 1
    for item in issues[:10]:
        print(f"{rank}. [{item['severity'].upper()}] {item['check']}: {item['message']}")
        rank += 1
    if not issues:
        print("1. [INFO] No issues detected.")
    print("Suggested fixes:")
    for fix in unique_fixes[:10]:
        print(f"- [{fix['severity'].upper()}] {fix['check']}: {fix['fix']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
