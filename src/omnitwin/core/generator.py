# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

from omnitwin.core.contour import ContourEngine
from omnitwin.core.state_reducer import StateReducer
from omnitwin.core.turn_planner import TurnPlanner
from omnitwin.core.context_compiler import CognitivePromptCompiler
from omnitwin.adapters.llm_provider import BaseLLMProvider, OfflineSimulatorProvider, get_default_provider

logger = logging.getLogger("OmniTwin.CognitiveGenerator")


class CognitiveGenerator:
    """
    Executes grounded turn generation under strict contour constraints.
    - Compiles bounded JIT prompt with dynamic state, permissions, delivered EPs, and anti-slop rules.
    - Invokes LLM Provider (PI Gateway, OpenRouter, Vertex/Gemini, or offline simulator).
    - Extracts cited EP IDs from generated response.
    - Enforces 'No ID, No Claim' and semantic claim grounding via contour.verify_turn.
    - Formulates state mutation proposal and invokes state_reducer.
    """

    def __init__(
        self,
        contour: ContourEngine,
        reducer: StateReducer,
        planner: TurnPlanner,
        provider: Optional[BaseLLMProvider] = None,
    ):
        self.contour = contour
        self.reducer = reducer
        self.planner = planner
        self.compiler = CognitivePromptCompiler(self.contour, self.reducer, self.planner)
        self.provider = provider if provider is not None else get_default_provider()

    def _extract_citations(self, text: str) -> List[str]:
        """Extracts cited EP identifiers from text pattern: [ep_xxx] or (ep_xxx)"""
        pattern = r"\[(ep_[a-zA-Z0-9_]+)\]|\((ep_[a-zA-Z0-9_]+)\)"
        matches = re.findall(pattern, text)
        cited = []
        for m in matches:
            cited.append(m[0] if m[0] else m[1])
        return list(dict.fromkeys(cited))

    def _is_arabic(self, text: str) -> bool:
        """Detects if text contains Arabic characters."""
        return bool(re.search(r"[\u0600-\u06FF]", text))

    def _simulate_grounded_response(
        self,
        social_move: str,
        user_message: str,
        delivered_eps: List[Dict[str, Any]],
        state: Dict[str, Any],
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        """
        Deterministic, offline dialogue generation fallback.
        Produces character-grounded responses cited from delivered EPs.
        Supports both Arabic and English naturally.
        """
        cited_ids = []
        proposal = {
            "confidence": 0.85,
            "energy_delta": -0.02,
            "mood": state.get("mood", "neutral"),
        }

        primary_ep = delivered_eps[0] if delivered_eps else None
        is_ar = self._is_arabic(user_message) or (primary_ep and self._is_arabic(primary_ep.get("text", "")))

        if is_ar:
            if social_move == "check_in":
                text = "أهلاً، أخبارك إيه؟ لعلك بخير."
                if primary_ep:
                    cited_ids.append(primary_ep["id"])
                    text = f"أهلاً، أخبارك إيه؟ {primary_ep['text']} [{primary_ep['id']}]."
                proposal["mood"] = "good"
            elif social_move == "tease":
                text = "شايفك بتهزر! ماشي يا سيدي."
                proposal["mood"] = "playful"
                proposal["energy_delta"] = 0.05
            elif social_move == "minimal_presence":
                text = "طاقتي منخفضة شوية دلوقتي، هكلمك أول ما أفضى."
                proposal["mood"] = "tired"
                proposal["energy_delta"] = -0.05
            elif social_move == "give_opinion":
                if primary_ep:
                    cited_ids.append(primary_ep["id"])
                    text = f"رأيي في الموضوع ده: {primary_ep['text']} [{primary_ep['id']}]."
                else:
                    text = "شايف إنك تفكر فيها بهدوء الأول."
                proposal["add_concern"] = "decision_making"
            elif social_move == "practical_help":
                if primary_ep:
                    cited_ids.append(primary_ep["id"])
                    text = f"بخصوص ده، الحل العملي: {primary_ep['text']} [{primary_ep['id']}]."
                else:
                    text = "قولي التفاصيل ونرتبها سوا خطوة بخطوة."
                proposal["add_thread"] = "ongoing_problem"
            else:
                if primary_ep:
                    cited_ids.append(primary_ep["id"])
                    text = f"تمام، {primary_ep['text']} [{primary_ep['id']}]."
                else:
                    text = "تمام، سامعك ومعاك."
        else:
            if social_move == "check_in":
                text = "Hey there, good to hear from you."
                if primary_ep:
                    cited_ids.append(primary_ep["id"])
                    text = f"Hey there! {primary_ep['text']} [{primary_ep['id']}]."
                proposal["mood"] = "good"
            elif social_move == "tease":
                text = "Look who decided to check in!"
                proposal["mood"] = "playful"
                proposal["energy_delta"] = 0.05
            elif social_move == "minimal_presence":
                text = "A bit drained right now, let's catch up shortly."
                proposal["mood"] = "tired"
                proposal["energy_delta"] = -0.05
            elif social_move == "give_opinion":
                if primary_ep:
                    cited_ids.append(primary_ep["id"])
                    text = f"From my perspective, {primary_ep['text']} [{primary_ep['id']}]."
                else:
                    text = "I'd suggest taking a beat and considering the long-term impact."
                proposal["add_concern"] = "decision_making"
            elif social_move == "practical_help":
                if primary_ep:
                    cited_ids.append(primary_ep["id"])
                    text = f"Here is how I approach this: {primary_ep['text']} [{primary_ep['id']}]."
                else:
                    text = "Share the exact details and let's work through it step by step."
                proposal["add_thread"] = "ongoing_problem"
            else:
                if primary_ep:
                    cited_ids.append(primary_ep["id"])
                    text = f"Got it. {primary_ep['text']} [{primary_ep['id']}]."
                else:
                    text = "Understood, I am with you."

        return text, cited_ids, proposal

    def execute_turn(
        self,
        persona_id: str,
        user_id: str,
        user_message: str,
        tenant_id: str = "default",
        character_slug: Optional[str] = None,
        llm_generate_fn: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Executes an end-to-end cognitive turn:
        1. Context Compilation
        2. LLM or Simulator Generation
        3. Contour Grounding Verification ("No ID, No Claim")
        4. State Reduction & Allostasis Update
        """
        pid = persona_id or character_slug or "default"

        # 1. Compile minimal sufficient context pack (< 450 tokens)
        pack = self.compiler.compile_ai_context(pid, user_id, user_message, tenant_id=tenant_id)
        run_id = pack["run_id"]
        social_move = pack["social_move"]
        delivered_eps = pack["delivered_eps"]
        autonomic_state = pack.get("autonomic_state", {})

        current_state = self.reducer.get_or_seed_state(pid, user_id, tenant_id=tenant_id)
        active_provider_name = getattr(self.provider, "name", "unknown")

        raw_answer: str = ""
        cited_ids: List[str] = []
        proposal: Dict[str, Any] = {
            "confidence": 0.85,
            "energy_delta": -0.01,
            "mood": current_state.get("mood", "neutral"),
        }
        if social_move == "tease":
            proposal["mood"] = "playful"
            proposal["energy_delta"] = 0.05
        elif social_move == "check_in":
            proposal["mood"] = "good"
        elif social_move == "minimal_presence":
            proposal["mood"] = "tired"
            proposal["energy_delta"] = -0.05
        elif social_move == "give_opinion":
            proposal["add_concern"] = "decision_making"
        elif social_move == "practical_help":
            proposal["add_thread"] = "ongoing_problem"

        # 2. Generation via mock function, offline simulator, or live LLM provider
        if llm_generate_fn is not None:
            raw_answer = str(llm_generate_fn(user_message)).strip()
            cited_ids = self._extract_citations(raw_answer)
            active_provider_name = "custom_fn"
        elif isinstance(self.provider, OfflineSimulatorProvider):
            raw_answer, cited_ids, proposal = self._simulate_grounded_response(
                social_move, user_message, delivered_eps, current_state
            )
        else:
            system_prompt = f"""You are the cognitive digital twin of {pid}.
You must operate strictly under the cognitive state and negative constraints provided below.

{pack['context_prompt']}

Reply naturally as {pid} in conversational messages.
When expressing facts, beliefs, or personal opinions, cite the authorizing extract point ID like [ep_xxx].
Never break character, never act as a generic AI assistant."""

            try:
                raw_response = self.provider.generate(system_prompt, user_message)
                raw_answer = raw_response.strip()
                cited_ids = self._extract_citations(raw_answer)

                if hasattr(self.provider, "last_used_provider") and self.provider.last_used_provider:
                    active_provider_name = self.provider.last_used_provider

            except Exception as e:
                logger.warning(f"Live provider '{active_provider_name}' failed: {e}. Falling back to grounded simulator.")
                raw_answer, cited_ids, proposal = self._simulate_grounded_response(
                    social_move, user_message, delivered_eps, current_state
                )
                active_provider_name = "offline-simulator (fallback)"

        # 3. Enforce 'No ID, No Claim' and semantic claim verification
        ok, missing_ids, reason = self.contour.verify_turn(
            run_id=run_id,
            cited_ep_ids=cited_ids,
            raw_response=raw_answer,
            check_semantic_grounding=True,
        )

        if not ok:
            is_ar = self._is_arabic(user_message)
            safe_answer = "مش هقدر أفتي في دي دلوقتي." if is_ar else "I cannot verify or substantiate that claim right now."
            self.contour.record_answer(run_id, safe_answer)
            return {
                "run_id": run_id,
                "tenant_id": tenant_id,
                "persona_id": pid,
                "character_slug": pid,
                "user_id": user_id,
                "verified": False,
                "rejection_reason": reason,
                "missing_citations": missing_ids,
                "answer": safe_answer,
                "raw_unverified_answer": raw_answer,
                "social_move": "minimal_presence",
                "state": current_state,
                "provider": active_provider_name,
                "delivered_count": len(delivered_eps),
            }

        # 4. Clean citation tags for natural user delivery
        clean_bubbles_text = re.sub(r"\s*\[ep_[a-zA-Z0-9_]+\]|\s*\(ep_[a-zA-Z0-9_]+\)", "", raw_answer).strip()
        self.contour.record_answer(run_id, clean_bubbles_text)

        # 5. Record software conversation load in Allostasis Engine
        from omnitwin.adapters.allostasis_adapter import get_allostasis_engine
        allostasis_engine = get_allostasis_engine(pid)
        prompt_tokens = max(10, len(user_message.split()) * 2 + 50)
        completion_tokens = max(5, len(clean_bubbles_text.split()) * 2)
        allostasis_engine.record_chat_turn(prompt_tokens, completion_tokens)
        autonomic_state = allostasis_engine.get_autonomic_state()

        if "conversation_appetite" not in proposal:
            proposal["conversation_appetite"] = autonomic_state.get("conversation_appetite", "medium")

        # 6. Deterministically reduce state mutations
        updated_state = self.reducer.reduce_proposal(pid, user_id, proposal, tenant_id=tenant_id)

        return {
            "run_id": run_id,
            "tenant_id": tenant_id,
            "persona_id": pid,
            "character_slug": pid,
            "user_id": user_id,
            "verified": True,
            "answer": clean_bubbles_text,
            "cited_ids": cited_ids,
            "social_move": social_move,
            "state": updated_state,
            "delivered_count": len(delivered_eps),
            "provider": active_provider_name,
            "autonomic_state": autonomic_state,
        }
