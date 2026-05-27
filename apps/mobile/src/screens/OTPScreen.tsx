/**
 * OTPScreen — handles both registration OTP (purpose='verify') and
 * login 2FA OTP (purpose='login').
 *
 * Post-success routing:
 *   purpose='verify' → PINSetup (start onboarding flow)
 *   purpose='login'  → DeviceVerification (if is_new_device) or setAuth (triggers App nav)
 */
import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';
import type { RootStackParamList } from '../../App';
import { useVerifyOTP, isTokenResponse } from '@/hooks/useAuth';
import { TerahButton } from '@/components/TerahButton';
import { authService } from '@/services/auth';
import { useAuthStore, saveTokens } from '@/stores/authStore';
import { colors } from '@/utils/tokens';
import i18n from '@/locales';

const RESEND_COOLDOWN_SECONDS = 60;
const MAX_RESENDS = 3;

interface OTPScreenProps {
  navigation: NativeStackNavigationProp<RootStackParamList, 'OTP'>;
  route: RouteProp<RootStackParamList, 'OTP'>;
}

export function OTPScreen({ navigation, route }: OTPScreenProps) {
  const { userId, purpose, otpDev } = route.params;
  const setAuth = useAuthStore((s) => s.setAuth);

  const [otp, setOtp] = useState(otpDev ?? '');
  const [error, setError] = useState<string | null>(null);
  const [countdown, setCountdown] = useState(RESEND_COOLDOWN_SECONDS);
  const [resendCount, setResendCount] = useState(0);
  const inputRef = useRef<TextInput>(null);

  const verifyMutation = useVerifyOTP();

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setInterval(() => setCountdown((c) => c - 1), 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  const handleVerify = () => {
    setError(null);
    if (otp.length !== 6) {
      setError(i18n.t('auth.otp_invalid_format'));
      return;
    }

    verifyMutation.mutate(
      { user_id: userId, otp, purpose },
      {
        onSuccess: async (data) => {
          if (purpose === 'verify') {
            // Registration OTP — go to PIN setup
            navigation.navigate('PINSetup');
            return;
          }

          // Login OTP — data is AuthTokenResponse with tokens
          if (isTokenResponse(data)) {
            await saveTokens(data.access_token, data.refresh_token);

            if (data.is_new_device) {
              // New device: show warning screen before completing login
              navigation.navigate('DeviceVerification', {
                userId: data.user_id,
                kycStatus: data.kyc_status,
              });
            } else {
              // Known device: set auth state — App.tsx handles navigation
              setAuth(data.user_id, data.kyc_status, data.full_name);
            }
          }
        },
        onError: (err: any) => {
          setError(err.message ?? i18n.t('errors.generic'));
          setOtp('');
          inputRef.current?.focus();
        },
      },
    );
  };

  const handleResend = async () => {
    if (countdown > 0 || resendCount >= MAX_RESENDS) return;
    try {
      await authService.resendOTP({ user_id: userId, purpose });
      setResendCount((c) => c + 1);
      setCountdown(RESEND_COOLDOWN_SECONDS);
      setError(null);
    } catch (err: any) {
      setError(err.message ?? i18n.t('errors.generic'));
    }
  };

  const canResend = countdown === 0 && resendCount < MAX_RESENDS;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.offWhite }} edges={['top', 'bottom']}>
      <View style={styles.container}>
      <Text style={styles.title}>{i18n.t('auth.otp_title')}</Text>
      <Text style={styles.subtitle}>{i18n.t('auth.otp_subtitle')}</Text>

      {/* DEV mode banner — shown when SMS delivery failed and OTP came from API */}
      {otpDev ? (
        <View style={styles.devBanner}>
          <Text style={styles.devBannerText}>
            {'[DEV] SMS unavailable — OTP auto-filled: '}
            <Text style={styles.devBannerOtp}>{otpDev}</Text>
          </Text>
        </View>
      ) : null}

      {/* Single OTP input — numeric, auto-focuses */}
      <TextInput
        ref={inputRef}
        style={styles.otpInput}
        value={otp}
        onChangeText={(v) => {
          setOtp(v.replace(/\D/g, '').slice(0, 6));
          setError(null);
        }}
        keyboardType="number-pad"
        maxLength={6}
        placeholder="——————"
        placeholderTextColor={colors.lightGrey}
        accessibilityLabel={i18n.t('auth.otp_title')}
        autoFocus
      />

      {error ? (
        <Text style={styles.errorText} accessibilityRole="alert">
          {error}
        </Text>
      ) : null}

      <TerahButton
        label={i18n.t('auth.otp_verify_button')}
        onPress={handleVerify}
        loading={verifyMutation.isPending}
        disabled={otp.length !== 6}
        style={styles.verifyButton}
      />

      <TouchableOpacity
        onPress={handleResend}
        disabled={!canResend}
        accessibilityRole="button"
        accessibilityLabel={i18n.t('auth.otp_resend')}
        style={styles.resendContainer}
      >
        <Text style={[styles.resendText, !canResend && styles.resendDisabled]}>
          {countdown > 0
            ? i18n.t('auth.otp_resend_countdown', { seconds: countdown })
            : resendCount >= MAX_RESENDS
            ? i18n.t('auth.otp_resend_limit')
            : i18n.t('auth.otp_resend')}
        </Text>
      </TouchableOpacity>

      <TerahButton
        label={i18n.t('common.back')}
        onPress={() => navigation.goBack()}
        variant="ghost"
        style={styles.backButton}
      />
      </View>
    </SafeAreaView>
  );
}

export default OTPScreen;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.offWhite,
    paddingHorizontal: 24,
    paddingTop: 48,
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
    color: colors.darkGrey,
    lineHeight: 24,
    marginBottom: 36,
  },
  otpInput: {
    height: 72,
    borderWidth: 2,
    borderColor: colors.teal,
    borderRadius: 12,
    textAlign: 'center',
    fontFamily: 'Poppins_700Bold',
    fontSize: 32,
    color: colors.navy,
    backgroundColor: colors.white,
    letterSpacing: 14,
    marginBottom: 16,
  },
  errorText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.error,
    marginBottom: 12,
    textAlign: 'center',
  },
  verifyButton: {
    marginBottom: 16,
  },
  resendContainer: {
    alignItems: 'center',
    paddingVertical: 12,
    minHeight: 44,
    justifyContent: 'center',
  },
  resendText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.teal,
  },
  resendDisabled: {
    color: colors.midGrey,
  },
  backButton: {
    marginTop: 8,
  },
  devBanner: {
    backgroundColor: '#FFF3CD',
    borderWidth: 1,
    borderColor: '#FFB020',
    borderRadius: 8,
    padding: 10,
    marginBottom: 16,
  },
  devBannerText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: '#7B5800',
    textAlign: 'center',
  },
  devBannerOtp: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 15,
    color: '#7B5800',
    letterSpacing: 4,
  },
});
