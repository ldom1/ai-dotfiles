# Patching Immich after upload: API contract + a costly SSO gotcha

This is the concrete API this skill's `apply_destination_patch.py` was
built and verified against. If you're adapting the script to a different
destination system, the gotcha below (skip to "The SSO/reverse-proxy trap")
is the part most likely to generalize — read it even if you never touch
Immich.

## Endpoints used

All under `{base_url}/api` (immich-cli's `login-key` discovers this via
`/.well-known/immich` and writes it into `~/.config/immich/auth.yml` as
`url: https://host/api` — `apply_destination_patch.py` reads that file
directly rather than re-deriving it).

| Purpose | Method + path | Body | Notes |
|---|---|---|---|
| Find an asset by its original filename | `POST /search/metadata` | `{"originalFileName": "IMG_0001.jpg"}` | Returns `assets.items[]`; take `[0].id`. Safe to match on filename *only* if the uploader guarantees unique filenames within the batch — `triage.py` does this via its dest-path collision-avoidance loop, so this is safe for files that went through this skill's `triage.py`. |
| Bulk-set a date on many assets at once | `PUT /assets` | `{"ids": ["uuid", ...], "dateTimeOriginal": "1994-11-16T00:00:00.000Z"}` | `AssetBulkUpdateDto` server-side. One call handles up to a few hundred/thousand IDs — `apply_destination_patch.py` chunks at 500 to stay well clear of any body-size limit. This is the *bulk* endpoint; there's also a `PATCH /assets/{id}`-per-asset version but it's far slower at scale — use the bulk one. |
| Create an album | `POST /albums` | `{"albumName": "Undated / Recovered"}` | Returns the created album's `id`. |
| Add assets to an album | `PUT /albums/{id}/assets` | `{"ids": ["uuid", ...]}` | Same `ids` array shape as the bulk asset update. |

All confirmed by reading Immich's own server source (`server/src/dtos/asset.dto.ts`,
`server/src/dtos/album.dto.ts`, `server/src/controllers/asset.controller.ts`,
`server/src/controllers/album.controller.ts`), not assumed from generic docs —
worth doing the same (`gh api repos/immich-app/immich/contents/<path>`) if the
API surface has moved since this was written.

## The SSO/reverse-proxy trap

If the Immich instance you're patching is reachable through a domain gated
by SSO middleware (Authelia, oauth2-proxy, Authentik forward-auth, etc. — a
common self-hosting pattern to protect the web UI from the open internet),
**do not assume "the API key works, therefore the API is reachable."** A
real deployment hit this exact failure:

1. `immich login-key <url> <key>` crashed with a client-side `TypeError:
   Cannot read properties of undefined (reading 'includes')` deep inside
   the CLI's permission-check code.
2. This looked exactly like an API-key permission problem (the key in use
   was narrowly scoped), so the natural fix — create a new key with broader
   permissions — was tried. **It made no difference. Same crash, same line,
   with a full-permission key.**
3. The actual cause: the CLI's `login` flow first fetches
   `{url}/.well-known/immich` **unauthenticated** (no API key sent yet) to
   discover the real API base URL. If the reverse proxy in front of Immich
   applies its SSO `auth_request` gate to *every* path including
   `/.well-known/*` and `/api/*`, that fetch gets a 302 redirect to the SSO
   login page instead of JSON. The CLI's `try { ... } catch {}` around that
   discovery step silently swallows the failure, then proceeds to call
   `/api-keys/me` against the wrong base URL (missing the `/api` prefix
   the discovery step would have added) — which also gets redirected to
   HTML, and *that's* what produces the undefined-permissions crash. The
   error message is real but describes a downstream symptom, not the cause.
4. Confirmed with `curl -sk -D - -o /dev/null https://host/api/server/version`
   returning `302 ... Location: https://sso-host/login?rd=...` instead of
   `200 application/json` — that one-line check would have caught this in
   seconds instead of chasing a permissions red herring.

**Fix:** the reverse-proxy vhost needs `/.well-known/immich` and `/api/`
to bypass the SSO `auth_request` gate entirely, while the `/` browser UI
route stays gated. This is safe, not a security regression — Immich's own
API layer authenticates every request itself (the `x-api-key` header or a
JWT), independent of the SSO layer; the mobile app and any API client rely
on exactly this being true. Example (nginx + Authelia, adapt the
`auth_request`/`proxy_pass` lines to your stack):

```nginx
location /.well-known/immich {
    proxy_pass http://immich-backend:80;
    proxy_set_header Host $host;
}

location /api/ {
    proxy_pass http://immich-backend:80;
    proxy_set_header Host $host;
    # no auth_request here — Immich's own API auth covers this path
}

location / {
    auth_request /internal/sso/authz;   # SSO gate stays on the browser UI only
    proxy_pass http://immich-backend:80;
    ...
}
```

**Before running `apply_destination_patch.py` (or debugging any CLI
login/upload failure) against a self-hosted, SSO-fronted instance**, sanity
check with one `curl` call:

```bash
curl -sk -D - -o /dev/null https://your-immich-host/api/server/version
```

`200` + `application/json` means the API path is reachable and this whole
class of problem doesn't apply. A `302` to a login page means fix the
reverse-proxy config first — no amount of API-key permission tweaking or
CLI retries will fix it, because the request never reaches Immich's auth
layer at all.
