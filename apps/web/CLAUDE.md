# TerahBank Web — Next.js Customer Portal
TypeScript strict mode. SSR for all customer-facing pages. Tailwind CSS.

## Design tokens
```css
/* Use CSS variables — never hardcode hex */
--color-navy:      #0B1F4A;
--color-teal:      #00B4D8;
--color-off-white: #F4F7FB;   /* page background */
--color-light-grey:#E8EDF5;   /* borders */
--color-mid-grey:  #8A97B5;   /* placeholder, captions */
--color-dark-grey: #4A5568;   /* body text */
--color-success:   #00C48C;
--color-warning:   #FFB020;
--color-error:     #E53E3E;
```

## Layout rules (Design System v1.0)
- Page background: `#F4F7FB` (off-white) — never pure white
- Top nav: White · 72px · Logo left · Nav center · CTA pill (teal) right
- Max content width: 1280px centered · 48px top padding
- Grid: 4 col mobile / 8 col tablet / 12 col desktop
- Gutter: 16px mobile · 24px tablet/desktop

## Next.js patterns
- Server Components by default — use `'use client'` only when needed
- SSR for all customer-facing pages (performance on Cameroonian connections)
- API calls from Server Components go directly to FastAPI (server-to-server)
- Client Components use React Query for data fetching
- `app/` directory structure (Next.js 14+ App Router)

## i18n
```typescript
// Use next-intl
import { useTranslations } from 'next-intl';
const t = useTranslations('dashboard');
<h1>{t('total_balance')}</h1>
```

## Error handling
- All API errors: read `error.code`, map to i18n message (see docs/error-codes.md)
- `TOKEN_EXPIRED` → silent refresh → retry once → redirect to login
- Never show raw error codes or stack traces to users

## Accessibility
- WCAG 2.1 Level AA
- Never disable focus ring
- All interactive elements min 44×44px
- Max 1 primary CTA per view
- Error + success states on all form inputs
