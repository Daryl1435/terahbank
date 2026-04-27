import { getAccessToken, getRefreshToken } from '@/stores/authStore';

const BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL;

// ── Request types ──────────────────────────────────────────────────────────────

export interface RegisterRequest {
  full_name: string;
  phone_number: string;   // E.164 format e.g. +237600000000
  email: string;
  password: string;
  city?: string;
  address?: string;
  preferred_language?: 'fr' | 'en';
}

export interface LoginRequest {
  identifier: string;     // phone number or email address
  password: string;
}

export interface VerifyOTPRequest {
  user_id: string;
  otp: string;
  purpose: 'verify' | 'login';
  device_fingerprint?: string;
}

export interface ResendOTPRequest {
  user_id: string;
  purpose: 'verify' | 'login';
}

// ── Response types ─────────────────────────────────────────────────────────────

/** Returned by POST /auth/register */
export interface RegisterResponse {
  user_id: string;
  otp_required: boolean;
}

/**
 * Returned by POST /auth/login.
 * Does NOT contain tokens — login only starts 2FA.
 * Tokens are issued after /auth/verify-otp with purpose='login'.
 */
export interface LoginInitResponse {
  user_id: string;
  otp_required: boolean;
}

/** Returned by POST /auth/verify-otp with purpose='verify' (registration) */
export interface OTPVerifyResponse {
  verified: boolean;
}

/** Returned by POST /auth/verify-otp with purpose='login' */
export interface AuthTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  kyc_status: 'pending' | 'approved' | 'rejected';
  is_new_device: boolean;
}

export type VerifyOTPResponse = OTPVerifyResponse | AuthTokenResponse;

/** Returned by POST /auth/refresh */
export interface RefreshResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

// ── HTTP helpers ───────────────────────────────────────────────────────────────

const authHeaders = async (): Promise<HeadersInit> => {
  const token = await getAccessToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

const handleResponse = async <T>(res: Response): Promise<T> => {
  const json = await res.json();
  if (!res.ok || !json.success) {
    const message = json.error?.message ?? 'Request failed';
    const code = json.error?.code ?? 'UNKNOWN_ERROR';
    const err = new Error(message) as Error & { code: string };
    err.code = code;
    throw err;
  }
  return json.data as T;
};

// ── Auth service ───────────────────────────────────────────────────────────────

export const authService = {
  register: async (payload: RegisterRequest): Promise<RegisterResponse> => {
    const res = await fetch(`${BASE_URL}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<RegisterResponse>(res);
  },

  /**
   * POST /auth/login
   * Returns user_id + otp_required:true — does NOT issue tokens.
   * Tokens are issued in /auth/verify-otp after the user completes 2FA.
   */
  login: async (payload: LoginRequest): Promise<LoginInitResponse> => {
    const res = await fetch(`${BASE_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<LoginInitResponse>(res);
  },

  /**
   * POST /auth/verify-otp
   * purpose='verify' → { verified: true } (registration OTP)
   * purpose='login'  → AuthTokenResponse with access/refresh tokens
   */
  verifyOTP: async (payload: VerifyOTPRequest): Promise<VerifyOTPResponse> => {
    const res = await fetch(`${BASE_URL}/api/v1/auth/verify-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<VerifyOTPResponse>(res);
  },

  resendOTP: async (payload: ResendOTPRequest): Promise<void> => {
    const res = await fetch(`${BASE_URL}/api/v1/auth/resend-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<void>(res);
  },

  logout: async (): Promise<void> => {
    const headers = await authHeaders();
    const refreshToken = await getRefreshToken();
    const res = await fetch(`${BASE_URL}/api/v1/auth/logout`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    // Best-effort — always clear local state even if the API call fails
    return handleResponse<void>(res).catch(() => undefined);
  },

  refreshToken: async (): Promise<RefreshResponse> => {
    const refreshToken = await getRefreshToken();
    const res = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    return handleResponse<RefreshResponse>(res);
  },

  changePassword: async (payload: {
    current_password: string;
    new_password: string;
  }): Promise<void> => {
    const headers = await authHeaders();
    const res = await fetch(`${BASE_URL}/api/v1/auth/change-password`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });
    return handleResponse<void>(res);
  },

  /**
   * POST /auth/verify-pin
   * Returns a single-use pin_token (valid 60s) for authorising transfers.
   * Called immediately before POST /transactions/transfer — do not cache the token.
   */
  verifyPin: async (pin: string): Promise<{ pin_token: string; expires_in: number }> => {
    const headers = await authHeaders();
    const res = await fetch(`${BASE_URL}/api/v1/auth/verify-pin`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ pin }),
    });
    return handleResponse<{ pin_token: string; expires_in: number }>(res);
  },
};
