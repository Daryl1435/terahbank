/**
 * FR-027: Maturity countdown display for Term Deposit accounts.
 * Shows the number of days (or "matured") until a term deposit matures.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '@/utils/tokens';
import i18n from '@/locales';

interface MaturityCountdownProps {
  daysToMaturity: number;   // 0 = matured; positive = days remaining
  maturityDate: string;     // ISO date string for display
}

export const MaturityCountdown: React.FC<MaturityCountdownProps> = ({
  daysToMaturity,
  maturityDate,
}) => {
  const isMatured = daysToMaturity === 0;

  // Display "X months Y days" when > 30 days, else just days
  const months = Math.floor(daysToMaturity / 30);
  const remainingDays = daysToMaturity % 30;

  const countdownLabel = isMatured
    ? i18n.t('accounts.matured')
    : months >= 2
    ? i18n.t('accounts.months_to_maturity', { months })
    : i18n.t('accounts.days_to_maturity', { days: daysToMaturity });

  return (
    <View style={[styles.container, isMatured && styles.maturedContainer]}>
      <View style={styles.row}>
        {/* Hourglass icon placeholder */}
        <Text style={[styles.icon, isMatured && styles.iconMatured]}>
          {isMatured ? '✓' : '⏳'}
        </Text>
        <View style={styles.textGroup}>
          <Text style={[styles.label, isMatured && styles.labelMatured]}>
            {countdownLabel}
          </Text>
          <Text style={styles.dateText}>
            {i18n.t('accounts.maturity_date')}{': '}
            {maturityDate}
          </Text>
        </View>
      </View>
      {!isMatured && daysToMaturity <= 14 && (
        <View style={styles.urgentBadge}>
          <Text style={styles.urgentText}>
            {i18n.t('accounts.days_remaining', { days: daysToMaturity })}
          </Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.lightGrey,
    borderRadius: 10,
    padding: 12,
    marginTop: 12,
  },
  maturedContainer: {
    backgroundColor: '#E6F9F2',  // light success tint
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  icon: {
    fontSize: 22,
  },
  iconMatured: {
    color: colors.success,
  },
  textGroup: {
    flex: 1,
  },
  label: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 14,
    color: colors.navy,
  },
  labelMatured: {
    color: colors.success,
  },
  dateText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: colors.midGrey,
    marginTop: 2,
  },
  urgentBadge: {
    marginTop: 8,
    alignSelf: 'flex-start',
    backgroundColor: colors.warning,
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  urgentText: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 11,
    color: '#FFFFFF',
  },
});
