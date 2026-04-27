'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getUser, updateUserStatus } from '@/lib/api';
import { canMutate } from '@/lib/auth';
import { formatDate, formatXAF, maskPhone } from '@/lib/format';
import Badge, { statusVariant } from '@/components/Badge';
import LoadingSpinner from '@/components/LoadingSpinner';

const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  standard:     'Standard',
  project:      'Projet (Vault)',
  term_deposit: 'Dépôt à terme',
};

export default function UserDetailPage() {
  const params      = useParams<{ id: string }>();
  const router      = useRouter();
  const queryClient = useQueryClient();
  const userId      = params.id;

  const [confirmAction, setConfirmAction] = useState<'active' | 'suspended' | 'closed' | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin', 'user', userId],
    queryFn:  () => getUser(userId),
  });

  const mutation = useMutation({
    mutationFn: (newStatus: 'active' | 'suspended' | 'closed') =>
      updateUserStatus(userId, newStatus),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'user', userId] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      setConfirmAction(null);
    },
  });

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-64">
        <LoadingSpinner className="w-8 h-8" />
      </div>
    );
  }

  if (isError || !data?.data) {
    return (
      <div className="p-8">
        <p className="text-error">Utilisateur introuvable.</p>
        <Link href="/users" className="text-teal text-sm mt-2 inline-block hover:underline">
          ← Retour à la liste
        </Link>
      </div>
    );
  }

  const user    = data.data;
  const mutateAllowed = canMutate();

  return (
    <div className="p-8 max-w-4xl">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-mid-grey mb-6">
        <Link href="/users" className="hover:text-teal transition-colors">Utilisateurs</Link>
        <span>›</span>
        <span className="text-dark-grey">{user.full_name}</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between mb-8 flex-wrap gap-4">
        <div>
          <h1 className="font-poppins font-semibold text-2xl text-navy">{user.full_name}</h1>
          <p className="text-mid-grey text-sm mt-1">ID: <span className="font-mono text-xs">{user.user_id}</span></p>
        </div>
        <div className="flex gap-2">
          <Badge label={`KYC: ${user.kyc_status}`}    variant={statusVariant(user.kyc_status)} />
          <Badge label={user.account_status}           variant={statusVariant(user.account_status)} />
        </div>
      </div>

      {/* User info card */}
      <div className="bg-white rounded-xl shadow-card p-6 mb-6">
        <h2 className="font-poppins font-semibold text-base text-navy mb-4">Informations personnelles</h2>
        <dl className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm">
          <div>
            <dt className="text-mid-grey">E-mail</dt>
            <dd className="text-dark-grey font-medium">{user.email}</dd>
          </div>
          <div>
            <dt className="text-mid-grey">Téléphone</dt>
            <dd className="text-dark-grey font-medium font-mono">{maskPhone(user.phone_number)}</dd>
          </div>
          <div>
            <dt className="text-mid-grey">Langue préférée</dt>
            <dd className="text-dark-grey font-medium uppercase">{user.preferred_language}</dd>
          </div>
          <div>
            <dt className="text-mid-grey">Inscrit le</dt>
            <dd className="text-dark-grey font-medium">{formatDate(user.created_at)}</dd>
          </div>
        </dl>
      </div>

      {/* Accounts */}
      <div className="bg-white rounded-xl shadow-card p-6 mb-6">
        <h2 className="font-poppins font-semibold text-base text-navy mb-4">
          Comptes ({user.accounts.length})
        </h2>
        {user.accounts.length === 0 ? (
          <p className="text-mid-grey text-sm">Aucun compte ouvert.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm admin-table">
              <thead>
                <tr>
                  <th className="text-left px-3 py-2">Type</th>
                  <th className="text-left px-3 py-2">Numéro</th>
                  <th className="text-right px-3 py-2">Solde</th>
                  <th className="text-left px-3 py-2">Statut</th>
                </tr>
              </thead>
              <tbody>
                {user.accounts.map((acc) => (
                  <tr key={acc.account_id} className="border-t border-light-grey">
                    <td className="px-3 py-2 text-dark-grey">
                      {ACCOUNT_TYPE_LABELS[acc.account_type] ?? acc.account_type}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-mid-grey">{acc.account_number}</td>
                    <td className="px-3 py-2 text-right font-medium text-navy">{formatXAF(acc.balance)}</td>
                    <td className="px-3 py-2">
                      <Badge label={acc.status} variant={statusVariant(acc.status)} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Status management */}
      {mutateAllowed && (
        <div className="bg-white rounded-xl shadow-card p-6">
          <h2 className="font-poppins font-semibold text-base text-navy mb-4">Gestion du compte</h2>

          {mutation.isError && (
            <p className="text-error text-sm mb-3">
              {(mutation.error as Error)?.message ?? 'Erreur lors de la mise à jour.'}
            </p>
          )}

          {confirmAction ? (
            <div className="bg-warning/10 border border-warning/30 rounded-lg p-4">
              <p className="text-sm text-dark-grey mb-4">
                Confirmer l&apos;action : <strong>{confirmAction}</strong> pour{' '}
                <strong>{user.full_name}</strong> ?
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => mutation.mutate(confirmAction)}
                  disabled={mutation.isPending}
                  className="px-4 py-2 bg-navy text-white rounded-lg text-sm font-medium hover:bg-dark-navy transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {mutation.isPending && <LoadingSpinner />}
                  Confirmer
                </button>
                <button
                  onClick={() => setConfirmAction(null)}
                  className="px-4 py-2 border border-light-grey rounded-lg text-sm text-dark-grey hover:bg-light-grey transition-colors"
                >
                  Annuler
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap gap-3">
              {user.account_status !== 'active' && (
                <button
                  onClick={() => setConfirmAction('active')}
                  className="px-4 py-2 bg-success text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
                >
                  Réactiver le compte
                </button>
              )}
              {user.account_status !== 'suspended' && (
                <button
                  onClick={() => setConfirmAction('suspended')}
                  className="px-4 py-2 bg-warning text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
                >
                  Suspendre
                </button>
              )}
              {user.account_status !== 'closed' && (
                <button
                  onClick={() => setConfirmAction('closed')}
                  className="px-4 py-2 bg-error text-white rounded-lg text-sm font-medium hover:opacity-90 transition-opacity"
                >
                  Clôturer le compte
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
