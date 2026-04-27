import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '@/utils/tokens';
import { formatXAF } from '@/utils/formatXAF';
import { formatDateTime } from '@/utils/formatDate';
import i18n from '@/locales';
import type { Transaction } from '@/services/transactions';

interface TransactionItemProps {
  transaction: Transaction;
  locale?: string;
}

const STATUS_COLOR: Record<Transaction['status'], string> = {
  pending: colors.warning,
  processing: colors.warning,
  success: colors.success,
  failed: colors.error,
  reversed: colors.midGrey,
};

const STATUS_KEY: Record<Transaction['status'], string> = {
  pending: 'transactions.status_pending',
  processing: 'transactions.status_processing',
  success: 'transactions.status_success',
  failed: 'transactions.status_failed',
  reversed: 'transactions.status_failed',
};

const CHANNEL_ICON: Record<Transaction['channel'], string> = {
  mtn_momo: 'MTN',
  orange_money: 'OM',
  visa: 'VISA',
  mastercard: 'MC',
  internal: 'TB',
};

export const TransactionItem: React.FC<TransactionItemProps> = ({
  transaction,
  locale = 'fr',
}) => {
  const isCredit = transaction.transaction_type === 'deposit' || transaction.transaction_type === 'interest';
  const amountSign = isCredit ? '+' : '-';
  const amountColor = isCredit ? colors.success : colors.darkGrey;

  return (
    <View style={styles.container} accessibilityRole="none">
      <View style={styles.iconContainer}>
        <Text style={styles.channelText}>{CHANNEL_ICON[transaction.channel]}</Text>
      </View>

      <View style={styles.details}>
        <Text style={styles.reference} numberOfLines={1}>
          {transaction.reference}
        </Text>
        <Text style={styles.date}>{formatDateTime(transaction.created_at, locale)}</Text>
      </View>

      <View style={styles.right}>
        <Text style={[styles.amount, { color: amountColor }]}>
          {amountSign} {formatXAF(transaction.amount, locale)}
        </Text>
        <Text style={[styles.status, { color: STATUS_COLOR[transaction.status] }]}>
          {i18n.t(STATUS_KEY[transaction.status])}
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: colors.lightGrey,
  },
  iconContainer: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.lightGrey,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  channelText: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 11,
    color: colors.navy,
  },
  details: {
    flex: 1,
    marginRight: 8,
  },
  reference: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 14,
    color: colors.darkGrey,
    marginBottom: 2,
  },
  date: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: colors.midGrey,
  },
  right: {
    alignItems: 'flex-end',
  },
  amount: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 14,
    marginBottom: 2,
  },
  status: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 11,
  },
});
