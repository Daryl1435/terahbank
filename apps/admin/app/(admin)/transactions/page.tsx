'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { RefreshCw } from 'lucide-react';
import { listTransactions } from '@/lib/api';
import { formatXAF, formatDateTime } from '@/lib/format';
import { useTranslation } from '@/lib/i18n';
import Badge, { statusVariant } from '@/components/Badge';
import Pagination from '@/components/Pagination';
import LoadingSpinner from '@/components/LoadingSpinner';

const PAGE_SIZE = 50;

const TRANSACTION_TYPES = ['', 'deposit', 'withdrawal', 'transfer'];
const CHANNELS          = ['', 'internal', 'mtn_momo', 'orange_money', 'visa', 'mastercard'];
const STATUSES          = ['', 'pending', 'processing', 'success', 'failed'];

export default function TransactionsPage() {
  const { t } = useTranslation();
  const [userId,          setUserId]          = useState('');
  const [transactionType, setTransactionType] = useState('');
  const [channel,         setChannel]         = useState('');
  const [txnStatus,       setTxnStatus]       = useState('');
  const [dateFrom,        setDateFrom]        = useState('');
  const [dateTo,          setDateTo]          = useState('');
  const [offset,          setOffset]          = useState(0);

  const [submittedUserId, setSubmittedUserId] = useState('');

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: [
      'admin', 'transactions',
      submittedUserId, transactionType, channel, txnStatus, dateFrom, dateTo, offset,
    ],
    queryFn: () =>
      listTransactions({
        user_id:          submittedUserId || undefined,
        transaction_type: transactionType || undefined,
        channel:          channel         || undefined,
        status:           txnStatus       || undefined,
        date_from:        dateFrom        || undefined,
        date_to:          dateTo          || undefined,
        offset,
        limit: PAGE_SIZE,
      }),
    refetchInterval: 15_000,
  });

  const txns  = data?.data.transactions ?? [];
  const total = data?.data.total ?? 0;

  function applyFilters() {
    setSubmittedUserId(userId);
    setOffset(0);
  }

  const countText = t('transactions.countAuto').replace('{count}', String(total));

  return (
    <div className="p-8">
      <div className="flex items-start justify-between mb-6 flex-wrap gap-4">
        <div>
          <h1 className="font-poppins font-semibold text-2xl text-navy">{t('transactions.title')}</h1>
          <p className="text-mid-grey text-sm mt-1">{countText}</p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-3 py-2 border border-light-grey rounded-lg text-sm text-dark-grey hover:bg-light-grey transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          {t('transactions.refresh')}
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-card p-4 mb-6 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder={t('transactions.filters.userId')}
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          className="flex-1 min-w-[200px] px-3 py-2 border border-light-grey rounded-lg text-sm focus:outline-none focus:border-teal font-mono"
        />
        <select
          value={transactionType}
          onChange={(e) => { setTransactionType(e.target.value); setOffset(0); }}
          className="px-3 py-2 border border-light-grey rounded-lg text-sm focus:outline-none focus:border-teal"
        >
          <option value="">{t('transactions.filters.allTypes')}</option>
          {TRANSACTION_TYPES.slice(1).map((ty) => <option key={ty} value={ty}>{ty}</option>)}
        </select>
        <select
          value={channel}
          onChange={(e) => { setChannel(e.target.value); setOffset(0); }}
          className="px-3 py-2 border border-light-grey rounded-lg text-sm focus:outline-none focus:border-teal"
        >
          <option value="">{t('transactions.filters.allChannels')}</option>
          {CHANNELS.slice(1).map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select
          value={txnStatus}
          onChange={(e) => { setTxnStatus(e.target.value); setOffset(0); }}
          className="px-3 py-2 border border-light-grey rounded-lg text-sm focus:outline-none focus:border-teal"
        >
          <option value="">{t('transactions.filters.allStatuses')}</option>
          {STATUSES.slice(1).map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => { setDateFrom(e.target.value); setOffset(0); }}
          className="px-3 py-2 border border-light-grey rounded-lg text-sm focus:outline-none focus:border-teal"
          title={t('transactions.filters.dateStart')}
        />
        <input
          type="date"
          value={dateTo}
          onChange={(e) => { setDateTo(e.target.value); setOffset(0); }}
          className="px-3 py-2 border border-light-grey rounded-lg text-sm focus:outline-none focus:border-teal"
          title={t('transactions.filters.dateEnd')}
        />
        <button
          onClick={applyFilters}
          className="px-4 py-2 bg-teal text-white rounded-lg text-sm font-medium hover:bg-teal-dark transition-colors"
        >
          {t('transactions.filters.apply')}
        </button>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-card overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-16"><LoadingSpinner className="w-8 h-8" /></div>
        ) : isError ? (
          <p className="text-error text-sm text-center py-16">{t('transactions.loadError')}</p>
        ) : txns.length === 0 ? (
          <p className="text-mid-grey text-sm text-center py-16">{t('transactions.noResults')}</p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm admin-table">
                <thead>
                  <tr>
                    <th className="text-left px-4 py-3">{t('transactions.table.reference')}</th>
                    <th className="text-left px-4 py-3">{t('transactions.table.type')}</th>
                    <th className="text-left px-4 py-3">{t('transactions.table.channel')}</th>
                    <th className="text-right px-4 py-3">{t('transactions.table.amount')}</th>
                    <th className="text-left px-4 py-3">{t('transactions.table.status')}</th>
                    <th className="text-left px-4 py-3">{t('transactions.table.date')}</th>
                  </tr>
                </thead>
                <tbody>
                  {txns.map((txn) => (
                    <tr key={txn.transaction_id} className="border-t border-light-grey hover:bg-off-white transition-colors">
                      <td className="px-4 py-3 font-mono text-xs text-mid-grey">{txn.reference}</td>
                      <td className="px-4 py-3 text-dark-grey capitalize">{txn.transaction_type}</td>
                      <td className="px-4 py-3 text-dark-grey text-xs">{txn.channel}</td>
                      <td className="px-4 py-3 text-right font-medium text-navy">{formatXAF(txn.amount)}</td>
                      <td className="px-4 py-3">
                        <Badge label={txn.status} variant={statusVariant(txn.status)} />
                      </td>
                      <td className="px-4 py-3 text-mid-grey text-xs">{formatDateTime(txn.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination offset={offset} limit={PAGE_SIZE} total={total} onPageChange={setOffset} />
          </>
        )}
      </div>
    </div>
  );
}
