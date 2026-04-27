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
    const res = await fetch(`${BASE_URL}/api/v1/accounts`, { headers });
    return handleResponse<AccountsListData>(res);
  },

  getAccount: async (accountId: string): Promise<Account> => {
    const headers = await authHeaders();
    const res = await fetch(`${BASE_URL}/api/v1/accounts/${accountId}`, { headers });
    return handleResponse<Account>(res);
  },

  openStandardAccount: async (payload: OpenStandardAccountRequest): Promise<{ account_id: string; account_number: string; balance: number; status: string }> => {
    const headers = await authHeaders();
    const res = await fetch(`${BASE_URL}/api/v1/accounts/standard`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  openProjectAccount: async (payload: OpenProjectAccountRequest): Promise<{ account_id: string; account_number: string; project_name: string; target_amount: number; target_date: string; balance: number; penalty_rate: number; status: string }> => {
    const headers = await authHeaders();
    const res = await fetch(`${BASE_URL}/api/v1/accounts/project`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  openTermDeposit: async (payload: OpenTermDepositRequest): Promise<OpenTermDepositResponseData> => {
    const headers = await authHeaders();
    const res = await fetch(`${BASE_URL}/api/v1/accounts/term-deposit`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });
    return handleResponse<OpenTermDepositResponseData>(res);
  },

  termDepositCalculator: async (amount: number, durationMonths: number): Promise<TermDepositCalculatorResponse> => {
    const headers = await authHeaders();
    const url = new URL(`${BASE_URL}/api/v1/accounts/term-deposit/calculator`);
    url.searchParams.set('amount', String(amount));
    url.searchParams.set('duration_months', String(durationMonths));
    const res = await fetch(url.toString(), { headers });
    return handleResponse<TermDepositCalculatorResponse>(res);
  },

  closeAccount: async (accountId: string): Promise<{ account_id: string; account_number: string; account_type: string; status: string }> => {
    const headers = await authHeaders();
    const res = await fetch(`${BASE_URL}/api/v1/accounts/${accountId}`, {
      method: 'DELETE',
      headers,
    });
    return handleResponse(res);
  },
};
