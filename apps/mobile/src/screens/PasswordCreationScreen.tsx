/**
 * PasswordCreationScreen — dedicated password setup screen with complexity meter.
 * FR-003: min 10 chars, 1 uppercase, 1 digit, 1 special char.
 * Submits the full registration payload after password is set.
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';
import type { RootStackParamList } from '../../App';
import { useRegister } from '@/hooks/useAuth';
import { TerahButton } from '@/components/TerahButton';
import { TerahInput } from '@/components/TerahInput';
import { PasswordStrengthMeter } from '@/components/PasswordStrengthMeter';
import { colors } from '@/utils/tokens';
import { validatePassword } from '@/utils/validators';
import i18n from '@/locales';

interface PasswordCreationScreenProps {
  navigation: NativeStackNavigationProp<RootStackParamList, 'PasswordCreation'>;
  route: RouteProp<RootStackParamList, 'PasswordCreation'>;
}

export function PasswordCreationScreen({ navigation, route }: PasswordCreationScreenProps) {
  const { full_name, phone_number, email, city, address } = route.params;

  const [password, setPassword] = useState('');
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const registerMutation = useRegister();

  const handleCreate = () => {
    setPasswordError(null);
    setApiError(null);

    const passErr = validatePassword(password);
    if (passErr) {
      setPasswordError(passErr);
      return;
    }

    registerMutation.mutate(
      { full_name, phone_number, email, password, city, address },
      {
        onSuccess: (data) => {
          navigation.navigate('OTP', {
            userId: data.user_id,
            purpose: 'verify',
            otpDev: data.otp_dev,
          });
        },
        onError: (err: any) => {
          setApiError(err.message ?? i18n.t('errors.generic'));
        },
      },
    );
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.offWhite }} edges={['top', 'bottom']}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
      <ScrollView
        contentContainerStyle={styles.container}
        keyboardShouldPersistTaps="handled"
      >
        <Text style={styles.title}>{i18n.t('auth.create_password_title')}</Text>
        <Text style={styles.subtitle}>{i18n.t('auth.create_password_subtitle')}</Text>

        <TerahInput
          label={i18n.t('auth.password_placeholder')}
          placeholder="••••••••••"
          value={password}
          onChangeText={(v) => {
            setPassword(v);
            setPasswordError(null);
          }}
          secureTextEntry
          showPasswordToggle
          autoComplete="password-new"
          textContentType="newPassword"
          error={passwordError}
        />

        <PasswordStrengthMeter password={password} />

        {apiError ? (
          <Text style={styles.errorText} accessibilityRole="alert">
            {apiError}
          </Text>
        ) : null}

        <TerahButton
          label={i18n.t('auth.create_password_button')}
          onPress={handleCreate}
          loading={registerMutation.isPending}
          disabled={password.length === 0}
          style={styles.submitButton}
        />

        <TerahButton
          label={i18n.t('common.back')}
          onPress={() => navigation.goBack()}
          variant="ghost"
        />
      </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

export default PasswordCreationScreen;

const styles = StyleSheet.create({
  flex: {
    flex: 1,
    backgroundColor: colors.offWhite,
  },
  container: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingTop: 40,
    paddingBottom: 32,
  },
  title: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 24,
    color: colors.navy,
    marginBottom: 8,
  },
  subtitle: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 15,
    color: colors.midGrey,
    marginBottom: 28,
  },
  errorText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.error,
    marginBottom: 12,
    textAlign: 'center',
  },
  submitButton: {
    marginTop: 16,
    marginBottom: 12,
  },
});
