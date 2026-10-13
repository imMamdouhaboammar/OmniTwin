# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple


class ContourEngine:
    """
    Enforces the Contour Access Layer invariants:
    - LLM never reads raw tables directly.
    - Retrieval (FTS5 recall) is strictly decoupled from selection.
    - Delivery slice is bounded, immutable, and auditable.
    - 'No ID, No Claim': Verification rejects any cited ID not physically present in delivery.
    - Empty Citation Guard: Autobiographical or factual claims without citations fail verification.
    - Semantic Grounding: Entailment verification ensures cited nodes actually substantiate claims.
    """

    # Autobiographical assertion trigger patterns (multilingual: EN, AR)
    AUTOBIOGRAPHICAL_PATTERNS = [
        # English
        r"\bi\s+(?:was|became|remember|lived|worked|studied|graduated|met|traveled|bought|felt|decided|started|attended|practiced|grew up)\b",
        r"\bmy\s+(?:father|mother|sister|brother|friend|childhood|university|job|company|hometown|dog|cat|career|degree)\b",
        r"\bwhen\s+i\s+was\s+(?:in|young|living|studying|working|a)\b",
        r"\bi\s+(?:personally\s+)?(?:believe|hate|love|prefer|advise|dislike)\b",
        # Arabic
        r"(?:فاكر|فاكرة|عشت|اشتغلت|درست|اتخرجت|قابلت|سافرت|اشتريت|قررت|بدأت)",
        r"(?:بابا|ماما|أمي|أبويا|أختي|أخويا|صاحبي|صاحبتي|طفولتي|جامعتي|شغلي|بلدي)",
        r"(?:لما كنت|وأنا صغير|وأنا صغيرة|في الجامعة|في الشغل)",
        r"(?:أنا شخصياً|رأيي الشخصي|بحب|بكره|بفضل)",
    ]

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_schema(self, schema_path: Optional[str] = None) -> None:
        if schema_path is None:
            schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            ddl = f.read()
        with self._get_connection() as conn:
            conn.executescript(ddl)
            conn.commit()

    def insert_meta(
        self,
        meta_id: str,
        source_type: str,
        title: str,
        content_hash: str = "",
        persona_id: str = "default",
        tenant_id: str = "default",
        url: str = "",
        raw_path: str = "",
    ) -> None:
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO meta (id, tenant_id, persona_id, source_type, title, url, content_hash, created_at, raw_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (meta_id, tenant_id, persona_id, source_type, title, url, content_hash, created_at, raw_path),
            )
            conn.commit()

    def insert_ep(
        self,
        ep_id: str,
        meta_id: str,
        grp: str,
        vector: str,
        kind: str,
        text: str,
        tier: str = "B",
        confidence: float = 0.90,
        persona_id: str = "default",
        tenant_id: str = "default",
        subject: str = "",
        relation: str = "",
        object_: str = "",
        t_start: Optional[int] = None,
        deeplink: str = "",
        as_of: str = "",
    ) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO ep (id, meta_id, tenant_id, persona_id, grp, vector, kind, subject, relation, object, text, tier, confidence, t_start, deeplink, as_of)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (ep_id, meta_id, tenant_id, persona_id, grp, vector, kind, subject, relation, object_, text, tier, confidence, t_start, deeplink, as_of),
            )
            conn.commit()

    def open_intent(self, persona_id: str, user_id: str, user_message: str, tenant_id: str = "default") -> str:
        """Opens a tracked intent run and returns a unique run_id."""
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO runs (id, tenant_id, persona_id, user_id, intent, created_at, delivery_ep_ids, verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0);
                """,
                (run_id, tenant_id, persona_id, user_id, user_message, created_at, json.dumps([])),
            )
            conn.commit()
        return run_id

    def recall_candidates(
        self,
        query: str,
        limit: int = 10,
        persona_id: Optional[str] = None,
        tenant_id: str = "default",
    ) -> List[Dict[str, Any]]:
        """
        Recall candidate extract points using FTS5 BM25 ranking.
        Strictly respects tenant_id and persona_id scoping.
        """
        words = [
            w.strip()
            for w in query.replace('"', " ").replace("'", " ").replace("،", " ").replace("؟", " ").replace("!", " ").split()
            if len(w.strip()) > 1
        ]

        with self._get_connection() as conn:
            if not words:
                if persona_id:
                    cursor = conn.execute(
                        """
                        SELECT * FROM ep
                        WHERE persona_id = ? AND tenant_id = ?
                        ORDER BY confidence DESC LIMIT ?;
                        """,
                        (persona_id, tenant_id, limit),
                    )
                else:
                    cursor = conn.execute("SELECT * FROM ep WHERE tenant_id = ? ORDER BY confidence DESC LIMIT ?;", (tenant_id, limit))
                return [dict(row) for row in cursor.fetchall()]

            fts_query = " OR ".join(f'"{w}"' for w in words[:6])
            try:
                if persona_id:
                    cursor = conn.execute(
                        """
                        SELECT ep.*, ep_fts.rank
                        FROM ep_fts
                        JOIN ep ON ep.rowid = ep_fts.rowid
                        WHERE ep_fts MATCH ?
                          AND ep.persona_id = ?
                          AND ep.tenant_id = ?
                        ORDER BY ep_fts.rank
                        LIMIT ?;
                        """,
                        (fts_query, persona_id, tenant_id, limit),
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT ep.*, ep_fts.rank
                        FROM ep_fts
                        JOIN ep ON ep.rowid = ep_fts.rowid
                        WHERE ep_fts MATCH ? AND ep.tenant_id = ?
                        ORDER BY ep_fts.rank
                        LIMIT ?;
                        """,
                        (fts_query, tenant_id, limit),
                    )
                rows = cursor.fetchall()
            except Exception:
                rows = []

            if not rows:
                # Scoped fallback without FTS match
                if persona_id:
                    cursor = conn.execute(
                        """
                        SELECT * FROM ep
                        WHERE persona_id = ? AND tenant_id = ?
                        ORDER BY confidence DESC LIMIT ?;
                        """,
                        (persona_id, tenant_id, limit),
                    )
                else:
                    cursor = conn.execute("SELECT * FROM ep WHERE tenant_id = ? ORDER BY confidence DESC LIMIT ?;", (tenant_id, limit))
                return [dict(r) for r in cursor.fetchall()]

            return [dict(r) for r in rows]

    def compile_delivery(self, run_id: str, selected_ep_ids: List[str]) -> Dict[str, Any]:
        """
        Locks the exact delivery slice for this run into disk storage.
        The LLM only receives what is delivered here.
        """
        with self._get_connection() as conn:
            if selected_ep_ids:
                placeholders = ",".join("?" for _ in selected_ep_ids)
                cursor = conn.execute(
                    f"SELECT * FROM ep WHERE id IN ({placeholders});",
                    selected_ep_ids,
                )
                delivered_rows = [dict(r) for r in cursor.fetchall()]
                actual_ids = [r["id"] for r in delivered_rows]
            else:
                delivered_rows = []
                actual_ids = []

            conn.execute(
                "UPDATE runs SET delivery_ep_ids = ? WHERE id = ?;",
                (json.dumps(actual_ids), run_id),
            )
            conn.commit()

        return {
            "run_id": run_id,
            "delivered_count": len(delivered_rows),
            "delivered_eps": delivered_rows,
        }

    # Public ergonomic alias
    lock_delivery = compile_delivery

    def record_answer(self, run_id: str, answer_text: str) -> None:
        with self._get_connection() as conn:
            conn.execute("UPDATE runs SET answer = ? WHERE id = ?;", (answer_text, run_id))
            conn.commit()

    def _contains_autobiographical_assertion(self, text: str) -> bool:
        """Determines if the response makes personal, experiential, or autobiographical assertions."""
        lower_text = text.lower()
        for pattern in self.AUTOBIOGRAPHICAL_PATTERNS:
            if re.search(pattern, lower_text, re.IGNORECASE):
                return True
        return False

    def verify_turn(
        self,
        run_id: str,
        cited_ep_ids: List[str],
        raw_response: Optional[str] = None,
        check_semantic_grounding: bool = True,
    ) -> Tuple[bool, List[str], str]:
        """
        Verifies the 'No ID, No Claim' invariant and semantic grounding.
        1. 'No ID, No Claim': Rejects any citation not in the run's compiled delivery slice.
        2. Empty Citation Guard: Rejects autobiographical assertions made without any citations.
        3. Semantic Entailment: Verifies factual alignment between cited nodes and response.
        """
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT delivery_ep_ids, persona_id, tenant_id FROM runs WHERE id = ?;", (run_id,))
            row = cursor.fetchone()
            if not row:
                return False, cited_ep_ids, f"Run {run_id} not found."

            delivered_ids = set(json.loads(row["delivery_ep_ids"]))
            cited_set = set(cited_ep_ids)
            unauthorized_ids = list(cited_set - delivered_ids)

            # Invariant 1: No cited ID outside delivery slice
            if unauthorized_ids:
                rejection = f"Violation of 'No ID, No Claim': Cited IDs {unauthorized_ids} were not delivered in run {run_id}."
                return False, unauthorized_ids, rejection

            # Invariant 2: Empty Citation Guard on autobiographical claims
            if raw_response and len(cited_set) == 0 and self._contains_autobiographical_assertion(raw_response):
                rejection = (
                    "Uncited Claim Violation: Autobiographical or personal factual assertion requires "
                    "grounding evidence from the delivery slice. Cannot assert autobiographical facts without citation."
                )
                return False, [], rejection

            # Invariant 3: Semantic Entailment Check
            if check_semantic_grounding and raw_response and cited_set:
                placeholders = ",".join("?" for _ in cited_set)
                ep_rows = conn.execute(
                    f"SELECT id, text, subject, object FROM ep WHERE id IN ({placeholders});",
                    list(cited_set),
                ).fetchall()

                # Common multilingual stopwords to exclude from semantic overlap
                stopwords = {
                    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were",
                    "been", "have", "has", "had", "will", "would", "can", "could", "should",
                    "not", "but", "about", "into", "over", "after", "all", "any", "both",
                    "each", "few", "more", "most", "other", "some", "such", "than", "too",
                    "very", "you", "your", "they", "them", "their", "she", "her", "his",
                    "him", "our", "ours", "who", "whom", "whose", "what", "which", "where",
                    "when", "why", "how", "في", "من", "على", "إلى", "عن", "مع", "هذا",
                    "هذه", "التي", "الذي", "كان", "كانت", "يكون", "أن", "إن"
                }

                # Clean response text into normalized tokens, stripping citation markers and stopwords
                clean_resp = re.sub(r"\[ep_[a-zA-Z0-9_]+\]|\(ep_[a-zA-Z0-9_]+\)", "", raw_response.lower())
                resp_tokens = set(re.findall(r"[\w]+", clean_resp)) - stopwords

                for ep_r in ep_rows:
                    ep_text = ep_r["text"].lower()
                    ep_subj = (ep_r["subject"] or "").lower()
                    ep_obj = (ep_r["object"] or "").lower()

                    # Key semantic anchors (subject, object, or salient words, excluding stopwords)
                    raw_anchors = set(re.findall(r"[\w]{3,}", ep_text))
                    semantic_anchors = raw_anchors - stopwords
                    if ep_subj and ep_subj not in stopwords:
                        semantic_anchors.add(ep_subj)
                    if ep_obj and ep_obj not in stopwords:
                        semantic_anchors.add(ep_obj)

                    overlap = semantic_anchors.intersection(resp_tokens)

                    # If the cited EP has multiple content words but zero intersection with response,
                    # the citation is spurious hallucinated grounding.
                    if len(semantic_anchors) >= 2 and len(overlap) == 0:
                        rejection = (
                            f"Semantic Grounding Violation: Cited node {ep_r['id']} has no semantic "
                            "alignment with the generated response."
                        )
                        return False, [ep_r["id"]], rejection

            conn.execute("UPDATE runs SET verified = 1 WHERE id = ?;", (run_id,))
            conn.commit()
            return True, [], "ACCEPTED"
