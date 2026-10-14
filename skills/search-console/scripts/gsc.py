#!/usr/bin/env python3
"""Read-only Google Search Console client (stdlib only).

Config: ~/.config/gsc/credentials.json (OAuth "Desktop app" client JSON),
        ~/.config/gsc/token.json (written by `auth`).
"""
import argparse
import datetime as dt
import http.server
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

CONFIG = Path.home() / ".config" / "gsc"
CREDS = CONFIG / "credentials.json"
TOKEN = CONFIG / "token.json"
SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
PORT = 8765
REDIRECT = f"http://127.0.0.1:{PORT}/"
API = "https://searchconsole.googleapis.com"


def die(msg, code=1):
    print(f"gsc: {msg}", file=sys.stderr)
    sys.exit(code)


def client():
    if not CREDS.exists():
        die(f"missing {CREDS} — create an OAuth 'Desktop app' client and save its JSON there", 3)
    data = json.loads(CREDS.read_text())
    c = data.get("installed") or data.get("web") or die(f"{CREDS}: not an OAuth client JSON")
    return c["client_id"], c["client_secret"]


def post_form(url, fields):
    req = urllib.request.Request(url, urllib.parse.urlencode(fields).encode())
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if "invalid_grant" in body:
            die("refresh token expired or revoked (Testing apps expire after 7 days) — run: gsc.py auth", 3)
        die(f"token endpoint HTTP {e.code}: {body}")


def exchange(code):
    cid, secret = client()
    tok = post_form("https://oauth2.googleapis.com/token", {
        "code": code, "client_id": cid, "client_secret": secret,
        "redirect_uri": REDIRECT, "grant_type": "authorization_code",
    })
    if "refresh_token" not in tok:
        die(f"no refresh_token in response: {sorted(tok)}")
    CONFIG.mkdir(parents=True, exist_ok=True)
    TOKEN.write_text(json.dumps({"refresh_token": tok["refresh_token"]}))
    TOKEN.chmod(0o600)
    print(f"gsc: token saved to {TOKEN}")


def code_from_url(url):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    if "error" in q:
        die(f"consent refused: {q['error'][0]}")
    return q.get("code", [None])[0] or die("no ?code= in that URL")


def cmd_auth(args):
    if args.url:  # fallback: browser could not reach the loopback server (e.g. WSL)
        return exchange(code_from_url(args.url))
    cid, _ = client()
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": REDIRECT, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent",
    })
    print(f"Open this URL and sign in:\n\n{url}\n")
    print(f"If the browser then shows 'connection refused', copy its address bar and run:\n"
          f"  gsc.py auth --url '<that URL>'\n")
    webbrowser.open(url)
    got = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            got["url"] = self.path
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"gsc: done, you can close this tab.")

        def log_message(self, *_):
            pass

    try:
        srv = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    except OSError as e:
        die(f"port {PORT} busy ({e.strerror}) — stop the other `gsc.py auth` or use --url")
    with srv:
        while "url" not in got:
            srv.handle_request()
    exchange(code_from_url(got["url"]))


def access_token():
    cid, secret = client()
    if not TOKEN.exists():
        die("not authenticated — run: gsc.py auth", 3)
    tok = post_form("https://oauth2.googleapis.com/token", {
        "refresh_token": json.loads(TOKEN.read_text())["refresh_token"],
        "client_id": cid, "client_secret": secret, "grant_type": "refresh_token",
    })
    return tok["access_token"]


def call(path, body=None):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {access_token()}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        die(f"{path} HTTP {e.code}: {e.read().decode()}")


def site_path(site):
    return "/webmasters/v3/sites/" + urllib.parse.quote(site, safe="")


def cmd_sites(_):
    for s in call("/webmasters/v3/sites").get("siteEntry", []):
        print(f"{s['siteUrl']}\t{s['permissionLevel']}")


def cmd_query(args):
    end = args.end or (dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=3)).isoformat()
    start = args.start or (dt.date.fromisoformat(end) - dt.timedelta(days=27)).isoformat()
    dims = [d for d in args.dimensions.split(",") if d]
    body = {"startDate": start, "endDate": end, "dimensions": dims,
            "rowLimit": args.limit, "type": args.type}
    if args.filter:
        body["dimensionFilterGroups"] = [{"filters": [
            dict(zip(("dimension", "operator", "expression"), f.split(":", 2))) for f in args.filter
        ]}]
    rows = call(site_path(args.site) + "/searchAnalytics/query", body).get("rows", [])
    print(f"# {args.site} {start}..{end} type={args.type} rows={len(rows)}")
    print("\t".join(dims + ["clicks", "impressions", "ctr", "position"]))
    for r in rows:
        print("\t".join(r.get("keys", []) + [
            str(r["clicks"]), str(r["impressions"]), f"{r['ctr']:.4f}", f"{r['position']:.1f}"]))


def cmd_inspect(args):
    res = call("/v1/urlInspection/index:inspect", {"inspectionUrl": args.url, "siteUrl": args.site})
    print(json.dumps(res.get("inspectionResult", res), indent=1))


def cmd_sitemaps(args):
    print(json.dumps(call(site_path(args.site) + "/sitemaps").get("sitemap", []), indent=1))


def main():
    p = argparse.ArgumentParser(description="Read-only Google Search Console client")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("auth", help="one-time OAuth sign-in")
    a.add_argument("--url", help="paste the redirect URL when the loopback server was unreachable")
    a.set_defaults(fn=cmd_auth)

    sub.add_parser("sites", help="list properties and permission level").set_defaults(fn=cmd_sites)

    q = sub.add_parser("query", help="search analytics (TSV)")
    q.add_argument("site", help="property, e.g. sc-domain:example.com or https://example.com/")
    q.add_argument("--start", help="YYYY-MM-DD (default: end - 27 days)")
    q.add_argument("--end", help="YYYY-MM-DD (default: today - 3 days, data lags)")
    q.add_argument("--dimensions", default="query", help="comma list: query,page,country,device,date,searchAppearance")
    q.add_argument("--filter", action="append", metavar="DIM:OP:EXPR",
                   help="e.g. page:contains:/blog (OP: equals, contains, notEquals, notContains, includingRegex, excludingRegex); repeat = AND")
    q.add_argument("--limit", type=int, default=100, help="rows, max 25000")
    q.add_argument("--type", default="web", help="web, image, video, news, discover, googleNews")
    q.set_defaults(fn=cmd_query)

    i = sub.add_parser("inspect", help="URL inspection: index status, canonical, crawl")
    i.add_argument("site")
    i.add_argument("url")
    i.set_defaults(fn=cmd_inspect)

    s = sub.add_parser("sitemaps", help="submitted sitemaps and their status")
    s.add_argument("site")
    s.set_defaults(fn=cmd_sitemaps)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
