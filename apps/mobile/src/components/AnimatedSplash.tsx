import React, { useEffect } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Animated, {
  Easing,
  runOnJS,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withDelay,
  withSpring,
  withTiming,
} from 'react-native-reanimated';
import Svg, { Circle, Path, Rect } from 'react-native-svg';
import { colors } from '@/utils/tokens';

interface Props {
  onFinish: () => void;
}

const UNDERLINE_W = 124;
const HOLD_MS     = 1800;
const EXIT_MS     = 480;

export default function AnimatedSplash({ onFinish }: Props) {
  const reducedMotion = useReducedMotion();

  const shieldScale      = useSharedValue(reducedMotion ? 1 : 0.35);
  const shieldOpacity    = useSharedValue(0);
  const wordmarkOpacity  = useSharedValue(0);
  const wordmarkY        = useSharedValue(reducedMotion ? 0 : 28);
  const taglineOpacity   = useSharedValue(0);
  const underlineWidth   = useSharedValue(0);
  const containerOpacity = useSharedValue(1);

  useEffect(() => {
    const dismiss = withDelay(
      HOLD_MS,
      withTiming(0, { duration: EXIT_MS }, (finished) => {
        if (finished) runOnJS(onFinish)();
      }),
    );

    if (reducedMotion) {
      shieldOpacity.value    = 1;
      wordmarkOpacity.value  = 1;
      taglineOpacity.value   = 1;
      underlineWidth.value   = UNDERLINE_W;
      containerOpacity.value = dismiss;
      return;
    }

    // Shield: spring scale + fade
    shieldScale.value   = withSpring(1, { damping: 11, stiffness: 150 });
    shieldOpacity.value = withTiming(1, { duration: 420, easing: Easing.out(Easing.quad) });

    // Wordmark: slide up + fade
    wordmarkOpacity.value = withDelay(260, withTiming(1, { duration: 440 }));
    wordmarkY.value       = withDelay(260, withTiming(0, {
      duration: 440,
      easing: Easing.out(Easing.cubic),
    }));

    // Tagline: fade
    taglineOpacity.value = withDelay(520, withTiming(1, { duration: 380 }));

    // Underline: draw left → right via width
    underlineWidth.value = withDelay(760, withTiming(UNDERLINE_W, {
      duration: 500,
      easing: Easing.out(Easing.quad),
    }));

    // Exit
    containerOpacity.value = dismiss;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const shieldStyle = useAnimatedStyle(() => ({
    transform: [{ scale: shieldScale.value }],
    opacity:   shieldOpacity.value,
  }));

  const wordmarkStyle = useAnimatedStyle(() => ({
    opacity:   wordmarkOpacity.value,
    transform: [{ translateY: wordmarkY.value }],
  }));

  const taglineStyle = useAnimatedStyle(() => ({
    opacity: taglineOpacity.value,
  }));

  const underlineStyle = useAnimatedStyle(() => ({
    width: underlineWidth.value,
  }));

  const rootStyle = useAnimatedStyle(() => ({
    opacity: containerOpacity.value,
  }));

  return (
    <Animated.View style={[styles.root, rootStyle]}>
      {/* Radial glow behind shield */}
      <View style={styles.glow} />

      {/* Shield */}
      <Animated.View style={shieldStyle}>
        <Svg width={168} height={200} viewBox="10 10 80 108">
          {/* Shield body — slightly lighter navy so it reads on the background */}
          <Path
            d="M20,18 L70,18 L70,70 C70,95 45,110 45,110 C45,110 20,95 20,70 Z"
            fill="#122C64"
          />
          {/* Teal accent bar across top */}
          <Rect x="20" y="18" width="50" height="8" rx="2" fill={colors.teal} />
          {/* T — horizontal bar */}
          <Rect x="33" y="40" width="24" height="5" rx="2" fill="white" />
          {/* T — vertical stem */}
          <Rect x="43" y="45" width="5" height="30" rx="2" fill="white" />
          {/* Teal dot at shield base */}
          <Circle cx="45" cy="95" r="4" fill={colors.teal} />
        </Svg>
      </Animated.View>

      {/* TerahBank wordmark */}
      <Animated.View style={[styles.wordmarkRow, wordmarkStyle]}>
        <Text style={styles.terah}>Terah</Text>
        <Text style={styles.bank}>Bank</Text>
      </Animated.View>

      {/* Tagline */}
      <Animated.View style={taglineStyle}>
        <Text style={styles.tagline}>SAVE. GROW. THRIVE.</Text>
      </Animated.View>

      {/* Underline — grows left to right */}
      <View style={styles.underlineTrack}>
        <Animated.View style={[styles.underline, underlineStyle]} />
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
