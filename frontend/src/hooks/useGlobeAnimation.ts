'use client';

import { useState, useEffect, useCallback } from 'react';
import { useUIStore } from '@/lib/store';

interface UseGlobeAnimationOptions {
  fps?: number;
  pulseSpeed?: number;
}

interface GlobeAnimationState {
  animationFrame: number;
  pulseValue: number;
  isAnimating: boolean;
}

export function useGlobeAnimation(options: UseGlobeAnimationOptions = {}): GlobeAnimationState {
  const { fps = 30, pulseSpeed = 0.05 } = options;
  const { isPlaying } = useUIStore();
  const [animationFrame, setAnimationFrame] = useState(0);

  useEffect(() => {
    // Always run a slow animation for pulsing effects, even when not playing
    const interval = setInterval(() => {
      setAnimationFrame((prev) => (prev + 1) % 360);
    }, 1000 / fps);

    return () => clearInterval(interval);
  }, [fps]);

  // Calculate pulse value (0-1, oscillating)
  const pulseValue = (Math.sin(animationFrame * pulseSpeed) + 1) / 2;

  return {
    animationFrame,
    pulseValue,
    isAnimating: isPlaying,
  };
}

// Color interpolation helper for time-based arc coloring
export function getTimeBasedColor(
  daysSinceDetection: number,
  baseAlpha: number = 180
): [number, number, number, number] {
  // Recent (0-7 days): Red
  // 1-2 weeks: Yellow/Orange
  // 3+ weeks: Blue/Cyan
  // Older: Fade out

  if (daysSinceDetection <= 7) {
    // Red - urgent/recent
    const intensity = 1 - daysSinceDetection / 7;
    return [239, 68 + Math.round(87 * (1 - intensity)), 68, baseAlpha];
  } else if (daysSinceDetection <= 14) {
    // Orange to Yellow transition
    const progress = (daysSinceDetection - 7) / 7;
    return [
      245,
      Math.round(158 + 40 * progress),
      Math.round(11 + 50 * progress),
      baseAlpha * 0.9,
    ];
  } else if (daysSinceDetection <= 21) {
    // Yellow to Cyan transition
    const progress = (daysSinceDetection - 14) / 7;
    return [
      Math.round(245 - 185 * progress),
      Math.round(198 - 16 * progress),
      Math.round(61 + 143 * progress),
      baseAlpha * 0.8,
    ];
  } else if (daysSinceDetection <= 60) {
    // Cyan - older but still relevant
    const fadeProgress = (daysSinceDetection - 21) / 39;
    return [60, 182, 204, Math.round(baseAlpha * 0.7 * (1 - fadeProgress * 0.5))];
  } else {
    // Very old - fade to dim
    return [100, 150, 180, Math.round(baseAlpha * 0.3)];
  }
}

// Pulsing width calculation for animated arcs
export function getPulsingWidth(
  baseWidth: number,
  pulseValue: number,
  isHighPriority: boolean = false
): number {
  const pulseAmplitude = isHighPriority ? 0.4 : 0.2;
  return baseWidth * (1 + pulseAmplitude * pulseValue);
}
