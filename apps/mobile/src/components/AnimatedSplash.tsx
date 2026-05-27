import React, { useEffect, useRef } from 'react';
import { Animated, Platform, StyleSheet, Text, View } from 'react-native';
import Svg, { Circle, Path, Rect } from 'react-native-svg';
import { colors } from '@/utils/tokens';

interface Props {
  onFinish: () => void;
}

const UNDERLINE_W = 124;
const HOLD_MS     = 1800;
const EXIT_MS     = 480;

export default function AnimatedSplash({ onFinish }: Props) {
  const shieldScale      = useRef(new Animated.Value(0.35)).current;
  const shieldOpacity    = useRef(new Animated.Value(0)).current;
  const wordmarkOpacity  = useRef(new Animated.Value(0)).current;
  const wordmarkY        = useRef(new Animated.Value(28)).current;
  const taglineOpacity   = useRef(new Animated.Value(0)).current;
  const underlineWidth   = useRef(new Animated.Value(0)).current;
  const containerOpacity = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (Platform.OS === 'web') {
      onFinish();
      return;
    }

    const exitAnim = Animated.sequence([
      Animated.delay(HOLD_MS),
      Animated.timing(containerOpacity, {
        toValue: 0,
        duration: EXIT_MS,
        useNativeDriver: true,
      }),
    ]);

    Animated.parallel([
      // Shield: spring scale + fade
      Animated.spring(shieldScale, {
        toValue: 1,
        damping: 11,
        stiffness: 150,
        useNativeDriver: true,
      }),
      Animated.timing(shieldOpacity, {
        toValue: 1,
        duration: 420,
        useNativeDriver: true,
      }),
      // Wordmark: slide up + fade
      Animated.sequence([
        Animated.delay(260),
        Animated.parallel([
          Animated.timing(wordmarkOpacity, { toValue: 1, duration: 440, useNativeDriver: true }),
          Animated.timing(wordmarkY, { toValue: 0, duration: 440, useNativeDriver: true }),
        ]),
      ]),
      // Tagline
      Animated.sequence([
        Animated.delay(520),
        Animated.timing(taglineOpacity, { toValue: 1, duration: 380, useNativeDriver: true }),
      ]),
      // Underline (useNativeDriver: false — animates width)
      Animated.sequence([
        Animated.delay(760),
        Animated.timing(underlineWidth, {
          toValue: UNDERLINE_W,
          duration: 500,
          useNativeDriver: false,
        }),
      ]),
      // Exit
      exitAnim,
    ]).start(({ finished }) => {
      if (finished) onFinish();
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Animated.View style={[styles.root, { opacity: containerOpacity }]}>
      <View style={styles.glow} />

      <Animated.View style={{ transform: [{ scale: shieldScale }], opacity: shieldOpacity }}>
        <Svg width={168} height={200} viewBox="10 10 80 108">
          <Path
            d="M20,18 L70,18 L70,70 C70,95 45,110 45,110 C45,110 20,95 20,70 Z"
            fill="#122C64"
          />
          <Rect x="20" y="18" width="50" height="8" rx="2" fill={colors.teal} />
          <Rect x="33" y="40" width="24" height="5" rx="2" fill="white" />
          <Rect x="43" y="45" width="5" height="30" rx="2" fill="white" />
          <Circle cx="45" cy="95" r="4" fill={colors.teal} />
        </Svg>
      </Animated.View>

      <Animated.View style={[styles.wordmarkRow, { opacity: wordmarkOpacity, transform: [{ translateY: wordmarkY }] }]}>
        <Text style={styles.terah}>Terah</Text>
        <Text style={styles.bank}>Bank</Text>
      </Animated.View>

      <Animated.View style={{ opacity: taglineOpacity }}>
        <Text style={styles.tagline}>SAVE. GROW. THRIVE.</Text>
      </Animated.View>

      <View style={styles.underlineTrack}>
        <Animated.View style={[styles.underline, { width: underlineWidth }]} />
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  root: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: colors.navy,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 999,
  },
  glow: {
    position: 'absolute',
    width: 380,
    height: 380,
    borderRadius: 190,
    backgroundColor: '#162D5E',
    opacity: 0.55,
  },
  wordmarkRow: {
    flexDirection: 'row',
    marginTop: 24,
  },
  terah: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 46,
    color: 'white',
    letterSpacing: -1,
    includeFontPadding: false,
  },
  bank: {
    fontFamily: 'Poppins_700Bold',
    fontSize: 46,
    color: colors.teal,
    letterSpacing: -1,
    includeFontPadding: false,
  },
  tagline: {
    fontFamily: 'Roboto_400Regular',
    fontSize: 13,
    color: '#6B7A99',
    letterSpacing: 2.5,
    marginTop: 10,
  },
  underlineTrack: {
    marginTop: 12,
    height: 3,
    width: UNDERLINE_W,
    overflow: 'hidden',
  },
  underline: {
    height: 3,
    backgroundColor: colors.teal,
    borderRadius: 2,
  },
});
