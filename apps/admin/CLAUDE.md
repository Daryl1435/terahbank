# TerahBank Admin — Next.js Back-Office
Internal tool for TerahBank operations staff. TypeScript strict mode.

## RBAC — enforce on every admin page and action
```typescript
// Three roles — check on every protected route
type AdminRole = 'super_admin' | 'operations_staff' | 'read_only_analyst';

// What each role can do:
// super_admin:        full access including PATCH /admin/config
// operations_staff:   user management, KYC queue, transaction monitoring, reports
// read_only_analyst:  read-only views, no mutations whatsoever

// UI rule: hide mutation buttons for read_only_analyst
// Security rule: verify role server-side — UI hiding is UX, not security
```

## Admin MFA
- Admin login requires TOTP (RFC 6238) in addition to password
- Never allow admin access with only a password — even in development

## Layout
- Sidebar nav: Navy (#0B1F4A) · 240px · Collapsible to 64px icon-only
- Active nav item: Teal left border 3px + Teal 10% row fill
- Page background: Off-White (#F4F7FB)
- Data tables: White background · Alternating Off-White rows · Teal header row

## Sensitive data display rules
- Never log user PII to browser console
- Mask phone numbers in table views: `+237 6XX XXX XXX`
- Mask card numbers: `**** **** **** 1234`
- KYC document images: load via presigned URLs (short TTL) — never store in state longer than session

## Report generation (exports)
- CSV: stream directly — don't load entire dataset into memory
- PDF: generate server-side — never client-side
- Max export rows: 10,000 — paginate larger exports
- Always run reports against the read replica, never the primary DB

## Key admin flows
- KYC queue: approve → write audit log → activate user → send notification
- Config update (super_admin only): validate value → write audit log → update system_config → invalidate Redis cache
- User suspend: write audit log → set status=suspended → invalidate all user sessions in Redis
