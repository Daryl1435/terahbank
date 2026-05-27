'use client';

import { useQuery } from '@tanstack/react-query';
import { subDays, formatISO } from 'date-fns';
import {
  ClipboardCheck,
  ArrowLeftRight,
  Users,
  ShieldAlert,
  BarChart3,
} from 'lucide-react';
import { getKYCQueue, listTransactions, listUsers, getFraudAlerts } from '@/lib/api';
import { formatXAF } from '@/lib/format';
import { useTranslation } from '@/lib/i18n';
import LoadingSpinner from '@/components/LoadingSpinner';

interface KPICardProps {
  label:    string;
  value:    string | number;
  subtext?: string;
  accent?:  string;
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

const QUICK_LINKS = [
  { href: '/kyc',          icon: ClipboardCheck, labelKey: 'nav.kyc'          },
  { href: '/transactions', icon: ArrowLeftRight,  labelKey: 'nav.transactions' },
  { href: '/users',        icon: Users,           labelKey: 'nav.users'        },
  { href: '/fraud-alerts', icon: ShieldAlert,     labelKey: 'nav.fraudAlerts'  },
  { href: '/reports',      icon: BarChart3,       labelKey: 'nav.reports'      },
] as const;

export default function DashboardPage() {
  const { t } = useTranslation();
  const thirtyDaysAgo = formatISO(subDays(new Date(), 30), { representation: 'date' });

  const { data: usersData,  isLoading: loadingUsers  } = useQuery({
    queryKey: ['admin', 'users', 'count'],
    queryFn:  () => listUsers({ limit: 1 }),
  });

  const { data: kycData,    isLoading: loadingKyc    } = useQuery({
    queryKey: ['admin', 'kyc', 'count'],
    queryFn:  () => getKYCQueue({ limit: 1 }),
  });

  const { data: txnData,    isLoading: loadingTxn    } = useQuery({
    queryKey: ['admin', 'transactions', 'monthly'],
    queryFn:  () => listTransactions({ date_from: thirtyDaysAgo, limit: 1 }),
  });

  const { data: fraudData,  isLoading: loadingFraud  } = useQuery({
    queryKey: ['admin', 'fraud-alerts', 'count'],
    queryFn:  () => getFraudAlerts({ limit: 1 }),
  });

  const { data: txnVolumeData, isLoading: loadingVolume } = useQuery({
    queryKey: ['admin', 'transactions', 'volume', thirtyDaysAgo],
    queryFn:  () => listTransactions({ date_from: thirtyDaysAgo, status: 'success', limit: 500 }),
  });

  const monthlyVolume = txnVolumeData?.data.transactions.reduce((sum, tx) => sum + tx.amount, 0) ?? 0;

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="font-poppins font-semibold text-2xl text-navy">{t('dashboard.title')}</h1>
        <p className="text-mid-grey text-sm mt-1">{t('dashboard.subtitle')}</p>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6 mb-10">
        <KPICard
          label={t('dashboard.kpi.totalUsers')}
          value={usersData?.data.total ?? '—'}
          subtext={t('dashboard.kpi.totalUsersSub')}
          accent="border-teal"
          loading={loadingUsers}
        />
        <KPICard
          label={t('dashboard.kpi.pendingKyc')}
          value={kycData?.data.total ?? '—'}
          subtext={t('dashboard.kpi.pendingKycSub')}
          accent="border-warning"
          loading={loadingKyc}
        />
        <KPICard
          label={t('dashboard.kpi.transactions30d')}
          value={txnData?.data.total ?? '—'}
          subtext={t('dashboard.kpi.transactions30dSub')}
          accent="border-success"
          loading={loadingTxn}
        />
        <KPICard
          label={t('dashboard.kpi.fraudAlerts')}
          value={fraudData?.data.total ?? '—'}
          subtext={t('dashboard.kpi.fraudAlertsSub')}
          accent="border-error"
          loading={loadingFraud}
        />
      </div>

      {/* Volume card */}
      <div className="bg-navy rounded-xl p-6 shadow-card mb-10 max-w-sm">
        <p className="text-xs font-roboto text-white/60 uppercase tracking-wide mb-2">
          {t('dashboard.volume.label')}
        </p>
        {loadingVolume ? (
          <LoadingSpinner className="mt-2" />
        ) : (
          <p className="font-poppins font-bold text-3xl text-white">
            {formatXAF(monthlyVolume)}
          </p>
        )}
        <p className="text-white/50 text-xs mt-1">{t('dashboard.volume.subtext')}</p>
      </div>

      {/* Quick links */}
      <div>
        <h2 className="font-poppins font-semibold text-lg text-navy mb-4">{t('dashboard.quickAccess')}</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {QUICK_LINKS.map((link) => {
            const Icon = link.icon;
            return (
              <a
                key={link.href}
                href={link.href}
                className="bg-white rounded-xl shadow-card p-4 flex items-center gap-3 hover:shadow-modal transition-shadow group"
              >
                <Icon className="w-6 h-6 text-navy group-hover:text-teal transition-colors flex-shrink-0" />
                <span className="font-poppins font-semibold text-sm text-navy group-hover:text-teal transition-colors">
                  {t(link.labelKey)}
                </span>
              </a>
            );
          })}
        </div>
      </div>
    </div>
  );
}
