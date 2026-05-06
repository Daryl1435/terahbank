/**
 * FR-023/025: Open Term Deposit with inline interest calculator.
 * Flow: user enters amount + duration → taps "Simuler" → sees projected returns →
 *       taps "Confirmer l'ouverture" → account created.
 *
 * FR-024: 2% per annum, pro-rata by month (read from system_config via calculator API).
 * FR-026: Early break penalty shown in calculator preview.
 * FR-025: Calculator displayed before user confirms.
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import { useOpenTermDeposit } from '@/hooks/useBalance';
import { accountsService, TermDepositCalculatorResponse } from '@/services/accounts';
import { TerahButton } from '@/components/TerahButton';
import { TerahInput } from '@/components/TerahInput';
import { colors } from '@/utils/tokens';
import { formatXAF } from '@/utils/formatXAF';
import i18n from '@/locales';

type OpenTermDepositNavProp = NativeStackNavigationProp<RootStackParamList, 'OpenTermDeposit'>;

interface OpenTermDepositScreenProps {
  navigation: OpenTermDepositNavProp;
}

const MIN_AMOUNT = 20_000_000; // 200,000 XAF

export default function OpenTermDepositScreen({ navigation }: OpenTermDepositScreenProps) {
  const [amountInput, setAmountInput] = useState('');
  const [durationInput, setDurationInput] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string | null>>({});

  // FR-025: calculator state
  const [calculator, setCalculator] = useState<TermDepositCalculatorResponse | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [calcError, setCalcError] = useState<string | null>(null);

  const mutation = useOpenTermDeposit();

  const parsedAmount = parseInt(amountInput.replace(/\D/g, ''), 10);
  const parsedDuration = parseInt(durationInput, 10);

  const isValidAmount = !isNaN(parsedAmount) && parsedAmount >= MIN_AMOUNT;
  const isValidDuration = !isNaN(parsedDuration) && parsedDuration >= 1;
  const canCalculate = isValidAmount && isValidDuration;

  // ── FR-025: Fetch projection from calculator API ──────────────────────────
  const handleCalculate = async () => {
    if (!canCalculate) {
      const errs: Record<string, string | null> = {};
      if (!isValidAmount) errs.amount = i18n.t('accounts.amount_hint');
      if (!isValidDuration) errs.duration = i18n.t('accounts.duration_months_hint');
      setFieldErrors(errs);
      return;
    }
    setFieldErrors({});
    setCalcError(null);
    setCalculator(null);
    setIsCalculating(true);
    try {
      const result = await accountsService.termDepositCalculator(parsedAmount, parsedDuration);
      setCalculator(result);
    } catch (err: any) {
      setCalcError(err?.message ?? i18n.t('errors.generic'));
    } finally {
      setIsCalculating(false);
    }
  };

  // ── FR-023: Open the account ──────────────────────────────────────────────
  const handleConfirm = () => {
    if (!calculator) return; // must preview first

    mutation.mutate(
      { amount: parsedAmount, duration_months: parsedDuration },
      {
        onSuccess: (data) => {
          Alert.alert(
            i18n.t('accounts.open_success'),
            `${formatXAF(data.principal)} · ${data.duration_months} mois`,
            [{ text: i18n.t('common.confirm'), onPress: () => navigation.navigate('Dashboard') }],
          );
        },
        onError: (err: any) => {
          setCalcError(err?.message ?? i18n.t('errors.generic'));
        },
      },
    );
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.offWhite }} edges={['top', 'bottom']}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
      <ScrollView
        style={styles.screen}
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
      >
        {/* Back */}
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backButton}
          accessibilityRole="button"
          accessibilityLabel={i18n.t('common.back')}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <Text style={styles.backText}>← {i18n.t('common.back')}</Text>
        </TouchableOpacity>

        <Text style={styles.icon}>📈</Text>
        <Text style={styles.title}>{i18n.t('accounts.term_deposit')}</Text>
        <Text style={styles.subtitle}>{i18n.t('accounts.term_deposit_desc')}</Text>

        {/* Amount input */}
        <TerahInput
          label={i18n.t('accounts.amount')}
          value={amountInput}
          onChangeText={(v) => {
            setAmountInput(v);
            setFieldErrors((e) => ({ ...e, amount: null }));
            setCalculator(null);
          }}
          placeholder={i18n.t('accounts.amount_placeholder')}
          hint={i18n.t('accounts.amount_hint')}
          keyboardType="numeric"
          error={fieldErrors.amount}
        />

        {/* Duration input */}
        <TerahInput
          label={i18n.t('accounts.duration_months')}
          value={durationInput}
          onChangeText={(v) => {
            setDurationInput(v);
            setFieldErrors((e) => ({ ...e, duration: null }));
            setCalculator(null);
          }}
          placeholder={i18n.t('accounts.duration_months_placeholder')}
          hint={i18n.t('accounts.duration_months_hint')}
          keyboardType="numeric"
          error={fieldErrors.duration}
        />

        {/* FR-025: Calculate button */}
        <TerahButton
          label={isCalculating ? i18n.t('accounts.loading_calculator') : i18n.t('accounts.preview')}
          onPress={handleCalculate}
          variant="secondary"
          loading={isCalculating}
          disabled={!canCalculate || isCalculating}
          style={styles.calcButton}
        />

        {/* Calculator error */}
        {calcError ? (
          <Text style={styles.errorText}>{calcError}</Text>
        ) : null}

        {/* FR-025: Calculator results */}
        {calculator ? (
          <View style={styles.calculatorCard}>
            <Text style={styles.calcTitle}>{i18n.t('accounts.calculator_title')}</Text>
            <Text style={styles.calcSubtitle}>{i18n.t('accounts.calculator_subtitle')}</Text>

            <View style={styles.calcDivider} />

            <View style={styles.calcRow}>
              <Text style={styles.calcKey}>{i18n.t('accounts.principal')}</Text>
              <Text style={styles.calcValue}>{formatXAF(calculator.amount)}</Text>
            </View>
            <View style={styles.calcRow}>
              <Text style={styles.calcKey}>{i18n.t('accounts.interest_rate')}</Text>
              <Text style={[styles.calcValue, styles.calcHighlight]}>
                {(calculator.interest_rate * 100).toFixed(2)}% / an
              </Text>
            </View>
            <View style={styles.calcRow}>
              <Text style={styles.calcKey}>{i18n.t('accounts.projected_interest')}</Text>
              <Text style={[styles.calcValue, styles.calcHighlight]}>
                + {formatXAF(calculator.projected_interest)}
              </Text>
            </View>
            <View style={styles.calcRow}>
              <Text style={styles.calcKey}>{i18n.t('accounts.maturity_date')}</Text>
              <Text style={styles.calcValue}>{calculator.maturity_date}</Text>
            </View>

            <View style={styles.calcTotalRow}>
              <Text style={styles.calcTotalKey}>{i18n.t('accounts.total_at_maturity')}</Text>
              <Text style={styles.calcTotalValue}>{formatXAF(calculator.total_at_maturity)}</Text>
            </View>

            <View style={styles.calcDivider} />

            {/* FR-026: Early break warning */}
            <Text style={styles.earlyBreakTitle}>En cas de sortie anticipée</Text>
            <View style={styles.calcRow}>
              <Text style={styles.calcKey}>{i18n.t('accounts.early_break_penalty')}</Text>
              <Text style={[styles.calcValue, styles.penaltyValue]}>
                − {formatXAF(calculator.early_break_penalty)}
              </Text>
            </View>
            <View style={styles.calcRow}>
              <Text style={styles.calcKey}>{i18n.t('accounts.net_if_broken_early')}</Text>
              <Text style={styles.calcValue}>{formatXAF(calculator.net_if_broken_early)}</Text>
            </View>
          </View>
        ) : null}

        {/* Rules box */}
        <View style={styles.rulesBox}>
          <Text style={styles.rulesTitle}>À savoir</Text>
          <Text style={styles.rulesText}>
            • Capital garanti (hors pénalité de sortie anticipée){'\n'}
            • Taux d'intérêt fixé à la souscription{'\n'}
            • Intérêts versés à l'échéance uniquement
          </Text>
        </View>

        {/* Confirm button — only enabled after calculator preview */}
        <TerahButton
          label={i18n.t('accounts.confirm_open')}
          onPress={handleConfirm}
          loading={mutation.isPending}
          disabled={!calculator || mutation.isPending}
          style={styles.submitButton}
        />

        {!calculator ? (
          <Text style={styles.calcHint}>
            Utilisez le bouton « Simuler » pour prévisualiser vos gains avant de confirmer.
          </Text>
        ) : null}
      </ScrollView>
      </KeyboardAvoidingView>
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
    paddingBottom: 48,
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
  icon: {
    fontSize: 48,
    marginBottom: 12,
  },
  title: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 24,
    color: colors.navy,
    marginBottom: 8,
  },
  subtitle: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.midGrey,
    marginBottom: 28,
    lineHeight: 20,
  },
  calcButton: {
    marginBottom: 8,
  },
  errorText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.error,
    marginBottom: 12,
    textAlign: 'center',
  },
  // FR-025: Calculator card
  calculatorCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 18,
    marginTop: 16,
    marginBottom: 16,
    borderWidth: 1.5,
    borderColor: colors.teal + '40',
  },
  calcTitle: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 16,
    color: colors.navy,
    marginBottom: 4,
  },
  calcSubtitle: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.midGrey,
    marginBottom: 12,
  },
  calcDivider: {
    height: 1,
    backgroundColor: colors.lightGrey,
    marginVertical: 12,
  },
  calcRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 5,
  },
  calcKey: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.midGrey,
    flex: 1,
  },
  calcValue: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 13,
    color: colors.darkGrey,
    textAlign: 'right',
  },
  calcHighlight: {
    color: colors.teal,
    fontFamily: 'Poppins_600SemiBold',
  },
  penaltyValue: {
    color: colors.error,
  },
  calcTotalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: colors.navy,
    borderRadius: 10,
    padding: 12,
    marginTop: 8,
  },
  calcTotalKey: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 13,
    color: 'rgba(255,255,255,0.8)',
  },
  calcTotalValue: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 18,
    color: '#FFFFFF',
  },
  earlyBreakTitle: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 13,
    color: colors.warning,
    marginBottom: 6,
  },
  rulesBox: {
    backgroundColor: '#FFFFFF',
    borderRadius: 10,
    padding: 14,
    marginBottom: 24,
  },
  rulesTitle: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 13,
    color: colors.navy,
    marginBottom: 8,
  },
  rulesText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.midGrey,
    lineHeight: 20,
  },
  submitButton: {
    marginTop: 8,
  },
  calcHint: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: colors.midGrey,
    textAlign: 'center',
    marginTop: 12,
    fontStyle: 'italic',
  },
});
