# OmniTwin Privacy & Data Protection Architecture

Privacy and data ownership are core architectural priorities of OmniTwin. Unlike cloud-centric agent platforms that centralize user conversational logs, OmniTwin is designed from the ground up as a **local-first, privacy-preserving cognitive engine**.

---

## 1. Privacy Invariants

### A. Local-First Data Sovereignty
- All episodic memories, relationship profiles, dynamic emotional states, and knowledge graphs reside on local storage in a standard SQLite file (`omnitwin.db`).
- OmniTwin includes **zero phone-home analytics, telemetry pings, or user tracking**.

### B. Data Minimization & Bounded Delivery
- Traditional chat architectures dump entire conversation histories into context prompts.
- OmniTwin extracts atomic Extract Points (EPs) and delivers only the minimal sufficient context slice (< 450 tokens) required to ground a specific interaction turn.
- Personal background details irrelevant to the active topic are never exposed in prompt context.

### C. Right to Erasure (Cascading Deletion)
OmniTwin implements complete cascading deletion for memory records and persona profiles:
- Calling `HierarchicalMemory.delete_persona(persona_id)` triggers a transactional cascade that permanently deletes:
  - All Extract Points (`ep` table)
  - All FTS5 full-text search indexes (`ep_fts`)
  - All associative graph edges (`associative_edges`)
  - All raw episodic archive events (`episodic_archive`)
  - All dynamic relational states (`dynamic_state`)
  - All metadata provenance records (`meta`)
- Calling `delete_ep(ep_id)` purges the specific node and removes all incoming and outgoing associative links.

---

## 2. Wearable Telemetry & Health Data Protection

### A. Non-Clinical Informational Use
OmniTwin processes wearable telemetry (such as R-R interval streams or heart rate) exclusively for conversational pacing, cognitive appetite modulation, and energy estimation.

**Strict Disclaimer**:
OmniTwin is **NOT** a medical device, diagnostic tool, or clinical monitoring system. Physiological estimates (such as RMSSD or Baevsky Stress Index) must never be used for medical decisions, clinical evaluations, or therapeutic interventions.

### B. Raw Sensor Stream Minimization
- Raw millisecond R-R streams are processed in memory to compute aggregate pacing metrics (e.g. RMSSD) and are **not** permanently persisted in the relational database unless explicitly configured by the user.
- Telemetry feeds are isolated per `(tenant_id, persona_id)`.
