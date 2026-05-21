import { useEffect, useState } from 'react';
import { AccessibilityInfo } from 'react-native';

/**
 * Returns true when the user has enabled "Reduce Motion" in system accessibility settings.
 * Use this to skip or instant-complete animations (Milestone 7.3 — prefers-reduced-motion).
 *
 * Example:
 *   const reduced = useReducedMotion();
 *   Animated.timing(val, { duration: reduced ? 0 : 400, ... });
 */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    // Read initial value
    AccessibilityInfo.isReduceMotionEnabled().then(setReduced).catch(() => {});

    // Subscribe to future changes (user toggles in Settings while app is open)
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduced);
    return () => sub.remove();
  }, []);

  return reduced;
}
