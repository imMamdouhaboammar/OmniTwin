// Copyright 2026 Mamdouh Aboammar
// SPDX-License-Identifier: Apache-2.0

export interface CadenceConfig {
  medianChars: number;
  maxBubbles: number;
  burstProbability: number;
  typingSpeedMsPerChar: number;
}

export const DEFAULT_CADENCE_CONFIG: CadenceConfig = {
  medianChars: 14,
  maxBubbles: 3,
  burstProbability: 0.35,
  typingSpeedMsPerChar: 35,
};

/**
 * Splits monolithic model output into human-like chat bubbles.
 * Follows empirical distribution: median length ~10-20 chars, max 3 bubbles.
 */
export function splitIntoBubbles(
  text: string,
  config: CadenceConfig = DEFAULT_CADENCE_CONFIG
): string[] {
  const trimmed = text.trim();
  if (!trimmed) {
    return [];
  }

  // If text is already very short, return as a single bubble
  if (trimmed.length <= 25) {
    return [trimmed];
  }

  // Split on newlines, ellipsis, exclamation, question marks, or Arabic comma
  const rawSegments = trimmed
    .split(/[\n\r]+|[.!?…]+|[،؛]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0);

  if (rawSegments.length <= 1) {
    // Attempt chunking by word boundaries if text exceeds 40 chars
    const words = trimmed.split(/\s+/);
    if (words.length > 8) {
      const midpoint = Math.ceil(words.length / 2);
      return [
        words.slice(0, midpoint).join(" "),
        words.slice(midpoint).join(" "),
      ].slice(0, config.maxBubbles);
    }
    return [trimmed];
  }

  // Consolidate into at most maxBubbles
  const bubbles: string[] = [];
  for (const seg of rawSegments) {
    if (bubbles.length === 0) {
      bubbles.push(seg);
    } else if (bubbles.length < config.maxBubbles && (seg.length > 10 || bubbles[bubbles.length - 1].length > 30)) {
      bubbles.push(seg);
    } else {
      // Append to the last bubble
      bubbles[bubbles.length - 1] = `${bubbles[bubbles.length - 1]} ${seg}`;
    }
  }

  return bubbles.slice(0, config.maxBubbles);
}

/**
 * Calculates human typing latency in milliseconds for a bubble.
 */
export function calculateTypingDelayMs(
  bubbleText: string,
  config: CadenceConfig = DEFAULT_CADENCE_CONFIG
): number {
  const baseDelay = bubbleText.length * config.typingSpeedMsPerChar;
  // Add realistic jitter +/- 20%
  const jitter = (Math.random() * 0.4 - 0.2) * baseDelay;
  return Math.max(300, Math.min(4000, Math.round(baseDelay + jitter)));
}
