// Typed API client for all admin endpoints.
// All requests add Authorization: Bearer <admin_token> from cookies.

import { getToken } from './auth';
import type {
  AdminLoginData,
  AdminTransactionListData,
  AdminUserDetail,
  AdminUserListData,
  ConfigListData,
  FraudAlertListData,
  KYCQueueData,
  TerahResponse,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1';

class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly code?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const message = body?.detail?.message ?? body?.detail ?? `HTTP ${res.status}`;
    const code    = body?.detail?.code ?? undefined;
    throw new ApiError(res.status, message, code);
  }

  return res.json() as Promise<T>;
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export async function adminLogin(
  email: string,
  password: string,
): Promise<TerahResponse<AdminLoginData>> {
  return apiFetch('/admin/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

// ── Users ─────────────────────────────────────────────────────────────────────

export async function listUsers(params: {
  search?: string;
  kyc_status?: string;
  account_status?: string;
  offset?: number;
  limit?: number;
}): Promise<TerahResponse<AdminUserListData>> {
  const q = new URLSearchParams();
  if (params.search)         q.set('search', params.search);
  if (params.kyc_status)     q.set('kyc_status', params.kyc_status);
  if (params.account_status) q.set('account_status', params.account_status);
  if (params.offset != null) q.set('offset', String(params.offset));
  if (params.limit  != null) q.set('limit',  String(params.limit));
  return apiFetch(`/admin/users?${q}`);
}

export async function getUser(userId: string): Promise<TerahResponse<AdminUserDetail>> {
  return apiFetch(`/admin/users/${userId}`);
}

export async function updateUserStatus(
  userId: string,
  status: 'active' | 'suspended' | 'closed',
): Promise<TerahResponse<{ user_id: string; account_status: string }>> {
  return apiFetch(`/admin/users/${userId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

// ── KYC ──────────────────────────────────────────────────────────────────────

export async function getKYCQueue(params: {
  offset?: number;
  limit?: number;
}): Promise<TerahResponse<KYCQueueData>> {
  const q = new URLSearchParams();
  if (params.offset != null) q.set('offset', String(params.offset));
  if (params.limit  != null) q.set('limit',  String(params.limit));
  return apiFetch(`/admin/kyc/queue?${q}`);
}

export async function makeKYCDecision(
  userId: string,
  decision: 'approved' | 'rejected',
  rejectionReason?: string,
): Promise<TerahResponse<{ user_id: string; kyc_status: string; document_id: string }>> {
  return apiFetch(`/admin/kyc/${userId}/decision`, {
    method: 'POST',
    body: JSON.stringify({ decision, rejection_reason: rejectionReason ?? null }),
  });
}

// ── Transactions ─────────────────────────────────────────────────────────────

export async function listTransactions(params: {
  user_id?: string;
  transaction_type?: string;
  channel?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  offset?: number;
  limit?: number;
}): Promise<TerahResponse<AdminTransactionListData>> {
  const q = new URLSearchParams();
  if (params.user_id)          q.set('user_id', params.user_id);
  if (params.transaction_type) q.set('transaction_type', params.transaction_type);
  if (params.channel)          q.set('channel', params.channel);
  if (params.status)           q.set('status', params.status);
  if (params.date_from)        q.set('date_from', params.date_from);
  if (params.date_to)          q.set('date_to', params.date_to);
  if (params.offset != null)   q.set('offset', String(params.offset));
  if (params.limit  != null)   q.set('limit',  String(params.limit));
  return apiFetch(`/admin/transactions?${q}`);
}

// ── Config ────────────────────────────────────────────────────────────────────

export async function getConfig(): Promise<TerahResponse<ConfigListData>> {
  return apiFetch('/admin/config');
}

export async function updateConfig(
  key: string,
  value: string,
): Promise<TerahResponse<{ key: string; value: string; updated_at: string }>> {
  return apiFetch('/admin/config', {
    method: 'PATCH',
    body: JSON.stringify({ key, value }),
  });
}

// ── Fraud alerts ──────────────────────────────────────────────────────────────

export async function getFraudAlerts(params: {
  offset?: number;
  limit?: number;
}): Promise<TerahResponse<FraudAlertListData>> {
  const q = new URLSearchParams();
  if (params.offset != null) q.set('offset', String(params.offset));
  if (params.limit  != null) q.set('limit',  String(params.limit));
  return apiFetch(`/admin/fraud-alerts?${q}`);
}

// ── Reports (CSV download — browser-initiated) ────────────────────────────────

export function downloadTransactionsCSV(dateFrom?: string, dateTo?: string): void {
  const token = getToken();
  const q = new URLSearchParams();
  if (dateFrom) q.set('date_from', dateFrom);
  if (dateTo)   q.set('date_to', dateTo);
  // Open in new tab — browser handles file download
  const url = `${API_BASE}/admin/reports/transactions?${q}`;
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.setAttribute('download', '');
  // Pass token via query param since we can't set headers on anchor download
  // The backend needs to support ?token= for report downloads — use fetch approach instead
  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then((res) => res.blob())
    .then((blob) => {
      const blobUrl = URL.createObjectURL(blob);
      anchor.href = blobUrl;
      anchor.click();
      URL.revokeObjectURL(blobUrl);
    });
}

export function downloadUsersCSV(): void {
  const token = getToken();
  const url = `${API_BASE}/admin/reports/users`;
  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then((res) => res.blob())
    .then((blob) => {
      const blobUrl = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = blobUrl;
      anchor.setAttribute('download', 'users.csv');
      anchor.click();
      URL.revokeObjectURL(blobUrl);
    });
}

export function downloadInsuranceCommissionsCSV(): void {
  const token = getToken();
  const url = `${API_BASE}/admin/reports/insurance-commissions`;
  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then((res) => res.blob())
    .then((blob) => {
      const blobUrl = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = blobUrl;
      anchor.setAttribute('download', 'insurance_commissions.csv');
      anchor.click();
      URL.revokeObjectURL(blobUrl);
    });
}
