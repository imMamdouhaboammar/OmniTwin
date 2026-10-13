# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Any, Dict, Optional

from omnitwin.core.contour import ContourEngine
from omnitwin.core.state_reducer import StateReducer


def import_persona_pack(
    json_path: str,
    db_path: str,
    schema_path: Optional[str] = None,
    tenant_id: str = "default",
) -> Dict[str, Any]:
    """
    Imports a persona definition JSON pack into the OmniTwin knowledge store.
    Character-agnostic, user-agnostic, and fully multi-tenant.
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Persona file {json_path} does not exist.")

    with open(json_path, "r", encoding="utf-8") as f:
        raw_bytes = f.read().encode("utf-8")
        data = json.loads(raw_bytes.decode("utf-8"))

    content_hash = hashlib.sha256(raw_bytes).hexdigest()

    persona_id = data.get("persona_id") or data.get("id") or data.get("character_slug") or "default_twin"
    name = data.get("name") or persona_id.capitalize()
    title = data.get("title") or f"{name} Cognitive Persona Specification"
    tenant = tenant_id if tenant_id != "default" else (data.get("tenant_id") or "default")

    contour = ContourEngine(db_path)
    contour.init_schema(schema_path)

    # 1. Insert Meta Card
    meta_id = f"meta_{persona_id}_canonical"
    contour.insert_meta(
        meta_id=meta_id,
        source_type="profile",
        title=title,
        content_hash=content_hash,
        persona_id=persona_id,
        tenant_id=tenant,
        url="file://" + os.path.abspath(json_path),
        raw_path=json_path,
    )

    imported_ep_count = 0

    # 2. Extract and Insert Core Principles
    principles = data.get("core_personality", {}).get("principles", [])
    for idx, p in enumerate(principles, start=1):
        contour.insert_ep(
            ep_id=f"ep_{persona_id}_prin_{idx:02d}",
            meta_id=meta_id,
            grp="core_personality",
            vector="principles",
            kind="axiom",
            text=p,
            tier="A",
            confidence=0.95,
            persona_id=persona_id,
            tenant_id=tenant,
            subject=name,
            relation="believes_in",
            object_=p,
        )
        imported_ep_count += 1

    # 3. Extract and Insert Worldview
    worldview = data.get("worldview", {})
    if isinstance(worldview, dict):
        for topic, text in worldview.items():
            contour.insert_ep(
                ep_id=f"ep_{persona_id}_world_{topic}",
                meta_id=meta_id,
                grp="worldview",
                vector=topic,
                kind="belief",
                text=str(text),
                tier="A",
                confidence=0.92,
                persona_id=persona_id,
                tenant_id=tenant,
                subject=name,
                relation="views",
                object_=topic,
            )
            imported_ep_count += 1

    # 4. Extract and Insert Communication Rules & Cadence
    comm = data.get("communication", {})
    rhythms = comm.get("rhythm", [])
    for idx, r in enumerate(rhythms, start=1):
        contour.insert_ep(
            ep_id=f"ep_{persona_id}_rhythm_{idx:02d}",
            meta_id=meta_id,
            grp="communication",
            vector="rhythm",
            kind="heuristic",
            text=r,
            tier="A",
            confidence=0.95,
            persona_id=persona_id,
            tenant_id=tenant,
            subject=name,
            relation="uses_cadence",
            object_=r,
        )
        imported_ep_count += 1

    lexical = comm.get("lexical_energy", [])
    for idx, lex in enumerate(lexical, start=1):
        contour.insert_ep(
            ep_id=f"ep_{persona_id}_lexical_{idx:02d}",
            meta_id=meta_id,
            grp="communication",
            vector="lexical_energy",
            kind="preference",
            text=f"Signature phrase or expression: {lex}",
            tier="A",
            confidence=0.90,
            persona_id=persona_id,
            tenant_id=tenant,
            subject=name,
            relation="speaks_with",
            object_=lex,
        )
        imported_ep_count += 1

    # Guardrails
    anti_rules = data.get("anti_ai_rules", []) or data.get("guardrails", [])
    for idx, rule in enumerate(anti_rules, start=1):
        contour.insert_ep(
            ep_id=f"ep_{persona_id}_anti_{idx:02d}",
            meta_id=meta_id,
            grp="guardrails",
            vector="anti_ai_rules",
            kind="antipattern",
            text=rule,
            tier="A",
            confidence=0.98,
            persona_id=persona_id,
            tenant_id=tenant,
            subject=name,
            relation="rejects",
            object_=rule,
        )
        imported_ep_count += 1

    # 5. Extract Goals
    goals = data.get("goals_and_recurring_concerns", {}).get("high_confidence", []) or data.get("goals", [])
    for idx, goal in enumerate(goals, start=1):
        contour.insert_ep(
            ep_id=f"ep_{persona_id}_goal_{idx:02d}",
            meta_id=meta_id,
            grp="goals",
            vector="active_concerns",
            kind="stance",
            text=goal,
            tier="B",
            confidence=0.85,
            persona_id=persona_id,
            tenant_id=tenant,
            subject=name,
            relation="aims_for",
            object_=goal,
        )
        imported_ep_count += 1

    # 6. Extract Preferences
    prefs = data.get("preferences", {}).get("high_or_medium_confidence", {}) or data.get("preferences", {})
    if isinstance(prefs, dict):
        for pref_key, pref_val in prefs.items():
            contour.insert_ep(
                ep_id=f"ep_{persona_id}_pref_{pref_key}",
                meta_id=meta_id,
                grp="preferences",
                vector=pref_key,
                kind="preference",
                text=str(pref_val),
                tier="B",
                confidence=0.88,
                persona_id=persona_id,
                tenant_id=tenant,
                subject=name,
                relation="prefers",
                object_=pref_key,
            )
            imported_ep_count += 1

    # 7. Extract Relational Stances
    relationships = data.get("relationships", [])
    reducer = StateReducer(db_path)

    if isinstance(relationships, list):
        for rel in relationships:
            uid = rel.get("user_id", "default_user")
            contour.insert_ep(
                ep_id=f"ep_{persona_id}_rel_{uid}",
                meta_id=meta_id,
                grp="relationships",
                vector=uid,
                kind="relation",
                text=f"Relationship with {uid}: {rel.get('role', 'collaborator')}. Closeness {rel.get('closeness', 0.5)}. Trust {rel.get('trust', 0.5)}.",
                tier="A",
                confidence=0.95,
                persona_id=persona_id,
                tenant_id=tenant,
                subject=name,
                relation="relates_to",
                object_=uid,
            )
            imported_ep_count += 1

            # Seed dynamic state
            seed = {
                "mood": rel.get("initial_mood", "neutral"),
                "energy": float(rel.get("initial_energy", 0.7)),
                "conversation_appetite": rel.get("initial_appetite", "chatty"),
                "current_mode": rel.get("current_mode", "casual"),
                "active_concerns": [],
                "active_threads": [],
                "relationship_state": {
                    "role": rel.get("role", "collaborator"),
                    "closeness": float(rel.get("closeness", 0.5)),
                    "trust": float(rel.get("trust", 0.5)),
                    "comfort": float(rel.get("comfort", 0.5)),
                    "teasing_permission": float(rel.get("teasing_permission", 0.3)),
                    "affection_permission": float(rel.get("affection_permission", 0.2)),
                    "vulnerability_permission": float(rel.get("vulnerability_permission", 0.3)),
                    "romantic_assumption_allowed": bool(rel.get("romantic_assumption_allowed", False)),
                },
            }
            reducer.get_or_seed_state(persona_id, uid, default_seed=seed, tenant_id=tenant)
    else:
        # Default user seed
        reducer.get_or_seed_state(persona_id, "default_user", tenant_id=tenant)

    return {
        "persona_id": persona_id,
        "name": name,
        "tenant_id": tenant,
        "meta_id": meta_id,
        "imported_ep_count": imported_ep_count,
        "db_path": db_path,
    }


def import_canonical_pack(json_path: str, db_path: str, schema_path: Optional[str] = None) -> None:
    """Backwards-compatible wrapper."""
    import_persona_pack(json_path=json_path, db_path=db_path, schema_path=schema_path)


class PersonaImporter:
    """Object-oriented persona pack importer."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def import_from_file(
        self,
        file_path: str,
        tenant_id: str = "default",
        persona_id: Optional[str] = None,
    ) -> int:
        res = import_persona_pack(
            json_path=file_path,
            db_path=self.db_path,
            tenant_id=tenant_id,
        )
        return res.get("imported_ep_count", 0)
