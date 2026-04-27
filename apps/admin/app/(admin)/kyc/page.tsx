'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getKYCQueue, makeKYCDecision } from '@/lib/api';
import { formatDateTime, maskPhone } from '@/lib/format';
import Pagination from '@/components/Pagination';
import LoadingSpinner from '@/components/LoadingSpinner';
import type { KYCQueueItem } from '@/lib/types';

const PAGE_SIZE = 20;

const REJECTION_REASONS = [
  'Document illisible ou de mauvaise qualité',
  'Document expiré',
  'Nom ne correspond pas au compte',
  'Document non accepté (type invalide)',
  'Suspicion de falsification',
  'Autre (voir commentaire)',
];

function KYCRow({
  item,
  onApprove,
  onReject,
}: {
  item: KYCQueueItem;
  onApprove: (userId: string) => void;
  onReject:  (userId: string) => void;
}) {
  return (
    <tr className="border-t border-light-grey hover:bg-off-white transition-colors">
      <td className="px-4 py-3 font-medium text-navy">{item.full_name}</td>
      <td className="px-4 py-3 text-dark-grey text-sm">{item.email}</td>
      <td className="px-4 py-3 font-mono text-xs text-dark-grey">{maskPhone(item.phone_number)}</td>
      <td className="px-4 py-3 text-sm">
        <span className="bg-navy/10 text-navy px-2 py-0.5 rounded font-mono text-xs">
          {item.document_type}
        </span>
      </td>
      <td className="px-4 py-3 text-mid-grey text-xs">{formatDateTime(item.uploaded_at)}</td>
      <td className="px-4 py-3">
        <div className="flex gap-2">
          <button
            onClick={() => onApprove(item.user_id)}
            className="px-3 py-1 bg-success text-white rounded text-xs font-medium hover:opacity-90 transition-opacity"
          >
            Approuver
          </button>
          <button
            onClick={() => onReject(item.user_id)}
            className="px-3 py-1 bg-error text-white rounded text-xs font-medium hover:opacity-90 transition-opacity"
          >
            Rejeter
          </button>
        </div>
      </td>
    </tr>
  );
}

export default function KYCQueuePage() {
  const queryClient = useQueryClient();
  const [offset, setOffset] = useState(0);

  const [approveUserId, setApproveUserId] = useState<string | null>(null);
  const [rejectUserId,  setRejectUserId]  = useState<string | null>(null);
  const [rejectionReason, setRejectionReason] = useState(REJECTION_REASONS[0]);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin', 'kyc', 'queue', offset],
    queryFn:  () => getKYCQueue({ offset, limit: PAGE_SIZE }),
    refetchInterval: 30_000, // auto-refresh every 30s
  });

  const mutation = useMutation({
    mutationFn: ({
      userId,
      decision,
      reason,
    }: {
      userId: string;
      decision: 'approved' | 'rejected';
      reason?: string;
    }) => makeKYCDecision(userId, decision, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'kyc'] });
      setApproveUserId(null);
      setRejectUserId(null);
    },
  });

  const items = data?.data.items ?? [];
  const total = data?.data.total ?? 0;

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="font-poppins font-semibold text-2xl text-navy">File KYC</h1>
        <p className="text-mid-grey text-sm mt-1">
          {total} document{total !== 1 ? 's' : ''} en attente de vérification
        </p>
      </div>

      {/* Approve confirm modal */}
      {approveUserId && (
        <div className="fixed inset-0 bg-navy/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-modal p-6 max-w-sm w-full">
            <h3 className="font-poppins font-semibold text-navy text-lg mb-2">Approuver le KYC</h3>
            <p className="text-sm text-dark-grey mb-6">
              Confirmer l&apos;approbation du document KYC pour cet utilisateur ?
            </p>
            {mutation.isError && (
              <p className="text-error text-sm mb-4">{(mutation.error as Error)?.message}</p>
            )}
            <div className="flex gap-3">
              <button
                onClick={() => mutation.mutate({ userId: approveUserId, decision: 'approved' })}
                disabled={mutation.isPending}
                className="flex-1 bg-success text-white py-2.5 rounded-lg text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {mutation.isPending && <LoadingSpinner />}
                Confirmer
              </button>
              <button
                onClick={() => setApproveUserId(null)}
                className="flex-1 border border-light-grey py-2.5 rounded-lg text-sm text-dark-grey hover:bg-light-grey transition-colors"
              >
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reject modal with reason dropdown */}
      {rejectUserId && (
        <div className="fixed inset-0 bg-navy/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-modal p-6 max-w-sm w-full">
            <h3 className="font-poppins font-semibold text-navy text-lg mb-2">Rejeter le KYC</h3>
            <p className="text-sm text-dark-grey mb-4">
              Sélectionnez le motif de rejet. Il sera communiqué à l&apos;utilisateur.
            </p>
            <select
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              className="w-full px-3 py-2 border border-light-grey rounded-lg text-sm mb-4 focus:outline-none focus:border-teal"
            >
              {REJECTION_REASONS.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
            {mutation.isError && (
              <p className="text-error text-sm mb-4">{(mutation.error as Error)?.message}</p>
            )}
            <div className="flex gap-3">
              <button
                onClick={() =>
                  mutation.mutate({
                    userId: rejectUserId,
                    decision: 'rejected',
                    reason: rejectionReason,
                  })
                }
                disabled={mutation.isPending}
                className="flex-1 bg-error text-white py-2.5 rounded-lg text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {mutation.isPending && <LoadingSpinner />}
                Rejeter
              </button>
              <button
                onClick={() => setRejectUserId(null)}
                className="flex-1 border border-light-grey py-2.5 rounded-lg text-sm text-dark-grey hover:bg-light-grey transition-colors"
              >
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl shadow-card overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-16"><LoadingSpinner className="w-8 h-8" /></div>
        ) : isError ? (
          <p className="text-error text-sm text-center py-16">Erreur de chargement.</p>
        ) : items.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-3xl mb-3">✅</p>
            <p className="font-poppins font-semibold text-navy">File vide</p>
            <p className="text-mid-grey text-sm mt-1">Tous les documents ont été traités.</p>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm admin-table">
                <thead>
                  <tr>
                    <th className="text-left px-4 py-3">Nom</th>
                    <th className="text-left px-4 py-3">E-mail</th>
                    <th className="text-left px-4 py-3">Téléphone</th>
                    <th className="text-left px-4 py-3">Document</th>
                    <th className="text-left px-4 py-3">Soumis le</th>
                    <th className="px-4 py-3">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <KYCRow
                      key={item.document_id}
                      item={item}
                      onApprove={setApproveUserId}
                      onReject={setRejectUserId}
                    />
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
