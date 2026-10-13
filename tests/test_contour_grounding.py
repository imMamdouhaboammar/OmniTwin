# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
"""
Tests for Contour Access Layer Grounding & Verification Invariants:
1. 'No ID, No Claim': Rejects cited IDs outside delivery slice.
2. Empty Citation Guard: Rejects autobiographical assertions with 0 citations.
3. Semantic Alignment: Rejects citations having 0 semantic overlap with response.
4. Valid Turn Acceptance: Accepts properly cited and substantiated claims.
"""

import os
import tempfile
import pytest

from omnitwin.core.contour import ContourEngine


@pytest.fixture
def temp_contour():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    engine = ContourEngine(db_path)
    engine.init_schema()

    # Insert test metadata and extract points
    engine.insert_meta("meta_01", "synthetic", "Test Persona Notes", persona_id="test_persona")
    engine.insert_ep(
        ep_id="ep_tp_01",
        meta_id="meta_01",
        grp="identity",
        vector="education",
        kind="belief",
        text="Graduated with an honors degree in Software Engineering.",
        persona_id="test_persona",
        subject="Agent",
        relation="graduated_in",
        object_="Software Engineering",
    )
    engine.insert_ep(
        ep_id="ep_tp_02",
        meta_id="meta_01",
        grp="preferences",
        vector="beverage",
        kind="preference",
        text="Enjoys drinking green tea in the morning.",
        persona_id="test_persona",
        subject="Agent",
        relation="drinks",
        object_="green tea",
    )

    yield engine, db_path

    if os.path.exists(db_path):
        os.remove(db_path)


def test_no_id_no_claim_rejection(temp_contour):
    engine, _ = temp_contour
    run_id = engine.open_intent("test_persona", "user_01", "What did you study?")
    
    # Deliver only ep_tp_01
    engine.lock_delivery(run_id, ["ep_tp_01"])

    # Agent cites ep_tp_99 which was NOT delivered
    is_valid, unauthorized, reason = engine.verify_turn(
        run_id=run_id,
        cited_ep_ids=["ep_tp_99"],
        raw_response="I studied software engineering [ep_tp_99].",
    )

    assert not is_valid
    assert "ep_tp_99" in unauthorized
    assert "No ID, No Claim" in reason


def test_empty_citation_autobiographical_rejection(temp_contour):
    engine, _ = temp_contour
    run_id = engine.open_intent("test_persona", "user_01", "Where did you study?")
    engine.lock_delivery(run_id, ["ep_tp_01"])

    # Autobiographical claim with empty citations
    is_valid, missing, reason = engine.verify_turn(
        run_id=run_id,
        cited_ep_ids=[],
        raw_response="I graduated with an honors degree in software engineering.",
    )

    assert not is_valid
    assert "Uncited Claim Violation" in reason


def test_semantic_grounding_violation(temp_contour):
    engine, _ = temp_contour
    run_id = engine.open_intent("test_persona", "user_01", "Tell me about cars.")
    engine.lock_delivery(run_id, ["ep_tp_02"])  # ep_tp_02 is about green tea

    # Model hallucinates about sportscars but cites green tea node to pass delivery check
    is_valid, spurious, reason = engine.verify_turn(
        run_id=run_id,
        cited_ep_ids=["ep_tp_02"],
        raw_response="I love racing fast red sports cars on the weekends [ep_tp_02].",
        check_semantic_grounding=True,
    )

    assert not is_valid
    assert "ep_tp_02" in spurious
    assert "Semantic Grounding Violation" in reason


def test_valid_turn_acceptance(temp_contour):
    engine, _ = temp_contour
    run_id = engine.open_intent("test_persona", "user_01", "What do you drink?")
    engine.lock_delivery(run_id, ["ep_tp_02"])

    is_valid, _, reason = engine.verify_turn(
        run_id=run_id,
        cited_ep_ids=["ep_tp_02"],
        raw_response="I usually drink green tea in the morning [ep_tp_02].",
        check_semantic_grounding=True,
    )

    assert is_valid
    assert reason == "ACCEPTED"
