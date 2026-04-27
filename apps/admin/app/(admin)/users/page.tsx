'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { listUsers } from '@/lib/api';
import { formatDate, maskPhone } from '@/lib/format';
import Badge, { statusVariant } from '@/components/Badge';
import Pagination from '@/components/Pagination';
import LoadingSpinner from '@/components/LoadingSpinner';

const PAGE_SIZE = 20;

const KYC_STATUSES    = ['', 'pending', 'approved', 'rejected'];
const ACCOUNT_STATUSES = ['', 'active', 'suspended', 'closed'];

export default function UsersPage() {
  const [search,        setSearch]        = useState('');
  const [kycStatus,     setKycStatus]     = useState('');
  const [accountStatus, setAccountStatus] = useState('');
  const [offset,        setOffset]        = useState(0);

  // Debounce search: re-fetch only when user stops typing
  const [debouncedSearch, setDebouncedSearch] = useState('');
  function handleSearchChange(value: string) {
    setSearch(value);
    clearTimeout((handleSearchChange as unknown as { _t?: ReturnType<typeof setTimeout> })._t);
    (handleSearchChange as unknown as { _t?: ReturnType<typeof setTimeout> })._t = setTimeout(() => {
      setDebouncedSearch(value);
      setOffset(0);
    }, 350);
  }

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin', 'users', debouncedSearch, kycStatus, accountStatus, offset],
    queryFn: () =>
      listUsers({
        search:         debouncedSearch || undefined,
        kyc_status:     kycStatus || undefined,
        account_status: accountStatus || undefined,
        offset,
        limit: PAGE_SIZE,
      }),
  });

  const users = data?.data.users ?? [];
  const total = data?.data.total ?? 0;

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="font-poppins font-semibold text-2xl text-navy">Utilisateurs</h1>
        <p className="text-mid-grey text-sm mt-1">
          {total > 0 ? `${total} utilisateur${total > 1 ? 's' : ''}` : 'Recherche…'}
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-card p-4 mb-6 flex flex-wrap gap-3">
        <input
          type="search"
          placeholder="Rechercher nom, email, téléphone…"
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="flex-1 min-w-[220px] px-3 py-2 border border-light-grey rounded-lg text-sm focus:outline-none focus:border-teal"
        />
        <select
          value={kycStatus}
          onChange={(e) => { setKycStatus(e.target.value); setOffset(0); }}
          className="px-3 py-2 border border-light-grey rounded-lg text-sm focus:outline-none focus:border-teal"
        >
          <option value="">Tous KYC</option>
          {KYC_STATUSES.slice(1).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          value={accountStatus}
          onChange={(e) => { setAccountStatus(e.target.value); setOffset(0); }}
          className="px-3 py-2 border border-light-grey rounded-lg text-sm focus:outline-none focus:border-teal"
        >
          <option value="">Tous statuts</option>
          {ACCOUNT_STATUSES.slice(1).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl shadow-card overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <LoadingSpinner className="w-8 h-8" />
          </div>
        ) : isError ? (
          <p className="text-error text-sm text-center py-16">Erreur de chargement.</p>
        ) : users.length === 0 ? (
          <p className="text-mid-grey text-sm text-center py-16">Aucun utilisateur trouvé.</p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm admin-table">
                <thead>
                  <tr>
                    <th className="text-left px-4 py-3">Nom</th>
                    <th className="text-left px-4 py-3">E-mail</th>
                    <th className="text-left px-4 py-3">Téléphone</th>
                    <th className="text-left px-4 py-3">KYC</th>
                    <th className="text-left px-4 py-3">Compte</th>
                    <th className="text-left px-4 py-3">Inscrit le</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.user_id} className="border-t border-light-grey hover:bg-off-white transition-colors">
                      <td className="px-4 py-3 font-medium text-navy">{user.full_name}</td>
                      <td className="px-4 py-3 text-dark-grey">{user.email}</td>
                      <td className="px-4 py-3 text-dark-grey font-mono text-xs">{maskPhone(user.phone_number)}</td>
                      <td className="px-4 py-3">
                        <Badge label={user.kyc_status} variant={statusVariant(user.kyc_status)} />
                      </td>
                      <td className="px-4 py-3">
                        <Badge label={user.account_status} variant={statusVariant(user.account_status)} />
                      </td>
                      <td className="px-4 py-3 text-mid-grey text-xs">{formatDate(user.created_at)}</td>
                      <td className="px-4 py-3">
                        <Link
                          href={`/users/${user.user_id}`}
                          className="text-teal text-xs hover:underline font-medium"
                        >
                          Détail →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              offset={offset}
              limit={PAGE_SIZE}
              total={total}
              onPageChange={setOffset}
            />
          </>
        )}
      </div>
    </div>
  );
}
