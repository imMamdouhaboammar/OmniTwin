# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
"""
OmniTwin ↔ Rafiq Integration Design Example
============================================

STATUS: ARCHITECTURAL DESIGN — Not a verified runtime integration.

This module demonstrates how an application such as Rafiq could call OmniTwin's
cognitive engine to obtain grounded context before invoking its own LLM.

Uses only actual, tested OmniTwin public APIs with synthetic personas.
No dependency on the Rafiq codebase is introduced.

To run:
    cd /path/to/OmniTwin
    PYTHONPATH=src python3 examples/integrations/rafiq/design_contract.py
"""

import json
import sys
import os
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

from omnitwin import (
    ContourEngine,
    StateReducer,
    TurnPlanner,
    CognitivePromptCompiler,
)
from omnitwin.adapters.llm_provider import OfflineSimulatorProvider


# ---------------------------------------------------------------------------
# Synthetic persona data — no real person is represented
# ---------------------------------------------------------------------------
SYNTHETIC_EPISODES = [
    {
        "ep_id": "nova_ep_001",
        "group": "preferences",
        "vector": "technology",
        "kind": "belief",
        "text": "Prefers clear, modular code architecture over clever one-liners.",
    },
    {
        "ep_id": "nova_ep_002",
        "group": "preferences",
        "vector": "collaboration",
        "kind": "preference",
        "text": "Values asynchronous communication for complex technical discussions.",
    },
    {
        "ep_id": "nova_ep_003",
        "group": "episodic",
        "vector": "project_memory",
        "kind": "anecdote",
        "text": "Worked with the user on designing a REST API schema last week.",
    },
]


# ---------------------------------------------------------------------------
# Simulated Rafiq session — Rafiq owns auth, user identity, and UI
# ---------------------------------------------------------------------------
class SimulatedRafiqSession:
    """
    Represents the application-layer context that Rafiq would provide.
    OmniTwin never manages user authentication or UI state.
    """

    def __init__(self, tenant_id: str, persona_id: str, user_id: str):
        self.tenant_id = tenant_id
        self.persona_id = persona_id
        self.user_id = user_id

    def as_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "persona_id": self.persona_id,
            "user_id": self.user_id,
        }


# ---------------------------------------------------------------------------
# OmniTwin cognitive provider — wraps OmniTwin's real Python API
# In production this would be a gRPC or REST client
# ---------------------------------------------------------------------------
class OmniTwinCognitiveProvider:
    """
    OmniTwin integration layer from Rafiq's perspective.

    In production: call the gRPC CognitiveEngineService (port 50051).
    This class uses direct in-process calls for local testability.
    """

    def __init__(self, db_path: Optional[str] = None):
        import tempfile
        # Use a shared temp file so all OmniTwin components read the same data.
        # ":memory:" creates isolated per-connection databases in SQLite.
        if db_path is None:
            self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
            db_path = self._tmp.name
        self.db_path = db_path
        self.contour = ContourEngine(db_path)
        self.contour.init_schema()
        self.reducer = StateReducer(db_path)
        self.planner = TurnPlanner(self.contour, self.reducer)
        self.compiler = CognitivePromptCompiler(self.contour, self.reducer, self.planner)

    def seed_persona_memory(
        self,
        persona_id: str,
        tenant_id: str,
        episodes: list,
    ) -> int:
        """
        Seed synthetic episodic memories for a persona.
        In a Rafiq integration, this step would import from the persona's
        knowledge base rather than hardcoded episode dicts.
        """
        meta_id = f"meta_{persona_id}_base"
        self.contour.insert_meta(
            meta_id=meta_id,
            source_type="synthetic",
            title=f"{persona_id.title()} Synthetic Knowledge Base",
            persona_id=persona_id,
            tenant_id=tenant_id,
        )
        count = 0
        for ep in episodes:
            self.contour.insert_ep(
                ep_id=ep["ep_id"],
                meta_id=meta_id,
                grp=ep["group"],
                vector=ep["vector"],
                kind=ep["kind"],
                text=ep["text"],
                persona_id=persona_id,
                tenant_id=tenant_id,
            )
            count += 1
        return count

    def get_cognitive_context(
        self,
        session: SimulatedRafiqSession,
        user_message: str,
    ) -> dict:
        """
        Main integration entry point.

        Returns a compiled cognitive context pack:
        - context (XML): Bounded evidence slice (< 450 tokens)
        - cited_ids: Evidence IDs referenced
        - run_id: Audit ticket for verification step
        - social_move: Planned conversational move
        - bubble_count: Suggested message bubble count
        - allostatic_load: Cognitive fatigue signal 0.0–1.0

        Rafiq uses the context XML when constructing its LLM prompt.
        OmniTwin does NOT call Rafiq's LLM — that remains Rafiq's responsibility.
        """
        result = self.compiler.compile_ai_context(
            persona_id=session.persona_id,
            user_id=session.user_id,
            user_message=user_message,
            tenant_id=session.tenant_id,
        )
        delivered_eps = result.get("delivered_eps", [])
        cited_ids = [ep["id"] for ep in delivered_eps if "id" in ep]
        autonomic = result.get("autonomic_state", {})
        return {
            "context_xml": result.get("context_prompt", ""),
            "delivered_eps": delivered_eps,
            "cited_ids": cited_ids,
            "run_id": result.get("run_id", ""),
            "social_move": result.get("social_move", ""),
            "bubble_count": result.get("bubble_count", 1),
            "estimated_tokens": result.get("estimated_tokens", 0.0),
            "allostatic_load": autonomic.get("allostatic_load", 0.0),
            "episode_count": len(delivered_eps),
        }

    def verify_grounding(
        self,
        run_id: str,
        cited_ids: list,
        generated_response: str,
    ) -> dict:
        """
        Optional post-generation grounding step.

        After Rafiq's LLM generates a response, the application may send it
        back to OmniTwin for verification against the delivery slice locked
        at planning time (identified by run_id).
        """
        verified, violations, message = self.contour.verify_turn(
            run_id=run_id,
            cited_ep_ids=cited_ids,
            raw_response=generated_response,
        )
        return {"verified": verified, "violations": violations, "message": message}


