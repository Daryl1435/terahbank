import React, { useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
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
import { useAppStore } from '@/stores/appStore';
import { colors } from '@/utils/tokens';
import i18n from '@/locales';

interface LoginScreenProps {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Login'>;
}

export function LoginScreen({ navigation }: LoginScreenProps) {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword]     = useState('');
  const [formError, setFormError]   = useState<string | null>(null);

  const loginMutation = useLogin();
  const language      = useAppStore((s) => s.language);
  const setLanguage   = useAppStore((s) => s.setLanguage);

  // Switch language and update i18n locale immediately
  const toggleLanguage = () => {
    const next = language === 'fr' ? 'en' : 'fr';
    i18n.locale = next;
    setLanguage(next);
    // Clear any validation errors so they re-render in the new language
    setFormError(null);
  };

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
          navigation.navigate('OTP', {
            userId: data.user_id,
            purpose: 'login',
            otpDev: data.otp_dev,
          });
        },
        onError: (err: any) => {
          setFormError(err.message ?? i18n.t('errors.generic'));
        },
      },
    );
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >

        {/* ── Language toggle pill — top-right corner ─────────────────────── */}
        <View style={styles.langRow}>
          <TouchableOpacity
            onPress={toggleLanguage}
            style={styles.langPill}
            accessibilityRole="button"
            accessibilityLabel={language === 'fr' ? 'Switch to English' : 'Passer en Français'}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          >
            {/* Highlight the active language */}
            <Text style={[styles.langOption, language === 'fr' && styles.langActive]}>FR</Text>
            <Text style={styles.langSep}>|</Text>
            <Text style={[styles.langOption, language === 'en' && styles.langActive]}>EN</Text>
          </TouchableOpacity>
        </View>

        <ScrollView
          contentContainerStyle={styles.container}
          keyboardShouldPersistTaps="handled"
        >

          {/* Brand */}
          <View style={styles.brandArea}>
            <TerahLogo variant="full" width={220} />
          </View>

          <Text style={styles.title}>{i18n.t('auth.login_title')}</Text>
          <Text style={styles.subtitle}>{i18n.t('auth.login_subtitle')}</Text>

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
  safe: {
    flex: 1,
    backgroundColor: colors.offWhite,
  },
  flex: {
    flex: 1,
    backgroundColor: colors.offWhite,
  },

  // Language toggle
  langRow: {
    alignItems: 'flex-end',
    paddingHorizontal: 20,
    paddingTop: 12,
  },
  langPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.lightGrey,
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
    gap: 6,
  },
  langOption: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 12,
    color: colors.midGrey,
  },
  langActive: {
    color: colors.navy,
  },
  langSep: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: colors.midGrey,
  },

  // Main content
  container: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingTop: 32,
    paddingBottom: 32,
  },
  brandArea: {
    alignItems: 'center',
    marginBottom: 36,
  },
  title: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 24,
    color: colors.navy,
    marginBottom: 6,
  },
  subtitle: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.midGrey,
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
