# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import math
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional


class StateReducer:
    """
    Deterministic reducer for dynamic cognitive, emotional, and relational state.
    Implements:
    - Exponential salience decay for conversational concerns.
    - Energy-attenuated conversational appetite.
    - Relational permission boundary gates.
    - Propose-and-reduce contract (proposals with low confidence are rejected).
    - Multi-tenant and persona scoping.
    """

    DEFAULT_RELATIONSHIP_SEED: Dict[str, Any] = {
        "role": "collaborator",
        "closeness": 0.50,
        "trust": 0.50,
        "comfort": 0.50,
        "teasing_permission": 0.30,
        "affection_permission": 0.20,
        "vulnerability_permission": 0.30,
        "romantic_assumption_allowed": False,
    }

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def get_or_seed_state(
        self,
        persona_id: str,
        user_id: str,
        default_seed: Optional[Dict[str, Any]] = None,
        tenant_id: str = "default",
        character_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieves existing dynamic state or seeds a new baseline for (tenant_id, persona_id, user_id)."""
        pid = persona_id or character_slug or "default"
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM dynamic_state WHERE tenant_id = ? AND persona_id = ? AND user_id = ?;",
                (tenant_id, pid, user_id),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "tenant_id": row["tenant_id"],
                    "persona_id": row["persona_id"],
                    "character_slug": row["persona_id"],
                    "user_id": row["user_id"],
                    "mood": row["mood"],
                    "energy": row["energy"],
                    "conversation_appetite": row["conversation_appetite"],
                    "current_mode": row["current_mode"],
                    "active_concerns": json.loads(row["active_concerns_json"]),
                    "active_threads": json.loads(row["active_threads_json"]),
                    "relationship_state": json.loads(row["relationship_state_json"]),
                    "updated_at": row["updated_at"],
                }

            # Seed new state
            seed = default_seed or {
                "mood": "neutral",
                "energy": 0.70,
                "conversation_appetite": "chatty",
                "current_mode": "casual",
                "active_concerns": [],
                "active_threads": [],
                "relationship_state": dict(self.DEFAULT_RELATIONSHIP_SEED),
            }

            now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            conn.execute(
                """
                INSERT INTO dynamic_state (
                    tenant_id, persona_id, user_id, mood, energy, conversation_appetite,
                    current_mode, active_concerns_json, active_threads_json,
                    relationship_state_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    tenant_id,
                    pid,
                    user_id,
                    seed.get("mood", "neutral"),
                    float(seed.get("energy", 0.70)),
                    seed.get("conversation_appetite", "chatty"),
                    seed.get("current_mode", "casual"),
                    json.dumps(seed.get("active_concerns", [])),
                    json.dumps(seed.get("active_threads", [])),
                    json.dumps(seed.get("relationship_state", self.DEFAULT_RELATIONSHIP_SEED)),
                    now_iso,
                ),
            )
            conn.commit()
            return {
                "tenant_id": tenant_id,
                "persona_id": pid,
                "character_slug": pid,
                "user_id": user_id,
                **seed,
                "updated_at": now_iso,
            }

    def compute_salience_decay(
        self,
        concern: Any,
        elapsed_hours: float,
        arousal: Optional[float] = None,
        lambda_decay: float = 0.05,
        omega_arousal: float = 2.0,
    ) -> float:
        """Calculates exponential salience decay: S(t) = S_0 * exp( - lambda * delta_t / (1 + omega * Arousal) )"""
        if isinstance(concern, dict):
            initial_salience = float(concern.get("salience", 0.7))
            effective_arousal = float(concern.get("arousal", 0.5)) if arousal is None else arousal
        else:
            initial_salience = float(concern)
            effective_arousal = 0.5 if arousal is None else float(arousal)

        effective_decay = lambda_decay * elapsed_hours / (1.0 + omega_arousal * effective_arousal)
        new_salience = initial_salience * math.exp(-effective_decay)
        return max(0.0, min(1.0, new_salience))

    def evaluate_permission(self, relationship_state: Dict[str, Any], action: str) -> bool:
        """
        Evaluates relational permission boundaries.
        Returns False if the action exceeds earned closeness, trust, or explicit permission levels.
        """
        if action in ("romance", "romantic_intimacy"):
            return bool(relationship_state.get("romantic_assumption_allowed", False))

        if action == "tease":
            if "teasing_permission" in relationship_state:
                return float(relationship_state["teasing_permission"]) >= 0.35
            closeness = relationship_state.get("closeness", 0.5)
            trust = relationship_state.get("trust", 0.5)
            return ((closeness * 0.6) + (trust * 0.4)) >= 0.65

        if action == "affection":
            if "affection_permission" in relationship_state:
                return float(relationship_state["affection_permission"]) >= 0.35
            closeness = relationship_state.get("closeness", 0.5)
            return closeness >= 0.60

        if action == "vulnerability":
            if "vulnerability_permission" in relationship_state:
                return float(relationship_state["vulnerability_permission"]) >= 0.35
            trust = relationship_state.get("trust", 0.5)
            return trust >= 0.70

        thresholds = {
            "seek_opinion": 0.40,
            "disagree": 0.50,
            "request_call": 0.60,
        }
        threshold = thresholds.get(action, 0.50)
        closeness = relationship_state.get("closeness", 0.5)
        trust = relationship_state.get("trust", 0.5)
        score = (closeness * 0.6) + (trust * 0.4)
        return score >= threshold

    def reduce_proposal(
        self,
        persona_id: str,
        user_id: str,
        proposal: Dict[str, Any],
        tenant_id: str = "default",
        character_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Deterministically reduces state mutations.
        Rejects proposals with confidence < 0.6 or invalid schema.
        """
        pid = persona_id or character_slug or "default"
        current_state = self.get_or_seed_state(pid, user_id, tenant_id=tenant_id)
        confidence = proposal.get("confidence", 0.0)

        # Invariant: Reject ambiguous or low-confidence proposals
        if confidence < 0.6:
            return current_state

        # Update mood if valid
        new_mood = proposal.get("mood")
        valid_moods = {
            "neutral", "good", "playful", "bored", "tired", "stressed",
            "annoyed", "sad", "anxious", "excited", "hopeful", "overwhelmed"
        }
        if new_mood in valid_moods:
            current_state["mood"] = new_mood

        # Update energy with clamping
        energy_delta = proposal.get("energy_delta", 0.0)
        current_energy = current_state.get("energy", 0.7)
        updated_energy = max(0.0, min(1.0, current_energy + energy_delta))
        current_state["energy"] = updated_energy

        # Energy attenuates conversational appetite
        if "conversation_appetite" in proposal and proposal["conversation_appetite"] in {"chatty", "medium", "low", "minimal"}:
            current_state["conversation_appetite"] = proposal["conversation_appetite"]
        elif updated_energy < 0.35:
            current_state["conversation_appetite"] = "minimal"
        elif updated_energy >= 0.70:
            current_state["conversation_appetite"] = "chatty"

        # Apply exponential decay to all existing concerns
        now_unix = time.time()
        raw_concerns: List[Dict[str, Any]] = current_state.get("active_concerns", [])
        active_concerns = []
        for c in raw_concerns:
            created = c.get("created_at_unix", now_unix)
            elapsed_hours = max(0.0, (now_unix - created) / 3600.0)
            cur_salience = c.get("salience", 0.5)
            arousal = c.get("arousal", 0.5)
            new_sal = self.compute_salience_decay(cur_salience, elapsed_hours, arousal)
            if new_sal >= 0.10:
                active_concerns.append({
                    "topic": c["topic"],
                    "salience": round(new_sal, 3),
                    "arousal": arousal,
                    "created_at_unix": created,
                })

        add_concern = proposal.get("add_concern")
        if add_concern:
            existing_topics = [c.get("topic") for c in active_concerns]
            if add_concern not in existing_topics:
                active_concerns.append({
                    "topic": add_concern,
                    "salience": 0.8,
                    "arousal": 0.6,
                    "created_at_unix": now_unix,
                })

        resolve_concern = proposal.get("resolve_concern")
        if resolve_concern:
            active_concerns = [c for c in active_concerns if c.get("topic") != resolve_concern]

        # Keep top 6 by salience
        active_concerns.sort(key=lambda c: c.get("salience", 0.0), reverse=True)
        current_state["active_concerns"] = active_concerns[:6]

        # Update active threads (max 12)
        active_threads: List[str] = current_state.get("active_threads", [])
        add_thread = proposal.get("add_thread")
        if add_thread and add_thread not in active_threads:
            active_threads.append(add_thread)
        resolve_thread = proposal.get("resolve_thread")
        if resolve_thread and resolve_thread in active_threads:
            active_threads.remove(resolve_thread)
        current_state["active_threads"] = active_threads[:12]

        # Persist reduced state
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        current_state["updated_at"] = now_iso
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE dynamic_state
                SET mood = ?, energy = ?, conversation_appetite = ?, current_mode = ?,
                    active_concerns_json = ?, active_threads_json = ?,
                    relationship_state_json = ?, updated_at = ?
                WHERE tenant_id = ? AND persona_id = ? AND user_id = ?;
                """,
                (
                    current_state["mood"],
                    current_state["energy"],
                    current_state["conversation_appetite"],
                    current_state["current_mode"],
                    json.dumps(current_state["active_concerns"]),
                    json.dumps(current_state["active_threads"]),
                    json.dumps(current_state["relationship_state"]),
                    now_iso,
                    tenant_id,
                    pid,
                    user_id,
                ),
            )
            conn.commit()

        return current_state

    def reduce_biometric_telemetry(
        self,
        persona_id: str,
        user_id: str,
        rr_intervals_ms: Optional[List[float]] = None,
        sleep_hours: float = 7.5,
        healthkit_sample: Optional[Any] = None,
        tenant_id: str = "default",
        character_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Integrates wearable telemetry into behavioral pacing.
        Disclaimer: This is for informational conversational pacing only, NOT clinical diagnostic use.
        """
        from omnitwin.core.biometrics import BiometricProcessor
        from omnitwin.adapters.allostasis_adapter import get_allostasis_engine

        pid = persona_id or character_slug or "default"
        processor = BiometricProcessor()
        engine = get_allostasis_engine(pid)

        bio_metrics: Dict[str, Any] = {}

        if healthkit_sample is not None:
            hk_res = engine.ingest_healthkit_sample(healthkit_sample)
            autonomic = hk_res["autonomic_state"]
            bio_metrics = {
                "sample_type": hk_res.get("sample_type"),
                "allostatic_load": autonomic.get("allostatic_load", 0.0),
                "is_depleted": autonomic.get("is_depleted", False),
            }
            target_energy = autonomic.get("energy", 0.7)
            target_appetite = autonomic.get("conversation_appetite", "medium")
        elif rr_intervals_ms and len(rr_intervals_ms) >= 2:
            bio_res = processor.process_telemetry_payload(rr_intervals_ms, sleep_hours=sleep_hours)
            bio_metrics = bio_res
            target_energy = bio_res.get("attenuated_energy", 0.7)
            target_appetite = bio_res.get("conversation_appetite", "medium")
            engine.ingest_rr_intervals(rr_intervals_ms, sleep_hours=sleep_hours)
        else:
            return self.get_or_seed_state(pid, user_id, tenant_id=tenant_id)

        # Propose state change derived from autonomic load
        proposal = {
            "energy_delta": round(target_energy - 0.70, 2),
            "conversation_appetite": target_appetite,
            "confidence": 0.90,
        }
        if bio_metrics.get("stress_index", 0.0) > 300.0 or bio_metrics.get("is_depleted", False):
            proposal["mood"] = "tired"

        updated = self.reduce_proposal(pid, user_id, proposal, tenant_id=tenant_id)
        updated["biometrics"] = bio_metrics
        return updated
