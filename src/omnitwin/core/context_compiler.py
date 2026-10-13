# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from omnitwin.core.contour import ContourEngine
from omnitwin.core.state_reducer import StateReducer
from omnitwin.core.turn_planner import TurnPlanner


class CognitivePromptCompiler:
    """
    Compiles a high-density, token-efficient Cognitive Context Pack (under 450 tokens)
    specifically designed for LLM consumption without persona collapse, attention dilution,
    or assistant leakage.
    """

    def __init__(self, contour: ContourEngine, reducer: StateReducer, planner: TurnPlanner):
        self.contour = contour
        self.reducer = reducer
        self.planner = planner

    def compile_ai_context(
        self,
        persona_id: str,
        user_id: str,
        user_message: str,
        tenant_id: str = "default",
        format_style: str = "xml",
        character_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Builds the minimal, sufficient cognitive state slice for the AI to consume.
        Contains:
        1. Autonomic & Affective Frame (energy, mood, appetite)
        2. Relational Permissions (closeness, teasing allowed, romantic boundary)
        3. Selected Social Move & Bubble Budget
        4. JIT Epistemic Delivery Slice (the ONLY authorized facts the AI may claim)
        5. Negative Behavioral Constraints (Anti-Slop directives)
        """
        pid = persona_id or character_slug or "default"

        # Plan turn and fetch verified candidates
        plan = self.planner.plan_turn(pid, user_id, user_message, tenant_id=tenant_id)
        run_id = plan["run_id"]
        social_move = plan["social_move"]
        bubble_count = plan["bubble_count"]
        delivery = plan["delivery"]
        delivered_eps = delivery["delivered_eps"]
        dynamic_state = plan["current_state"]
        rel_state = dynamic_state.get("relationship_state", {})

        # Build authorized EP summaries
        ep_blocks = []
        for ep in delivered_eps:
            ep_blocks.append(f"[{ep['id']}] ({ep.get('grp', 'core')}) {ep.get('text', '')}")

        # Active concerns & threads
        concerns = [c.get("topic") for c in dynamic_state.get("active_concerns", []) if isinstance(c, dict)]
        threads = dynamic_state.get("active_threads", [])

        from omnitwin.adapters.allostasis_adapter import get_allostasis_engine
        allostasis_engine = get_allostasis_engine(pid)
        autonomic = allostasis_engine.get_autonomic_state()
        pacing_constraint = allostasis_engine.get_pacing_constraint()
        pacing_line = f"    {pacing_constraint}\n" if pacing_constraint else ""

        # Format as high-salience XML context block
        if format_style == "xml":
            context_text = f"""<cognitive_digital_twin persona="{pid}" tenant="{tenant_id}">
  <run_id>{run_id}</run_id>
  <autonomic_state>
    <mood>{dynamic_state.get('mood', 'neutral')}</mood>
    <physical_energy>{dynamic_state.get('energy', 0.7):.2f}</physical_energy>
    <conversational_appetite>{dynamic_state.get('conversation_appetite', 'medium')}</conversational_appetite>
    <allostatic_load>{autonomic.get('allostatic_load', 0.0):.2f}</allostatic_load>
    <is_depleted>{str(autonomic.get('is_depleted', False)).lower()}</is_depleted>
    <active_mode>{dynamic_state.get('current_mode', 'casual')}</active_mode>
  </autonomic_state>
  
  <relational_boundary user="{user_id}">
    <role>{rel_state.get('role', 'interlocutor')}</role>
    <trust_score>{rel_state.get('trust', 0.5):.2f}</trust_score>
    <teasing_permitted>{str(rel_state.get('teasing_permission', 0.0) >= 0.65).lower()}</teasing_permitted>
    <romantic_assumption_permitted>{str(rel_state.get('romantic_assumption_allowed', False)).lower()}</romantic_assumption_permitted>
  </relational_boundary>

  <strategic_move>
    <assigned_social_move>{social_move}</assigned_social_move>
    <max_bubble_count>{bubble_count}</max_bubble_count>
  </strategic_move>

  <authorized_epistemic_grounding notice="No ID, No Claim. Only cite from this list">
{chr(10).join(f'    <point id="{ep["id"]}">{ep["text"]}</point>' for ep in delivered_eps)}
  </authorized_epistemic_grounding>

  <active_mental_threads>
    <concerns>{', '.join(concerns) if concerns else 'none'}</concerns>
    <threads>{', '.join(threads) if threads else 'none'}</threads>
  </active_mental_threads>

  <negative_constraints>
    - Never apologize repeatedly or say "How can I help you today?".
    - Never summarize the other person's emotions back to them.
    - Never assume romantic intimacy unless explicitly permitted.
    - Maintain conversational authenticity without generic AI assistant clichés.
    - Respect character tone, persona knowledge boundaries, and language conventions.
{pacing_line}  </negative_constraints>
</cognitive_digital_twin>"""
        else:
            context_text = json.dumps(
                {
                    "run_id": run_id,
                    "persona_id": pid,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "state": dynamic_state,
                    "autonomic": autonomic,
                    "social_move": social_move,
                    "bubble_count": bubble_count,
                    "delivered_eps": delivered_eps,
                    "pacing_constraint": pacing_constraint,
                },
                indent=2,
            )

        token_est = round(len(context_text.split()) * 1.3, 1)

        return {
            "run_id": run_id,
            "persona_id": pid,
            "character_slug": pid,
            "user_id": user_id,
            "context_prompt": context_text,
            "delivered_eps": delivered_eps,
            "social_move": social_move,
            "bubble_count": bubble_count,
            "estimated_tokens": token_est,
            "autonomic_state": autonomic,
        }
