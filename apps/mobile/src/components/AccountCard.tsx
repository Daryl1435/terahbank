import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors } from '@/utils/tokens';
import { formatXAF } from '@/utils/formatXAF';
import i18n from '@/locales';
import type { Account } from '@/services/accounts';
import { MaturityCountdown } from '@/components/MaturityCountdown';

interface AccountCardProps {
  account: Account;
  onPress?: () => void;
}

const ACCOUNT_TYPE_KEY: Record<Account['account_type'], string> = {
  standard: 'accounts.standard',
  project: 'accounts.project',
  term_deposit: 'accounts.term_deposit',
};

export const AccountCard: React.FC<AccountCardProps> = ({ account, onPress }) => {
  const typeLabel = i18n.t(ACCOUNT_TYPE_KEY[account.account_type]);

  // FR-017: progress bar for project accounts (from backend-computed progress_pct)
  const progressPercent = account.account_type === 'project' && account.target_amount
    ? (account.progress_pct ?? Math.min(100, Math.round((account.balance / account.target_amount) * 100)))
    : null;

  const isGoalReached = progressPercent !== null && progressPercent >= 100;

  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={onPress ? 0.8 : 1}
      accessibilityRole={onPress ? 'button' : 'none'}
      accessibilityLabel={`${typeLabel}: ${formatXAF(account.balance)}`}
      style={styles.card}
    >
      {/* Header row: type label + project name / maturity badge */}
      <View style={styles.header}>
        <Text style={styles.typeLabel}>{typeLabel}</Text>
        {account.account_type === 'project' && account.project_name ? (
          <Text style={styles.subLabel} numberOfLines={1}>
            {account.project_name}
          </Text>
        ) : null}
        {account.account_type === 'term_deposit' && account.days_to_maturity !== undefined ? (
          <Text
            style={[
              styles.subLabel,
              account.days_to_maturity <= 14 && styles.urgentLabel,
              account.days_to_maturity === 0 && styles.maturedLabel,
            ]}
          >
            {account.days_to_maturity === 0
              ? i18n.t('accounts.matured')
              : i18n.t('accounts.days_remaining', { days: account.days_to_maturity })}
          </Text>
        ) : null}
      </View>

      {/* Balance */}
      <Text style={styles.balance}>{formatXAF(account.balance)}</Text>

      {/* Account number */}
      {account.account_number ? (
        <Text style={styles.accountNumber}>{account.account_number}</Text>
      ) : null}

      {/* Project: progress bar + target info */}
      {progressPercent !== null && (
        <View style={styles.progressContainer}>
          <View style={styles.progressTrack}>
            <View
              style={[
                styles.progressFill,
                { width: `${progressPercent}%` },
                isGoalReached && styles.progressFillSuccess,
              ]}
            />
          </View>
          <View style={styles.progressLabelRow}>
            <Text style={styles.progressLabel}>
              {isGoalReached
                ? i18n.t('accounts.goal_reached')
                : i18n.t('accounts.progress', { percent: progressPercent })}
            </Text>
            {account.target_amount ? (
              <Text style={styles.targetLabel}>
                {formatXAF(account.target_amount)}
              </Text>
            ) : null}
          </View>
        </View>
      )}

      {/* Term Deposit: compact maturity info in card (not full countdown — that's in detail view) */}
      {account.account_type === 'term_deposit' && account.maturity_date && (
        <Text style={styles.maturityDateLabel}>
          {i18n.t('accounts.maturity_date')}: {account.maturity_date}
        </Text>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginHorizontal: 16,
    marginBottom: 8,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  typeLabel: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 12,
    color: colors.teal,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  subLabel: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: colors.midGrey,
    flex: 1,
    textAlign: 'right',
    marginLeft: 8,
  },
  urgentLabel: {
    color: colors.warning,
    fontFamily: 'Roboto_500Medium',
  },
  maturedLabel: {
    color: colors.success,
    fontFamily: 'Roboto_500Medium',
  },
  balance: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 24,
    color: colors.navy,
    marginBottom: 4,
  },
  accountNumber: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: colors.midGrey,
  },
  progressContainer: {
    marginTop: 12,
  },
  progressTrack: {
    height: 6,
    backgroundColor: colors.lightGrey,
    borderRadius: 999,
    overflow: 'hidden',
    marginBottom: 4,
  },
  progressFill: {
    height: '100%',
    backgroundColor: colors.teal,
    borderRadius: 999,
  },
  progressFillSuccess: {
    backgroundColor: colors.success,
  },
  progressLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  progressLabel: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 11,
    color: colors.midGrey,
  },
  targetLabel: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 11,
    color: colors.midGrey,
  },
  maturityDateLabel: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: colors.midGrey,
    marginTop: 8,
  },
});
