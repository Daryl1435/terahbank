# TerahBank — Feature Flags

> Control feature availability without code deployments.
> Enables safe rollouts, A/B testing, emergency kill switches, and regulatory phasing.
> Phase 1 uses environment-variable-based flags. Phase 2 can upgrade to LaunchDarkly.

---

## Why Feature Flags for TerahBank

1. **Regulatory rollout** — COBAC may approve features in phases. Kill switch without deployment.
2. **Provider readiness** — Orange Money, VISA partner, insurance APIs may not be ready at launch.
3. **Gradual rollout** — enable features for beta users before full launch.
4. **Emergency kill switch** — disable a broken payment channel instantly without a deployment.

---

## Phase 1: Environment Variable Flags

All flags are read from environment variables. Changing them requires an ECS task restart (< 2 min).

### Flag Registry

```env
# Payment Channels
FEATURE_MTN_MOMO=true              # MTN Mobile Money deposits/withdrawals
FEATURE_ORANGE_MONEY=false         # Orange Money (Phase 2 — pending partner agreement)
FEATURE_VISA_CARD_PAYMENT=true     # VISA/MasterCard card deposits
FEATURE_VIRTUAL_CARD=true          # Virtual VISA card issuance

# Account Types
FEATURE_STANDARD_ACCOUNT=true      # Standard Savings Account
FEATURE_PROJECT_ACCOUNT=true       # Project Account (Vault)
FEATURE_TERM_DEPOSIT=true          # Term Deposit Account
FEATURE_MULTI_CARD=false           # Multiple virtual cards per user (Phase 2)

# Features
FEATURE_AUTO_SAVE=false            # Auto-save rules (Should Have — Phase 2)
FEATURE_INSURANCE=false            # Insurance products (Should Have — Phase 2)
FEATURE_SAVINGS_INSIGHTS=false     # Dashboard savings insights message (Phase 2)
FEATURE_BIOMETRIC_AUTH=true        # PIN + biometric login
FEATURE_FRAUD_DETECTION=true       # Fraud rules engine

# Platform
FEATURE_WEB_CUSTOMER_PORTAL=true   # Customer web app
FEATURE_ADMIN_PANEL=true           # Admin back-office
FEATURE_IOS_APP=false              # iOS app (Phase 2)

# Maintenance
FEATURE_MAINTENANCE_MODE=false     # Show maintenance screen to all users
FEATURE_READ_ONLY_MODE=false       # Allow reads, block all writes (DB maintenance)
```

---

## Flag Access Pattern (Backend — FastAPI)

```python
# core/feature_flags.py
import os
from functools import lru_cache

class FeatureFlags:
    @staticmethod
    def is_enabled(flag: str) -> bool:
        return os.getenv(f"FEATURE_{flag.upper()}", "false").lower() == "true"

    # Convenience properties
    @property
    def mtn_momo(self) -> bool: return self.is_enabled("MTN_MOMO")
    @property
    def orange_money(self) -> bool: return self.is_enabled("ORANGE_MONEY")
    @property
    def virtual_card(self) -> bool: return self.is_enabled("VIRTUAL_CARD")
    @property
    def insurance(self) -> bool: return self.is_enabled("INSURANCE")
    @property
    def maintenance_mode(self) -> bool: return self.is_enabled("MAINTENANCE_MODE")

flags = FeatureFlags()

# Usage in routes
@router.post("/transactions/deposit")
async def deposit(payload: DepositRequest):
    if payload.channel == "orange_money" and not flags.orange_money:
        raise HTTPException(422, detail={"code": "FEATURE_UNAVAILABLE",
            "message": "Orange Money is not available yet."})
    ...
```

### Maintenance Mode Middleware
```python
# middleware/maintenance.py
@app.middleware("http")
async def maintenance_check(request: Request, call_next):
    if flags.maintenance_mode:
        # Allow admin endpoints through
        if request.url.path.startswith("/api/v1/admin"):
            return await call_next(request)
        return JSONResponse(
            status_code=503,
            content={"success": False, "error": {
                "code": "MAINTENANCE_MODE",
                "message": "TerahBank est en maintenance. Revenez dans quelques minutes."
            }}
        )
    return await call_next(request)
```

