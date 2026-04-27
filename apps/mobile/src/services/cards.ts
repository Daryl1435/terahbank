import { getAccessToken } from '@/stores/authStore';
import 'react-native-get-random-values';
import { v4 as uuidv4 } from 'uuid';

const BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL;

// -- Types --

export type CardStatus = 'active' | 'frozen' | 'expired' | 'cancelled';

export interface Card {
  card_id: string;
  account_id: string;
  last_four: string;
  expiry_date: string;   // YYYY-MM-DD
  status: CardStatus;
  daily_limit: number | null;
  per_transaction_limit: number | null;
  created_at: string;
}

export interface IssueCardRequest {
  account_id: string;
}

export interface UpdateLimitsRequest {
  daily_limit?: number;            // BIGINT smallest XAF unit
  per_transaction_limit?: number;  // BIGINT smallest XAF unit
}

// -- API helpers --

async function authHeaders(): Promise<Record<string, string>> {
  const token = await getAccessToken();
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

// -- Card API functions --

export async function fetchCards(): Promise<Card[]> {
  const resp = await fetch(`${BASE_URL}/api/v1/cards/`, {
    headers: await authHeaders(),
  });
  const json = await resp.json();
  if (!resp.ok || !json.success) {
    throw new Error(json?.data?.message ?? json?.message ?? 'Failed to load cards');
  }
  return (json.data?.cards ?? []) as Card[];
}

export async function issueCard(payload: IssueCardRequest): Promise<Card> {
  const idempotency_key = uuidv4();
  const resp = await fetch(`${BASE_URL}/api/v1/cards/`, {
    method: 'POST',
    headers: { ...(await authHeaders()), 'Idempotency-Key': idempotency_key },
    body: JSON.stringify(payload),
  });
  const json = await resp.json();
  if (!resp.ok || !json.success) {
    const detail = json?.detail;
    throw new Error(
      typeof detail === 'object'
        ? detail?.message ?? JSON.stringify(detail)
        : detail ?? 'Card issuance failed',
    );
  }
  return json.data as Card;
}

export async function freezeCard(cardId: string): Promise<Card> {
  const resp = await fetch(`${BASE_URL}/api/v1/cards/${cardId}/freeze`, {
    method: 'PATCH',
    headers: await authHeaders(),
  });
  const json = await resp.json();
  if (!resp.ok || !json.success) {
    const detail = json?.detail;
    throw new Error(
      typeof detail === 'object' ? detail?.message ?? JSON.stringify(detail) : detail ?? 'Freeze failed',
    );
  }
  return json.data as Card;
}

export async function unfreezeCard(cardId: string): Promise<Card> {
  const resp = await fetch(`${BASE_URL}/api/v1/cards/${cardId}/unfreeze`, {
    method: 'PATCH',
    headers: await authHeaders(),
  });
  const json = await resp.json();
  if (!resp.ok || !json.success) {
    const detail = json?.detail;
    throw new Error(
      typeof detail === 'object' ? detail?.message ?? JSON.stringify(detail) : detail ?? 'Unfreeze failed',
    );
  }
  return json.data as Card;
}

export async function updateCardLimits(
  cardId: string,
  payload: UpdateLimitsRequest,
): Promise<Card> {
  const resp = await fetch(`${BASE_URL}/api/v1/cards/${cardId}/limits`, {
    method: 'PATCH',
    headers: await authHeaders(),
    body: JSON.stringify(payload),
  });
  const json = await resp.json();
  if (!resp.ok || !json.success) {
    const detail = json?.detail;
    throw new Error(
      typeof detail === 'object' ? detail?.message ?? JSON.stringify(detail) : detail ?? 'Limit update failed',
    );
  }
  return json.data as Card;
}
