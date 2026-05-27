'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle } from 'lucide-react';
import { getConfig, updateConfig } from '@/lib/api';
import { formatDateTime } from '@/lib/format';
import { isSuperAdmin } from '@/lib/auth';
import { useTranslation } from '@/lib/i18n';
import type { TranslationKey } from '@/lib/i18n';
import LoadingSpinner from '@/components/LoadingSpinner';
import type { ConfigItem } from '@/lib/types';

const RATE_KEYS = new Set([
  'penalty_rate_project',
  'term_deposit_interest_rate',
  'early_break_penalty_rate',
]);

const AMOUNT_KEYS = new Set([
  'standard_min_balance',
  'standard_min_initial_deposit',
  'term_deposit_min_amount',
  'visa_max_cards_per_user',
]);

function validateConfigValue(key: string, value: string): TranslationKey | null {
  if (!value.trim()) return 'config.validation.required';
  if (RATE_KEYS.has(key)) {
    const n = parseFloat(value);
    if (isNaN(n) || n < 0 || n > 1) return 'config.validation.invalidRate';
  }
  if (AMOUNT_KEYS.has(key)) {
    const n = parseInt(value, 10);
    if (isNaN(n) || n < 0) return 'config.validation.invalidAmount';
  }
  return null;
}

function ConfigRow({ item, canEdit }: { item: ConfigItem; canEdit: boolean }) {
  const queryClient = useQueryClient();
  const { t } = useTranslation();
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
    const errKey = validateConfigValue(item.key, editValue);
    if (errKey) { setValError(t(errKey)); return; }
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
                {t('config.save')}
              </button>
              <button
                onClick={handleCancel}
                className="px-3 py-1 border border-light-grey rounded text-xs text-dark-grey hover:bg-light-grey transition-colors"
              >
                {t('config.cancel')}
              </button>
            </div>
          ) : (
            <button
              onClick={() => setEditing(true)}
              className="px-3 py-1 border border-light-grey rounded text-xs text-teal hover:bg-light-grey transition-colors"
            >
              {t('config.edit')}
            </button>
          )
        )}
      </td>
    </tr>
  );
}

export default function ConfigPage() {
  const canEdit = isSuperAdmin();
  const { t } = useTranslation();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin', 'config'],
    queryFn:  () => getConfig(),
  });

  const configs = data?.data.config ?? [];

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="font-poppins font-semibold text-2xl text-navy">{t('config.title')}</h1>
        <p className="text-mid-grey text-sm mt-1">
          {canEdit ? t('config.subtitleEdit') : t('config.subtitleRead')}
        </p>
      </div>

      {!canEdit && (
        <div className="mb-6 p-4 rounded-xl bg-warning/10 border border-warning/30 text-sm text-dark-grey flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-warning flex-shrink-0 mt-0.5" />
          {t('config.restricted')}
        </div>
      )}

      <div className="bg-white rounded-xl shadow-card overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-16"><LoadingSpinner className="w-8 h-8" /></div>
        ) : isError ? (
          <p className="text-error text-sm text-center py-16">{t('config.loadError')}</p>
        ) : configs.length === 0 ? (
          <p className="text-mid-grey text-sm text-center py-16">{t('config.noEntries')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm admin-table">
              <thead>
                <tr>
                  <th className="text-left px-4 py-3">{t('config.table.key')}</th>
                  <th className="text-left px-4 py-3">{t('config.table.value')}</th>
                  <th className="text-left px-4 py-3">{t('config.table.lastUpdated')}</th>
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
