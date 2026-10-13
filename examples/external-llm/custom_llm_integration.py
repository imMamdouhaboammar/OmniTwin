#!/usr/bin/env python3
# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
"""
Example: Plugging an External LLM into OmniTwin
===============================================
Demonstrates how to plug any external LLM (OpenAI, Anthropic Claude, local Ollama, vLLM)
into the OmniTwin Cognitive Continuity Engine while maintaining strict 'No ID, No Claim'
grounding and contour verification.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from omnitwin import ContourEngine, StateReducer, TurnPlanner, CognitiveGenerator
from omnitwin.adapters.llm_provider import BaseLLMProvider


class CustomMockExternalLLM(BaseLLMProvider):
    """
    Example custom provider simulating an LLM API call.
    In real deployments, you would call OpenAI, Anthropic, or Ollama here.
    """

    @property
    def name(self) -> str:
        return "custom-external-llm"

    def is_available(self) -> bool:
        return True

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
        print("\n[LLM Provider Invocation]")
        print(f"System Prompt Length: {len(system_prompt)} chars")
        print(f"User Message: {user_prompt}")
        
        # An external LLM generates a response citing the delivered node:
        return "Based on my background in distributed systems, I strongly prefer local SQLite for durability [ep_alex_db_01]."


def main():
    db_path = "omnitwin_custom_llm.db"
    try:
        contour = ContourEngine(db_path)
        contour.init_schema()

        # Seed grounded node
        contour.insert_meta("meta_01", "profile", "Work History", persona_id="alex")
        contour.insert_ep(
            ep_id="ep_alex_db_01",
            meta_id="meta_01",
            grp="beliefs",
            vector="databases",
            kind="belief",
            text="Prefers local SQLite for durability and embedded deployment.",
            persona_id="alex",
        )

        reducer = StateReducer(db_path)
        planner = TurnPlanner(contour, reducer)

        # Wire custom LLM provider
        custom_provider = CustomMockExternalLLM()
        generator = CognitiveGenerator(
            contour=contour,
            reducer=reducer,
            planner=planner,
            provider=custom_provider,
        )

        print("Executing Turn with Custom LLM Provider...")
        result = generator.execute_turn(
            persona_id="alex",
            user_id="user_42",
            user_message="What database do you recommend?",
        )

        print("\n--- Final Turn Result ---")
        print(f"Answer: {result['answer']}")
        print(f"Verified: {result['verified']}")
        print(f"Citations: {result['cited_ids']}")
        print(f"Active Provider: {result['provider']}")
        print(f"Allostatic Energy: {result['state']['energy']:.2f}")

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    main()
