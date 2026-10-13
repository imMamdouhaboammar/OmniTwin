#!/usr/bin/env python3
# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
"""
Example: Ingest a Synthetic Persona Pack and Execute Grounded Turns
===================================================================
Demonstrates loading a persona pack, inspecting the extracted nodes,
and executing grounded cognitive turns with the OfflineSimulatorProvider.
"""

import os
import sys
import tempfile

# Ensure src is on Python path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from omnitwin import (
    ContourEngine,
    StateReducer,
    TurnPlanner,
    CognitiveGenerator,
    PersonaImporter,
    HierarchicalMemory,
)


def main():
    print("=" * 60)
    print("OmniTwin Synthetic Persona Ingest & Query Example")
    print("=" * 60)

    persona_path = os.path.join(
        REPO_ROOT, "examples", "synthetic-persona", "alex_cognitive_companion.json"
    )
    if not os.path.exists(persona_path):
        print(f"Error: Persona pack not found at {persona_path}", file=sys.stderr)
        sys.exit(1)

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        print(f"\n[1] Initializing database at: {db_path}")
        contour = ContourEngine(db_path)
        contour.init_schema()

        print("[2] Importing synthetic persona 'Alex Rivers'...")
        importer = PersonaImporter(db_path)
        count = importer.import_from_file(persona_path, tenant_id="default", persona_id="alex")
        print(f"    Successfully indexed {count} cognitive nodes.")

        print("\n[3] Setting up Cognitive Core components...")
        memory = HierarchicalMemory(db_path)
        reducer = StateReducer(db_path)
        planner = TurnPlanner(contour, reducer)
        generator = CognitiveGenerator(contour=contour, reducer=reducer, planner=planner)

        test_queries = [
            "Hey Alex, good morning! How are you doing today?",
            "What kind of coffee do you like best?",
            "What did you study back at university?",
        ]

        print("\n[4] Executing Grounded Turns:")
        for idx, query in enumerate(test_queries, 1):
            print(f"\n--- Turn {idx} ---")
            print(f"User: \"{query}\"")
            
            result = generator.execute_turn(
                persona_id="alex",
                user_id="collaborator",
                user_message=query,
                tenant_id="default",
            )

            print(f"Twin: {result.get('answer')}")
            print(f"Contour Verified:   {result.get('verified')}")
            print(f"Cited Extract Pts:  {result.get('cited_ids')}")
            print(f"Social Move Chosen: {result.get('social_move')}")
            if not result.get("verified"):
                print(f"Rejection Reason:   {result.get('rejection_reason')}")

        print("\n[5] Inspecting Updated Relational State:")
        final_state = reducer.get_or_seed_state("alex", "collaborator", tenant_id="default")
        rel = final_state.get("relationship_state", {})
        print(f"    Mood: {final_state.get('mood')} | Energy: {final_state.get('energy'):.2f}")
        print(f"    Closeness: {rel.get('closeness'):.2f} | Trust: {rel.get('trust'):.2f}")
        print("\nSuccess! Grounded cognitive continuity loop completed without errors.")

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    main()
