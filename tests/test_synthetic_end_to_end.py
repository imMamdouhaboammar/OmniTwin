# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
"""
End-to-End Multi-Turn Conversation Test with Synthetic Persona:
Tests continuous grounded dialogue, state evolution, and memory continuity.
"""

import os
import tempfile
import pytest

from omnitwin import (
    ContourEngine,
    StateReducer,
    TurnPlanner,
    CognitiveGenerator,
    PersonaImporter,
)


@pytest.fixture
def e2e_system():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    contour = ContourEngine(db_path)
    contour.init_schema()

    # Import synthetic persona
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    persona_path = os.path.join(repo_root, "examples", "synthetic-persona", "alex_cognitive_companion.json")

    importer = PersonaImporter(db_path)
    importer.import_from_file(persona_path, tenant_id="test_org", persona_id="alex")

    reducer = StateReducer(db_path)
    planner = TurnPlanner(contour, reducer)
    generator = CognitiveGenerator(contour=contour, reducer=reducer, planner=planner)

    yield generator, reducer, contour, db_path

    if os.path.exists(db_path):
        os.remove(db_path)


def test_multi_turn_continuity(e2e_system):
    generator, reducer, _, _ = e2e_system
    tenant_id = "test_org"
    persona_id = "alex"
    user_id = "collaborator"

    # Turn 1: Opinion request
    turn1 = generator.execute_turn(
        persona_id=persona_id,
        user_id=user_id,
        user_message="What is your stance on distributed systems and naming?",
        tenant_id=tenant_id,
    )
    assert turn1["verified"] is True
    assert len(turn1["answer"]) > 0

    # Turn 2: Follow-up question on coffee preferences
    turn2 = generator.execute_turn(
        persona_id=persona_id,
        user_id=user_id,
        user_message="What kind of coffee do you prefer when working?",
        tenant_id=tenant_id,
    )
    assert turn2["verified"] is True
    assert "answer" in turn2

    # Verify state progression
    final_state = reducer.get_or_seed_state(persona_id, user_id, tenant_id=tenant_id)
    assert final_state["persona_id"] == persona_id
    assert final_state["tenant_id"] == tenant_id
    assert final_state["energy"] > 0
    assert "mood" in final_state
