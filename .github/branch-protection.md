# Branch Protection Rules

Configure these in GitHub → Settings → Branches → Add rule.
These cannot be automated without a GitHub token — do this once when the repo is created.

## `main` branch

- **Require a pull request before merging**: ✅
  - Required approvals: **2**
  - Dismiss stale pull request approvals when new commits are pushed: ✅
  - Require review from Code Owners: ✅ (uses `.github/CODEOWNERS`)
- **Require status checks to pass before merging**: ✅
  - Required checks: `backend-lint-test`, `frontend-lint-test`, `mobile-lint`, `security-scan`
  - Require branches to be up to date before merging: ✅
- **Require conversation resolution before merging**: ✅
- **Require signed commits**: ✅
- **Do not allow bypassing the above settings**: ✅
- **Restrict who can push to matching branches**: `@ibridge-team/backend-leads` only

## `staging` branch

- **Require a pull request before merging**: ✅
  - Required approvals: **1**
  - Require review from Code Owners: ✅
- **Require status checks to pass before merging**: ✅
  - Required checks: `backend-lint-test`, `frontend-lint-test`, `mobile-lint`
- **Require conversation resolution before merging**: ✅

## GitHub Environments

Set up two environments in GitHub → Settings → Environments:

### `staging`
- No required reviewers (auto-deploys on push to staging branch)
- Secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `VERCEL_TOKEN`, `E2E_TEST_USER_PHONE`, `E2E_TEST_USER_PASSWORD`, `STAGING_SUBNET_ID`, `STAGING_SG_ID`, `AWS_ACCOUNT_ID`

### `production`
- Required reviewers: **2** from `@ibridge-team/backend-leads`
- Secrets: `PROD_AWS_ACCESS_KEY_ID`, `PROD_AWS_SECRET_ACCESS_KEY`, `VERCEL_TOKEN`, `PROD_SUBNET_ID`, `PROD_SG_ID`, `AWS_ACCOUNT_ID`
- Deployment branches: `main` only
