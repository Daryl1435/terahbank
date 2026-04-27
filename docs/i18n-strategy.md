# TerahBank — Internationalisation (i18n) Strategy

> French (fr) and English (en) at launch. Arabic + local languages on roadmap.
> Default language: French (fr) — Cameroon is majority Francophone.
> Rule: NO hardcoded user-facing strings anywhere in any app. Everything goes through i18n.

---

## Language Decision Logic

```
1. User's saved preferred_language in DB (users.preferred_language)
2. Fallback: device/browser locale
3. Fallback: 'fr' (French — Cameroon default)
```

---

## Backend (FastAPI)

### API Error Messages
All error `message` fields must be translated. The API reads `Accept-Language` header:

```python
# middleware/i18n.py
def get_locale(request: Request) -> str:
    lang = request.headers.get('Accept-Language', 'fr')
    supported = ['fr', 'en']
    return lang[:2] if lang[:2] in supported else 'fr'

# Usage in error responses
def error_response(code: str, lang: str = 'fr', **kwargs) -> dict:
    message = MESSAGES[lang][code].format(**kwargs)
    return {"success": False, "error": {"code": code, "message": message}}
```

### Translation Files (Backend)
```python
# locales/fr.py
MESSAGES = {
    "INSUFFICIENT_BALANCE": "Solde insuffisant. Disponible: {available} XAF.",
    "KYC_REQUIRED": "Vérifiez votre identité pour utiliser cette fonctionnalité.",
    "TOKEN_EXPIRED": "Votre session a expiré. Veuillez vous reconnecter.",
    "OTP_EXPIRED": "Ce code a expiré. Demandez-en un nouveau.",
    # ... all error codes from docs/error-codes.md
}

# locales/en.py
MESSAGES = {
    "INSUFFICIENT_BALANCE": "Insufficient funds. Available: {available} XAF.",
    "KYC_REQUIRED": "Please complete identity verification to use this feature.",
    "TOKEN_EXPIRED": "Your session has expired. Please log in again.",
    "OTP_EXPIRED": "This code has expired. Request a new one.",
    # ...
}
```

### Notification Templates (SendGrid)
- Create separate SendGrid templates for `fr` and `en`
- Template IDs stored in env: `SENDGRID_TEMPLATE_MONTHLY_SUMMARY_FR`, `SENDGRID_TEMPLATE_MONTHLY_SUMMARY_EN`
- Select template based on `user.preferred_language`

---

## Mobile App (React Native)

### Library: `i18n-js` + `expo-localization`

```bash
npx expo install expo-localization
npm install i18n-js
```

### File Structure
```
/apps/mobile/
└── locales/
    ├── fr.json     ← French (primary)
    ├── en.json     ← English
    └── index.ts    ← i18n configuration
```

### Configuration
```typescript
// locales/index.ts
import { I18n } from 'i18n-js';
import * as Localization from 'expo-localization';
import fr from './fr.json';
import en from './en.json';

const i18n = new I18n({ fr, en });
i18n.locale = Localization.getLocales()[0].languageCode ?? 'fr';
i18n.enableFallback = true;
i18n.defaultLocale = 'fr';

export default i18n;
```

### Translation File Format
```json
// locales/fr.json
{
  "auth": {
    "login_title": "Connexion",
    "phone_placeholder": "Numéro de téléphone",
    "password_placeholder": "Mot de passe",
    "login_button": "Se connecter",
    "forgot_password": "Mot de passe oublié ?",
    "no_account": "Pas encore de compte ?"
  },
  "dashboard": {
    "total_balance": "Solde total",
    "deposit": "Déposer",
    "withdraw": "Retirer",
    "transfer": "Transférer",
    "greeting_morning": "Bonjour, {name}",
    "greeting_afternoon": "Bon après-midi, {name}",
    "greeting_evening": "Bonsoir, {name}"
  },
  "accounts": {
    "standard": "Compte Épargne",
    "project": "Compte Projet",
    "term_deposit": "Dépôt à Terme",
    "new_project": "Nouveau Projet",
    "target_amount": "Montant cible",
    "target_date": "Date cible",
    "progress": "{percent}% atteint",
    "milestone_25": "🎉 25% de votre objectif atteint !",
    "milestone_50": "🎉 Mi-chemin ! Continuez comme ça !",
    "milestone_75": "🔥 75% ! Vous y êtes presque !",
    "milestone_100": "🏆 Félicitations ! Objectif atteint !"
  },
  "transactions": {
    "deposit_success": "Dépôt réussi",
    "deposit_failed": "Dépôt échoué",
    "amount_deposited": "{amount} XAF ajoutés à votre compte.",
    "status_pending": "En attente",
    "status_processing": "En cours",
    "status_success": "Réussi",
    "status_failed": "Échoué"
  },
  "errors": {
    "insufficient_balance": "Solde insuffisant. Disponible : {available} XAF.",
    "kyc_required": "Vérifiez votre identité pour continuer.",
    "generic": "Une erreur s'est produite. Veuillez réessayer."
  },
  "common": {
    "confirm": "Confirmer",
    "cancel": "Annuler",
    "continue": "Continuer",
    "back": "Retour",
    "save": "Enregistrer",
    "loading": "Chargement...",
    "retry": "Réessayer",
    "xaf": "XAF"
  }
}
```

