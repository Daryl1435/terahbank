/**
 * PasswordStrengthMeter — real-time visual indicator of password complexity.
 * FR-003: min 10 chars, 1 uppercase, 1 digit, 1 special char.
 * Shows a 4-segment colored progress bar + individual requirement checklist.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors } from '@/utils/tokens';
import i18n from '@/locales';

interface PasswordStrengthMeterProps {
  password: string;
}

interface Requirement {
  key: string;
  label: string;
  test: (p: string) => boolean;
}

const REQUIREMENTS: Requirement[] = [
  { key: 'length',    label: 'req_length',    test: (p) => p.length >= 10 },
  { key: 'uppercase', label: 'req_uppercase',  test: (p) => /[A-Z]/.test(p) },
  { key: 'number',    label: 'req_number',     test: (p) => /[0-9]/.test(p) },
  { key: 'special',   label: 'req_special',    test: (p) => /[^A-Za-z0-9]/.test(p) },
];

const STRENGTH_COLORS = ['#E53E3E', '#FFB020', '#FFB020', '#00B4D8', '#00C48C'] as const;

const strengthLabel = (score: number): string => {
  if (score <= 1) return i18n.t('auth.strength_weak');
  if (score === 2) return i18n.t('auth.strength_medium');
  if (score === 3) return i18n.t('auth.strength_good');
  return i18n.t('auth.strength_strong');
};

export function PasswordStrengthMeter({ password }: PasswordStrengthMeterProps) {
  const results = REQUIREMENTS.map((req) => ({
    ...req,
    met: req.test(password),
  }));
  const score = results.filter((r) => r.met).length;
  const barColor = STRENGTH_COLORS[score];

  if (!password) return null;

  return (
    <View style={styles.container} accessibilityLiveRegion="polite">
      {/* Progress bar — 4 segments */}
      <View style={styles.barRow}>
        {REQUIREMENTS.map((_, i) => (
          <View
            key={i}
            style={[
              styles.barSegment,
              { backgroundColor: i < score ? barColor : colors.lightGrey },
            ]}
          />
        ))}
        <Text style={[styles.strengthLabel, { color: barColor }]}>
          {strengthLabel(score)}
        </Text>
      </View>

      {/* Requirement checklist */}
      <View style={styles.requirements}>
        {results.map((req) => (
          <View key={req.key} style={styles.reqRow}>
            <Text style={[styles.reqIcon, req.met ? styles.reqMet : styles.reqUnmet]}>
              {req.met ? '✓' : '○'}
            </Text>
            <Text style={[styles.reqText, req.met ? styles.reqTextMet : styles.reqTextUnmet]}>
              {i18n.t(`auth.${req.label}`)}
            </Text>
          </View>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 4,
    marginBottom: 8,
  },
  barRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginBottom: 10,
  },
  barSegment: {
    flex: 1,
    height: 4,
    borderRadius: 2,
  },
  strengthLabel: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 12,
    marginLeft: 8,
    minWidth: 44,
    textAlign: 'right',
  },
  requirements: {
    gap: 4,
  },
  reqRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  reqIcon: {
    fontSize: 13,
    width: 16,
    textAlign: 'center',
  },
  reqMet: {
    color: colors.success,
  },
  reqUnmet: {
    color: colors.midGrey,
  },
  reqText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
  },
  reqTextMet: {
    color: colors.darkGrey,
  },
  reqTextUnmet: {
    color: colors.midGrey,
  },
});
