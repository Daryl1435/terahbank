/**
 * FR-047: Account detail view — tap-to-expand from dashboard.
 * Unified screen for all 3 account types (standard, project, term_deposit).
 * Shows type-specific sections below the common header.
 */
import React from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';
import type { RootStackParamList } from '../../App';
import { useAccount } from '@/hooks/useBalance';
import { ProgressBar } from '@/components/ProgressBar';
import { MaturityCountdown } from '@/components/MaturityCountdown';
import { TerahButton } from '@/components/TerahButton';
import { colors } from '@/utils/tokens';
import { formatXAF } from '@/utils/formatXAF';
import { formatDate } from '@/utils/formatDate';
import i18n from '@/locales';

type AccountDetailNavProp = NativeStackNavigationProp<RootStackParamList, 'AccountDetail'>;
type AccountDetailRouteProp = RouteProp<RootStackParamList, 'AccountDetail'>;

interface AccountDetailScreenProps {
  navigation: AccountDetailNavProp;
  route: AccountDetailRouteProp;
}

// Status badge colors
const STATUS_COLORS: Record<string, string> = {
  active: colors.success,
  locked: colors.warning,
  closed: colors.midGrey,
};

export default function AccountDetailScreen({ navigation, route }: AccountDetailScreenProps) {
  const { accountId } = route.params;
  const { data: account, isLoading, isError, refetch } = useAccount(accountId);

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.teal} />
      </View>
    );
  }

  if (isError || !account) {
    return (
      <View style={styles.centered}>
        <Text style={styles.errorText}>{i18n.t('errors.generic')}</Text>
        <TerahButton
          label={i18n.t('common.retry')}
          onPress={() => refetch()}
          style={{ marginTop: 16 }}
        />
      </View>
    );
  }

  const statusColor = STATUS_COLORS[account.status] ?? colors.midGrey;
  const progressPct = account.account_type === 'project' && account.target_amount
    ? (account.progress_pct ?? Math.min(100, Math.round((account.balance / account.target_amount) * 100)))
    : null;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.offWhite }} edges={['top', 'bottom']}>
      <ScrollView style={styles.screen} contentContainerStyle={styles.container}>
      {/* Back button */}
      <TouchableOpacity
        onPress={() => navigation.goBack()}
        style={styles.backButton}
        accessibilityRole="button"
        accessibilityLabel={i18n.t('common.back')}
        hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
      >
        <Text style={styles.backText}>← {i18n.t('common.back')}</Text>
      </TouchableOpacity>

      {/* Account type label + status */}
      <View style={styles.typeRow}>
        <Text style={styles.typeLabel}>
          {i18n.t(`accounts.${account.account_type}`)}
        </Text>
        <View style={[styles.statusBadge, { backgroundColor: statusColor + '20' }]}>
          <Text style={[styles.statusText, { color: statusColor }]}>
            {account.status.toUpperCase()}
          </Text>
        </View>
      </View>

      {/* Balance — FR-046/047 */}
      <Text style={styles.balance}>{formatXAF(account.balance)}</Text>
      <Text style={styles.balanceLabel}>{i18n.t('accounts.balance_label')}</Text>

      {/* Account number */}
      <View style={styles.infoCard}>
        <View style={styles.infoRow}>
          <Text style={styles.infoKey}>{i18n.t('accounts.account_number_label')}</Text>
          <Text style={styles.infoValue}>{account.account_number}</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoKey}>{i18n.t('accounts.created_on')}</Text>
          <Text style={styles.infoValue}>{formatDate(account.created_at)}</Text>
        </View>
      </View>

      {/* ── Standard Account section ─────────────────────────────────────────── */}
      {account.account_type === 'standard' && (
        <View style={styles.section}>
          {account.savings_insight ? (
            <View style={styles.insightBanner}>
              <Text style={styles.insightText}>💡 {account.savings_insight}</Text>
            </View>
          ) : null}
          <Text style={styles.sectionTitle}>{i18n.t('transactions.history_title')}</Text>
          <TerahButton
            label={i18n.t('transactions.history_title')}
            variant="secondary"
            onPress={() => navigation.navigate('TransactionHistory', { accountId })}
          />
        </View>
      )}

      {/* ── Project Account section (FR-017, FR-018, FR-020) ──────────────────── */}
      {account.account_type === 'project' && (
        <View style={styles.section}>
          {/* Project name */}
          {account.project_name ? (
            <Text style={styles.projectName}>{account.project_name}</Text>
          ) : null}

          {/* Progress bar — FR-017 */}
          {progressPct !== null && account.target_amount ? (
            <View style={styles.progressSection}>
              <ProgressBar
                percent={progressPct}
                label={i18n.t('accounts.target_amount_label')}
                showPercent
              />
              <View style={styles.targetRow}>
                <Text style={styles.infoKey}>{i18n.t('accounts.target_amount')}</Text>
                <Text style={styles.infoValue}>{formatXAF(account.target_amount)}</Text>
              </View>
            </View>
          ) : null}

          {/* Target date */}
          {account.target_date ? (
            <View style={styles.infoCard}>
              <View style={styles.infoRow}>
                <Text style={styles.infoKey}>{i18n.t('accounts.target_date')}</Text>
                <Text style={styles.infoValue}>{account.target_date}</Text>
              </View>
              {account.penalty_rate !== undefined && account.penalty_rate !== null ? (
                <View style={styles.infoRow}>
                  <Text style={styles.infoKey}>{i18n.t('accounts.early_break_rate')}</Text>
                  <Text style={styles.infoValue}>
                    {(Number(account.penalty_rate) * 100).toFixed(2)}%
                  </Text>
                </View>
              ) : null}
            </View>
          ) : null}

          {/* Auto-save rule info */}
          {account.auto_save_rule ? (
            <View style={styles.infoCard}>
              <Text style={styles.infoCardTitle}>Épargne automatique</Text>
              <View style={styles.infoRow}>
                <Text style={styles.infoKey}>Montant</Text>
                <Text style={styles.infoValue}>
                  {formatXAF(account.auto_save_rule.amount)}
                </Text>
              </View>
              <View style={styles.infoRow}>
                <Text style={styles.infoKey}>Fréquence</Text>
                <Text style={styles.infoValue}>{account.auto_save_rule.frequency}</Text>
              </View>
            </View>
          ) : null}
        </View>
      )}

      {/* ── Term Deposit section (FR-024, FR-025, FR-026, FR-027) ────────────── */}
      {account.account_type === 'term_deposit' && (
        <View style={styles.section}>
          {/* Maturity countdown — FR-027 */}
          {account.maturity_date && account.days_to_maturity !== undefined ? (
            <MaturityCountdown
              daysToMaturity={account.days_to_maturity}
              maturityDate={account.maturity_date}
            />
          ) : null}

          {/* Term deposit details */}
          <View style={styles.infoCard}>
            {/* FR-024: Interest rate */}
            {account.interest_rate !== undefined && account.interest_rate !== null ? (
              <View style={styles.infoRow}>
                <Text style={styles.infoKey}>{i18n.t('accounts.interest_rate')}</Text>
                <Text style={[styles.infoValue, styles.highlightValue]}>
                  {(Number(account.interest_rate) * 100).toFixed(2)}% / an
                </Text>
              </View>
            ) : null}

            {/* FR-026: Early break penalty rate */}
            {account.penalty_rate !== undefined && account.penalty_rate !== null ? (
              <View style={styles.infoRow}>
                <Text style={styles.infoKey}>{i18n.t('accounts.early_break_rate')}</Text>
                <Text style={styles.infoValue}>
                  {(Number(account.penalty_rate) * 100).toFixed(2)}%
                </Text>
              </View>
            ) : null}

            {/* Principal */}
            <View style={styles.infoRow}>
              <Text style={styles.infoKey}>{i18n.t('accounts.principal')}</Text>
              <Text style={styles.infoValue}>{formatXAF(account.balance)}</Text>
            </View>
          </View>

          {/* Transaction history link */}
          <Text style={styles.sectionTitle}>{i18n.t('transactions.history_title')}</Text>
          <TerahButton
            label={i18n.t('transactions.history_title')}
            variant="secondary"
            onPress={() => navigation.navigate('TransactionHistory', { accountId })}
          />
        </View>
      )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.offWhite,
  },
  container: {
    paddingHorizontal: 16,
    paddingBottom: 40,
  },
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.offWhite,
  },
  errorText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 15,
    color: colors.error,
    textAlign: 'center',
  },
  backButton: {
    paddingTop: 24,
    paddingBottom: 16,
    minHeight: 44,
    alignSelf: 'flex-start',
  },
  backText: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 14,
    color: colors.teal,
  },
  typeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  typeLabel: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 13,
    color: colors.teal,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  statusBadge: {
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  statusText: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 10,
    letterSpacing: 0.5,
  },
  balance: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 36,
    color: colors.navy,
  },
  balanceLabel: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.midGrey,
    marginBottom: 20,
  },
  infoCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  infoCardTitle: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 13,
    color: colors.navy,
    marginBottom: 10,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: colors.lightGrey,
  },
  infoKey: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.midGrey,
    flex: 1,
  },
  infoValue: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 13,
    color: colors.darkGrey,
    textAlign: 'right',
  },
  highlightValue: {
    color: colors.teal,
    fontFamily: 'Poppins_600SemiBold',
  },
  section: {
    marginTop: 8,
  },
  sectionTitle: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 15,
    color: colors.navy,
    marginTop: 16,
    marginBottom: 8,
  },
  projectName: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 22,
    color: colors.navy,
    marginBottom: 16,
  },
  progressSection: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  targetRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  insightBanner: {
    backgroundColor: colors.teal + '15',
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
  },
  insightText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.navy,
  },
});
