'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { en } from '@/locales/en';
import { fr } from '@/locales/fr';

export type Language = 'en' | 'fr';

type Translations = typeof en;

// Recursive dot-notation key extractor (depth-limited for TS performance)
type DotKeys<T, Prefix extends string = ''> = {
  [K in keyof T & string]: T[K] extends string
    ? `${Prefix}${K}`
    : T[K] extends object
    ? DotKeys<T[K], `${Prefix}${K}.`>
    : never;
}[keyof T & string];

export type TranslationKey = DotKeys<Translations>;

interface LanguageContextValue {
  lang:    Language;
  setLang: (lang: Language) => void;
  t:       (key: TranslationKey) => string;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

const STORAGE_KEY    = 'admin_lang';
const DEFAULT_LANG: Language = 'en';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const DICTIONARIES: Record<Language, any> = { en, fr };

function resolve(dict: Record<string, unknown>, key: string): string {
  const parts = key.split('.');
  let node: unknown = dict;
  for (const part of parts) {
    if (node == null || typeof node !== 'object') return key;
    node = (node as Record<string, unknown>)[part];
  }
  return typeof node === 'string' ? node : key;
}

export function LanguageProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [lang, setLangState] = useState<Language>(DEFAULT_LANG);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'en' || stored === 'fr') setLangState(stored);
  }, []);

  const setLang = useCallback((next: Language) => {
    setLangState(next);
    localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const t = useCallback(
    (key: TranslationKey): string => resolve(DICTIONARIES[lang], key),
    [lang],
  );

  return React.createElement(
    LanguageContext.Provider,
    { value: { lang, setLang, t } },
    children,
  );
}

export function useTranslation() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useTranslation must be used inside LanguageProvider');
  return ctx;
}
