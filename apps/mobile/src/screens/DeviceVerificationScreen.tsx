/**
 * DeviceVerificationScreen — shown after login OTP when is_new_device=true.
 * Warn user that their account was accessed from an unrecognised device.
 * Confirm → setAuth → App.tsx navigates to Dashboard or KYC gate.
 * Deny → logout (best-effort) + navigate to Login.
 */
import React, { useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RouteProp } from '@react-navigation/native';
import type { RootStackParamList } from '../../App';
import { TerahButton } from '@/components/TerahButton';
import { useAuthStore } from '@/stores/authStore';
import { authService } from '@/services/auth';
import { colors } from '@/utils/tokens';
import i18n from '@/locales';

interface DeviceVerificationScreenProps {
  navigation: NativeStackNavigationProp<RootStackParamList, 'DeviceVerification'>;
  route: RouteProp<RootStackParamList, 'DeviceVerification'>;
}

export function DeviceVerificationScreen({ navigation, route }: DeviceVerificationScreenProps) {
  const { userId, kycStatus } = route.params;
  const setAuth = useAuthStore((s) => s.setAuth);
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const [denyLoading, setDenyLoading] = useState(false);

  const handleConfirm = () => {
    // Known user confirmed — complete login
    setAuth(userId, kycStatus);
    // App.tsx will react to isAuthenticated=true and navigate
  };

  const handleDeny = async () => {
    setDenyLoading(true);
    try {
      await authService.logout();
    } catch {
      // Best-effort — always clear local state
    } finally {
      await clearAuth();
      setDenyLoading(false);
      // clearAuth sets isAuthenticated=false → App.tsx shows Login
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.offWhite }} edges={['top', 'bottom']}>
      <View style={styles.container}>
      {/* Warning icon */}
      <View style={styles.iconCircle}>
        <Text style={styles.iconText}>!</Text>
      </View>

      <Text style={styles.title}>{i18n.t('auth.new_device_title')}</Text>
      <Text style={styles.subtitle}>{i18n.t('auth.new_device_subtitle')}</Text>

      <TerahButton
        label={i18n.t('auth.new_device_confirm')}
        onPress={handleConfirm}
        style={styles.confirmButton}
      />

      <TerahButton
        label={i18n.t('auth.new_device_deny')}
        onPress={handleDeny}
        loading={denyLoading}
        variant="ghost"
        style={styles.denyButton}
      />
      </View>
    </SafeAreaView>
  );
}

export default DeviceVerificationScreen;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.offWhite,
    paddingHorizontal: 32,
    alignItems: 'center',
    justifyContent: 'center',
    paddingBottom: 48,
  },
  iconCircle: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: colors.warning,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 32,
  },
  iconText: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 48,
    color: '#FFFFFF',
    lineHeight: 60,
  },
  title: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 24,
    color: colors.navy,
    marginBottom: 12,
    textAlign: 'center',
  },
  subtitle: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 15,
    color: colors.darkGrey,
    lineHeight: 24,
    textAlign: 'center',
    marginBottom: 48,
  },
  confirmButton: {
    width: '100%',
    marginBottom: 12,
  },
  denyButton: {
    width: '100%',
  },
});
