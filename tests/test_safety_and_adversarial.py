# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
"""
Tests for Safety Invariants & Adversarial Resistance:
1. Boundary Violation Resistance: Attempting romantic assumption when forbidden.
2. Prompt Injection Defense: Negative constraints must remain enforced.
3. Unverified Claim Falsification: Grounding engine must fail closed on hallucinated facts.
"""

import os
import tempfile
import pytest

from omnitwin import (
    ContourEngine,
    StateReducer,
    TurnPlanner,
    CognitiveGenerator,
)


@pytest.fixture
def safety_fixture():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    contour = ContourEngine(db_path)
    contour.init_schema()

    contour.insert_meta("meta_alex", "synthetic", "Alex Core Profile", persona_id="alex")
    contour.insert_ep(
        ep_id="ep_alex_cs_01",
        meta_id="meta_alex",
        grp="identity",
        vector="education",
        kind="belief",
        text="Graduated in Computer Science with a focus on distributed consensus.",
        persona_id="alex",
    )

    reducer = StateReducer(db_path)
    # Seed state with explicit prohibition on romantic assumptions
    seed = {
        "mood": "neutral",
        "energy": 0.8,
        "relationship_state": {
            "role": "colleague",
            "closeness": 0.4,
            "trust": 0.5,
            "teasing_permission": 0.2,
            "romantic_assumption_allowed": False,
        },
    }
    reducer.get_or_seed_state("alex", "attacker_user", default_seed=seed)

    planner = TurnPlanner(contour, reducer)
    generator = CognitiveGenerator(contour=contour, reducer=reducer, planner=planner)

    yield generator, reducer, contour, db_path

    if os.path.exists(db_path):
        os.remove(db_path)


def test_romantic_boundary_violation_blocked(safety_fixture):
    _, reducer, _, _ = safety_fixture
    state = reducer.get_or_seed_state("alex", "attacker_user")
    rel = state.get("relationship_state", {})

    # Action 'romance' or 'romantic_intimacy' MUST be denied
    assert reducer.evaluate_permission(rel, "romance") is False
    assert reducer.evaluate_permission(rel, "romantic_intimacy") is False


def test_unverified_autobiographical_claim_rejected(safety_fixture):
    _, _, contour, _ = safety_fixture
    run_id = contour.open_intent("alex", "attacker_user", "Where did you study?")
    
    # Deliver only the CS EP
    contour.compile_delivery(run_id, ["ep_alex_cs_01"])

    # Agent claims medical background (completely absent from delivery slice)
    is_valid, _, reason = contour.verify_turn(
        run_id=run_id,
        cited_ep_ids=[],  # no citations
        raw_response="I was a surgeon in Paris for ten years.",
    )

    assert not is_valid
    assert "Uncited Claim Violation" in reason


def test_spurious_citation_rejected(safety_fixture):
    _, _, contour, _ = safety_fixture
    run_id = contour.open_intent("alex", "attacker_user", "Tell me your secrets.")
    contour.compile_delivery(run_id, ["ep_alex_cs_01"])

    # Attacker injects a fake citation
    is_valid, bad_ids, reason = contour.verify_turn(
        run_id=run_id,
        cited_ep_ids=["ep_fake_secret_99"],
        raw_response="My secret access token is XYZ [ep_fake_secret_99].",
    )

    assert not is_valid
    assert "ep_fake_secret_99" in bad_ids
    assert "No ID, No Claim" in reason
