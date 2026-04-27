/**
 * FR-041: Transaction detail view with real-time status polling.
 *
 * For pending/processing transactions: polls GET /transactions/{id}/status every 3s.
 * Stops polling when status reaches a terminal state (success | failed | reversed).
 * Used after deposit (202 accepted) and after transfer (show result).
 *
 * Poll stops after 125s (matching backend MTN MoMo timeout + buffer).
 */
import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  ActivityIndicator,
} from 'react-native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';
import type { RootStackParamList } from '../../App';
import { useTransaction, useTransactionStatus } from '@/hooks/useTransactions';
import { TerahButton } from '@/components/TerahButton';
import type { TransactionStatus } from '@/services/transactions';
import { colors, spacing, radius } from '@/utils/tokens';
import { formatXAF } from '@/utils/formatXAF';
import { formatDateTime } from '@/utils/formatDate';
import i18n from '@/locales';

type DetailNavProp = NativeStackNavigationProp<RootStackParamList, 'TransactionDetail'>;
type DetailRouteProp = RouteProp<RootStackParamList, 'TransactionDetail'>;

interface TransactionDetailScreenProps {
  navigation: DetailNavProp;
  route: DetailRouteProp;
}

const TERMINAL_STATUSES: TransactionStatus[] = ['success', 'failed', 'reversed'];
const POLL_TIMEOUT_MS = 125_000;  // Stop polling after 125s (matches backend MoMo timeout)

const STATUS_ICON: Record<TransactionStatus, string> = {
  pending:    '⏳',
  processing: '⚙️',
  success:    '✅',
  failed:     '❌',
  reversed:   '↩️',
};

const STATUS_COLOR: Record<TransactionStatus, string> = {
  pending:    colors.warning,
  processing: colors.warning,
  success:    colors.success,
  failed:     colors.error,
  reversed:   colors.midGrey,
};

const TYPE_KEY: Record<string, string> = {
  deposit:    'transactions.type_deposit',
  withdrawal: 'transactions.type_withdrawal',
  transfer:   'transactions.type_transfer',
  fee:        'transactions.type_fee',
  interest:   'transactions.type_interest',
  penalty:    'transactions.type_penalty',
};

const CHANNEL_KEY: Record<string, string> = {
  mtn_momo:     'transactions.channel_mtn_momo',
  orange_money:  'transactions.channel_orange_money',
  visa:          'transactions.channel_visa',
  mastercard:    'transactions.channel_mastercard',
  internal:      'transactions.channel_internal',
};

const STATUS_LABEL_KEY: Record<TransactionStatus, string> = {
  pending:    'transactions.status_pending',
  processing: 'transactions.status_processing',
  success:    'transactions.status_success',
  failed:     'transactions.status_failed',
  reversed:   'transactions.status_reversed',
};