---

## Flag Access Pattern (Mobile — React Native)

```typescript
// hooks/useFeatureFlags.ts
// Flags are fetched from API on app launch and cached

interface FeatureFlags {
  mtnMomo: boolean;
  orangeMoney: boolean;
  virtualCard: boolean;
  insurance: boolean;
  autoSave: boolean;
  maintenanceMode: boolean;
}

// Backend exposes: GET /api/v1/config/features (public endpoint)
// Returns: { flags: { mtn_momo: true, orange_money: false, ... } }

export const useFeatureFlags = () => {
  const { data: flags } = useQuery(['feature-flags'], fetchFlags, {
    staleTime: 5 * 60 * 1000,  // Cache for 5 minutes
    cacheTime: 30 * 60 * 1000
  });
  return flags ?? DEFAULT_FLAGS;
};

// Usage in components
const { virtualCard, insurance } = useFeatureFlags();
{virtualCard && <VirtualCardTab />}
{insurance && <InsuranceTab />}
```

---

## Flag Access Pattern (Web/Admin — Next.js)

```typescript
// lib/featureFlags.ts (server-side)
export const getFeatureFlags = () => ({
  mtnMomo: process.env.FEATURE_MTN_MOMO === 'true',
  orangeMoney: process.env.FEATURE_ORANGE_MONEY === 'true',
  virtualCard: process.env.FEATURE_VIRTUAL_CARD === 'true',
  insurance: process.env.FEATURE_INSURANCE === 'true',
  maintenanceMode: process.env.FEATURE_MAINTENANCE_MODE === 'true',
});

// In page components (server component)
export default async function DashboardPage() {
  const flags = getFeatureFlags();
  return <Dashboard flags={flags} />;
}
```

---

## Launch Readiness Flag State

The table below defines the expected flag values for each milestone:

| Flag | Local Dev | Staging | Launch (Production) | Phase 2 |
|---|---|---|---|---|
| `FEATURE_MTN_MOMO` | true | true | true | true |
| `FEATURE_ORANGE_MONEY` | false | true (testing) | false → true | true |
| `FEATURE_VISA_CARD_PAYMENT` | true | true | true | true |
| `FEATURE_VIRTUAL_CARD` | true | true | true | true |
| `FEATURE_STANDARD_ACCOUNT` | true | true | true | true |
| `FEATURE_PROJECT_ACCOUNT` | true | true | true | true |
| `FEATURE_TERM_DEPOSIT` | true | true | true | true |
| `FEATURE_AUTO_SAVE` | false | true (testing) | false | true |
| `FEATURE_INSURANCE` | false | true (testing) | false | true |
| `FEATURE_MULTI_CARD` | false | false | false | true |
| `FEATURE_IOS_APP` | false | false | false | true |

---

## Emergency Procedures

### Kill switch — MTN MoMo is down
```bash
# Update AWS SSM Parameter Store (ECS auto-reloads on next task start)
aws ssm put-parameter --name /terahbank/prod/FEATURE_MTN_MOMO --value "false" --overwrite
# Restart ECS tasks to pick up new env value
aws ecs update-service --cluster terahbank-prod --service api --force-new-deployment
# Time to take effect: ~2 minutes
```

### Enable maintenance mode (emergency)
```bash
aws ssm put-parameter --name /terahbank/prod/FEATURE_MAINTENANCE_MODE --value "true" --overwrite
aws ecs update-service --cluster terahbank-prod --service api --force-new-deployment
```

---

## Phase 2: Upgrade to LaunchDarkly (When Needed)

When you need:
- Per-user / per-segment flag targeting
- Gradual percentage rollouts (e.g. enable for 10% of users)
- A/B testing
- Real-time flag changes without ECS restart

Migrate to LaunchDarkly SDK — the flag access pattern via `flags.is_enabled()` stays the same, only the backing implementation changes.
