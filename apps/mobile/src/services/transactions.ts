import { getAccessToken } from '@/stores/authStore';
import 'react-native-get-random-values';
import { v4 as uuidv4 } from 'uuid';

const BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL;

// -- Types --

export type TransactionType = 'deposit' | 'withdrawal' | 'transfer' | 'fee' | 'interest' | 'penalty';
export type TransactionChannel = 'mtn_momo' | 'orange_money' | 'visa' | 'mastercard' | 'internal';
export type TransactionStatus = 'pending' | 'processing' | 'success' | 'failed' | 'reversed';

export interface Transaction {
  id: string;
  reference: string;
  amount: number;           // BIGINT — smallest XAF unit. NEVER FLOAT.
  currency: string;
  transaction_type: TransactionType;
  channel: TransactionChannel;
  status: TransactionStatus;
  created_at: string;
  completed_at?: string;
}

export interface DepositRequest {
  account_id: string;
  amount: number;           // BIGINT
  channel: 'mtn_momo' | 'orange_money' | 'visa' | 'mastercard';
  idempotency_key?: string; // Auto-generated if not provided
}

export interface WithdrawRequest {
  account_id: string;
  amount: number;           // BIGINT
  channel: 'mtn_momo' | 'orange_money';
  destination_phone: string; // E.164 — mobile wallet receiving the funds
  pin_token: string;         // Single-use token from POST /auth/verify-pin
  idempotency_key?: string;
}

export interface TransferRequest {
  from_account_id: string;
  to_account_id?: string;           // own account transfer
  to_phone_or_account?: string;     // TerahBank-user transfer
  amount: number;                   // BIGINT
  pin_token: string;
  idempotency_key?: string;
}

// -- Helpers --

const authHeaders = async (idempotencyKey: string): Promise<HeadersInit> => {
  const token = await getAccessToken();
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
    'Idempotency-Key': idempotencyKey,
  };
};

const handleResponse = async <T>(res: Response): Promise<T> => {
  const json = await res.json();
  if (!res.ok || !json.success) {
    throw new Error(json.error?.message ?? 'Request failed');
  }
  return json.data as T;
};

// -- Service --

export const transactionsService = {
  listTransactions: async (params?: {
    account_id?: string;
    page?: number;
    limit?: number;
  }): Promise<Transaction[]> => {
    const token = await getAccessToken();
    const query = new URLSearchParams(params as Record<string, string>).toString();
    const res = await fetch(`${BASE_URL}/api/v1/transactions${query ? `?${query}` : ''}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return handleResponse(res);
  },

  getTransaction: async (transactionId: string): Promise<Transaction> => {
    const token = await getAccessToken();
    const res = await fetch(`${BASE_URL}/api/v1/transactions/${transactionId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return handleResponse(res);
  },

  pollStatus: async (transactionId: string): Promise<{ status: TransactionStatus }> => {
    const token = await getAccessToken();
    const res = await fetch(`${BASE_URL}/api/v1/transactions/${transactionId}/status`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return handleResponse(res);
  },

  deposit: async (payload: DepositRequest): Promise<Transaction> => {
    const key = payload.idempotency_key ?? uuidv4();
    const headers = await authHeaders(key);
    const res = await fetch(`${BASE_URL}/api/v1/transactions/deposit`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ ...payload, idempotency_key: key }),
    });
    return handleResponse(res);
  },

  withdraw: async (payload: WithdrawRequest): Promise<Transaction> => {
    const key = payload.idempotency_key ?? uuidv4();
    const headers = await authHeaders(key);
    const res = await fetch(`${BASE_URL}/api/v1/transactions/withdraw`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ ...payload, idempotency_key: key }),
    });
    return handleResponse(res);
  },

  transfer: async (payload: TransferRequest): Promise<Transaction> => {
    const key = payload.idempotency_key ?? uuidv4();
    const headers = await authHeaders(key);
    const res = await fetch(`${BASE_URL}/api/v1/transactions/transfer`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ ...payload, idempotency_key: key }),
    });
    return handleResponse(res);
  },
};
