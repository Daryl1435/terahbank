/**
 * PINSetupScreen — FR-006: 6-digit PIN setup with confirm step.
 * Uses custom PINKeypad (never system keyboard). PIN stored in SecureStore.
 * Two-step flow: enter → confirm → navigate to BiometricSetup.
 */
import React, { useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../../App';
import { PINKeypad } from '@/components/PINKeypad';
import { colors } from '@/utils/tokens';
import i18n from '@/locales';

const PIN_LENGTH = 6;

interface PINSetupScreenProps {
  navigation: NativeStackNavigationProp<RootStackParamList, 'PINSetup'>;
}

export function PINSetupScreen({ navigation }: PINSetupScreenProps) {
  const [step, setStep] = useState<'enter' | 'confirm'>('enter');
  const [pin, setPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const currentPin = step === 'enter' ? pin : confirmPin;
  const setCurrentPin = step === 'enter' ? setPin : setConfirmPin;

  const handleKeyPress = async (key: string) => {
    if (saving) return;

    if (key === 'backspace') {
      setCurrentPin((p) => p.slice(0, -1));
      setError(null);
      return;
    }

    const next = currentPin + key;
    setCurrentPin(next);

    if (next.length < PIN_LENGTH) return;

    if (step === 'enter') {
      // Move to confirm step
      setStep('confirm');
    } else {
      // Confirm step — compare
      if (next !== pin) {
        setError(i18n.t('auth.pin_mismatch'));
        setStep('enter');
        setPin('');
        setConfirmPin('');
        return;
      }
      // Match — save and proceed
      setSaving(true);
      try {
        await SecureStore.setItemAsync('user_pin', next);
        navigation.navigate('BiometricSetup');
      } finally {
        setSaving(false);
      }
    }
  };

  const title = step === 'enter'
    ? i18n.t('auth.pin_setup_title')
    : i18n.t('auth.pin_confirm_title');
  const subtitle = step === 'enter'
    ? i18n.t('auth.pin_setup_subtitle')
    : i18n.t('auth.pin_confirm_subtitle');

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.subtitle}>{subtitle}</Text>

      {/* PIN dots — 6 circles */}
      <View style={styles.dotsRow} accessibilityLabel={`${currentPin.length} sur ${PIN_LENGTH} chiffres saisis`}>
        {Array.from({ length: PIN_LENGTH }).map((_, i) => (
          <View
            key={i}
            style={[styles.dot, i < currentPin.length && styles.dotFilled]}
          />
        ))}
      </View>

      {error ? (
        <Text style={styles.errorText} accessibilityRole="alert">
          {error}
        </Text>
      ) : (
        <View style={styles.errorPlaceholder} />
      )}

      <PINKeypad
        onKeyPress={handleKeyPress}
        disabled={saving || currentPin.length >= PIN_LENGTH}
        style={styles.keypad}
      />
    </View>
  );
}

export default PINSetupScreen;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.offWhite,
    paddingHorizontal: 24,
    paddingTop: 56,
    alignItems: 'center',
  },
  title: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 24,
    color: colors.navy,
    marginBottom: 8,
    textAlign: 'center',
  },
  subtitle: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 15,
    color: colors.darkGrey,
    lineHeight: 24,
    marginBottom: 40,
    textAlign: 'center',
  },
  dotsRow: {
    flexDirection: 'row',
    gap: 16,
    marginBottom: 16,
  },
  dot: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 2,
    borderColor: colors.teal,
    backgroundColor: 'transparent',
  },
  dotFilled: {
    backgroundColor: colors.teal,
  },
  errorText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.error,
    textAlign: 'center',
    marginBottom: 8,
    minHeight: 20,
  },
  errorPlaceholder: {
    minHeight: 20,
    marginBottom: 8,
  },
  keypad: {
    marginTop: 16,
    width: '100%',
    maxWidth: 320,
  },
});
