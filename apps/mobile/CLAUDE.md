# TerahBank Mobile — React Native + Expo
Phase 1: Android only. TypeScript strict mode. Expo managed workflow.

## Design tokens — use these, never hardcode hex
```typescript
export const colors = {
  navy:       '#0B1F4A',   // Primary backgrounds, app bar
  teal:       '#00B4D8',   // CTAs, active states, accents
  tealDark:   '#0096B4',   // CTA hover/press
  offWhite:   '#F4F7FB',   // ALL screen backgrounds (never pure white)
  lightGrey:  '#E8EDF5',   // Borders, dividers
  midGrey:    '#8A97B5',   // Placeholder text, captions
  darkGrey:   '#4A5568',   // Body text
  darkNavy:   '#162D5E',   // Hover, gradient end
  success:    '#00C48C',   // Confirmed transactions
  warning:    '#FFB020',   // Pending, low balance
  error:      '#E53E3E',   // Failed, invalid input
  info:       '#00B4D8',   // Informational banners
} as const;
```

## Component specs (from Design System v1.0)
- Screen background: always `colors.offWhite` — never pure white
- App bar: 56px height · Navy background · White title · Poppins SemiBold 18px
- Bottom tab bar: 56px · White · max 5 tabs · Teal active indicators
- FAB (main CTA): 56px Teal circle · White icon · bottom-right
- Cards: White fill · radius 12px · 16px horizontal margin · 8px gap between
- Min touch target: 44×44px on ALL interactive elements — no exceptions
- Fonts: Poppins (headings, buttons, labels) · Roboto (body, forms, captions)
- Icons: Phosphor Icons — `regular` style default, `fill` for active/selected

## Security rules
- Tokens: stored in `expo-secure-store` only — NEVER AsyncStorage
- PIN: custom numeric keypad — never system keyboard for PIN input
- Biometric: `expo-local-authentication`
- Session: auto-terminate after 15 min inactivity (background timer)

## i18n — mandatory on every user-facing string
```typescript
import i18n from '@/locales';
// ✅ Correct
<Text>{i18n.t('dashboard.total_balance')}</Text>
// ❌ Never hardcode
<Text>Total Balance</Text>
```

## State management
- Remote server state: React Query (TanStack Query)
- Local UI state: React useState / useReducer
- Global app state: Zustand
- Never store sensitive data in Zustand (tokens, PIN) — use SecureStore

## Animation rules
- Respect `prefers-reduced-motion` — always provide instant fallback
- Transaction success: green overlay → checkmark spring → fade after 1.5s
- Progress bar: 0% → current on mount (400ms ease-out)
- Skeleton: pulse animation while loading

## File structure
```
apps/mobile/src/
├── screens/           ← One file per screen
├── components/        ← Reusable UI components
├── hooks/             ← Custom hooks (useAuth, useFeatureFlags)
├── services/          ← API calls (React Query queries/mutations)
├── stores/            ← Zustand stores
├── locales/           ← fr.json, en.json, index.ts
└── utils/             ← formatXAF, formatDate, validators
```

## Available skills
- `/new-screen` — scaffold a new screen with nav + i18n
- `/new-component` — scaffold a reusable component
