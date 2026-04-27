'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getFraudAlerts } from '@/lib/api';
import { formatDateTime, formatXAF } from '@/lib/format';
import Pagination from '@/components/Pagination';
import LoadingSpinner from '@/components/LoadingSpinner';

const PAGE_SIZE = 50;

const RULE_LABELS: Record<string, { label: string; color: string }> = {
  LARGE_TRANSACTION:            { label: 'Transaction importante',       color: 'bg-error/10 text-error border-error/30' },
  VELOCITY_BREACH:              { label: 'Vélocité excessive',            color: 'bg-error/10 text-error border-error/30' },
  NEW_DEVICE_LARGE_WITHDRAWAL:  { label: 'Nouveau appareil + retrait',    color: 'bg-warning/10 text-warning border-warning/30' },
  NEW_ACCOUNT_RECIPIENT:        { label: 'Destinataire nouveau compte',   color: 'bg-warning/10 text-warning border-warning/30' },
};

export default function FraudAlertsPage() {
  const [offset,  setOffset]  = useState(0);
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin', 'fraud-alerts', offset],
    queryFn:  () => getFraudAlerts({ offset, limit: PAGE_SIZE }),
    refetchInterval: 30_000,
  });

  const alerts = data?.data.alerts ?? [];
  const total  = data?.data.total  ?? 0;

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="font-poppins font-semibold text-2xl text-navy">Alertes fraude</h1>
        <p className="text-mid-grey text-sm mt-1">
          {total} alerte{total !== 1 ? 's' : ''} enregistrée{total !== 1 ? 's' : ''} · rafraîchissement auto 30s
        </p>
      </div>

      {/* Rule legend */}
      <div className="flex flex-wrap gap-2 mb-6">
        {Object.entries(RULE_LABELS).map(([key, val]) => (
          <span
            key={key}
            className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${val.color}`}
          >
            {val.label}
          </span>
        ))}
      </div>

      <div className="bg-white rounded-xl shadow-card overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-16"><LoadingSpinner className="w-8 h-8" /></div>
        ) : isError ? (
          <p className="text-error text-sm text-center py-16">Erreur de chargement.</p>
        ) : alerts.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-3xl mb-3">🛡</p>
            <p className="font-poppins font-semibold text-navy">Aucune alerte</p>
            <p className="text-mid-grey text-sm mt-1">Aucune activité suspecte détectée.</p>
          </div>
        ) : (
          <>
            <div className="divide-y divide-light-grey">
              {alerts.map((alert) => {
                const ruleMeta = RULE_LABELS[alert.rule] ?? { label: alert.rule, color: 'bg-neutral text-dark-grey border-light-grey' };
                const isExpanded = expanded === alert.alert_id;
                return (
                  <div key={alert.alert_id} className="p-4 hover:bg-off-white transition-colors">
                    <div className="flex items-start justify-between gap-4 flex-wrap">
                      <div className="flex items-start gap-3">
                        <span
                          className={`mt-0.5 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border flex-shrink-0 ${ruleMeta.color}`}
                        >
                          {ruleMeta.label}
                        </span>
                        <div>
                          <p className="text-sm text-dark-grey">
                            User: <span className="font-mono text-xs text-mid-grey">{alert.actor_id}</span>
                          </p>
                          {alert.metadata.amount != null && (
                            <p className="text-sm font-medium text-navy">
                              {formatXAF(alert.metadata.amount as number)}
                            </p>
                          )}
                          {alert.metadata.txn_count_in_window != null && (
                            <p className="text-sm text-dark-grey">
                              {alert.metadata.txn_count_in_window as number} transactions en{' '}
                              {alert.metadata.window_minutes as number} min
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-mid-grey text-xs flex-shrink-0">
                          {formatDateTime(alert.created_at)}
                        </span>
                        <button
                          onClick={() => setExpanded(isExpanded ? null : alert.alert_id)}
                          className="text-teal text-xs hover:underline flex-shrink-0"
                        >
                          {isExpanded ? 'Masquer' : 'Détails'}
                        </button>
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="mt-3 bg-navy/5 rounded-lg p-3">
                        <p className="text-xs font-mono text-mid-grey mb-1">Métadonnées</p>
                        <pre className="text-xs text-dark-grey overflow-x-auto">
                          {JSON.stringify(alert.metadata, null, 2)}
                        </pre>
                        <p className="text-xs text-mid-grey mt-2">
                          ID alerte: <span className="font-mono">{alert.alert_id}</span>
                        </p>
                        {alert.entity_id && (
                          <p className="text-xs text-mid-grey">
                            Transaction: <span className="font-mono">{alert.entity_id}</span>
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <Pagination offset={offset} limit={PAGE_SIZE} total={total} onPageChange={setOffset} />
          </>
        )}
      </div>
    </div>
  );
}
