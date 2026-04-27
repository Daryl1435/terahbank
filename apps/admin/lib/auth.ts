// Admin auth helpers — tokens stored in cookies for Next.js middleware access.
// Cookies are not httpOnly (client needs to read them) but are SameSite=Strict.

import type { AdminRole } from './types';

const TOKEN_COOKIE = 'admin_token';
const ROLE_COOKIE  = 'admin_role';
const MAX_AGE      = 12 * 60 * 60; // 12 hours — matches backend JWT expiry

function setCookie(name: string, value: string, maxAge: number): void {
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAge}; SameSite=Strict`;
}

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function deleteCookie(name: string): void {
  document.cookie = `${name}=; path=/; max-age=0`;
}

export function saveAuth(token: string, role: string): void {
  setCookie(TOKEN_COOKIE, token, MAX_AGE);
  setCookie(ROLE_COOKIE, role, MAX_AGE);
}

export function getToken(): string | null {
  return getCookie(TOKEN_COOKIE);
}

export function getRole(): AdminRole | null {
  return getCookie(ROLE_COOKIE) as AdminRole | null;
}

export function clearAuth(): void {
  deleteCookie(TOKEN_COOKIE);
  deleteCookie(ROLE_COOKIE);
}

export function isSuperAdmin(): boolean {
  return getRole() === 'super_admin';
}

export function canMutate(): boolean {
  return getRole() !== 'read_only_analyst';
}
