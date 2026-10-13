# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from omnitwin.core.contour import ContourEngine
from omnitwin.core.state_reducer import StateReducer


class TurnPlanner:
    """
    Multi-stage cognitive turn planner:
    1. Evaluates user intent and conversational intent signals.
    2. Reads current dynamic state, energy, and relational permissions.
    3. Selects the primary social move (multilingual support).
    4. Recalls candidate EPs scoped strictly by tenant and persona.
    5. Locks bounded delivery slice into the database.
    6. Produces cognitive turn plan with cadence budgeting.
    """

    # Multilingual intent triggers
    CHECK_IN_TRIGGERS = [
        "hi", "hello", "hey", "good morning", "good evening", "how are you", "what's up",
        "صباح الخير", "مساء الخير", "ازيك", "عامل ايه", "عاملة ايه", "أهلاً", "مرحبا"
    ]
    OPINION_TRIGGERS = [
        "what do you think", "your opinion", "what's your view", "should i", "do you prefer",
        "recommend", "advice", "suggest", "opinion",
        "رأيك", "ايه رأيك", "أعمل ايه", "تفتكر", "تفتكري", "شايف ايه", "بتفضل ايه"
    ]
    HELP_TRIGGERS = [
        "problem", "issue", "error", "bug", "help", "code", "work", "fix",
        "مشكلة", "عطل", "كود", "فلوس", "شغل", "ساعدني", "حل"
    ]
    TEASE_TRIGGERS = [
        "arrogant", "forgot me", "where were you", "too busy", "ghosting",
        "مغرور", "مغرورة", "يا عم", "فينك", "نسيتنا", "كبرت علينا"
    ]

    def __init__(self, contour: ContourEngine, reducer: StateReducer):
        self.contour = contour
        self.reducer = reducer

    def select_social_move(self, user_message: str, current_state: Dict[str, Any]) -> str:
        energy = current_state.get("energy", 0.7)
        relationship = current_state.get("relationship_state", {})
        msg_lower = user_message.strip().lower()

        # Low energy forces minimal presence move
        if energy < 0.35:
            return "minimal_presence"

        # Teasing trigger (requires relational permission)
        if any(w in msg_lower for w in self.TEASE_TRIGGERS) and self.reducer.evaluate_permission(relationship, "tease"):
            return "tease"

        # Opinion or recommendation request
        if any(w in msg_lower for w in self.OPINION_TRIGGERS):
            return "give_opinion"

        # Greetings & check-in
        if any(w in msg_lower for w in self.CHECK_IN_TRIGGERS):
            return "check_in"

        # Practical / technical request
        if any(w in msg_lower for w in self.HELP_TRIGGERS):
            return "practical_help"

        # Short message default
        if len(user_message.strip()) <= 15:
            return "acknowledge"

        return "answer"

    def plan_turn(
        self,
        persona_id: str,
        user_id: str,
        user_message: str,
        tenant_id: str = "default",
        character_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        pid = persona_id or character_slug or "default"

        # 1. Open an auditable run ticket
        run_id = self.contour.open_intent(pid, user_id, user_message, tenant_id=tenant_id)

        # 2. Get current dynamic state
        state = self.reducer.get_or_seed_state(pid, user_id, tenant_id=tenant_id)

        # 3. Select dominant social move
        social_move = self.select_social_move(user_message, state)

        # 4. Recall candidate EPs using FTS5 BM25 strictly scoped by tenant and persona
        candidates = self.contour.recall_candidates(user_message, limit=5, persona_id=pid, tenant_id=tenant_id)

        # 5. Filter to bounded selection (at most 3 EPs for context economy)
        selected_ep_ids = [c["id"] for c in candidates[:3]]

        # 6. Compile delivery slice locked into the database
        delivery = self.contour.compile_delivery(run_id, selected_ep_ids)

        # 7. Formulate cadence parameters
        bubble_count = 1 if len(user_message) < 20 and state.get("energy", 0.7) < 0.5 else 2

        return {
            "run_id": run_id,
            "tenant_id": tenant_id,
            "persona_id": pid,
            "character_slug": pid,
            "user_id": user_id,
            "social_move": social_move,
            "bubble_count": bubble_count,
            "current_state": state,
            "delivery": delivery,
        }

    def plan_cadence_budget(self, energy: float, social_move: str) -> Dict[str, Any]:
        """Formulates cadence boundaries (bubble count and typing delay bounds)."""
        if energy < 0.35 or social_move == "minimal_presence":
            return {"max_bubbles": 1, "target_chars": 35}
        if energy >= 0.70 and social_move in ("give_opinion", "practical_help"):
            return {"max_bubbles": 3, "target_chars": 120}
        return {"max_bubbles": 2, "target_chars": 60}

