'use client';

import { useState } from 'react';
import { downloadTransactionsCSV, downloadUsersCSV, downloadInsuranceCommissionsCSV } from '@/lib/api';

export default function ReportsPage() {
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo,   setDateTo]   = useState('');
  const [loading,  setLoading]  = useState<string | null>(null);

  async function handleDownload(type: 'transactions' | 'users' | 'insurance') {
    setLoading(type);
    try {
      if (type === 'transactions') {
        downloadTransactionsCSV(dateFrom || undefined, dateTo || undefined);
      } else if (type === 'users') {
        downloadUsersCSV();
      } else {
        downloadInsuranceCommissionsCSV();
      }
      await new Promise((r) => setTimeout(r, 1500));
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="font-poppins font-semibold text-2xl text-navy">Reports</h1>
        <p className="text-mid-grey text-sm mt-1">
          Export data as CSV. Maximum 100,000 rows per export.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {/* Transactions report */}
        <div className="bg-white rounded-xl shadow-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-3xl">↔</span>
            <div>
              <h2 className="font-poppins font-semibold text-lg text-navy">Transactions</h2>
              <p className="text-mid-grey text-sm">CSV export of all transactions</p>
            </div>
          </div>

          <div className="space-y-3 mb-5">
            <div>
              <label className="block text-xs font-medium text-dark-grey mb-1">
                Start date (optional)
              </label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full px-3 py-2 border border-light-grey rounded-lg text-sm focus:outline-none focus:border-teal"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-dark-grey mb-1">
                End date (optional)
              </label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full px-3 py-2 border border-light-grey rounded-lg text-sm focus:outline-none focus:border-teal"
              />
            </div>
          </div>

          <button
            onClick={() => handleDownload('transactions')}
            disabled={loading !== null}
            className="w-full bg-teal text-white py-2.5 rounded-lg font-poppins font-semibold text-sm hover:bg-teal-dark transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading === 'transactions' ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Preparing…
              </>
            ) : (
              '⬇ Download CSV'
            )}
          </button>
        </div>

        {/* Users report */}
        <div className="bg-white rounded-xl shadow-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-3xl">👥</span>
            <div>
              <h2 className="font-poppins font-semibold text-lg text-navy">Users</h2>
              <p className="text-mid-grey text-sm">CSV export of all user accounts</p>
            </div>
          </div>

          <div className="bg-off-white rounded-lg p-4 mb-5 text-sm text-dark-grey">
            <p className="font-medium mb-1">Exported columns:</p>
            <p className="text-xs text-mid-grey font-mono">
              user_id, full_name, email, phone_number, kyc_status, account_status,
              preferred_language, created_at
            </p>
          </div>

          <button
            onClick={() => handleDownload('users')}
            disabled={loading !== null}
            className="w-full bg-navy text-white py-2.5 rounded-lg font-poppins font-semibold text-sm hover:bg-dark-navy transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading === 'users' ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Preparing…
              </>
            ) : (
              '⬇ Download CSV'
            )}
          </button>
        </div>

        {/* Insurance commissions report */}
        <div className="bg-white rounded-xl shadow-card p-6">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-3xl">🛡</span>
            <div>
              <h2 className="font-poppins font-semibold text-lg text-navy">Insurance Commissions</h2>
              <p className="text-mid-grey text-sm">CSV export of referral commissions</p>
            </div>
          </div>

          <div className="bg-off-white rounded-lg p-4 mb-5 text-sm text-dark-grey">
            <p className="font-medium mb-1">Exported columns:</p>
            <p className="text-xs text-mid-grey font-mono">
              policy_id, user_id, partner_id, policy_type, product_name,
              policy_number, status, start_date, expiry_date, commission_amount_xaf, created_at
            </p>
          </div>

          <button
            onClick={() => handleDownload('insurance')}
            disabled={loading !== null}
            className="w-full py-2.5 rounded-lg font-poppins font-semibold text-sm transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            style={{ backgroundColor: '#0B8A8A', color: 'white' }}
          >
            {loading === 'insurance' ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Preparing…
              </>
            ) : (
              '⬇ Download CSV'
            )}
          </button>
        </div>
      </div>

      {/* Compliance note */}
      <div className="mt-8 p-4 rounded-xl bg-teal/10 border border-teal/30 text-sm text-dark-grey">
        <strong>COBAC Note:</strong> Exports containing personal data (PII) are subject to
        confidentiality obligations. Do not share outside TerahBank secure channels.
        Data is extracted in real time from the read replica.
      </div>
    </div>
  );
}
