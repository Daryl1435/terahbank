/**
 * FR-010/011: Open Standard Savings Account.
 * - Minimum initial deposit: 100 XAF (10,000 units)
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
import { colors } from '@/utils/tokens';
import { formatXAF } from '@/utils/formatXAF';
import i18n from '@/locales';

type OpenStandardNavProp = NativeStackNavigationProp<RootStackParamList, 'OpenStandardAccount'>;

interface OpenStandardAccountScreenProps {
  navigation: OpenStandardNavProp;
}

const MIN_DEPOSIT = 10_000;  // 100 XAF in smallest unit

export default function OpenStandardAccountScreen({ navigation }: OpenStandardAccountScreenProps) {
  const [depositInput, setDepositInput] = useState('');
  const [fieldError, setFieldError] = useState<string | null>(null);

  const mutation = useOpenStandardAccount();

  const parsedDeposit = parseInt(depositInput.replace(/\D/g, ''), 10);
  const isValidAmount = !isNaN(parsedDeposit) && parsedDeposit >= MIN_DEPOSIT;

  const handleSubmit = () => {
    if (!depositInput.trim()) {
      setFieldError(i18n.t('errors.generic'));
      return;
    }
    if (isNaN(parsedDeposit) || parsedDeposit < MIN_DEPOSIT) {
      setFieldError(i18n.t('accounts.initial_deposit_hint'));
      return;
    }
    setFieldError(null);

    mutation.mutate(
      { initial_deposit: parsedDeposit },
      {
        onSuccess: () => {
          Alert.alert(
            i18n.t('accounts.open_success'),
            formatXAF(parsedDeposit),
            [{ text: i18n.t('common.confirm'), onPress: () => navigation.navigate('Dashboard') }],
          );
        },
        onError: (err: any) => {
          const msg = err?.message ?? i18n.t('errors.generic');
          setFieldError(msg);
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

        {/* Icon + title */}
        <Text style={styles.icon}>💰</Text>
        <Text style={styles.title}>{i18n.t('accounts.standard')}</Text>
        <Text style={styles.subtitle}>{i18n.t('accounts.standard_desc')}</Text>

        {/* Deposit input */}
        <TerahInput
          label={i18n.t('accounts.initial_deposit')}
          value={depositInput}
          onChangeText={(v) => {
            setDepositInput(v);
            setFieldError(null);
          }}
          placeholder={i18n.t('accounts.initial_deposit_placeholder')}
          hint={i18n.t('accounts.initial_deposit_hint')}
          keyboardType="numeric"
          error={fieldError}
        />

        {/* Live preview */}
        {isValidAmount ? (
          <View style={styles.preview}>
            <Text style={styles.previewLabel}>Dépôt initial</Text>
            <Text style={styles.previewValue}>{formatXAF(parsedDeposit)}</Text>
          </View>
        ) : null}

        {/* Rules reminder */}
        <View style={styles.rulesBox}>
          <Text style={styles.rulesTitle}>À savoir</Text>
          <Text style={styles.rulesText}>
            • Solde minimum maintenu : 1 000 XAF{'\n'}
            • Un seul Compte Épargne par client{'\n'}
            • Retraits libres et sans frais
          </Text>
        </View>

        <TerahButton
          label={i18n.t('accounts.confirm_open')}
          onPress={handleSubmit}
          loading={mutation.isPending}
          disabled={!isValidAmount}
          style={styles.submitButton}
        />
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
  preview: {
    backgroundColor: colors.teal + '15',
    borderRadius: 10,
    padding: 14,
    marginBottom: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  previewLabel: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.navy,
  },
  previewValue: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 18,
    color: colors.teal,
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
});
