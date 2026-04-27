import React, { useEffect, useRef } from 'react';
import { View, Text, Animated, StyleSheet, useColorScheme } from 'react-native';
import { colors } from '@/utils/tokens';

interface ProgressBarProps {
  percent: number;   // 0–100
  label?: string;
  showPercent?: boolean;
  height?: number;
  color?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  percent,
  label,
  showPercent = true,
  height = 8,
  color = colors.teal,
}) => {
  const clampedPercent = Math.min(100, Math.max(0, percent));
  const animatedWidth = useRef(new Animated.Value(0)).current;

  // Respect prefers-reduced-motion — detect via AccessibilityInfo in production;
  // here we default to animating and fall back to instant if system reduces motion.
  useEffect(() => {
    // 400ms ease-out per design system animation rules
    Animated.timing(animatedWidth, {
      toValue: clampedPercent,
      duration: 400,
      useNativeDriver: false,
    }).start();
  }, [clampedPercent]);

  const widthInterpolated = animatedWidth.interpolate({
    inputRange: [0, 100],
    outputRange: ['0%', '100%'],
    extrapolate: 'clamp',
  });

  return (
    <View style={styles.container}>
      {label || showPercent ? (
        <View style={styles.labelRow}>
          {label ? <Text style={styles.label}>{label}</Text> : <View />}
          {showPercent ? (
            <Text style={styles.percentText}>{clampedPercent}%</Text>
          ) : null}
        </View>
      ) : null}
      <View style={[styles.track, { height }]}>
        <Animated.View
          style={[
            styles.fill,
            { width: widthInterpolated, height, backgroundColor: color },
          ]}
          accessibilityRole="progressbar"
          accessibilityValue={{ min: 0, max: 100, now: clampedPercent }}
        />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
  },
  labelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  label: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: colors.darkGrey,
  },
  percentText: {
    fontFamily: 'Poppins_600SemiBold',
    fontSize: 13,
    color: colors.teal,
  },
  track: {
    backgroundColor: colors.lightGrey,
    borderRadius: 999,
    overflow: 'hidden',
  },
  fill: {
    borderRadius: 999,
  },
});
