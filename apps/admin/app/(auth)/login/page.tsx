'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { adminLogin } from '@/lib/api';
import { saveAuth } from '@/lib/auth';
import { useTranslation } from '@/lib/i18n';
import LoadingSpinner from '@/components/LoadingSpinner';

function LoginForm() {
  const router       = useRouter();
  const searchParams = useSearchParams();
  const { t } = useTranslation();

  const [step,     setStep]     = useState<'credentials' | 'totp'>('credentials');
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [totp,     setTotp]     = useState('');
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);

  const [pendingToken, setPendingToken] = useState<{ token: string; role: string } | null>(null);

  async function handleCredentials(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await adminLogin(email, password);
      if (!res.success) throw new Error(t('login.errorLogin'));

      const { access_token, role } = res.data;
      setPendingToken({ token: access_token, role });
      setStep('totp');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('login.errorGeneric'));
    } finally {
      setLoading(false);
    }
  }

  async function handleTotp(e: React.FormEvent) {
    e.preventDefault();
    if (!pendingToken) return;
    setError(null);

    if (!/^\d{6}$/.test(totp)) {
      setError(t('login.errorTotp'));
      return;
    }

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
          <img
            src="/logo-symbol.svg"
            alt="TerahBank"
            className="h-16 mx-auto mb-3"
          />
          <p className="font-poppins font-semibold text-white text-xl">TerahBank</p>
          <p className="text-mid-grey text-sm mt-1">{t('login.adminPanel')}</p>
        </div>

        <div className="bg-white rounded-2xl shadow-modal p-8">
          {step === 'credentials' ? (
            <>
              <h2 className="font-poppins font-semibold text-navy text-lg mb-6">{t('login.signIn')}</h2>

              {error && (
                <div className="mb-4 p-3 rounded-lg bg-error/10 border border-error/30 text-error text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handleCredentials} noValidate>
                <div className="mb-4">
                  <label htmlFor="email" className="block text-sm font-medium text-dark-grey mb-1">
                    {t('login.emailAddress')}
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
                    {t('login.password')}
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
                  {t('login.continue')}
                </button>
              </form>
            </>
          ) : (
            <>
              <button
                onClick={() => { setStep('credentials'); setError(null); setTotp(''); }}
                className="text-mid-grey text-sm mb-4 hover:text-teal transition-colors flex items-center gap-1"
              >
                <ArrowLeft className="w-4 h-4" />
                {t('login.back')}
              </button>

              <h2 className="font-poppins font-semibold text-navy text-lg mb-2">
                {t('login.twoFactor')}
              </h2>
              <p className="text-mid-grey text-sm mb-3">
                {t('login.twoFactorDesc')}
              </p>

              {process.env.NODE_ENV === 'development' && (
                <p className="text-xs text-teal bg-teal/10 border border-teal/20 rounded-lg px-3 py-2 mb-5">
                  {t('login.devNotice')}
                </p>
              )}

              {error && (
                <div className="mb-4 p-3 rounded-lg bg-error/10 border border-error/30 text-error text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={handleTotp} noValidate>
                <div className="mb-6">
                  <label htmlFor="totp" className="block text-sm font-medium text-dark-grey mb-1">
                    {t('login.totpCode')}
                  </label>
                  <input
                    id="totp"
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={6}
                    required
                    autoFocus
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
                  {t('login.signInBtn')}
                </button>
              </form>
            </>
          )}
        </div>

        <p className="text-mid-grey text-xs text-center mt-6">
          {t('login.restricted')}
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
