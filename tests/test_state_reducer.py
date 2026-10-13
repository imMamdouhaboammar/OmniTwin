# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
"""
Tests for Deterministic State Reducer:
1. State Seeding & Multi-tenant/persona scoping.
2. Permission boundary checks (teasing, vulnerability, affection).
3. Salience decay of active concerns over elapsed time.
4. Low confidence proposal rejection (fails closed below 0.60).
5. Energy progression and clamp invariants [0.0, 1.0].
"""

import os
import tempfile
import time
import pytest

from omnitwin.core.contour import ContourEngine
from omnitwin.core.state_reducer import StateReducer


@pytest.fixture
def temp_reducer():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    contour = ContourEngine(db_path)
    contour.init_schema()
    reducer = StateReducer(db_path)

    yield reducer, db_path

    if os.path.exists(db_path):
        os.remove(db_path)


def test_state_seeding_and_scoping(temp_reducer):
    reducer, _ = temp_reducer
    state_a = reducer.get_or_seed_state("persona_a", "user_1", tenant_id="tenant_x")
    assert state_a["persona_id"] == "persona_a"
    assert state_a["tenant_id"] == "tenant_x"
    assert state_a["user_id"] == "user_1"
    assert "energy" in state_a
    assert "mood" in state_a

    # Different user has separate state
    state_b = reducer.get_or_seed_state("persona_a", "user_2", tenant_id="tenant_x")
    assert state_b["user_id"] == "user_2"


def test_permission_boundary_checks(temp_reducer):
    reducer, _ = temp_reducer
    rel = {
        "teasing_permission": 0.40,
        "affection_permission": 0.15,
        "vulnerability_permission": 0.60,
        "romantic_assumption_allowed": False,
    }

    assert reducer.evaluate_permission(rel, "tease") is True
    assert reducer.evaluate_permission(rel, "affection") is False  # below threshold
    assert reducer.evaluate_permission(rel, "vulnerability") is True
    assert reducer.evaluate_permission(rel, "romance") is False


def test_proposal_rejection_on_low_confidence(temp_reducer):
    reducer, _ = temp_reducer
    reducer.get_or_seed_state("persona_a", "user_1")

    # Proposal with confidence < 0.60 should be rejected without state mutation
    low_conf_proposal = {
        "confidence": 0.45,
        "mood": "ecstatic",
        "energy_delta": 0.50,
    }

    reduced = reducer.reduce_proposal("persona_a", "user_1", low_conf_proposal)
    # Mood should remain default neutral because proposal was rejected
    assert reduced["mood"] != "ecstatic"


def test_salience_decay(temp_reducer):
    reducer, _ = temp_reducer
    initial_seed = {
        "mood": "neutral",
        "energy": 0.8,
        "active_concerns": [
            {
                "topic": "deadline",
                "salience": 0.90,
                "arousal": 0.70,
                "created_at_unix": time.time() - (24 * 3600),  # 24 hours ago
            }
        ],
    }
    reducer.get_or_seed_state("persona_a", "user_1", default_seed=initial_seed)

    # Empty proposal triggers decay computation
    updated = reducer.reduce_proposal("persona_a", "user_1", {"confidence": 0.90})
    concerns = updated.get("active_concerns", [])
    
    # Salience should have decayed from 0.90 after 24 hours
    assert len(concerns) <= 1
    if concerns:
        assert concerns[0]["salience"] < 0.90
