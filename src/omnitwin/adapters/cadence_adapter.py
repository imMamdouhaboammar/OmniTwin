# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import re
import time
from typing import List


def split_into_bubbles(text: str, max_bubbles: int = 3) -> List[str]:
    """
    Splits an utterance into natural chat bubbles based on sentence boundaries,
    ellipses, and punctuation, preserving natural conversational flow.
    """
    trimmed = text.strip()
    if not trimmed:
        return []
    if len(trimmed) <= 25:
        return [trimmed]

    segments = [
        s.strip()
        for s in re.split(r"[\n\r]+|[.!?…]+|[،؛]+", trimmed)
        if len(s.strip()) > 0
    ]
    if len(segments) <= 1:
        words = trimmed.split()
        if len(words) > 8:
            mid = (len(words) + 1) // 2
            return [" ".join(words[:mid]), " ".join(words[mid:])][:max_bubbles]
        return [trimmed]

    bubbles = []
    for seg in segments:
        if not bubbles:
            bubbles.append(seg)
        elif len(bubbles) < max_bubbles and (len(seg) > 10 or len(bubbles[-1]) > 30):
            bubbles.append(seg)
        else:
            bubbles[-1] = f"{bubbles[-1]} {seg}"

    return bubbles[:max_bubbles]


def split_and_stream(text: str, simulate_delay: bool = False) -> List[str]:
    """Splits utterance and optionally sleeps for realistic typing latency."""
    bubbles = split_into_bubbles(text)
    for b in bubbles:
        if simulate_delay:
            delay = max(0.1, min(0.6, len(b) * 0.015))
            time.sleep(delay)
    return bubbles
