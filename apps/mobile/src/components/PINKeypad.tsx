/**
 * PINKeypad — custom numeric keypad for PIN entry.
 * Security: NEVER uses the system keyboard for PIN input (CLAUDE.md requirement).
 * All keys meet the 44×44 minimum touch target requirement.
 */
import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ViewStyle,
} from 'react-native';
import { colors } from '@/utils/tokens';

interface PINKeypadProps {
  onKeyPress: (key: string) => void;  // key is '0'–'9' or 'backspace'
  disabled?: boolean;
  style?: ViewStyle;
}

const ROWS = [
  ['1', '2', '3'],
  ['4', '5', '6'],
  ['7', '8', '9'],
  ['', '0', 'backspace'],
];

export function PINKeypad({ onKeyPress, disabled = false, style }: PINKeypadProps) {
  return (
    <View style={[styles.grid, style]} accessible={false}>
      {ROWS.map((row, rowIdx) => (
        <View key={rowIdx} style={styles.row}>
          {row.map((key, colIdx) => {
            if (key === '') {
              return <View key={colIdx} style={styles.emptyCell} />;
            }
            const isBackspace = key === 'backspace';
            return (
              <TouchableOpacity
                key={colIdx}
                onPress={() => !disabled && onKeyPress(key)}
                disabled={disabled}
                activeOpacity={0.6}
                style={[styles.key, disabled && styles.keyDisabled]}
                accessibilityRole="button"
                accessibilityLabel={isBackspace ? 'Supprimer' : key}
                hitSlop={{ top: 4, bottom: 4, left: 4, right: 4 }}
              >
                {isBackspace ? (
                  <Text style={[styles.backspaceIcon, disabled && styles.keyTextDisabled]}>
                    ⌫
                  </Text>
                ) : (
                  <Text style={[styles.keyText, disabled && styles.keyTextDisabled]}>
                    {key}
                  </Text>
                )}
              </TouchableOpacity>
            );
          })}
        </View>
      ))}
    </View>
  );
}

const KEY_SIZE = 72;

const styles = StyleSheet.create({
  grid: {
    width: '100%',
    gap: 12,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 16,
  },
  key: {
    width: KEY_SIZE,
    height: KEY_SIZE,
    borderRadius: KEY_SIZE / 2,
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.lightGrey,
    // Shadow for depth
    shadowColor: colors.navy,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 2,
  },
  keyDisabled: {
    opacity: 0.4,
  },
  emptyCell: {
    width: KEY_SIZE,
    height: KEY_SIZE,
  },
  keyText: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 22,
    color: colors.navy,
  },
  backspaceIcon: {
    fontSize: 24,
    color: colors.navy,
  },
  keyTextDisabled: {
    color: colors.midGrey,
  },
});