# ---------------------------------------------------------------------------
# Simulate the full integration turn
# ---------------------------------------------------------------------------
def simulate_rafiq_omnitwin_turn() -> bool:
    print("=" * 62)
    print("  OmniTwin ↔ Rafiq Integration Design Contract — v0.1.0")
    print("  STATUS: Architectural design using real OmniTwin APIs")
    print("=" * 62)

    # Step 1: Rafiq session
    session = SimulatedRafiqSession(
        tenant_id="rafiq_demo_tenant",
        persona_id="nova_assistant",
        user_id="demo_user_42",
    )
    print(f"\n[1] Rafiq session established: {json.dumps(session.as_dict(), indent=4)}")

    # Step 2: OmniTwin initialization & persona memory seeding
    omnitwin = OmniTwinCognitiveProvider()
    count = omnitwin.seed_persona_memory(
        persona_id=session.persona_id,
        tenant_id=session.tenant_id,
        episodes=SYNTHETIC_EPISODES,
    )
    print(f"[2] {count} synthetic episodes seeded into OmniTwin memory")

    # Step 3: Incoming user message
    user_message = "What's your take on API design patterns for collaboration tools?"
    print(f"\n[3] User message: {user_message!r}")

    # Step 4: Rafiq calls OmniTwin for cognitive context
    ctx = omnitwin.get_cognitive_context(session, user_message)
    print("\n[4] OmniTwin cognitive context returned:")
    print(f"    • Run ID          : {ctx['run_id']}")
    print(f"    • Episodes cited  : {ctx['episode_count']}")
    print(f"    • Cited IDs       : {ctx['cited_ids']}")
    print(f"    • Social move     : {ctx['social_move']}")
    print(f"    • Bubble count    : {ctx['bubble_count']}")
    print(f"    • Allostatic load : {ctx['allostatic_load']:.2f}")
    xml_preview = ctx["context_xml"][:300] if ctx["context_xml"] else "(no context produced)"
    print(f"\n    Context XML (≤300 chars):\n    {xml_preview}{'...' if len(ctx['context_xml']) > 300 else ''}")

    # Step 5: Rafiq's LLM generates response
    # In production: Rafiq calls Gemini API / Vertex AI with context_xml injected.
    # Here we use OmniTwin's offline simulator only as a demonstration stand-in.
    print("\n[5] Rafiq LLM generates response (offline simulator stand-in)")
    print("    In production: Rafiq calls Gemini API / Vertex AI here")
    provider = OfflineSimulatorProvider()
    system_prompt = ctx["context_xml"] or "You are a helpful AI assistant."
    llm_response = provider.generate(
        system_prompt=system_prompt,
        user_message=user_message,
    )
    print(f"\n    Generated: {llm_response!r}")

    # Step 6: Optional grounding verification
    print("\n[6] Rafiq sends response to OmniTwin for grounding verification")
    verification = omnitwin.verify_grounding(
        run_id=ctx["run_id"],
        cited_ids=ctx["cited_ids"],
        generated_response=llm_response,
    )
    print(f"    Verified  : {verification['verified']}")
    print(f"    Message   : {verification['message']}")

    # Clean up temporary SQLite database if created
    if hasattr(omnitwin, "_tmp") and os.path.exists(omnitwin.db_path):
        os.unlink(omnitwin.db_path)

    print("\n" + "=" * 62)
    print("  Design contract executed successfully.")
    print("  See docs/integrations/rafiq.md for the full specification.")
    print("=" * 62)
    return True


if __name__ == "__main__":
    success = simulate_rafiq_omnitwin_turn()
    sys.exit(0 if success else 1)
