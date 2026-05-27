'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Shield } from 'lucide-react';
import { getFraudAlerts } from '@/lib/api';
import { formatDateTime, formatXAF } from '@/lib/format';
import { useTranslation } from '@/lib/i18n';
import type { TranslationKey } from '@/lib/i18n';
import Pagination from '@/components/Pagination';
import LoadingSpinner from '@/components/LoadingSpinner';

const PAGE_SIZE = 50;

const RULE_COLORS: Record<string, string> = {
  LARGE_TRANSACTION:            'bg-error/10 text-error border-error/30',
  VELOCITY_BREACH:              'bg-error/10 text-error border-error/30',
  NEW_DEVICE_LARGE_WITHDRAWAL:  'bg-warning/10 text-warning border-warning/30',
  NEW_ACCOUNT_RECIPIENT:        'bg-warning/10 text-warning border-warning/30',
};

const RULE_KEYS: Record<string, TranslationKey> = {
  LARGE_TRANSACTION:            'fraud.rules.LARGE_TRANSACTION',
  VELOCITY_BREACH:              'fraud.rules.VELOCITY_BREACH',
  NEW_DEVICE_LARGE_WITHDRAWAL:  'fraud.rules.NEW_DEVICE_LARGE_WITHDRAWAL',
  NEW_ACCOUNT_RECIPIENT:        'fraud.rules.NEW_ACCOUNT_RECIPIENT',
};

export default function FraudAlertsPage() {
  const [offset,   setOffset]   = useState(0);
  const [expanded, setExpanded] = useState<string | null>(null);
  const { t } = useTranslation();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin', 'fraud-alerts', offset],
    queryFn:  () => getFraudAlerts({ offset, limit: PAGE_SIZE }),
    refetchInterval: 30_000,
  });

  const alerts = data?.data.alerts ?? [];
  const total  = data?.data.total  ?? 0;

  const countText = t('fraud.countAuto').replace('{count}', String(total));

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="font-poppins font-semibold text-2xl text-navy">{t('fraud.title')}</h1>
        <p className="text-mid-grey text-sm mt-1">{countText}</p>
      </div>

      {/* Rule legend */}
      <div className="flex flex-wrap gap-2 mb-6">
        {Object.entries(RULE_KEYS).map(([key, tKey]) => (
          <span
            key={key}
            className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${RULE_COLORS[key] ?? ''}`}
          >
            {t(tKey)}
          </span>
        ))}
      </div>

      <div className="bg-white rounded-xl shadow-card overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-16"><LoadingSpinner className="w-8 h-8" /></div>
        ) : isError ? (
          <p className="text-error text-sm text-center py-16">{t('fraud.loadError')}</p>
        ) : alerts.length === 0 ? (
          <div className="text-center py-16">
            <Shield className="w-12 h-12 text-mid-grey mx-auto mb-3" />
            <p className="font-poppins font-semibold text-navy">{t('fraud.noAlerts')}</p>
            <p className="text-mid-grey text-sm mt-1">{t('fraud.noAlertsDesc')}</p>
          </div>
        ) : (
          <>
            <div className="divide-y divide-light-grey">
              {alerts.map((alert) => {
                const ruleKey   = RULE_KEYS[alert.rule];
                const ruleLabel = ruleKey ? t(ruleKey) : alert.rule;
                const ruleColor = RULE_COLORS[alert.rule] ?? 'bg-neutral text-dark-grey border-light-grey';
                const isExpanded = expanded === alert.alert_id;

                const txnCount  = alert.metadata.txn_count_in_window as number | undefined;
                const winMins   = alert.metadata.window_minutes       as number | undefined;

                return (
                  <div key={alert.alert_id} className="p-4 hover:bg-off-white transition-colors">
                    <div className="flex items-start justify-between gap-4 flex-wrap">
                      <div className="flex items-start gap-3">
                        <span
                          className={`mt-0.5 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border flex-shrink-0 ${ruleColor}`}
                        >
                          {ruleLabel}
                        </span>
                        <div>
                          <p className="text-sm text-dark-grey">
                            {t('fraud.user')}: <span className="font-mono text-xs text-mid-grey">{alert.actor_id}</span>
                          </p>
                          {alert.metadata.amount != null && (
                            <p className="text-sm font-medium text-navy">
                              {formatXAF(alert.metadata.amount as number)}
                            </p>
                          )}
                          {txnCount != null && winMins != null && (
                            <p className="text-sm text-dark-grey">
                              {t('fraud.txnInWindow')
                                .replace('{count}',   String(txnCount))
                                .replace('{minutes}', String(winMins))}
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
                          {isExpanded ? t('fraud.hide') : t('fraud.details')}
                        </button>
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="mt-3 bg-navy/5 rounded-lg p-3">
                        <p className="text-xs font-mono text-mid-grey mb-1">{t('fraud.metadata')}</p>
                        <pre className="text-xs text-dark-grey overflow-x-auto">
                          {JSON.stringify(alert.metadata, null, 2)}
                        </pre>
                        <p className="text-xs text-mid-grey mt-2">
                          {t('fraud.alertId')}: <span className="font-mono">{alert.alert_id}</span>
                        </p>
                        {alert.entity_id && (
                          <p className="text-xs text-mid-grey">
                            {t('fraud.transaction')}: <span className="font-mono">{alert.entity_id}</span>
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
