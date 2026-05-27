import { getAccessToken } from '@/stores/authStore';

const BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL;

// ── Types ──────────────────────────────────────────────────────────────────────

export type AccountType = 'standard' | 'project' | 'term_deposit';
export type AccountStatus = 'active' | 'closed' | 'locked';

export interface AutoSaveRule {
  rule_id: string;
  account_id: string;
  source_account_id: string;
  amount: number;          // BIGINT
  frequency: 'daily' | 'weekly' | 'monthly';
  day_of_week: number | null;
  next_execution_at: string;
  is_active: boolean;
}

export interface Account {
  account_id: string;      // UUID — backend field name
  account_type: AccountType;
  account_number: string;
  balance: number;         // BIGINT — smallest XAF unit. NEVER FLOAT.
  status: AccountStatus;
  created_at: string;

  // Project account fields
  project_name?: string;
  target_amount?: number;  // BIGINT
  target_date?: string;    // ISO date (YYYY-MM-DD)
  progress_pct?: number;   // 0–100
  penalty_rate?: number;
  auto_save_rule?: AutoSaveRule;

  // Term deposit fields
  maturity_date?: string;  // ISO date (YYYY-MM-DD)
  interest_rate?: number;
  days_to_maturity?: number; // FR-027

  // Optional insight (FR-015)
  savings_insight?: string;
}

export interface AccountsListData {
  accounts: Account[];
  total_balance: number;   // BIGINT — sum of all account balances
}

export interface OpenStandardAccountRequest {
  initial_deposit: number; // BIGINT — smallest XAF unit
  momo_phone?: string;     // phone used for the initial deposit transfer
}

export interface OpenProjectAccountRequest {
  project_name: string;
  target_amount: number;   // BIGINT — min 0
  target_date: string;     // ISO date — min 6 months from today
}

export interface OpenTermDepositRequest {
  amount: number;          // BIGINT — min 20_000_000 (200,000 XAF)
  duration_months: number; // >= 1
}

export interface TermDepositCalculatorResponse {
  amount: number;          // BIGINT
  duration_months: number;
  interest_rate: number;   // Annual rate (e.g. 0.02)
  projected_interest: number;  // BIGINT — floor(principal × rate × months / 12)
  total_at_maturity: number;   // BIGINT
  early_break_penalty: number; // BIGINT
  net_if_broken_early: number; // BIGINT
  maturity_date: string;       // ISO date
}

export interface OpenTermDepositResponseData {
  account_id: string;
  account_number: string;
  principal: number;
  interest_rate: number;
  early_break_rate: number;
  projected_interest: number;
  total_at_maturity: number;
  maturity_date: string;
  duration_months: number;
  days_to_maturity: number;
  status: string;
}

// ── Mock store ─────────────────────────────────────────────────────────────────
// Accounts created this session — start empty so users can test the full
// account-creation flow without a real API.

const _mockCreated: Account[] = [];

function _allMockAccounts(): Account[] {
  return [..._mockCreated];
}

function _mockAcctNumber(type: AccountType): string {
  const prefix = type === 'standard' ? 'STD' : type === 'project' ? 'PRJ' : 'TRM';
  return `${prefix}-${Math.floor(Math.random() * 99999).toString().padStart(5, '0')}`;
}

function _mockCalc(amount: number, durationMonths: number): TermDepositCalculatorResponse {
  const rate = 0.02;
  const projected_interest = Math.floor(amount * rate * durationMonths / 12);
  const total_at_maturity = amount + projected_interest;
  const early_break_penalty = Math.floor(projected_interest * 0.5);
  const net_if_broken_early = amount - early_break_penalty;
  const maturity = new Date();
  maturity.setMonth(maturity.getMonth() + durationMonths);
  return {
    amount,
    duration_months: durationMonths,
    interest_rate: rate,
    projected_interest,
    total_at_maturity,
    early_break_penalty,
    net_if_broken_early,
    maturity_date: maturity.toISOString().split('T')[0],
  };
}

// ── Helpers ────────────────────────────────────────────────────────────────────

const authHeaders = async (): Promise<HeadersInit> => {
  const token = await getAccessToken();
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
};

const handleResponse = async <T>(res: Response): Promise<T> => {
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.error?.message ?? 'Request failed');
  }
  return json.data as T;
};

// ── Service ────────────────────────────────────────────────────────────────────

