import { create } from 'zustand';

// Global UI state — non-sensitive only
// Tokens, PIN, and biometric data live in expo-secure-store (see authStore.ts)

type Language = 'fr' | 'en';
type FontSize = 'small' | 'medium' | 'large';

interface AppState {
  language: Language;
  fontSize: FontSize;
  lastActiveAt: number | null;  // epoch ms — used for 15-min inactivity check (FR-008)

  setLanguage: (lang: Language) => void;
  setFontSize: (size: FontSize) => void;
  touchActivity: () => void;
  isSessionExpired: () => boolean;
}

const SESSION_TIMEOUT_MS = 15 * 60 * 1000; // FR-008: 15 min inactivity

export const useAppStore = create<AppState>((set, get) => ({
  language: 'fr',
  fontSize: 'medium',
  lastActiveAt: null,

  setLanguage: (language) => set({ language }),
  setFontSize: (fontSize) => set({ fontSize }),

  touchActivity: () => set({ lastActiveAt: Date.now() }),

  isSessionExpired: () => {
    const { lastActiveAt } = get();
    if (lastActiveAt === null) return false;
    return Date.now() - lastActiveAt > SESSION_TIMEOUT_MS;
  },
}));
