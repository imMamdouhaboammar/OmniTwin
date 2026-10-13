# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
"""
Tests for Biometric Signal Processing & Conversational Pacing:
1. RMSSD calculation from R-R series.
2. Baevsky Stress Index calculation.
3. Empty/sparse series handling without crashes.
4. Non-clinical disclaimer presence in docstring and module metadata.
"""

from omnitwin.core.biometrics import BiometricProcessor
import omnitwin.core.biometrics as biometrics_mod


def test_rmssd_calculation():
    processor = BiometricProcessor()
    # Constant RR intervals -> 0 variance -> RMSSD = 0
    assert processor.compute_rmssd([800.0, 800.0, 800.0]) == 0.0

    # Alternating intervals: diffs are 50ms each -> RMSSD should be 50.0
    rr_series = [800.0, 850.0, 800.0, 850.0, 800.0]
    rmssd = processor.compute_rmssd(rr_series)
    assert abs(rmssd - 50.0) < 1e-4


def test_baevsky_stress_index():
    processor = BiometricProcessor()
    # Realistic 20-sample RR series around 800ms
    rr_series = [
        800, 820, 790, 810, 800, 830, 780, 805, 815, 795,
        800, 825, 785, 810, 800, 835, 775, 810, 805, 790
    ]
    result = processor.compute_baevsky_stress_index(rr_series)

    assert "stress_index" in result
    assert result["stress_index"] > 0
    assert "mode_seconds" in result
    assert "mode_amplitude_percent" in result


def test_sparse_or_empty_series_handling():
    processor = BiometricProcessor()
    # Empty
    assert processor.compute_rmssd([]) == 0.0
    sparse_res = processor.compute_baevsky_stress_index([])
    assert sparse_res["stress_index"] == 50.0  # default fallback

    # Single element
    assert processor.compute_rmssd([800.0]) == 0.0


def test_non_clinical_disclaimer_present():
    assert "NON-CLINICAL" in biometrics_mod.__doc__
    assert "NON-MEDICAL" in biometrics_mod.__doc__