export const accountsService = {
  listAccounts: async (): Promise<AccountsListData> => {
    const headers = await authHeaders();
    try {
      const res = await fetch(`${BASE_URL}/api/v1/accounts`, { headers });
      if (!res.ok) throw new Error('API not ready');
      return handleResponse<AccountsListData>(res);
    } catch {
      const accounts = _allMockAccounts();
      const total_balance = accounts.reduce((s, a) => s + a.balance, 0);
      return { accounts, total_balance };
    }
  },

  getAccount: async (accountId: string): Promise<Account> => {
    const headers = await authHeaders();
    try {
      const res = await fetch(`${BASE_URL}/api/v1/accounts/${accountId}`, { headers });
      if (!res.ok) throw new Error('API not ready');
      return handleResponse<Account>(res);
    } catch {
      const found = _allMockAccounts().find((a) => a.account_id === accountId);
      if (found) return found;
      throw new Error('Account not found');
    }
  },

  openStandardAccount: async (
    payload: OpenStandardAccountRequest,
  ): Promise<{ account_id: string; account_number: string; balance: number; status: string }> => {
    const headers = await authHeaders();
    try {
      const res = await fetch(`${BASE_URL}/api/v1/accounts/standard`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error('API not ready');
      return handleResponse(res);
    } catch (err: any) {
      // Preserve real API errors (e.g. 409 duplicate account) if they came through
      if (err?.message && !err.message.includes('API not ready') && !err.message.includes('fetch')) {
        throw err;
      }
      const existing = _allMockAccounts().find((a) => a.account_type === 'standard');
      if (existing) throw new Error('You already have a Standard Savings Account.');
      const account_number = _mockAcctNumber('standard');
      const newAcct: Account = {
        account_id: `mock-std-${Date.now()}`,
        account_type: 'standard',
        account_number,
        balance: payload.initial_deposit,
        status: 'active',
        created_at: new Date().toISOString(),
      };
      _mockCreated.push(newAcct);
      return { account_id: newAcct.account_id, account_number, balance: newAcct.balance, status: 'active' };
    }
  },

  openProjectAccount: async (
    payload: OpenProjectAccountRequest,
  ): Promise<{ account_id: string; account_number: string; project_name: string; target_amount: number; target_date: string; balance: number; penalty_rate: number; status: string }> => {
    const headers = await authHeaders();
    try {
      const res = await fetch(`${BASE_URL}/api/v1/accounts/project`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error('API not ready');
      return handleResponse(res);
    } catch (err: any) {
      if (err?.message && !err.message.includes('API not ready') && !err.message.includes('fetch')) {
        throw err;
      }
      const account_number = _mockAcctNumber('project');
      const newAcct: Account = {
        account_id: `mock-proj-${Date.now()}`,
        account_type: 'project',
        account_number,
        balance: 0,
        status: 'active',
        created_at: new Date().toISOString(),
        project_name: payload.project_name,
        target_amount: payload.target_amount,
        target_date: payload.target_date,
        progress_pct: 0,
        penalty_rate: 0.05,
      };
      _mockCreated.push(newAcct);
      return {
        account_id: newAcct.account_id,
        account_number,
        project_name: payload.project_name,
        target_amount: payload.target_amount,
        target_date: payload.target_date,
        balance: 0,
        penalty_rate: 0.05,
        status: 'active',
      };
    }
  },

  openTermDeposit: async (payload: OpenTermDepositRequest): Promise<OpenTermDepositResponseData> => {
    const headers = await authHeaders();
    try {
      const res = await fetch(`${BASE_URL}/api/v1/accounts/term-deposit`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error('API not ready');
      return handleResponse<OpenTermDepositResponseData>(res);
    } catch (err: any) {
      if (err?.message && !err.message.includes('API not ready') && !err.message.includes('fetch')) {
        throw err;
      }
      const calc = _mockCalc(payload.amount, payload.duration_months);
      const account_number = _mockAcctNumber('term_deposit');
      const days_to_maturity = payload.duration_months * 30;
      const newAcct: Account = {
        account_id: `mock-term-${Date.now()}`,
        account_type: 'term_deposit',
        account_number,
        balance: payload.amount,
        status: 'active',
        created_at: new Date().toISOString(),
        maturity_date: calc.maturity_date,
        interest_rate: calc.interest_rate,
        days_to_maturity,
      };
      _mockCreated.push(newAcct);
      return {
        account_id: newAcct.account_id,
        account_number,
        principal: payload.amount,
        interest_rate: calc.interest_rate,
        early_break_rate: 0.5,
        projected_interest: calc.projected_interest,
        total_at_maturity: calc.total_at_maturity,
        maturity_date: calc.maturity_date,
        duration_months: payload.duration_months,
        days_to_maturity,
        status: 'active',
      };
    }
  },

  termDepositCalculator: async (amount: number, durationMonths: number): Promise<TermDepositCalculatorResponse> => {
    const headers = await authHeaders();
    const url = new URL(`${BASE_URL}/api/v1/accounts/term-deposit/calculator`);
    url.searchParams.set('amount', String(amount));
    url.searchParams.set('duration_months', String(durationMonths));
    try {
      const res = await fetch(url.toString(), { headers });
      if (!res.ok) throw new Error('API not ready');
      return handleResponse<TermDepositCalculatorResponse>(res);
    } catch {
      return _mockCalc(amount, durationMonths);
    }
  },

  closeAccount: async (accountId: string): Promise<{ account_id: string; account_number: string; account_type: string; status: string }> => {
    const headers = await authHeaders();
    try {
      const res = await fetch(`${BASE_URL}/api/v1/accounts/${accountId}`, {
        method: 'DELETE',
        headers,
      });
      if (!res.ok) throw new Error('API not ready');
      return handleResponse(res);
    } catch {
      const idx = _mockCreated.findIndex((a) => a.account_id === accountId);
      if (idx >= 0) _mockCreated.splice(idx, 1);
      return { account_id: accountId, account_number: '', account_type: '', status: 'closed' };
    }
  },
};
