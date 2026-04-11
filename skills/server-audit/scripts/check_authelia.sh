#!/usr/bin/env bash
set -euo pipefail
python3 - "$1" <<'PY'
import json, os, sys, urllib.error, urllib.request

cfg = json.load(open(sys.argv[1], encoding="utf-8"))
au = cfg.get("authelia", {})
portal = au.get("portal_url", "")
protected = au.get("protected_url", "")
expect_redirect = bool(au.get("expect_redirect_when_unauthenticated", True))
user_env = au.get("user_env", "AUTHELIA_USER")
pass_env = au.get("password_env", "AUTHELIA_PASS")

result = {"check":"authelia","status":"pass","severity":"info","findings":[],"evidence":[],"suggested_fixes":[],"meta":{"mode":"probe+optional-creds"}}

def fetch(url):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=12) as resp:
        body = resp.read(2048).decode("utf-8", errors="ignore")
        return int(resp.getcode()), dict(resp.headers), body

if portal:
    try:
        code, _, _ = fetch(portal)
        result["evidence"].append(f"portal_url status={code}")
    except Exception as exc:
        result["status"] = "error"
        result["severity"] = "high"
        result["findings"].append("Authelia portal is not reachable.")
        result["evidence"].append(str(exc))
        result["suggested_fixes"].append("Check DNS/TLS and Authelia container/service status.")

if protected:
    try:
        code, headers, body = fetch(protected)
        location = headers.get("Location", "")
        if expect_redirect:
            if code in (301, 302, 303, 307, 308) or "authelia" in location.lower():
                result["evidence"].append(f"protected_url redirect/auth challenge observed (status={code}).")
            else:
                result["status"] = "warn"
                result["severity"] = "medium"
                result["findings"].append("Protected endpoint did not redirect/challenge as expected.")
                result["suggested_fixes"].append("Validate nginx auth_request/authelia middleware wiring.")
        else:
            if code >= 400:
                result["status"] = "warn"
                result["severity"] = "medium"
                result["findings"].append(f"Protected endpoint returned unexpected status {code}.")
        if "authelia" in body.lower():
            result["evidence"].append("Authelia marker text found in protected flow response.")
    except urllib.error.HTTPError as exc:
        if expect_redirect and exc.code in (401, 302, 303):
            result["evidence"].append(f"protected_url challenge observed via HTTPError status={exc.code}")
        else:
            result["status"] = "warn"
            result["severity"] = "medium"
            result["findings"].append(f"Protected endpoint returned HTTP error {exc.code}.")
    except Exception as exc:
        result["status"] = "error"
        result["severity"] = "high"
        result["findings"].append("Protected endpoint check failed.")
        result["evidence"].append(str(exc))
        result["suggested_fixes"].append("Check reverse proxy, DNS, and TLS reachability.")

username = os.getenv(user_env, "")
password = os.getenv(pass_env, "")
if username and password:
    result["evidence"].append("Credential env vars detected for optional credentialed flow.")
else:
    result["evidence"].append("Credentialed flow skipped (no auth env vars set).")

if not result["findings"]:
    result["findings"].append("Authelia probe checks passed.")

print(json.dumps(result, indent=2))
PY
