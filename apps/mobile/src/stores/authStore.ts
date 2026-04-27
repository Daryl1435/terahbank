import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';

// SECURITY: tokens stored in SecureStore only — NEVER in Zustand state or AsyncStorage

interface AuthState {
  userId: string | null;
  isAuthenticated: boolean;
  kycStatus: 'pending' | 'approved' | 'rejected' | null;
  setAuth: (userId: string, kycStatus: string) => void;
  clearAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  userId: null,
  isAuthenticated: false,
  kycStatus: null,

  setAuth: (userId, kycStatus) => {
    set({ userId, isAuthenticated: true, kycStatus: kycStatus as AuthState['kycStatus'] });
  },

  clearAuth: async () => {
    await SecureStore.deleteItemAsync('access_token');
    await SecureStore.deleteItemAsync('refresh_token');
    set({ userId: null, isAuthenticated: false, kycStatus: null });
  },
}));

// Token helpers — always use SecureStore, never Zustand for tokens
export const saveTokens = async (accessToken: string, refreshToken: string) => {
  await SecureStore.setItemAsync('access_token', accessToken);
  await SecureStore.setItemAsync('refresh_token', refreshToken);
};

export const getAccessToken = () => SecureStore.getItemAsync('access_token');
export const getRefreshToken = () => SecureStore.getItemAsync('refresh_token');
