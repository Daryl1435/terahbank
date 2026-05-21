import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';

// Global UI state — non-sensitive only.
// Tokens, PIN, and biometric data live in expo-secure-store (see authStore.ts).

// SecureStore keys — exported so App.tsx can read them at startup
export const LANGUAGE_PREF_KEY     = 'terahbank_language_pref';
export const LANGUAGE_SELECTED_KEY = 'terahbank_language_selected';
export const FONT_SIZE_PREF_KEY    = 'terahbank_font_size_pref';

type Language = 'fr' | 'en';
export type FontSize  = 'small' | 'medium' | 'large';

interface AppState {
  language:         Language;
  languageSelected: boolean;        // true once user has picked a language on first launch
  fontSize:         FontSize;
  lastActiveAt:     number | null;  // epoch ms — used for 15-min inactivity check (FR-008)

  setLanguage:         (lang: Language) => void;
  setLanguageSelected: (selected: boolean) => void;
  setFontSize:         (size: FontSize) => void;
  touchActivity:       () => void;
  isSessionExpired:    () => boolean;
}

const SESSION_TIMEOUT_MS = 15 * 60 * 1000; // FR-008: 15 min inactivity

export const useAppStore = create<AppState>((set, get) => ({
  language:         'fr',
  languageSelected: false,
  fontSize:         'medium',
  lastActiveAt:     null,

  // Persist language choice to SecureStore (fire-and-forget — not sensitive)
  setLanguage: (language) => {
    SecureStore.setItemAsync(LANGUAGE_PREF_KEY, language).catch(() => {});
    set({ language });
  },

  // Persist the "has selected" flag so the picker is never shown again
  setLanguageSelected: (languageSelected) => {
    if (languageSelected) {
      SecureStore.setItemAsync(LANGUAGE_SELECTED_KEY, 'true').catch(() => {});
    }
    set({ languageSelected });
  },

  setFontSize: (fontSize) => {
    SecureStore.setItemAsync(FONT_SIZE_PREF_KEY, fontSize).catch(() => {});
    set({ fontSize });
  },

  touchActivity: () => set({ lastActiveAt: Date.now() }),

  isSessionExpired: () => {
    const { lastActiveAt } = get();
    if (lastActiveAt === null) return false;
    return Date.now() - lastActiveAt > SESSION_TIMEOUT_MS;
  },
}));
