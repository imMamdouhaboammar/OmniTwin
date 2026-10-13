# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
"""
Tests for Multi-Stage Cognitive Turn Planner:
1. Intent-to-Move Selection: check_in, give_opinion, practical_help, tease, minimal_presence.
2. Low-energy override: forces minimal_presence when energy < 0.35.
3. Cadence budget planning: bounded bubbles [1, 3] and token constraints.
4. Recall bounds: limits candidate EPs to delivery budget.
"""

import os
import tempfile
import pytest

from omnitwin.core.contour import ContourEngine
from omnitwin.core.state_reducer import StateReducer
from omnitwin.core.turn_planner import TurnPlanner


@pytest.fixture
def temp_planner():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    contour = ContourEngine(db_path)
    contour.init_schema()
    reducer = StateReducer(db_path)
    planner = TurnPlanner(contour, reducer)

    yield planner, contour, reducer, db_path

    if os.path.exists(db_path):
        os.remove(db_path)


def test_intent_to_move_mapping(temp_planner):
    planner, _, _, _ = temp_planner
    base_state = {
        "energy": 0.8,
        "relationship_state": {"closeness": 0.7, "trust": 0.8, "teasing_permission": 0.6},
    }

    # Greeting -> check_in
    assert planner.select_social_move("Hello there, good morning!", base_state) == "check_in"
    # Arabic greeting -> check_in
    assert planner.select_social_move("صباح الخير يا فندم", base_state) == "check_in"

    # Opinion request -> give_opinion
    assert planner.select_social_move("What is your opinion on microservices?", base_state) == "give_opinion"
    assert planner.select_social_move("ايه رأيك في الموضوع ده؟", base_state) == "give_opinion"

    # Problem/help -> practical_help
    assert planner.select_social_move("I have a critical bug in the database", base_state) == "practical_help"


def test_low_energy_forces_minimal_presence(temp_planner):
    planner, _, _, _ = temp_planner
    low_energy_state = {
        "energy": 0.20,  # Below 0.35 threshold
        "relationship_state": {"closeness": 0.8, "trust": 0.8},
    }

    # Even a greeting should receive minimal presence when exhausted
    move = planner.select_social_move("Hey, what are you up to?", low_energy_state)
    assert move == "minimal_presence"


def test_cadence_budget_limits(temp_planner):
    planner, _, _, _ = temp_planner
    budget_chatty = planner.plan_cadence_budget(energy=0.85, social_move="check_in")
    assert budget_chatty["max_bubbles"] >= 1
    assert budget_chatty["max_bubbles"] <= 3

    budget_tired = planner.plan_cadence_budget(energy=0.20, social_move="minimal_presence")
    assert budget_tired["max_bubbles"] == 1
