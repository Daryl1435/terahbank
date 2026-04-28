'use client';

import { useQuery } from '@tanstack/react-query';
import { subDays, formatISO } from 'date-fns';
import { getKYCQueue, listTransactions, listUsers, getFraudAlerts } from '@/lib/api';
import { formatXAF } from '@/lib/format';
import LoadingSpinner from '@/components/LoadingSpinner';

interface KPICardProps {
  label: string;
  value: string | number;
  subtext?: string;
  accent?: string;
  loading?: boolean;
}

function KPICard({ label, value, subtext, accent = 'border-teal', loading }: KPICardProps) {
  return (
    <div className={`bg-white rounded-xl shadow-card p-6 border-t-4 ${accent}`}>
      <p className="text-xs font-roboto text-mid-grey uppercase tracking-wide mb-2">{label}</p>
      {loading ? (
        <LoadingSpinner className="mt-2" />
      ) : (
        <>
          <p className="font-poppins font-bold text-3xl text-navy">{value}</p>
          {subtext && <p className="text-xs text-mid-grey mt-1">{subtext}</p>}
        </>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const thirtyDaysAgo = formatISO(subDays(new Date(), 30), { representation: 'date' });

  const { data: usersData, isLoading: loadingUsers } = useQuery({
    queryKey: ['admin', 'users', 'count'],
    queryFn: () => listUsers({ limit: 1 }),
  });

  const { data: kycData, isLoading: loadingKyc } = useQuery({
    queryKey: ['admin', 'kyc', 'count'],
    queryFn: () => getKYCQueue({ limit: 1 }),
  });

  const { data: txnData, isLoading: loadingTxn } = useQuery({
    queryKey: ['admin', 'transactions', 'monthly'],
    queryFn: () => listTransactions({ date_from: thirtyDaysAgo, limit: 1 }),
  });

  const { data: fraudData, isLoading: loadingFraud } = useQuery({
    queryKey: ['admin', 'fraud-alerts', 'count'],
    queryFn: () => getFraudAlerts({ limit: 1 }),
  });

  const { data: txnVolumeData, isLoading: loadingVolume } = useQuery({
    queryKey: ['admin', 'transactions', 'volume', thirtyDaysAgo],
    queryFn:  () => listTransactions({ date_from: thirtyDaysAgo, status: 'success', limit: 500 }),
  });

  const monthlyVolume = txnVolumeData?.data.transactions.reduce((sum, t) => sum + t.amount, 0) ?? 0;

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="font-poppins font-semibold text-2xl text-navy">Dashboard</h1>
        <p className="text-mid-grey text-sm mt-1">Key performance indicators overview</p>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6 mb-10">
        <KPICard
          label="Total Users"
          value={usersData?.data.total ?? '—'}
          subtext="Registered accounts"
          accent="border-teal"
          loading={loadingUsers}
        />
        <KPICard
          label="Pending KYC"
          value={kycData?.data.total ?? '—'}
          subtext="Documents to review"
          accent="border-warning"
          loading={loadingKyc}
        />
        <KPICard
          label="Transactions (30d)"
          value={txnData?.data.total ?? '—'}
          subtext="All transactions"
          accent="border-success"
          loading={loadingTxn}
        />
        <KPICard
          label="Fraud Alerts"
          value={fraudData?.data.total ?? '—'}
          subtext="Total recorded"
          accent="border-error"
          loading={loadingFraud}
        />
      </div>

      {/* Volume card */}
      <div className="bg-navy rounded-xl p-6 shadow-card mb-10 max-w-sm">
        <p className="text-xs font-roboto text-white/60 uppercase tracking-wide mb-2">
          Monthly volume (successful)
        </p>
        {loadingVolume ? (
          <LoadingSpinner className="mt-2" />
        ) : (
          <p className="font-poppins font-bold text-3xl text-white">
            {formatXAF(monthlyVolume)}
          </p>
        )}
        <p className="text-white/50 text-xs mt-1">Settled transactions — last 30 days</p>
      </div>

      {/* Quick links */}
      <div>
        <h2 className="font-poppins font-semibold text-lg text-navy mb-4">Quick access</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {[
            { href: '/kyc',          icon: '📋', label: 'KYC Queue' },
            { href: '/transactions', icon: '↔',  label: 'Transactions' },
            { href: '/users',        icon: '👥', label: 'Users' },
            { href: '/fraud-alerts', icon: '⚠',  label: 'Fraud Alerts' },
            { href: '/reports',      icon: '📊', label: 'Reports' },
          ].map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="bg-white rounded-xl shadow-card p-4 flex items-center gap-3 hover:shadow-modal transition-shadow group"
            >
              <span className="text-2xl">{link.icon}</span>
              <span className="font-poppins font-semibold text-sm text-navy group-hover:text-teal transition-colors">
                {link.label}
              </span>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
