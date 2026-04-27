import React, { useState } from 'react';
import {
  View,
  TextInput,
  Text,
  TouchableOpacity,
  StyleSheet,
  TextInputProps,
} from 'react-native';
import { colors } from '@/utils/tokens';

interface TerahInputProps extends TextInputProps {
  label: string;
  error?: string | null;
  hint?: string;
  showPasswordToggle?: boolean;
}

export const TerahInput: React.FC<TerahInputProps> = ({
  label,
  error,
  hint,
  showPasswordToggle = false,
  secureTextEntry,
  style,
  ...props
}) => {
  const [isPasswordVisible, setPasswordVisible] = useState(false);

  const isSecure = showPasswordToggle ? !isPasswordVisible : secureTextEntry;

  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label}</Text>
      <View style={[styles.inputWrapper, error ? styles.inputError : styles.inputDefault]}>
        <TextInput
          {...props}
          secureTextEntry={isSecure}
          style={[styles.input, style]}
          placeholderTextColor={colors.midGrey}
          accessibilityLabel={label}
          accessibilityHint={hint}
        />
        {showPasswordToggle && (
          <TouchableOpacity
            onPress={() => setPasswordVisible((v) => !v)}
            accessibilityLabel={isPasswordVisible ? 'Hide password' : 'Show password'}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            style={styles.toggleButton}
          >
            {/* Icon placeholder — replace with Phosphor Eye/EyeSlash */}
            <Text style={styles.toggleText}>{isPasswordVisible ? 'Hide' : 'Show'}</Text>
          </TouchableOpacity>
        )}
      </View>
      {error ? (
        <Text style={styles.errorText} accessibilityRole="alert">
          {error}
        </Text>
      ) : hint ? (
        <Text style={styles.hintText}>{hint}</Text>
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginBottom: 16,
  },
  label: {
    fontFamily: 'Roboto_500Medium',
    fontSize: 14,
    color: colors.darkGrey,
    marginBottom: 6,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: 8,
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 16,
    height: 56,             // Min touch target
  },
  inputDefault: {
    borderColor: colors.lightGrey,
  },
  inputError: {
    borderColor: colors.error,
  },
  input: {
    flex: 1,
    fontFamily: 'Roboto_400Regular',
    fontSize: 16,
    color: colors.darkGrey,
    paddingVertical: 0,
  },
  toggleButton: {
    paddingLeft: 8,
    minWidth: 44,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  toggleText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 14,
    color: colors.teal,
  },
  errorText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: colors.error,
    marginTop: 4,
  },
  hintText: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 12,
    color: colors.midGrey,
    marginTop: 4,
  },
});
