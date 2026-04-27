'use client';

import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import type { Metadata } from 'next';
import { adminLogin } from '@/lib/api';
import { saveAuth } from '@/lib/auth';
import LoadingSpinner from '@/components/LoadingSpinner';

export default function LoginPage() {
  const router       = useRouter();
  const searchParams = useSearchParams();

  const [step,     setStep]     = useState<'credentials' | 'totp'>('credentials');
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [totp,     setTotp]     = useState('');
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);

  // Stored temporarily between step 1 and step 2
  const [pendingToken, setPendingToken] = useState<{ token: string; role: string } | null>(null);

  async function handleCredentials(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await adminLogin(email, password);
      if (!res.success) throw new Error('Échec de la connexion.');

      const { access_token, role } = res.data;
      setPendingToken({ token: access_token, role });

      // TODO: when backend adds TOTP verification (/admin/auth/totp/verify),
      // check if totp_required is returned and conditionally advance to TOTP step.
      // For now, TOTP step is always shown — admins without TOTP enrolled skip with "000000".
      setStep('totp');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Erreur de connexion.');
    } finally {
      setLoading(false);
    }
  }

  async function handleTotp(e: React.FormEvent) {
    e.preventDefault();
    if (!pendingToken) return;
    setError(null);

    // Validate: must be exactly 6 digits
    if (!/^\d{6}$/.test(totp)) {
      setError('Le code TOTP doit comporter 6 chiffres.');
      return;
    }

    // TODO: POST /admin/auth/totp/verify with { totp_code: totp, session_token: pendingToken.token }
    // once the backend endpoint is implemented. For now, accept any valid 6-digit code.

    setLoading(true);
    try {
      saveAuth(pendingToken.token, pendingToken.role);
      const redirect = searchParams.get('from') ?? '/dashboard';
      router.push(redirect);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-navy flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-teal mb-4">
            <span className="font-poppins font-bold text-white text-2xl">T</span>
          </div>
          <h1 className="font-poppins font-semibold text-white text-2xl">TerahBank</h1>
          <p className="text-mid-grey text-sm mt-1">Panneau d&apos;administration</p>
        </div>

        <div className="bg-white rounded-2xl shadow-modal p-8">
          {step === 'credentials' ? (
            <>
              <h2 className="font-poppins font-semibold text-navy text-lg mb-6">Connexion</h2>

              {error && (
                <div className="mb-4 p-3 rounded-lg bg-error/10 border border-error/30 text-error text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handleCredentials} noValidate>
                <div className="mb-4">
                  <label htmlFor="email" className="block text-sm font-medium text-dark-grey mb-1">
                    Adresse e-mail
                  </label>
                  <input
                    id="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3 py-2 border border-light-grey rounded-lg text-sm focus:outline-none focus:border-teal transition-colors"
                    placeholder="admin@terahbank.com"
                  />
                </div>

                <div className="mb-6">
                  <label htmlFor="password" className="block text-sm font-medium text-dark-grey mb-1">
                    Mot de passe
                  </label>
                  <input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-3 py-2 border border-light-grey rounded-lg text-sm focus:outline-none focus:border-teal transition-colors"
                    placeholder="••••••••••••"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || !email || !password}
                  className="w-full bg-teal text-white py-2.5 rounded-lg font-poppins font-semibold text-sm hover:bg-teal-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? <LoadingSpinner /> : null}
                  Continuer
                </button>
              </form>
            </>
          ) : (
            <>
              <button
                onClick={() => { setStep('credentials'); setError(null); setTotp(''); }}
                className="text-mid-grey text-sm mb-4 hover:text-teal transition-colors flex items-center gap-1"
              >
                ← Retour
              </button>

              <h2 className="font-poppins font-semibold text-navy text-lg mb-2">
                Vérification TOTP
              </h2>
              <p className="text-mid-grey text-sm mb-6">
                Entrez le code à 6 chiffres de votre application d&apos;authentification.
              </p>

              {error && (
                <div className="mb-4 p-3 rounded-lg bg-error/10 border border-error/30 text-error text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handleTotp} noValidate>
                <div className="mb-6">
                  <label htmlFor="totp" className="block text-sm font-medium text-dark-grey mb-1">
                    Code d&apos;authentification
                  </label>
                  <input
                    id="totp"
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    required
                    value={totp}
                    onChange={(e) => setTotp(e.target.value.replace(/\D/g, ''))}
                    className="w-full px-3 py-2 border border-light-grey rounded-lg text-sm text-center tracking-widest font-poppins focus:outline-none focus:border-teal transition-colors"
                    placeholder="000000"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || totp.length !== 6}
                  className="w-full bg-teal text-white py-2.5 rounded-lg font-poppins font-semibold text-sm hover:bg-teal-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? <LoadingSpinner /> : null}
                  Connexion
                </button>
              </form>
            </>
          )}
        </div>

        <p className="text-mid-grey text-xs text-center mt-6">
          Accès réservé au personnel TerahBank autorisé uniquement.
        </p>
      </div>
    </div>
  );
}
