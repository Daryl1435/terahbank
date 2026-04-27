'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getConfig, updateConfig } from '@/lib/api';
import { formatDateTime } from '@/lib/format';
import { isSuperAdmin } from '@/lib/auth';
import LoadingSpinner from '@/components/LoadingSpinner';
import type { ConfigItem } from '@/lib/types';

/** Config keys that contain numeric rates — validated as float between 0 and 1. */
const RATE_KEYS = new Set([
  'penalty_rate_project',
  'term_deposit_interest_rate',
  'early_break_penalty_rate',
]);

/** Config keys that contain integer amounts. */
const AMOUNT_KEYS = new Set([
  'standard_min_balance',
  'standard_min_initial_deposit',
  'term_deposit_min_amount',
  'visa_max_cards_per_user',
]);

function validateConfigValue(key: string, value: string): string | null {
  if (!value.trim()) return 'La valeur est obligatoire.';
  if (RATE_KEYS.has(key)) {
    const n = parseFloat(value);
    if (isNaN(n) || n < 0 || n > 1) return 'Taux invalide. Doit être un décimal entre 0 et 1 (ex: 0.015).';
  }
  if (AMOUNT_KEYS.has(key)) {
    const n = parseInt(value, 10);
    if (isNaN(n) || n < 0) return 'Montant invalide. Doit être un entier positif.';
  }
  return null;
}

function ConfigRow({ item, canEdit }: { item: ConfigItem; canEdit: boolean }) {
  const queryClient = useQueryClient();
  const [editing,   setEditing]   = useState(false);
  const [editValue, setEditValue] = useState(item.value);
  const [valError,  setValError]  = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) => updateConfig(key, value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'config'] });
      setEditing(false);
      setValError(null);
    },
  });

  function handleSave() {
    const err = validateConfigValue(item.key, editValue);
    if (err) { setValError(err); return; }
    mutation.mutate({ key: item.key, value: editValue });
  }

  function handleCancel() {
    setEditing(false);
    setEditValue(item.value);
    setValError(null);
  }

  return (
    <tr className="border-t border-light-grey hover:bg-off-white transition-colors">
      <td className="px-4 py-3 font-mono text-xs text-navy font-medium">{item.key}</td>
      <td className="px-4 py-3">
        {editing ? (
          <div>
            <input
              type="text"
              value={editValue}
              onChange={(e) => { setEditValue(e.target.value); setValError(null); }}
              className="px-2 py-1 border border-teal rounded text-sm w-48 focus:outline-none font-mono"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSave();
                if (e.key === 'Escape') handleCancel();
              }}
            />
            {valError && <p className="text-error text-xs mt-1">{valError}</p>}
            {mutation.isError && (
              <p className="text-error text-xs mt-1">{(mutation.error as Error)?.message}</p>
            )}
          </div>
        ) : (
          <span className="font-mono text-sm text-dark-grey">{item.value}</span>
        )}
      </td>
      <td className="px-4 py-3 text-mid-grey text-xs">{formatDateTime(item.updated_at)}</td>
      <td className="px-4 py-3">
        {canEdit && (
          editing ? (
            <div className="flex gap-2">
              <button
                onClick={handleSave}
                disabled={mutation.isPending}
                className="px-3 py-1 bg-teal text-white rounded text-xs font-medium hover:bg-teal-dark transition-colors disabled:opacity-50 flex items-center gap-1"
              >
                {mutation.isPending && <LoadingSpinner />}
                Sauvegarder
              </button>
              <button
                onClick={handleCancel}
                className="px-3 py-1 border border-light-grey rounded text-xs text-dark-grey hover:bg-light-grey transition-colors"
              >
                Annuler
              </button>
            </div>
          ) : (
            <button
              onClick={() => setEditing(true)}
              className="px-3 py-1 border border-light-grey rounded text-xs text-teal hover:bg-light-grey transition-colors"
            >
              Modifier
            </button>
          )
        )}
      </td>
    </tr>
  );
}

export default function ConfigPage() {
  const canEdit = isSuperAdmin();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin', 'config'],
    queryFn:  () => getConfig(),
  });

  const configs = data?.data.config ?? [];

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="font-poppins font-semibold text-2xl text-navy">Configuration système</h1>
        <p className="text-mid-grey text-sm mt-1">
          {canEdit
            ? 'Paramètres modifiables — taux, limites et seuils opérationnels.'
            : 'Lecture seule — seul un Super Admin peut modifier la configuration.'}
        </p>
      </div>

      {!canEdit && (
        <div className="mb-6 p-4 rounded-xl bg-warning/10 border border-warning/30 text-sm text-dark-grey">
          ⚠ Accès restreint : la modification de la configuration est réservée aux Super Admins.
        </div>
      )}

      <div className="bg-white rounded-xl shadow-card overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-16"><LoadingSpinner className="w-8 h-8" /></div>
        ) : isError ? (
          <p className="text-error text-sm text-center py-16">Erreur de chargement.</p>
        ) : configs.length === 0 ? (
          <p className="text-mid-grey text-sm text-center py-16">Aucune configuration trouvée.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm admin-table">
              <thead>
                <tr>
                  <th className="text-left px-4 py-3">Clé</th>
                  <th className="text-left px-4 py-3">Valeur</th>
                  <th className="text-left px-4 py-3">Modifié le</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {configs.map((cfg) => (
                  <ConfigRow key={cfg.key} item={cfg} canEdit={canEdit} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
