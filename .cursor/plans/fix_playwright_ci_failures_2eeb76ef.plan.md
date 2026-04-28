---
name: Fix Playwright CI failures
overview: "All 3 Playwright tests fail due to a single env variable name mismatch: `urlCrypto.ts` reads `NEXT_AUTH_SECRET` but the webServer only receives `NEXTAUTH_SECRET`. A secondary issue is that `send-verification.ts` always tries SMTP even in CI."
todos:
  - id: fix-env
    content: Add NEXT_AUTH_SECRET to webServer.env in playwright.config.ts
    status: completed
  - id: fix-email
    content: Guard sendEmail in send-verification.ts with SEND_EMAIL_TO_USER check
    status: completed
isProject: false
---

# Fix Playwright CI Test Failures

## Root cause analysis

### Failure 1 (all 3 tests) — `NEXT_AUTH_SECRET` vs `NEXTAUTH_SECRET`

[`src/lib/urlCrypto.ts`](src/lib/urlCrypto.ts) line 10 reads:
```js
process.env.ENCRYPTION_SECRET || process.env.NEXT_AUTH_SECRET || ""
```

[`playwright.config.ts`](playwright.config.ts) webServer env only sets `NEXTAUTH_SECRET: "test-secret-key"` (no underscore between NEXT and AUTH). So `getKey()` gets an empty string and throws:

> `ENCRYPTION_SECRET or NEXT_AUTH_SECRET required`

This propagates through every code path that calls `encryptId()`:
- `withPoemToken()` — called on every GET /api/poems response → poems never appear on home page → **Test A1 fails**
- `createNewPoemNotification()` — called after poem creation → notification + redirect URL generation fails → poem not found on home → **Test B fails**  
- `event/index.ts` line 27 `encryptId(e._id)` — called when creating/returning events → event creation API fails → "Événement créé" toast never shown → **Test C fails**

### Failure 2 (noise, not a blocker) — `send-verification.ts` ignores `SEND_EMAIL_TO_USER`

[`send-verification.ts`](src/pages/api/emailchecks/send-verification.ts) always calls `sendEmail()` unconditionally, even when `SEND_EMAIL_TO_USER=""`. This throws `ECONNREFUSED 127.0.0.1:587` in CI. The registration UI handles the 500 gracefully (shows "Félicitations!" anyway), so it doesn't cause test failures — but it pollutes logs.

## Fixes

### Fix 1 — `playwright.config.ts` (critical)

Add `NEXT_AUTH_SECRET` to the webServer env so `encryptId()` gets a valid key:

```diff
  env: {
    MONGO_DB_URI,
    NEXT_PUBLIC_SITE_URL: "http://localhost:3000",
    NEXTAUTH_URL: "http://localhost:3000",
    NEXTAUTH_SECRET: "test-secret-key",
+   NEXT_AUTH_SECRET: "test-secret-key",
    SEND_EMAIL_TO_USER: "",
  },
```

### Fix 2 — `send-verification.ts` (cosmetic)

Guard the `sendEmail` call with the same `SEND_EMAIL_TO_USER` check already used in the poems notification path:

```diff
+ if (!process.env.SEND_EMAIL_TO_USER) {
+   return res.status(200).json({ success: true });
+ }
  try {
    const normalized = normalizeEmail(String(email));
    await sendEmail(...)
```
