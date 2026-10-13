# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0

"""
Allostasis and Physiological Regulation Adapter for OmniTwin.

Provides character-agnostic, local-first physiological pacing:
1. Privacy Fence (Boundary Isolation):
   Raw wearable signals (Apple Watch, Garmin, Oura, WHOOP) are validated against
   `biometric_sample.schema.json`. Raw values NEVER enter LLM context, long-term
   memory tables (ep, ep_fts, meta), or user-facing chat traces.
2. Autonomic Regulation:
   Only derived scalars cross the barrier into cognitive state:
   - `allostatic_load` (0.0 .. 1.0): normalized composite of software interaction velocity and wearable load.
   - `is_depleted`: boolean flag when cumulative load exceeds threshold (0.85).
   - `energy`: autonomic physical energy (0.1 .. 1.0).
   - `conversation_appetite`: "chatty" | "medium" | "low" | "minimal".
   - `should_force_red`: boolean flag when acute sample exceeds critical threshold.
3. Conversational Pacing:
   Rapid conversation bursts accumulate software allostatic load, pacing the conversation
   and enforcing response brevity when fatigued.

NON-CLINICAL / NON-MEDICAL DISCLAIMER:
This module is strictly an informational pacing mechanism for conversational AI agents.
It does NOT provide clinical diagnostics, medical evaluations, or physiological ground truth.
"""

from __future__ import annotations

import collections
import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import jsonschema

logger = logging.getLogger("OmniTwin.Allostasis")


class BiometricBarrierError(ValueError):
    """Raised when a biometric payload fails schema validation or violates isolation."""
    pass


class AllostasisTracker:
    """
    Tracks conversational token velocity and wearable biometrics over a sliding window
    to compute continuous allostatic load. Event-driven and zero-watt idle.
    """

    def __init__(
        self,
        window_sec: float = 300.0,
        biometric_window_sec: float = 1800.0,
        hr_red_bpm: float = 140.0,
        hrv_red_ms: float = 20.0,
        depletion_threshold: float = 0.85,
    ):
        self.window_sec = window_sec
        self.biometric_window_sec = biometric_window_sec
        self.hr_red_bpm = hr_red_bpm
        self.hrv_red_ms = hrv_red_ms
        self.depletion_threshold = depletion_threshold

        self._prompts: collections.deque[Tuple[float, int]] = collections.deque()
        self._biometrics: collections.deque[Tuple[float, str, float]] = collections.deque()

    def record_prompt(self, tokens: int = 100) -> None:
        """Records tokens spent in a chat interaction."""
        now = time.time()
        self._prompts.append((now, max(1, tokens)))
        self._prune(now)

    def record_biometric(self, sample_type: str, value: float) -> None:
        """Records a validated derived biometric scalar."""
        now = time.time()
        self._biometrics.append((now, sample_type, float(value)))
        self._prune(now)

    def _prune(self, now: float) -> None:
        prompt_cutoff = now - self.window_sec
        while self._prompts and self._prompts[0][0] < prompt_cutoff:
            self._prompts.popleft()

        bio_cutoff = now - self.biometric_window_sec
        while self._biometrics and self._biometrics[0][0] < bio_cutoff:
            self._biometrics.popleft()

    def get_software_load(self) -> float:
        """Calculates normalized software load (0.0 .. 1.0) from token velocity."""
        now = time.time()
        self._prune(now)
        total_tokens = sum(t for _, t in self._prompts)
        # 1500 tokens in 5 minutes represents high conversational burst
        raw_load = total_tokens / 1500.0
        return min(1.0, max(0.0, raw_load))

    def get_biometric_load(self) -> float:
        """Calculates normalized biometric load (0.0 .. 1.0) from recent wearable telemetry."""
        now = time.time()
        self._prune(now)
        if not self._biometrics:
            return 0.0

        load_components: List[float] = []
        for _, stype, val in self._biometrics:
            if stype == "heart_rate":
                # Elevated heart rate (> 100 bpm baseline)
                hr_norm = (val - 70.0) / (self.hr_red_bpm - 70.0)
                load_components.append(min(1.0, max(0.0, hr_norm)))
            elif stype == "heart_rate_variability_sdnn":
                # Low HRV indicates autonomic fatigue
                hrv_norm = (60.0 - val) / (60.0 - self.hrv_red_ms)
                load_components.append(min(1.0, max(0.0, hrv_norm)))
            elif stype == "respiratory_rate":
                rr_norm = (val - 14.0) / 12.0
                load_components.append(min(1.0, max(0.0, rr_norm)))

        if not load_components:
            return 0.0
        return min(1.0, max(0.0, sum(load_components) / len(load_components)))

    def get_composite_load(self) -> float:
        soft = self.get_software_load()
        bio = self.get_biometric_load()
        return min(1.0, max(soft, bio))

    def is_depleted(self) -> bool:
        return self.get_composite_load() >= self.depletion_threshold

    def should_force_red(self) -> bool:
        now = time.time()
        self._prune(now)
        # Check if most recent reading exceeds critical threshold
        for t, stype, val in reversed(self._biometrics):
            if now - t > 300.0:
                break
            if stype == "heart_rate" and val >= self.hr_red_bpm:
                return True
            if stype == "heart_rate_variability_sdnn" and val <= self.hrv_red_ms:
                return True
        return False

    def reset(self) -> None:
        self._prompts.clear()
        self._biometrics.clear()


