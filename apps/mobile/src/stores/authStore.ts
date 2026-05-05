import { Platform } from 'react-native';
import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';

// SECURITY: on native, tokens live in SecureStore (Keychain/Keystore).
// On web (dev only), SecureStore hangs — fall back to localStorage.
const storage = {
  set: async (key: string, value: string) => {
    if (Platform.OS === 'web') {
      localStorage.setItem(key, value);
    } else {
      await SecureStore.setItemAsync(key, value);
    }
  },
  get: async (key: string): Promise<string | null> => {
    if (Platform.OS === 'web') {
      return localStorage.getItem(key);
    }
    return SecureStore.getItemAsync(key);
  },
  delete: async (key: string) => {
    if (Platform.OS === 'web') {
      localStorage.removeItem(key);
    } else {
      await SecureStore.deleteItemAsync(key);
    }
  },
};

interface AuthState {
  userId: string | null;
  fullName: string | null;
  isAuthenticated: boolean;
  kycStatus: 'pending' | 'approved' | 'rejected' | null;
  setAuth: (userId: string, kycStatus: string, fullName?: string) => void;
  clearAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  userId: null,
  fullName: null,
  isAuthenticated: false,
  kycStatus: null,

  setAuth: (userId, kycStatus, fullName) => {
    set({ userId, fullName: fullName ?? null, isAuthenticated: true, kycStatus: kycStatus as AuthState['kycStatus'] });
  },

  clearAuth: async () => {
    await storage.delete('access_token');
    await storage.delete('refresh_token');
    set({ userId: null, isAuthenticated: false, kycStatus: null });
  },
}));

// Token helpers
export const saveTokens = async (accessToken: string, refreshToken: string) => {
  await storage.set('access_token', accessToken);
  await storage.set('refresh_token', refreshToken);
};

export const getAccessToken = () => storage.get('access_token');
export const getRefreshToken = () => storage.get('refresh_token');
