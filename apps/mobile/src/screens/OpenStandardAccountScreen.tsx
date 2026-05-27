/**
 * FR-010/011: Open Standard Savings Account.
 * - Minimum initial deposit: 100 XAF (user enters XAF, multiplied ×100 to units)
 * - MoMo phone validated for carrier detection (MTN / Orange)
 * - One Standard Account per user — 409 handled gracefully
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
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import { useOpenStandardAccount } from '@/hooks/useBalance';
import { TerahButton } from '@/components/TerahButton';
import { TerahInput } from '@/components/TerahInput';
import { TerahIcon } from '@/components/TerahIcon';
import { colors } from '@/utils/tokens';
import { formatXAF } from '@/utils/formatXAF';
import { detectCarrier, isValidCameroonPhone } from '@/utils/phoneCarrier';
import i18n from '@/locales';

type OpenStandardNavProp = NativeStackNavigationProp<RootStackParamList, 'OpenStandardAccount'>;

interface OpenStandardAccountScreenProps {
  navigation: OpenStandardNavProp;
}

const MIN_DEPOSIT_XAF = 100; // 100 XAF = 10,000 units

const CARRIER_COLORS = { mtn: '#FFCC00', orange: '#FF6600', unknown: colors.midGrey } as const;
const CARRIER_BG = { mtn: '#FFFBEB', orange: '#FFF4EB', unknown: colors.lightGrey } as const;

export default function OpenStandardAccountScreen({ navigation }: OpenStandardAccountScreenProps) {
  const [depositInput, setDepositInput] = useState('');
  const [phoneInput, setPhoneInput] = useState('');
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [phoneError, setPhoneError] = useState<string | null>(null);

  const mutation = useOpenStandardAccount();

  const parsedXAF = parseInt(depositInput.replace(/\D/g, ''), 10);
  const isValidAmount = !isNaN(parsedXAF) && parsedXAF >= MIN_DEPOSIT_XAF;
  const trimmedPhone = phoneInput.trim();
  const phoneValid = isValidCameroonPhone(trimmedPhone);
  const carrier = phoneValid ? detectCarrier(trimmedPhone) : 'unknown';

  const canSubmit = isValidAmount && phoneValid;

  const handleSubmit = () => {
    let hasError = false;
    if (!isValidAmount) {
      setFieldError(i18n.t('accounts.initial_deposit_hint'));
      hasError = true;
    }
    if (!phoneValid) {
      setPhoneError(i18n.t('accounts.momo_phone_error'));
      hasError = true;
    }
    if (hasError) return;
    setFieldError(null);
    setPhoneError(null);

    mutation.mutate(
      { initial_deposit: parsedXAF * 100, momo_phone: trimmedPhone },
      {
        onSuccess: (data) => {
          Alert.alert(
            i18n.t('accounts.open_success'),
            `${formatXAF(parsedXAF * 100)} · ${data.account_number}`,
            [{ text: i18n.t('common.confirm'), onPress: () => navigation.navigate('Dashboard') }],
          );
        },
        onError: (err: any) => {
          setFieldError(err?.message ?? i18n.t('errors.generic'));
        },
      },
    );
  };

  const carrierLabel =
    carrier === 'mtn'
      ? i18n.t('accounts.carrier_mtn')
      : carrier === 'orange'
      ? i18n.t('accounts.carrier_orange')
      : null;

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

          {/* Icon + title */}
          <View style={styles.iconContainer}>
            <TerahIcon name="wallet-outline" size={36} color={colors.teal} />
          </View>
          <Text style={styles.title}>{i18n.t('accounts.standard')}</Text>
          <Text style={styles.subtitle}>{i18n.t('accounts.standard_desc')}</Text>

          {/* Deposit amount (in XAF) */}
          <TerahInput
            label={i18n.t('accounts.initial_deposit')}
            value={depositInput}
            onChangeText={(v) => {
              setDepositInput(v.replace(/\D/g, ''));
              setFieldError(null);
            }}
            placeholder={i18n.t('accounts.initial_deposit_placeholder')}
            hint={i18n.t('accounts.initial_deposit_hint')}
            keyboardType="numeric"
            error={fieldError}
          />

          {/* Live XAF preview */}
          {isValidAmount ? (
            <View style={styles.preview}>
              <Text style={styles.previewLabel}>{i18n.t('accounts.initial_deposit_preview')}</Text>
              <Text style={styles.previewValue}>{formatXAF(parsedXAF * 100)}</Text>
            </View>
          ) : null}

          {/* MoMo phone */}
          <TerahInput
            label={i18n.t('accounts.momo_phone_label')}
            value={phoneInput}
            onChangeText={(v) => {
              setPhoneInput(v);
              setPhoneError(null);
            }}
            placeholder={i18n.t('accounts.momo_phone_placeholder')}
            hint={i18n.t('accounts.momo_phone_hint')}
            keyboardType="phone-pad"
            error={phoneError}
          />

          {/* Carrier badge */}
          {phoneValid && carrier !== 'unknown' ? (
            <View style={[styles.carrierBadge, { backgroundColor: CARRIER_BG[carrier] }]}>
              <TerahIcon
                name={carrier === 'mtn' ? 'phone-portrait-outline' : 'phone-portrait-outline'}
                size={16}
                color={CARRIER_COLORS[carrier]}
              />
              <Text style={[styles.carrierText, { color: CARRIER_COLORS[carrier] }]}>
                {carrierLabel}
              </Text>
            </View>
          ) : phoneValid && carrier === 'unknown' ? (
            <View style={[styles.carrierBadge, { backgroundColor: CARRIER_BG.unknown }]}>
              <Text style={[styles.carrierText, { color: colors.midGrey }]}>
                {i18n.t('accounts.carrier_unknown')}
              </Text>
            </View>
          ) : null}

          {/* Rules reminder */}
          <View style={styles.rulesBox}>
            <Text style={styles.rulesTitle}>{i18n.t('accounts.rules_title')}</Text>
            <Text style={styles.rulesText}>{i18n.t('accounts.standard_rules')}</Text>
          </View>

          <TerahButton
            label={i18n.t('accounts.confirm_open')}
            onPress={handleSubmit}
            loading={mutation.isPending}
            disabled={!canSubmit || mutation.isPending}
            style={styles.submitButton}
          />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.offWhite },
  container: { paddingHorizontal: 16, paddingBottom: 48 },
  backButton: {
    paddingTop: 24,
    paddingBottom: 16,
    minHeight: 44,
    alignSelf: 'flex-start',
  },
  backText: { fontFamily: 'Roboto_500Medium', fontSize: 14, color: colors.teal },
  iconContainer: {
    width: 64,
    height: 64,
    borderRadius: 16,
    backgroundColor: `${colors.teal}15`,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  title: { fontFamily: 'Poppins_700Bold', fontSize: 24, color: colors.navy, marginBottom: 8 },
  subtitle: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.midGrey,
    marginBottom: 28,
    lineHeight: 20,
  },
  preview: {
    backgroundColor: `${colors.teal}15`,
    borderRadius: 10,
    padding: 14,
    marginBottom: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  previewLabel: { fontFamily: 'Roboto_400Regular', fontSize: 14, color: colors.navy },
  previewValue: { fontFamily: 'Poppins_700Bold', fontSize: 18, color: colors.teal },
  carrierBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginBottom: 16,
    alignSelf: 'flex-start',
  },
  carrierText: { fontFamily: 'Roboto_500Medium', fontSize: 13 },
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
  submitButton: { marginTop: 8 },
});
