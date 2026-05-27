import { useMutation, useQuery } from '@tanstack/react-query';
import { useAuthStore, saveTokens } from '@/stores/authStore';
import { authService } from '@/services/auth';
import type {
  LoginRequest,
  RegisterRequest,
  VerifyOTPRequest,
  AuthTokenResponse,
} from '@/services/auth';

/**
 * useLogin — calls POST /auth/login.
 * Returns { user_id, otp_required } — does NOT issue tokens.
 * The screen is responsible for navigating to OTPScreen(purpose='login').
 */
export const useLogin = () =>
  useMutation({
    mutationFn: (payload: LoginRequest) => authService.login(payload),
  });

/**
 * useRegister — calls POST /auth/register.
 * Returns { user_id, otp_required }.
 * The screen navigates to OTPScreen(purpose='verify').
 */
export const useRegister = () =>
  useMutation({
    mutationFn: (payload: RegisterRequest) => authService.register(payload),
  });

/**
 * useVerifyOTP — calls POST /auth/verify-otp.
 * The screen handles all post-success routing:
 *   purpose='verify'  → navigate to PINSetup
 *   purpose='login'   → saveTokens + (setAuth or navigate DeviceVerification)
 *
 * Helper: isTokenResponse narrows the union type.
 */
export const isTokenResponse = (data: unknown): data is AuthTokenResponse =>
  typeof data === 'object' && data !== null && 'access_token' in data;

export const useVerifyOTP = () =>
  useMutation({
    mutationFn: (payload: VerifyOTPRequest) => authService.verifyOTP(payload),
    // All auth state + navigation decisions are made in the screen component.
  });

/**
 * useLogout — clears SecureStore tokens and Zustand auth state.
 * Best-effort server-side revocation — always clears local state.
 */
export const useLogout = () => {
  const clearAuth = useAuthStore((s) => s.clearAuth);

  return useMutation({
    mutationFn: () => authService.logout(),
    onSettled: async () => {
      await clearAuth();
    },
  });
};

export const useChangePassword = () =>
  useMutation({
    mutationFn: (payload: { current_password: string; new_password: string }) =>
      authService.changePassword(payload),
  });

/**
 * useProfile — fetches the authenticated user's full profile (name, phone, email).
 * Cached for 5 minutes; returns null while loading or on error.
 */
export const useProfile = () =>
  useQuery({
    queryKey: ['auth', 'me'],
    queryFn: () => authService.getMe(),
    staleTime: 5 * 60_000,
    retry: 1,
  });