class AllostasisEngine:
    """
    Physiological regulation and allostasis engine for an OmniTwin persona.
    Tracks software conversation bursts and wearable telemetry to modulate energy and pacing.
    """

    def __init__(
        self,
        persona_id: str = "default",
        schema_path: Optional[str] = None,
        hr_red_bpm: float = 140.0,
        hrv_red_ms: float = 20.0,
        window_sec: float = 300.0,
        biometric_window_sec: float = 1800.0,
    ):
        self.persona_id = persona_id
        self.hr_red_bpm = hr_red_bpm
        self.hrv_red_ms = hrv_red_ms
        self.last_sleep_hours: float = 7.5

        if schema_path is None:
            # Look up standard location in package config
            default_schema = Path(__file__).resolve().parent.parent.parent.parent / "config" / "biometric_sample_schema.json"
            if not default_schema.exists():
                default_schema = Path(__file__).resolve().parent.parent / "config" / "biometric_sample_schema.json"
            schema_path = str(default_schema)

        self.schema_path = schema_path
        self._schema = None
        if os.path.exists(schema_path):
            try:
                with open(schema_path, "r", encoding="utf-8") as f:
                    self._schema = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load biometric schema: {e}")

        self.tracker = AllostasisTracker(
            window_sec=window_sec,
            biometric_window_sec=biometric_window_sec,
            hr_red_bpm=hr_red_bpm,
            hrv_red_ms=hrv_red_ms,
        )

    def validate_sample(self, raw_sample: Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """Validates payload against official JSON schema."""
        if isinstance(raw_sample, str):
            try:
                sample_dict = json.loads(raw_sample)
            except Exception as e:
                raise BiometricBarrierError(f"Malformed JSON sample: {e}")
        elif isinstance(raw_sample, dict):
            sample_dict = raw_sample
        else:
            raise BiometricBarrierError(f"Expected dict or JSON string, got {type(raw_sample)}")

        if self._schema is not None:
            try:
                jsonschema.validate(instance=sample_dict, schema=self._schema)
            except jsonschema.ValidationError as err:
                raise BiometricBarrierError(f"Biometric barrier schema validation failed: {err.message}")

        return sample_dict

    def ingest_healthkit_sample(self, raw_sample: Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """Validates and ingests a wearable sample through the biometric barrier."""
        sample = self.validate_sample(raw_sample)
        stype = sample.get("type", "unknown")
        val = float(sample.get("value", 0.0))

        if stype == "sleep_analysis":
            self.last_sleep_hours = max(2.0, min(14.0, val))
        else:
            self.tracker.record_biometric(stype, val)

        autonomic = self.get_autonomic_state()
        return {
            "accepted": True,
            "sample_type": stype,
            "unit": sample.get("unit"),
            "autonomic_state": autonomic,
        }

    def ingest_rr_intervals(
        self,
        rr_intervals_ms: List[float],
        sleep_hours: float = 7.5,
        device: str = "Wearable Sensor",
        sampled_at_iso: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Converts raw R-R intervals into validated Heart Rate and SDNN samples."""
        self.last_sleep_hours = max(2.0, min(14.0, sleep_hours))

        if not rr_intervals_ms or len(rr_intervals_ms) < 2:
            return {
                "accepted": False,
                "reason": "Insufficient R-R intervals (minimum 2 required)",
                "autonomic_state": self.get_autonomic_state(),
            }

        iso_now = sampled_at_iso or datetime.now(tz=timezone.utc).isoformat()

        # 1. Mean Heart Rate
        mean_rr_ms = sum(rr_intervals_ms) / len(rr_intervals_ms)
        mean_rr_ms = max(300.0, min(2000.0, mean_rr_ms))
        heart_rate_bpm = round(60000.0 / mean_rr_ms, 1)

        # 2. SDNN
        variance = sum((x - mean_rr_ms) ** 2 for x in rr_intervals_ms) / len(rr_intervals_ms)
        sdnn_ms = round(math.sqrt(variance), 1)

        # Validate through barrier
        hr_payload = {
            "type": "heart_rate",
            "value": float(heart_rate_bpm),
            "unit": "count/min",
            "sampled_at": iso_now,
            "source": {"device": device},
        }
        self.ingest_healthkit_sample(hr_payload)

        hrv_payload = {
            "type": "heart_rate_variability_sdnn",
            "value": float(sdnn_ms),
            "unit": "ms",
            "sampled_at": iso_now,
            "source": {"device": device},
        }
        self.ingest_healthkit_sample(hrv_payload)

        return {
            "accepted": True,
            "hr_bpm": heart_rate_bpm,
            "sdnn_ms": sdnn_ms,
            "sample_count": len(rr_intervals_ms),
            "autonomic_state": self.get_autonomic_state(),
        }

    def record_chat_turn(self, prompt_tokens: int, completion_tokens: int) -> None:
        """Records tokens spent in conversational turn to track burst velocity."""
        total = max(1, prompt_tokens + completion_tokens)
        self.tracker.record_prompt(total)

    def get_autonomic_state(self) -> Dict[str, Any]:
        """
        Computes derived autonomic state scalars without leaking raw telemetry.
        Returns:
            - allostatic_load: 0.0 .. 1.0
            - software_load: 0.0 .. 1.0
            - biometric_load: 0.0 .. 1.0
            - is_depleted: bool
            - should_force_red: bool
            - energy: 0.1 .. 1.0
            - conversation_appetite: "chatty" | "medium" | "low" | "minimal"
            - pacing_hint: str
        """
        software_load = self.tracker.get_software_load()
        biometric_load = self.tracker.get_biometric_load()
        composite_load = self.tracker.get_composite_load()
        is_depleted = self.tracker.is_depleted()
        force_red = self.tracker.should_force_red()

        # Derive Physical Energy E_phys
        sleep_factor = min(1.0, self.last_sleep_hours / 7.0)
        base_energy = 0.90 - (0.65 * composite_load)
        energy = base_energy * (0.35 + 0.65 * sleep_factor)
        clamped_energy = round(max(0.10, min(1.0, energy)), 2)

        # Derive Conversational Appetite
        if force_red or is_depleted or composite_load >= 0.80 or clamped_energy < 0.30:
            appetite = "minimal"
            pacing_hint = "depleted_minimal_effort"
        elif composite_load >= 0.55 or clamped_energy < 0.50:
            appetite = "low"
            pacing_hint = "conversational_slowdown"
        elif composite_load >= 0.30 or clamped_energy < 0.70:
            appetite = "medium"
            pacing_hint = "normal_balanced"
        else:
            appetite = "chatty"
            pacing_hint = "fully_available"

        return {
            "allostatic_load": round(composite_load, 3),
            "software_load": round(software_load, 3),
            "biometric_load": round(biometric_load, 3),
            "is_depleted": bool(is_depleted),
            "should_force_red": bool(force_red),
            "energy": clamped_energy,
            "conversation_appetite": appetite,
            "pacing_hint": pacing_hint,
        }

    def get_pacing_constraint(self) -> str:
        """Returns prompt negative constraint when allostatic load mandates brevity."""
        autonomic = self.get_autonomic_state()
        appetite = autonomic["conversation_appetite"]
        if appetite == "minimal":
            return (
                "- Autonomic capacity is constrained (elevated allostatic load / depleted). "
                "Keep responses very brief, calm, and low effort (1 short message). "
                "Do not drive complex topics or ask multiple follow-ups. "
                "Never mention physiological sensors or medical devices."
            )
        elif appetite == "low":
            return (
                "- Conversational appetite is low. Respond concisely and calmly without over-extending."
            )
        return ""

    def reset(self) -> None:
        self.tracker.reset()


_ENGINES: Dict[str, AllostasisEngine] = {}


def get_allostasis_engine(persona_id: str = "default") -> AllostasisEngine:
    """Returns singleton AllostasisEngine for persona."""
    if persona_id not in _ENGINES:
        _ENGINES[persona_id] = AllostasisEngine(persona_id=persona_id)
    return _ENGINES[persona_id]


def get_harlo_engine(character_slug: str = "default") -> AllostasisEngine:
    """Backwards-compatibility alias."""
    return get_allostasis_engine(character_slug)
