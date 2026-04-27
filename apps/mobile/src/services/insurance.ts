import { getAccessToken } from '@/stores/authStore';

const BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL;

// ── Types ──────────────────────────────────────────────────────────────────────

export type PolicyType = 'health' | 'device' | 'micro';
export type PolicyStatus = 'active' | 'cancelled' | 'expired';

export interface InsuranceProduct {
  product_id: string;
  partner_id: string;
  name: string;
  description: string;
  policy_type: PolicyType;
  monthly_premium_xaf: number;
  max_coverage_xaf: number;
  features: string[];
}

export interface InsurancePolicy {
  policy_id: string;
  partner_id: string;
  policy_type: PolicyType;
  policy_number: string;
  product_name: string;
  status: PolicyStatus;
  start_date: string;       // ISO date YYYY-MM-DD
  expiry_date: string;      // ISO date YYYY-MM-DD
  monthly_premium_xaf: number;
  days_until_expiry: number | null;
}

export interface EnrollResponse {
  policy_id: string;
  policy_number: string;
  partner_id: string;
  policy_type: PolicyType;
  redirect_url: string;
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

export const insuranceService = {
  listProducts: async (): Promise<InsuranceProduct[]> => {
    const headers = await authHeaders();
    const res = await fetch(`${BASE_URL}/api/v1/insurance/products`, { headers });
    return handleResponse<InsuranceProduct[]>(res);
  },

  listMyPolicies: async (): Promise<InsurancePolicy[]> => {
    const headers = await authHeaders();
    const res = await fetch(`${BASE_URL}/api/v1/insurance/policies`, { headers });
    return handleResponse<InsurancePolicy[]>(res);
  },

  enroll: async (productId: string): Promise<EnrollResponse> => {
    const headers = await authHeaders();
    const res = await fetch(`${BASE_URL}/api/v1/insurance/policies`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ product_id: productId }),
    });
    return handleResponse<EnrollResponse>(res);
  },

  cancelPolicy: async (policyId: string): Promise<{ policy_id: string; status: string }> => {
    const headers = await authHeaders();
    const res = await fetch(`${BASE_URL}/api/v1/insurance/policies/${policyId}`, {
      method: 'DELETE',
      headers,
    });
    return handleResponse<{ policy_id: string; status: string }>(res);
  },
};