```json
// locales/en.json
{
  "auth": {
    "login_title": "Sign In",
    "phone_placeholder": "Phone number",
    "password_placeholder": "Password",
    "login_button": "Sign in",
    "forgot_password": "Forgot password?",
    "no_account": "Don't have an account?"
  },
  "dashboard": {
    "total_balance": "Total Balance",
    "deposit": "Deposit",
    "withdraw": "Withdraw",
    "transfer": "Transfer",
    "greeting_morning": "Good morning, {name}",
    "greeting_afternoon": "Good afternoon, {name}",
    "greeting_evening": "Good evening, {name}"
  },
  "accounts": {
    "standard": "Savings Account",
    "project": "Project Account",
    "term_deposit": "Term Deposit",
    "new_project": "New Project",
    "target_amount": "Target amount",
    "target_date": "Target date",
    "progress": "{percent}% achieved",
    "milestone_25": "🎉 25% of your goal reached!",
    "milestone_50": "🎉 Halfway there! Keep going!",
    "milestone_75": "🔥 75%! Almost there!",
    "milestone_100": "🏆 Congratulations! Goal achieved!"
  },
  "transactions": {
    "deposit_success": "Deposit Successful",
    "deposit_failed": "Deposit Failed",
    "amount_deposited": "{amount} XAF added to your account.",
    "status_pending": "Pending",
    "status_processing": "Processing",
    "status_success": "Success",
    "status_failed": "Failed"
  },
  "errors": {
    "insufficient_balance": "Insufficient funds. Available: {available} XAF.",
    "kyc_required": "Please verify your identity to continue.",
    "generic": "Something went wrong. Please try again."
  },
  "common": {
    "confirm": "Confirm",
    "cancel": "Cancel",
    "continue": "Continue",
    "back": "Back",
    "save": "Save",
    "loading": "Loading...",
    "retry": "Retry",
    "xaf": "XAF"
  }
}
```

### Usage in Components
```typescript
import i18n from '@/locales';

// Simple string
<Text>{i18n.t('dashboard.total_balance')}</Text>

// String with interpolation
<Text>{i18n.t('dashboard.greeting_morning', { name: user.full_name })}</Text>

// Language switching (user profile setting)
const switchLanguage = (lang: 'fr' | 'en') => {
  i18n.locale = lang;
  // Save to user profile via API PATCH /users/me
};
```

---

## Web App (Next.js)

### Library: `next-intl`

```bash
npm install next-intl
```

### File Structure
```
/apps/web/
└── messages/
    ├── fr.json
    └── en.json
```

Use the same JSON structure as the mobile locales for consistency.
Shared translation keys between mobile and web wherever possible.

### Configuration
```typescript
// next.config.js
const withNextIntl = require('next-intl/plugin')('./i18n.ts');
module.exports = withNextIntl({});

// i18n.ts
import { getRequestConfig } from 'next-intl/server';
export default getRequestConfig(async ({ locale }) => ({
    messages: (await import(`./messages/${locale}.json`)).default
}));
```

---

## Number & Currency Formatting

**Always format XAF amounts consistently:**
```typescript
// Utility function — use everywhere, never format inline
export const formatXAF = (amountInSmallestUnit: number, locale: string = 'fr'): string => {
    const amount = amountInSmallestUnit / 100;
    return new Intl.NumberFormat(locale === 'fr' ? 'fr-CM' : 'en-CM', {
        style: 'currency',
        currency: 'XAF',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
};
// Result: "5 000 XAF" (fr) or "XAF 5,000" (en)
```

**Date formatting:**
```typescript
export const formatDate = (date: string, locale: string = 'fr'): string => {
    return new Intl.DateTimeFormat(locale === 'fr' ? 'fr-CM' : 'en-CM', {
        day: 'numeric', month: 'long', year: 'numeric'
    }).format(new Date(date));
};
// Result: "21 février 2026" (fr) or "February 21, 2026" (en)
```

---

## Roadmap Languages

| Language | Priority | Notes |
|---|---|---|
| French (fr) | ✅ Launch | Primary — Cameroon majority |
| English (en) | ✅ Launch | Anglophone regions (SW, NW) |
| Arabic (ar) | Phase 3 | Adamawa, North, Far North regions |
| Pidgin English | Future | Informal — marketing materials only |
| Fulfuldé | Future | Pastoral communities |

**RTL support for Arabic:** Ensure React Native and Next.js layouts support `direction: rtl` before adding Arabic.
