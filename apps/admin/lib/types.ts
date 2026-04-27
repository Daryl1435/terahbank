// Shared TypeScript types — mirror the API schemas exactly.

export type AdminRole = 'super_admin' | 'operations_staff' | 'read_only_analyst';

export interface TerahResponse<T> {
  success: boolean;
  data: T;
  message: string | null;
  timestamp: string;
}

// ── Auth ────────────────────────────────────────────────────────────────────

export interface AdminLoginData {
  access_token: string;
  token_type: string;
  role: AdminRole;
}

// ── Users ───────────────────────────────────────────────────────────────────

export interface AdminUserItem {
  user_id: string;
  full_name: string;
  email: string;
  phone_number: string;
  kyc_status: string;
  account_status: string;
  preferred_language: string;
  created_at: string;
}

export interface AccountSummary {
  account_id: string;
  account_type: string;
  account_number: string;
  balance: number;
  status: string;
}

export interface AdminUserDetail extends AdminUserItem {
  accounts: AccountSummary[];
}

export interface AdminUserListData {
  users: AdminUserItem[];
  total: number;
  offset: number;
  limit: number;
}

// ── KYC ─────────────────────────────────────────────────────────────────────

export interface KYCQueueItem {
  document_id: string;
  user_id: string;
  full_name: string;
  email: string;
  phone_number: string;
  document_type: string;
  uploaded_at: string;
}

export interface KYCQueueData {
  items: KYCQueueItem[];
  total: number;
  offset: number;
  limit: number;
}

// ── Transactions ─────────────────────────────────────────────────────────────

export interface AdminTransactionItem {
  transaction_id: string;
  reference: string;
  user_id: string;
  transaction_type: string;
  channel: string;
  amount: number;
  currency: string;
  status: string;
  debit_account_id: string | null;
  credit_account_id: string | null;
  external_reference: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface AdminTransactionListData {
  transactions: AdminTransactionItem[];
  total: number;
  offset: number;
  limit: number;
}

// ── Config ───────────────────────────────────────────────────────────────────

export interface ConfigItem {
  key: string;
  value: string;
  updated_at: string;
}

export interface ConfigListData {
  config: ConfigItem[];
}

// ── Fraud alerts ─────────────────────────────────────────────────────────────

export interface FraudAlertItem {
  alert_id: string;
  rule: string;
  actor_id: string;
  entity_type: string;
  entity_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface FraudAlertListData {
  alerts: FraudAlertItem[];
  total: number;
  offset: number;
  limit: number;
}
