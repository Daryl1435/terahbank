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
import type { RootStackParamList } from '../../App';
import { useLogin } from '@/hooks/useAuth';
import { TerahButton } from '@/components/TerahButton';
import { TerahInput } from '@/components/TerahInput';
import { TerahLogo } from '@/components/TerahLogo';
import { colors } from '@/utils/tokens';
import i18n from '@/locales';

interface LoginScreenProps {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Login'>;
}

export function LoginScreen({ navigation }: LoginScreenProps) {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  const loginMutation = useLogin();

  const handleLogin = () => {
    setFormError(null);

    if (!identifier.trim() || !password) {
      setFormError(i18n.t('errors.generic'));
      return;
    }

    loginMutation.mutate(
      { identifier: identifier.trim(), password },
      {
        onSuccess: (data) => {
          // Login returns user_id + otp_required — navigate to 2FA OTP
          navigation.navigate('OTP', { userId: data.user_id, purpose: 'login' });
        },
        onError: (err: any) => {
          setFormError(err.message ?? i18n.t('errors.generic'));
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
        {/* Brand */}
        <View style={styles.brandArea}>
          <TerahLogo variant="full" width={220} />
        </View>

        <Text style={styles.title}>{i18n.t('auth.login_title')}</Text>

        <TerahInput
          label={i18n.t('auth.phone_label')}
          placeholder={i18n.t('auth.phone_placeholder')}
          value={identifier}
          onChangeText={setIdentifier}
          keyboardType="email-address"
          autoCapitalize="none"
          autoComplete="tel"
          textContentType="emailAddress"
        />

        <TerahInput
          label={i18n.t('auth.password_placeholder')}
          placeholder={i18n.t('auth.password_placeholder')}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          showPasswordToggle
          autoComplete="password"
          textContentType="password"
        />

        {formError ? (
          <Text style={styles.errorText} accessibilityRole="alert">
            {formError}
          </Text>
        ) : null}

        <TerahButton
          label={i18n.t('auth.login_button')}
          onPress={handleLogin}
          loading={loginMutation.isPending}
          style={styles.loginButton}
        />

        <TerahButton
          label={i18n.t('auth.forgot_password')}
          onPress={() => {/* Future milestone */}}
          variant="ghost"
        />

        <View style={styles.registerRow}>
          <Text style={styles.registerText}>{i18n.t('auth.no_account')} </Text>
          <TerahButton
            label={i18n.t('auth.register_link')}
            onPress={() => navigation.navigate('Register')}
            variant="ghost"
            style={styles.registerLink}
          />
        </View>
      </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

export default LoginScreen;

const styles = StyleSheet.create({
  flex: {
    flex: 1,
    backgroundColor: colors.offWhite,
  },
  container: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingTop: 56,
    paddingBottom: 32,
  },
  brandArea: {
    alignItems: 'center',
    marginBottom: 40,
  },
  title: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 22,
    color: colors.navy,
    marginBottom: 24,
  },
  errorText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.error,
    marginBottom: 12,
    textAlign: 'center',
  },
  loginButton: {
    marginTop: 8,
    marginBottom: 16,
  },
  registerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 8,
  },
  registerText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.darkGrey,
  },
  registerLink: {
    height: 'auto' as any,
    paddingHorizontal: 0,
  },
});
