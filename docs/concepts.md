# Core Concepts in OmniTwin

This document explains the foundational cognitive and architectural concepts underpinning OmniTwin.

---

## 1. Extract Points (EP)

An **Extract Point (EP)** is the fundamental atom of memory in OmniTwin. Rather than storing unbounded free-form text chunks, an EP represents an atomic, verifiable unit of knowledge, belief, preference, or relational stance.

### EP Schema Anatomy:
- `id`: Unique identifier (e.g. `ep_alex_01`).
- `meta_id`: Foreign key pointing to the source document or archive ticket in the `meta` table.
- `tenant_id` & `persona_id`: Strict isolation boundary tags.
- `grp`: High-level domain (e.g., `identity`, `preferences`, `architecture`, `relationships`).
- `vector`: Specific semantic category (e.g., `databases`, `coffee`, `education`).
- `kind`: Semantic type (`belief`, `heuristic`, `framework`, `stance`, `antipattern`, `procedure`, `reasoning`, `anecdote`, `prediction`, `axiom`, `relation`, `preference`).
- `text`: Human-readable statement of the memory.
- `tier`: Epistemic authority level (`A` for core identity facts, `B` for established beliefs/preferences, `C` for working hypotheses).
- `confidence`: Calibrated score between `0.0` and `1.0`.

---

## 2. "No ID, No Claim"

"No ID, No Claim" is OmniTwin's fundamental epistemic guardrail against hallucination:
- In conventional RAG, models receive context in a system prompt and are trusted not to hallucinate beyond it. However, models frequently invent plausible autobiographical backstories.
- In OmniTwin, every statement the agent makes about its life, beliefs, or relationships must be backed by an authorized citation tag (`[ep_xxx]`).
- The **Contour Access Layer** audits every turn against the run's locked delivery ticket. If an ID was not delivered, or if an autobiographical claim is made without any citation, the turn fails closed.

---

## 3. Hebbian Spreading Activation

Memories in OmniTwin do not exist in isolation; they are connected via directed, weighted edges in `associative_edges`:
- When a memory node is recalled, its activation energy spreads to adjacent nodes according to edge weights:
  \[
  A_j = A_i \cdot W_{ij} \cdot \delta
  \]
  where \(W_{ij}\) is the edge weight and \(\delta\) is the decay factor.
- This allows associative recall (e.g. thinking of *coffee* naturally activates related memories about *Ethiopian roasts* and *morning routines*) without requiring high-latency full-corpus embeddings.

---

## 4. Bounded JIT Cognitive Aperture

Modern context windows are often large (hundreds of thousands of tokens), but filling context windows with raw history causes attention dilution, slow inference, and high costs.

OmniTwin strictly bounds its just-in-time delivery slice to **< 450 tokens** formatted as structured XML:
- Up to 3 most salient Extract Points.
- Current dynamic state (mood, energy, appetite).
- Relational boundary gates (roles, permissions).
- Explicit negative constraints (what the twin must never say or assume).

---

## 5. Salience Decay & State Evolution

Relationships and mental states evolve dynamically:
- **Active Concerns**: When a problem or decision is discussed, it enters `active_concerns` with high salience (e.g. `0.80`).
- Over time, without reactivation, salience decays exponentially. Once it falls below `0.10`, the concern is pruned.
- **Relational Permissions**: Actions such as teasing, expressing deep vulnerability, or sharing intimate feelings are protected behind threshold gates that require accumulated trust and comfort.
