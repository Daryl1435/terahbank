import { getAccessToken } from '@/stores/authStore';
import 'react-native-get-random-values';
import { v4 as uuidv4 } from 'uuid';

const BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL;

// ── Types ──────────────────────────────────────────────────────────────────────

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
  idempotency_key?: string;
}

export interface WithdrawRequest {
  account_id: string;
  amount: number;           // BIGINT
  channel: 'mtn_momo' | 'orange_money';
  destination_phone: string;
  pin_token: string;
  idempotency_key?: string;
}

export interface TransferRequest {
  from_account_id: string;
  to_account_id?: string;
  to_phone_or_account?: string;
  amount: number;           // BIGINT
  pin_token: string;
  idempotency_key?: string;
}

// ── HTTP helpers ───────────────────────────────────────────────────────────────

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

// ── Dev simulation layer ───────────────────────────────────────────────────────
// Activated when the real API is unreachable or returns an error.
// Gives a realistic pending → processing → success flow so the full UI can be
// tested before MoMo/Orange Money backends are wired up.

const _now = Date.now();

// Pre-seeded history shown in TransactionHistoryScreen
const _mockHistory: Transaction[] = [
  {
    id: 'mock-hist-1',
    reference: 'TRH-DEP-250101',
    amount: 500000,        // 5,000 XAF
    currency: 'XAF',
    transaction_type: 'deposit',
    channel: 'mtn_momo',
    status: 'success',
    created_at: new Date(_now - 6 * 86_400_000).toISOString(),
    completed_at: new Date(_now - 6 * 86_400_000 + 8_000).toISOString(),
  },
  {
    id: 'mock-hist-2',
    reference: 'TRH-TRF-250103',
    amount: 200000,        // 2,000 XAF
    currency: 'XAF',
    transaction_type: 'transfer',
    channel: 'internal',
    status: 'success',
    created_at: new Date(_now - 4 * 86_400_000).toISOString(),
    completed_at: new Date(_now - 4 * 86_400_000 + 1_500).toISOString(),
  },
  {
    id: 'mock-hist-3',
    reference: 'TRH-WDR-250105',
    amount: 100000,        // 1,000 XAF
    currency: 'XAF',
    transaction_type: 'withdrawal',
    channel: 'orange_money',
    status: 'failed',
    created_at: new Date(_now - 2 * 86_400_000).toISOString(),
  },
  {
    id: 'mock-hist-4',
    reference: 'TRH-DEP-250107',
    amount: 1_000_000,     // 10,000 XAF
    currency: 'XAF',
    transaction_type: 'deposit',
    channel: 'mtn_momo',
    status: 'success',
    created_at: new Date(_now - 86_400_000).toISOString(),
    completed_at: new Date(_now - 86_400_000 + 6_000).toISOString(),
  },
  {
    id: 'mock-hist-5',
    reference: 'TRH-INT-250101',
    amount: 5_000,         // 50 XAF interest
    currency: 'XAF',
    transaction_type: 'interest',
    channel: 'internal',
    status: 'success',
    created_at: new Date(_now - 7 * 86_400_000).toISOString(),
    completed_at: new Date(_now - 7 * 86_400_000 + 500).toISOString(),
  },
];

// Tracks transactions created in this session (id → createdAt ms timestamp)
const _mockLiveStore = new Map<string, { txn: Transaction; createdAt: number }>();

function _mockRef(type: TransactionType): string {
  const prefix = type === 'deposit' ? 'DEP' : type === 'withdrawal' ? 'WDR' : 'TRF';
  const suffix = Math.floor(Math.random() * 999999).toString().padStart(6, '0');
  return `TRH-${prefix}-${suffix}`;
}

function _mockStatusByAge(createdAt: number): TransactionStatus {
  const age = Date.now() - createdAt;
  if (age < 4_000) return 'pending';
  if (age < 9_000) return 'processing';
  return 'success';
}

function _makeMockTxn(
  type: TransactionType,
  channel: TransactionChannel,
  amount: number,
): Transaction & { transaction_id: string } {
  const id = uuidv4();
  const txn: Transaction = {
    id,
    reference: _mockRef(type),
    amount,
    currency: 'XAF',
    transaction_type: type,
    channel,
    status: 'pending',
    created_at: new Date().toISOString(),
  };
  _mockLiveStore.set(id, { txn, createdAt: Date.now() });
  _mockHistory.unshift(txn);
  return { ...txn, transaction_id: id };
}

