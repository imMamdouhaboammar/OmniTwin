# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0

"""
Bio-mathematical signal processing module for conversational AI pacing.

NON-CLINICAL / NON-MEDICAL DISCLAIMER:
This module processes physiological telemetry (R-R interval streams, heart rate, HRV)
strictly as an informational behavioral pacing mechanism for conversational AI agents.
It does NOT provide clinical diagnostics, medical evaluations, or physiological ground truth.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


class BiometricProcessor:
    """
    Bio-mathematical engine processing wearable telemetry:
    - Calculates RMSSD (Root Mean Square of Successive Differences).
    - Calculates Baevsky Stress Index (SI) from R-R interval distributions.
    - Computes Physical Energy E_phys and Cognitive Load for agent pacing.
    """

    def __init__(self, bin_width_ms: int = 50):
        self.bin_width_ms = bin_width_ms

    def compute_rmssd(self, rr_intervals_ms: List[float]) -> float:
        """
        RMSSD = sqrt( (1 / (N - 1)) * sum( (RR_{i+1} - RR_i)^2 ) )
        """
        if len(rr_intervals_ms) < 2:
            return 0.0

        squared_diffs = [
            (rr_intervals_ms[i + 1] - rr_intervals_ms[i]) ** 2
            for i in range(len(rr_intervals_ms) - 1)
        ]
        mean_squared = sum(squared_diffs) / len(squared_diffs)
        return math.sqrt(mean_squared)

    def compute_baevsky_stress_index(self, rr_intervals_ms: List[float]) -> Dict[str, float]:
        """
        Baevsky Stress Index SI = (AMo * 100%) / (2 * Mo * delta_RR)
        Where:
        - Mo is the mode of RR intervals (in seconds).
        - AMo is the amplitude of the mode (% of intervals in the mode bin).
        - delta_RR = max(RR) - min(RR) in seconds.
        """
        if not rr_intervals_ms or len(rr_intervals_ms) < 10:
            return {
                "stress_index": 50.0,
                "mode_seconds": 0.8,
                "mode_amplitude_percent": 30.0,
                "variation_range_seconds": 0.3,
            }

        # Convert to seconds
        rr_sec = [x / 1000.0 if x > 200 else x for x in rr_intervals_ms]
        n = len(rr_sec)

        min_rr = min(rr_sec)
        max_rr = max(rr_sec)
        delta_rr = max(0.05, max_rr - min_rr)

        # Histogram binning (50ms = 0.05s bins)
        bin_width = self.bin_width_ms / 1000.0
        bins: Dict[int, int] = {}
        for val in rr_sec:
            bin_idx = int(val / bin_width)
            bins[bin_idx] = bins.get(bin_idx, 0) + 1

        # Mode calculation
        mode_bin = max(bins.keys(), key=lambda k: bins[k])
        mode_seconds = (mode_bin * bin_width) + (bin_width / 2.0)
        mode_count = bins[mode_bin]
        amo_percent = (mode_count / float(n)) * 100.0

        # Formula: SI = AMo / (2 * Mo * delta_RR)
        stress_index = (amo_percent) / (2.0 * mode_seconds * delta_rr)

        return {
            "stress_index": round(stress_index, 2),
            "mode_seconds": round(mode_seconds, 3),
            "mode_amplitude_percent": round(amo_percent, 2),
            "variation_range_seconds": round(delta_rr, 3),
        }

    def compute_physical_energy(self, stress_index: float, sleep_hours: float = 7.5) -> float:
        """
        Derives real-time physical energy (0.0 .. 1.0) from the Baevsky Stress Index and sleep.
        High SI (> 300) severely depletes conversational appetite.
        """
        clamped_si = max(30.0, min(800.0, stress_index))
        log_si = math.log(clamped_si)
        log_min = math.log(40.0)
        log_max = math.log(600.0)

        # Inverted: high stress = low energy
        si_energy = 1.0 - ((log_si - log_min) / (log_max - log_min))
        si_energy = max(0.1, min(1.0, si_energy))

        # Sleep multiplier (penalize if sleep < 6 hours)
        sleep_factor = min(1.0, sleep_hours / 7.0)
        final_energy = si_energy * (0.4 + 0.6 * sleep_factor)

        return round(max(0.1, min(1.0, final_energy)), 2)

    def process_telemetry_payload(
        self,
        rr_intervals_ms: List[float],
        sleep_hours: float = 7.5,
    ) -> Dict[str, Any]:
        """Calculates telemetry metrics independently without external daemon dependencies."""
        rmssd = self.compute_rmssd(rr_intervals_ms)
        si_metrics = self.compute_baevsky_stress_index(rr_intervals_ms)
        energy = self.compute_physical_energy(si_metrics["stress_index"], sleep_hours)

        if energy < 0.35:
            appetite = "minimal"
        elif energy < 0.60:
            appetite = "low"
        elif energy < 0.80:
            appetite = "medium"
        else:
            appetite = "chatty"

        return {
            "rmssd_ms": round(rmssd, 2),
            "stress_index": si_metrics["stress_index"],
            "mode_seconds": si_metrics["mode_seconds"],
            "attenuated_energy": energy,
            "conversation_appetite": appetite,
        }

    def process_telemetry(
        self,
        rr_intervals_ms: List[float],
        sleep_hours: float = 7.5,
        persona_id: str = "default",
        character_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Integrates R-R intervals with allostatic regulation while preserving legacy metrics."""
        from omnitwin.adapters.allostasis_adapter import get_allostasis_engine

        pid = persona_id or character_slug or "default"
        engine = get_allostasis_engine(pid)
        res = engine.ingest_rr_intervals(
            rr_intervals_ms=rr_intervals_ms,
            sleep_hours=sleep_hours,
        )

        rmssd = self.compute_rmssd(rr_intervals_ms)
        si_metrics = self.compute_baevsky_stress_index(rr_intervals_ms)
        legacy_energy = self.compute_physical_energy(si_metrics["stress_index"], sleep_hours)
        autonomic = res.get("autonomic_state", engine.get_autonomic_state())

        return {
            "rmssd_ms": round(rmssd, 2),
            "stress_index": si_metrics["stress_index"],
            "mode_seconds": si_metrics["mode_seconds"],
            "legacy_energy": legacy_energy,
            "allostasis_energy": autonomic.get("energy", 0.7),
            "allostatic_load": autonomic.get("allostatic_load", 0.2),
            "is_depleted": autonomic.get("is_depleted", False),
            "conversation_appetite": autonomic.get("conversation_appetite", "medium"),
            "autonomic_state": autonomic,
        }

    def process_healthkit_sample(
        self,
        raw_sample: Any,
        persona_id: str = "default",
        character_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ingests a wearable sample through the schema-guarded barrier."""
        from omnitwin.adapters.allostasis_adapter import get_allostasis_engine

        pid = persona_id or character_slug or "default"
        engine = get_allostasis_engine(pid)
        return engine.ingest_healthkit_sample(raw_sample)
