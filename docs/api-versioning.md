# TerahBank — API Versioning Contract

> Mobile apps cannot force-update users overnight. This doc prevents breaking changes from breaking live users.
> Rule: Never remove or rename a field in a response without a deprecation cycle.

---

## Current Version: v1

Base path: `/api/v1/`
All new development targets v1 unless explicitly creating v2.

---

## Versioning Strategy: URL Path Versioning

```
/api/v1/accounts     ← stable, in production
/api/v2/accounts     ← only created when v1 has breaking changes
```

Why URL path (not headers): Simplest to implement, debug, and test. Mobile Money providers and insurance partners all use URL versioning.

---

## What Constitutes a Breaking Change (requires v2)

| Breaking | Not Breaking |
|---|---|
| Removing a field from response | Adding a new optional field to response |
| Renaming a field | Adding a new optional query parameter |
| Changing a field's type (e.g. int → string) | Adding a new endpoint |
| Changing enum values that exist | Adding new enum values |
| Making an optional field required | Changing error message text |
| Changing authentication method | Adding a new error code |
| Changing HTTP method for an endpoint | Improving response time |
| Removing an endpoint entirely | Adding deprecation warnings |

---

## Deprecation Process

When a field, endpoint, or behavior must be removed:

**Step 1 — Announce deprecation (v1 still works)**
Add `X-Deprecated: true` response header and `_deprecated` warning in response:
```json
{
  "success": true,
  "data": { "balance": 500000 },
  "_warnings": ["Field 'old_field' is deprecated and will be removed in v2. Use 'new_field' instead."]
}
```

**Step 2 — Wait minimum 90 days**
Mobile apps on older versions need time for users to update.
Monitor `X-App-Version` header to see if old clients are still active.

**Step 3 — Release v2 endpoint**
Both v1 and v2 run simultaneously. v1 maintained for 6 more months.

**Step 4 — Sunset v1 endpoint**
Return `410 Gone` with migration instructions.
Log every 410 hit to identify clients still on v1.

---

## Client Version Tracking

All clients must send:
```
X-App-Version: 1.2.3         ← Mobile app version / web app build version
X-Platform: android           ← android | ios | web | admin
X-Client-Id: {device_uuid}    ← Unique device identifier (from Expo SecureStore)
```

Backend logs these headers on every request. Enables:
- Knowing which app versions are still active
- Forcing minimum version updates (see below)
- Debugging version-specific bugs

---

## Minimum Version Enforcement (Mobile)

When a security fix or critical bug fix requires users to update:

```python
# middleware/version_check.py
MINIMUM_VERSION = {
    "android": "1.0.0",
    "ios": "1.0.0",
}

@app.middleware("http")
async def version_check(request: Request, call_next):
    platform = request.headers.get("X-Platform", "")
    app_version = request.headers.get("X-App-Version", "0.0.0")

    if platform in MINIMUM_VERSION:
        if is_version_below(app_version, MINIMUM_VERSION[platform]):
            return JSONResponse(
                status_code=426,   # Upgrade Required
                content={"success": False, "error": {
                    "code": "APP_UPDATE_REQUIRED",
                    "message": "Please update TerahBank to continue.",
                    "details": {
                        "minimum_version": MINIMUM_VERSION[platform],
                        "store_url": "https://play.google.com/store/apps/details?id=com.terahbank"
                    }
                }}
            )
    return await call_next(request)
```

Mobile app handles `426` by showing a full-screen "Update Required" modal.

---

## Response Field Stability Rules

1. **Never remove a field** without a deprecation cycle
2. **Never change a field's type** — add a new field with the new type, keep old one
3. **Monetary fields:** always return in BIGINT (smallest XAF unit). Never change this.
4. **Date fields:** always return ISO 8601 (`2026-02-21T10:30:00Z`). Never change format.
5. **Enum values:** never remove or rename existing values — only add new ones
6. **Pagination:** cursor-based pagination shape is permanent — `{ data, cursor, has_more }`

---

## Pagination Contract (Stable — Never Change)

```json
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": {
      "cursor": "eyJjcmVhdGVkX2F0IjoiMjAyNi0wMi0yMVQxMDozMDowMFoiLCJpZCI6InV1aWQifQ==",
      "has_more": true,
      "count": 20
    }
  }
}
```

Client passes `?cursor=<value>` to get the next page.
Cursor is base64-encoded `{created_at, id}` — never expose raw SQL offset to clients.

---

## Changelog (maintain this as you ship)

| Version | Date | Changes |
|---|---|---|
| v1.0.0 | 2026-Q2 | Initial release — all Phase 1 endpoints |
| v1.x.x | TBD | Bug fixes, new optional fields, new endpoints |
| v2.0.0 | TBD | Breaking changes (list here when known) |
