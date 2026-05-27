/**
 * FR-016/022: Open a Project Account (Vault).
 * - project_name: free text
 * - target_amount: BIGINT (smallest XAF unit)
 * - target_date: ISO date — at least 6 months from today
 * Multiple project accounts per user are allowed (FR-022).
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
import { useOpenProjectAccount } from '@/hooks/useBalance';
import { TerahButton } from '@/components/TerahButton';
import { TerahInput } from '@/components/TerahInput';
import { ProgressBar } from '@/components/ProgressBar';
import { TerahIcon } from '@/components/TerahIcon';
import { colors } from '@/utils/tokens';
import { formatXAF } from '@/utils/formatXAF';
import i18n from '@/locales';

type OpenProjectNavProp = NativeStackNavigationProp<RootStackParamList, 'OpenProjectAccount'>;

interface OpenProjectAccountScreenProps {
  navigation: OpenProjectNavProp;
}

/** Validate YYYY-MM-DD format and at least 6 months from today. */
function validateTargetDate(value: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return i18n.t('accounts.date_format_error');
  }
  const target = new Date(value);
  if (isNaN(target.getTime())) {
    return i18n.t('accounts.date_invalid_error');
  }
  const today = new Date();
  const minDate = new Date(today);
  minDate.setMonth(minDate.getMonth() + 6);
  if (target < minDate) {
    return i18n.t('accounts.target_date_hint');
  }
  return null;
}

export default function OpenProjectAccountScreen({ navigation }: OpenProjectAccountScreenProps) {
  const [name, setName] = useState('');
  const [targetAmountInput, setTargetAmountInput] = useState('');
  const [targetDate, setTargetDate] = useState('');
  const [errors, setErrors] = useState<Record<string, string | null>>({});

  const mutation = useOpenProjectAccount();

  // User enters XAF — multiply ×100 to get units before sending to API
  const parsedAmountXAF = parseInt(targetAmountInput.replace(/\D/g, ''), 10);
  const parsedAmount = !isNaN(parsedAmountXAF) ? parsedAmountXAF * 100 : NaN;
  const hasAmount = !isNaN(parsedAmountXAF) && parsedAmountXAF > 0;

  const validate = (): boolean => {
    const newErrors: Record<string, string | null> = {};

    if (!name.trim()) {
      newErrors.name = i18n.t('accounts.project_name_required');
    }
    if (!hasAmount) {
      newErrors.amount = i18n.t('accounts.target_amount_required');
    }
    const dateError = validateTargetDate(targetDate);
    if (dateError) {
      newErrors.date = dateError;
    }

    setErrors(newErrors);
    return Object.values(newErrors).every((e) => !e);
  };

  const handleSubmit = () => {
    if (!validate()) return;

    mutation.mutate(
      {
        project_name: name.trim(),
        target_amount: parsedAmount,
        target_date: targetDate,
      },
      {
        onSuccess: (data) => {
          Alert.alert(
            i18n.t('accounts.open_success'),
            data.project_name,
            [{ text: i18n.t('common.confirm'), onPress: () => navigation.navigate('Dashboard') }],
          );
        },
        onError: (err: any) => {
          setErrors({ submit: err?.message ?? i18n.t('errors.generic') });
        },
      },
    );
  };

  // Progress preview
  const progressPct = hasAmount
    ? Math.min(100, 0)  // starts at 0% — no balance yet
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

        <View style={styles.iconContainer}>
          <TerahIcon name="flag-outline" size={36} color="#7C3AED" />
        </View>
        <Text style={styles.title}>{i18n.t('accounts.project')}</Text>
        <Text style={styles.subtitle}>{i18n.t('accounts.project_desc')}</Text>

        {/* Project name */}
        <TerahInput
          label={i18n.t('accounts.project_name')}
          value={name}
          onChangeText={(v) => { setName(v); setErrors((e) => ({ ...e, name: null })); }}
          placeholder={i18n.t('accounts.project_name_placeholder')}
          hint={i18n.t('accounts.project_name_hint')}
          error={errors.name}
          autoCapitalize="words"
        />

        {/* Target amount */}
        <TerahInput
          label={i18n.t('accounts.target_amount_label')}
          value={targetAmountInput}
          onChangeText={(v) => { setTargetAmountInput(v.replace(/\D/g, '')); setErrors((e) => ({ ...e, amount: null })); }}
          placeholder={i18n.t('accounts.target_amount_placeholder')}
          hint={i18n.t('accounts.target_amount_hint')}
          keyboardType="numeric"
          error={errors.amount}
        />

        {/* Target date */}
        <TerahInput
          label={i18n.t('accounts.target_date_label')}
          value={targetDate}
          onChangeText={(v) => { setTargetDate(v); setErrors((e) => ({ ...e, date: null })); }}
          placeholder={i18n.t('accounts.target_date_placeholder')}
          hint={i18n.t('accounts.target_date_hint')}
          error={errors.date}
          keyboardType="numbers-and-punctuation"
        />

        {/* Live goal preview */}
        {name.trim() && hasAmount ? (
          <View style={styles.preview}>
            <Text style={styles.previewProjectName}>{name.trim()}</Text>
            <Text style={styles.previewTarget}>{formatXAF(parsedAmountXAF * 100)}</Text>
            <ProgressBar percent={0} label={i18n.t('accounts.initial_progress')} showPercent />
          </View>
        ) : null}

        {/* Submit error */}
        {errors.submit ? (
          <Text style={styles.submitError}>{errors.submit}</Text>
        ) : null}

        {/* Rules */}
        <View style={styles.rulesBox}>
          <Text style={styles.rulesTitle}>{i18n.t('accounts.rules_title')}</Text>
          <Text style={styles.rulesText}>{i18n.t('accounts.project_rules')}</Text>
        </View>

        <TerahButton
          label={i18n.t('accounts.confirm_open')}
          onPress={handleSubmit}
          loading={mutation.isPending}
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
  iconContainer: {
    width: 64,
    height: 64,
    borderRadius: 16,
    backgroundColor: '#7C3AED15',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
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
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    gap: 4,
  },
  previewProjectName: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 18,
    color: colors.navy,
    marginBottom: 4,
  },
  previewTarget: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 14,
    color: colors.teal,
    marginBottom: 12,
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
  submitError: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.error,
    marginBottom: 16,
    textAlign: 'center',
  },
  submitButton: {
    marginTop: 8,
  },
});
