// Copyright 2026 Mamdouh Aboammar
// SPDX-License-Identifier: Apache-2.0

import { describe, expect, test } from "bun:test";
import { splitIntoBubbles, calculateTypingDelayMs, DEFAULT_CADENCE_CONFIG } from "../src/cadence";

describe("OmniTwin Cadence Engine", () => {
  test("returns empty array for empty or whitespace text", () => {
    expect(splitIntoBubbles("")).toEqual([]);
    expect(splitIntoBubbles("   \n\t  ")).toEqual([]);
  });

  test("preserves short utterances as single bubble", () => {
    const shortText = "Sounds good!";
    const bubbles = splitIntoBubbles(shortText);
    expect(bubbles).toEqual([shortText]);
  });

  test("splits multi-sentence text on punctuation boundaries", () => {
    const longText = "I looked into that architecture problem. We should decouple the storage layer! Let me know if that works.";
    const bubbles = splitIntoBubbles(longText);
    expect(bubbles.length).toBeGreaterThan(1);
    expect(bubbles.length).toBeLessThanOrEqual(DEFAULT_CADENCE_CONFIG.maxBubbles);
  });

  test("calculates positive bounded typing delay", () => {
    const delay = calculateTypingDelayMs("Hello there!");
    expect(delay).toBeGreaterThanOrEqual(300);
    expect(delay).toBeLessThanOrEqual(4000);
  });
});
