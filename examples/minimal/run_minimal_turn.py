#!/usr/bin/env python3
# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
"""
Minimal OmniTwin Example: Run a Cognitive Turn in Under 20 Lines
================================================================
Demonstrates the quickest way to initialize an OmniTwin database,
register a memory, and execute a grounded turn.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from omnitwin import ContourEngine, StateReducer, TurnPlanner, CognitiveGenerator

# 1. Initialize local SQLite cognitive database
db_path = "omnitwin_minimal.db"
contour = ContourEngine(db_path)
contour.init_schema()

# 2. Insert a grounded factual extract point (EP)
contour.insert_meta("meta_alex", "interview", "Systems Discussion", persona_id="alex")
contour.insert_ep(
    ep_id="ep_alex_db_01",
    meta_id="meta_alex",
    grp="architecture",
    vector="databases",
    kind="belief",
    text="Prefers local-first SQLite architectures with deterministic state machines.",
    persona_id="alex",
    subject="Alex",
    relation="advocates",
    object_="SQLite",
)

# 3. Create the cognitive engine and execute turn
reducer = StateReducer(db_path)
planner = TurnPlanner(contour, reducer)
generator = CognitiveGenerator(contour=contour, reducer=reducer, planner=planner)

result = generator.execute_turn(
    persona_id="alex",
    user_id="colleague",
    user_message="What database architecture do you recommend for local agents?",
)

print(f"Twin Reply: {result['answer']}")
print(f"Verified Grounding: {result['verified']}")
print(f"Cited EPs: {result.get('cited_ids')}")

# Clean up temporary database
if os.path.exists(db_path):
    os.remove(db_path)