// ── Service ────────────────────────────────────────────────────────────────────

export const transactionsService = {
  listTransactions: async (params?: {
    account_id?: string;
    status?: string;
    page?: number;
    limit?: number;
  }): Promise<Transaction[]> => {
    const token = await getAccessToken();
    // Filter out undefined/null so URLSearchParams doesn't produce "undefined" strings
    const clean = Object.fromEntries(
      Object.entries(params ?? {}).filter(([, v]) => v !== undefined && v !== null),
    ) as Record<string, string>;
    const query = new URLSearchParams(clean).toString();

    try {
      const res = await fetch(
        `${BASE_URL}/api/v1/transactions${query ? `?${query}` : ''}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!res.ok) throw new Error('API not ready');
      return handleResponse<Transaction[]>(res);
    } catch {
      // API unavailable — return simulated history filtered by requested status
      const statusFilter = params?.status;
      return statusFilter
        ? _mockHistory.filter((t) => t.status === statusFilter)
        : _mockHistory;
    }
  },

  getTransaction: async (transactionId: string): Promise<Transaction> => {
    // Check live mock store first (transactions created in this session)
    const live = _mockLiveStore.get(transactionId);
    if (live) {
      const status = _mockStatusByAge(live.createdAt);
      const completed_at =
        status === 'success' ? new Date().toISOString() : undefined;
      return { ...live.txn, status, ...(completed_at ? { completed_at } : {}) };
    }

    // Try real API
    const token = await getAccessToken();
    try {
      const res = await fetch(`${BASE_URL}/api/v1/transactions/${transactionId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('API not ready');
      return handleResponse<Transaction>(res);
    } catch {
      // Fall back to history snapshot
      const hist = _mockHistory.find((t) => t.id === transactionId);
      if (hist) return hist;
      throw new Error('Transaction not found');
    }
  },

  pollStatus: async (transactionId: string): Promise<{ status: TransactionStatus }> => {
    // For live mock transactions, age-based status progression
    const live = _mockLiveStore.get(transactionId);
    if (live) {
      const status = _mockStatusByAge(live.createdAt);
      // Sync the live store so getTransaction also returns the updated status
      _mockLiveStore.set(transactionId, { ...live, txn: { ...live.txn, status } });
      return { status };
    }

    const token = await getAccessToken();
    try {
      const res = await fetch(
        `${BASE_URL}/api/v1/transactions/${transactionId}/status`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!res.ok) throw new Error('API not ready');
      return handleResponse<{ status: TransactionStatus }>(res);
    } catch {
      return { status: 'success' };
    }
  },

  deposit: async (payload: DepositRequest): Promise<Transaction> => {
    const key = payload.idempotency_key ?? uuidv4();
    const headers = await authHeaders(key);
    try {
      const res = await fetch(`${BASE_URL}/api/v1/transactions/deposit`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ ...payload, idempotency_key: key }),
      });
      if (!res.ok) throw new Error('API not ready');
      return handleResponse<Transaction>(res);
    } catch {
      return _makeMockTxn('deposit', payload.channel as TransactionChannel, payload.amount) as any;
    }
  },

  withdraw: async (payload: WithdrawRequest): Promise<Transaction> => {
    const key = payload.idempotency_key ?? uuidv4();
    const headers = await authHeaders(key);
    try {
      const res = await fetch(`${BASE_URL}/api/v1/transactions/withdraw`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ ...payload, idempotency_key: key }),
      });
      if (!res.ok) throw new Error('API not ready');
      return handleResponse<Transaction>(res);
    } catch {
      return _makeMockTxn('withdrawal', payload.channel as TransactionChannel, payload.amount) as any;
    }
  },

  transfer: async (payload: TransferRequest): Promise<Transaction> => {
    const key = payload.idempotency_key ?? uuidv4();
    const headers = await authHeaders(key);
    try {
      const res = await fetch(`${BASE_URL}/api/v1/transactions/transfer`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ ...payload, idempotency_key: key }),
      });
      if (!res.ok) throw new Error('API not ready');
      return handleResponse<Transaction>(res);
    } catch {
      return _makeMockTxn('transfer', 'internal', payload.amount) as any;
    }
  },
};