export default function TransactionDetailScreen({
  navigation,
  route,
}: TransactionDetailScreenProps) {
  const { transactionId, reference } = route.params;

  // Fetch the full transaction record
  const { data: txn, isLoading, isError, refetch } = useTransaction(transactionId);

  // Determine current effective status (may be updated by polling)
  const [polledStatus, setPolledStatus] = useState<TransactionStatus | null>(null);
  const [pollingExpired, setPollingExpired] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const currentStatus: TransactionStatus = polledStatus ?? txn?.status ?? 'pending';
  const isTerminal = TERMINAL_STATUSES.includes(currentStatus);
  const shouldPoll = !isTerminal && !pollingExpired && !!transactionId;

  // FR-041: Real-time status poll every 3s
  useTransactionStatus(transactionId, shouldPoll);

  // Stop polling after POLL_TIMEOUT_MS regardless of status
  useEffect(() => {
    if (!shouldPoll) return;
    timeoutRef.current = setTimeout(() => setPollingExpired(true), POLL_TIMEOUT_MS);
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [shouldPoll]);

  // Sync polled status from transaction query updates
  useEffect(() => {
    if (txn?.status && txn.status !== polledStatus) {
      setPolledStatus(txn.status as TransactionStatus);
    }
  }, [txn?.status]);

  if (isLoading) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={colors.teal} />
        </View>
      </SafeAreaView>
    );
  }

  if (isError || !txn) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.centered}>
          <Text style={styles.errorText}>{i18n.t('errors.generic')}</Text>
          <TerahButton
            label={i18n.t('common.retry')}
            onPress={() => refetch()}
            style={{ marginTop: 16 }}
          />
        </View>
      </SafeAreaView>
    );
  }

  const statusColor = STATUS_COLOR[currentStatus];
  const statusIcon  = STATUS_ICON[currentStatus];

  return (
    <SafeAreaView style={styles.safe}>
      {/* App bar */}
      <View style={styles.appBar}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backButton}
          accessibilityRole="button"
          accessibilityLabel={i18n.t('common.back')}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <Text style={styles.backText}>←</Text>
        </TouchableOpacity>
        <Text style={styles.appBarTitle}>{i18n.t('transactions.detail_title')}</Text>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView style={styles.screen} contentContainerStyle={styles.container}>
        {/* Status hero */}
        <View style={styles.heroCard}>
          <Text style={styles.statusIcon}>{statusIcon}</Text>
          <Text style={[styles.statusLabel, { color: statusColor }]}>
            {i18n.t(STATUS_LABEL_KEY[currentStatus])}
          </Text>
          <Text style={styles.heroAmount}>{formatXAF(txn.amount)}</Text>
          <Text style={styles.heroReference} numberOfLines={1}>{txn.reference}</Text>

          {/* Polling indicator */}
          {shouldPoll && (
            <View style={styles.pollingRow}>
              <ActivityIndicator size="small" color={colors.teal} style={{ marginRight: 8 }} />
              <Text style={styles.pollingText}>{i18n.t('transactions.detail_polling')}</Text>
            </View>
          )}
        </View>

        {/* Detail rows */}
        <View style={styles.detailCard}>
          <DetailRow
            label={i18n.t('transactions.detail_type')}
            value={i18n.t(TYPE_KEY[txn.transaction_type] ?? 'transactions.type_transfer')}
          />
          <DetailRow
            label={i18n.t('transactions.detail_channel')}
            value={i18n.t(CHANNEL_KEY[txn.channel] ?? 'transactions.channel_internal')}
          />
          <DetailRow
            label={i18n.t('transactions.detail_status')}
            value={i18n.t(STATUS_LABEL_KEY[currentStatus])}
            valueColor={statusColor}
          />
          <DetailRow
            label={i18n.t('transactions.detail_date')}
            value={formatDateTime(txn.created_at)}
          />
          {txn.completed_at && (
            <DetailRow
              label={i18n.t('transactions.detail_completed')}
              value={formatDateTime(txn.completed_at)}
            />
          )}
          <DetailRow
            label={i18n.t('transactions.detail_reference')}
            value={txn.reference}
            mono
          />
        </View>

        {/* Actions */}
        <TerahButton
          label={i18n.t('transactions.history_title')}
          variant="secondary"
          onPress={() => navigation.navigate('TransactionHistory', {})}
          style={styles.cta}
        />
        <TerahButton
          label={i18n.t('dashboard.deposit')}
          onPress={() => navigation.navigate('Deposit')}
          style={styles.cta}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

// ── Reusable detail row ────────────────────────────────────────────────────────

function DetailRow({
  label,
  value,
  valueColor,
  mono = false,
}: {
  label: string;
  value: string;
  valueColor?: string;
  mono?: boolean;
}) {
  return (
    <View style={styles.detailRow}>
      <Text style={styles.detailKey}>{label}</Text>
      <Text
        style={[
          styles.detailValue,
          valueColor ? { color: valueColor } : null,
          mono ? styles.detailValueMono : null,
        ]}
        numberOfLines={2}
      >
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.offWhite },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  errorText: { fontFamily: 'Roboto_400Regular', fontSize: 15, color: colors.error },
  appBar: {
    backgroundColor: colors.navy,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
    height: 56,
  },
  backButton: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  backText: { fontFamily: 'Poppins_600SemiBold', fontSize: 20, color: '#FFFFFF' },
  appBarTitle: { fontFamily: 'Poppins_600SemiBold', fontSize: 18, color: '#FFFFFF' },
  screen: { flex: 1, backgroundColor: colors.offWhite },
  container: { paddingHorizontal: spacing.md, paddingBottom: 40, paddingTop: spacing.lg },
  heroCard: {
    backgroundColor: colors.white,
    borderRadius: radius.lg,
    padding: spacing.lg,
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  statusIcon: { fontSize: 52, marginBottom: spacing.sm },
  statusLabel: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 16,
    marginBottom: spacing.xs,
  },
  heroAmount: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 32,
    color: colors.navy,
    marginBottom: spacing.xs,
  },
  heroReference: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.midGrey,
  },
  pollingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: spacing.md,
  },
  pollingText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.teal,
  },
  detailCard: {
    backgroundColor: colors.white,
    borderRadius: radius.lg,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: colors.lightGrey,
  },
  detailKey: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.midGrey,
    flex: 1,
  },
  detailValue: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 14,
    color: colors.darkGrey,
    flex: 2,
    textAlign: 'right',
  },
  detailValueMono: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: colors.midGrey,
  },
  cta: { marginBottom: spacing.sm },
});
