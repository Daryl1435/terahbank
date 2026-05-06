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
import { TerahButton } from '@/components/TerahButton';
import { TerahInput } from '@/components/TerahInput';
import { TerahLogo } from '@/components/TerahLogo';
import { colors } from '@/utils/tokens';
import {
  validateFullName,
  validatePhoneNumber,
  validateEmail,
} from '@/utils/validators';
import i18n from '@/locales';

interface RegisterScreenProps {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Register'>;
}

type FormState = {
  full_name: string;
  phone_number: string;
  email: string;
  city: string;
  address: string;
};

export function RegisterScreen({ navigation }: RegisterScreenProps) {
  const [form, setForm] = useState<FormState>({
    full_name: '',
    phone_number: '',
    email: '',
    city: '',
    address: '',
  });
  const [errors, setErrors] = useState<Partial<FormState>>({});

  const set = (field: keyof FormState) => (value: string) =>
    setForm((f) => ({ ...f, [field]: value }));

  const validate = (): boolean => {
    const e: Partial<FormState> = {};
    const nameErr  = validateFullName(form.full_name);
    const phoneErr = validatePhoneNumber(form.phone_number);
    const emailErr = validateEmail(form.email);
    if (nameErr)  e.full_name    = nameErr;
    if (phoneErr) e.phone_number = phoneErr;
    if (emailErr) e.email        = emailErr;
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleContinue = () => {
    if (!validate()) return;
    // Navigate to PasswordCreation — password is set there so the
    // complexity meter gets its own dedicated screen (FR-003)
    navigation.navigate('PasswordCreation', {
      full_name:    form.full_name.trim(),
      phone_number: form.phone_number.trim(),
      email:        form.email.trim(),
      city:         form.city.trim() || undefined,
      address:      form.address.trim() || undefined,
    });
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
        <View style={styles.logoArea}>
          <TerahLogo variant="symbol" width={48} />
        </View>

        <Text style={styles.title}>{i18n.t('auth.register_title')}</Text>
        <Text style={styles.subtitle}>{i18n.t('auth.register_subtitle')}</Text>

        <TerahInput
          label={i18n.t('auth.full_name_label')}
          placeholder={i18n.t('auth.full_name_placeholder')}
          value={form.full_name}
          onChangeText={set('full_name')}
          autoCapitalize="words"
          autoComplete="name"
          textContentType="name"
          error={errors.full_name}
        />

        <TerahInput
          label={i18n.t('auth.phone_label')}
          placeholder="+237 6XX XXX XXX"
          value={form.phone_number}
          onChangeText={set('phone_number')}
          keyboardType="phone-pad"
          autoComplete="tel"
          textContentType="telephoneNumber"
          hint={i18n.t('auth.phone_hint')}
          error={errors.phone_number}
        />

        <TerahInput
          label={i18n.t('auth.email_label')}
          placeholder={i18n.t('auth.email_placeholder')}
          value={form.email}
          onChangeText={set('email')}
          keyboardType="email-address"
          autoCapitalize="none"
          autoComplete="email"
          textContentType="emailAddress"
          error={errors.email}
        />

        <TerahInput
          label={i18n.t('auth.city_label')}
          placeholder={i18n.t('auth.city_placeholder')}
          value={form.city}
          onChangeText={set('city')}
          autoCapitalize="words"
        />

        <TerahInput
          label={i18n.t('auth.address_label')}
          placeholder={i18n.t('auth.address_placeholder')}
          value={form.address}
          onChangeText={set('address')}
          autoCapitalize="sentences"
        />

        <TerahButton
          label={i18n.t('auth.register_button')}
          onPress={handleContinue}
          style={styles.submitButton}
        />

        <View style={styles.loginRow}>
          <Text style={styles.loginText}>{i18n.t('auth.already_account')} </Text>
          <TerahButton
            label={i18n.t('auth.login_button')}
            onPress={() => navigation.navigate('Login')}
            variant="ghost"
            style={styles.loginLink}
          />
        </View>
      </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

export default RegisterScreen;

const styles = StyleSheet.create({
  flex: {
    flex: 1,
    backgroundColor: colors.offWhite,
  },
  container: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingTop: 32,
    paddingBottom: 32,
  },
  logoArea: {
    alignItems: 'flex-start',
    marginBottom: 20,
  },
  title: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 24,
    color: colors.navy,
    marginBottom: 4,
  },
  subtitle: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 15,
    color: colors.midGrey,
    marginBottom: 28,
  },
  submitButton: {
    marginTop: 8,
    marginBottom: 16,
  },
  loginRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  loginText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.darkGrey,
  },
  loginLink: {
    height: 'auto' as any,
    paddingHorizontal: 0,
  },
});
