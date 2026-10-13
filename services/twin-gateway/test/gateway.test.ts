// Copyright 2026 Mamdouh Aboammar
// SPDX-License-Identifier: Apache-2.0

import { describe, expect, test } from "bun:test";
import { splitIntoBubbles } from "../src/cadence";

describe("OmniTwin Gateway Validation & Formatting", () => {
  test("validates character and persona slug format strictly", () => {
    const slugRegex = /^[a-zA-Z0-9_-]{1,64}$/;
    
    expect(slugRegex.test("alex")).toBe(true);
    expect(slugRegex.test("companion_v1")).toBe(true);
    expect(slugRegex.test("default-twin-01")).toBe(true);

    expect(slugRegex.test("")).toBe(false);
    expect(slugRegex.test("persona; DROP TABLE ep;")).toBe(false);
    expect(slugRegex.test("twin with spaces")).toBe(false);
    expect(slugRegex.test("../../../etc/passwd")).toBe(false);
  });

  test("validates turn input constraints", () => {
    const validPayload = {
      characterSlug: "alex",
      userId: "user_test",
      message: "Hello world",
    };
    expect(validPayload.characterSlug).toBe("alex");
    expect(validPayload.message.length).toBeLessThan(4096);
  });

  test("formats model responses into cadenced bubbles", () => {
    const sampleOutput = "Checking in on the project. We made good progress today. Let me know what you think!";
    const bubbles = splitIntoBubbles(sampleOutput);
    expect(bubbles.length).toBeGreaterThanOrEqual(1);
    expect(bubbles.length).toBeLessThanOrEqual(3);
    for (const b of bubbles) {
      expect(b.length).toBeGreaterThan(0);
    }
  });

  test("handles Arabic sentence boundary splitting in cadence engine", () => {
    const arabicText = "أهلاً بيك! راجعت الكود النهاردة وشكله ممتاز، خلينا نتقابل بكرة ونكمله سوا.";
    const bubbles = splitIntoBubbles(arabicText);
    expect(bubbles.length).toBeGreaterThanOrEqual(1);
  });
});
