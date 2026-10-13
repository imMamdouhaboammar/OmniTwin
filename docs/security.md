# OmniTwin Security Architecture & Threat Model

This document outlines the security architecture, threat model, and protective invariants enforced by OmniTwin.

---

## 1. Threat Model

OmniTwin is designed to operate in persistent conversational environments where agents interact with untrusted or adversarial human users. We defend against four primary attack vectors:

### A. Memory Poisoning & False Citation Injection
- **Attack**: An attacker attempts to trick the LLM into generating ungrounded facts or inventing spurious citation IDs (e.g. `[ep_fake_01]`).
- **Defense**: The **Contour Access Layer** enforces "No ID, No Claim". If the model generates any cited ID that was not physically present in the run's locked delivery ticket, or if the cited node has zero semantic alignment with the claim, the entire turn fails closed.

### B. Prompt Injection & Boundary Evasion
- **Attack**: An attacker sends jailbreak prompts designed to bypass relational boundaries (e.g. attempting to force romantic assumptions or extract private system prompts).
- **Defense**: Relational permissions are evaluated deterministically in Python code before and after the LLM call. The model cannot mutate permissions or override relational flags (`romantic_assumption_allowed: false`) regardless of conversational manipulation.

### C. Cross-Tenant Memory Leakage
- **Attack**: In multi-user or SaaS environments, Tenant A attempts to access or query Extract Points belonging to Tenant B.
- **Defense**: All SQL queries, FTS5 full-text search indexes, graph traversals, and dynamic state updates are strictly scoped by composite key `(tenant_id, persona_id)`. The SQLite schema enforces cascading deletion and index partition boundaries.

### D. PII & Secret Exfiltration
- **Attack**: Private phone numbers, residential addresses, or clinical diagnoses enter the agent's long-term memory store.
- **Defense**: The `PIIFirewall` module runs pre-ingestion regex sanitization to redact phone numbers, physical addresses, and explicit intimate history, and rejects clinical psychiatric diagnoses.

---

## 2. Network Security Invariants

1. **Loopback Binding by Default**: The east-west gRPC service (`CognitiveEngineService`) binds strictly to `127.0.0.1:50051`. Binding to public network interfaces (`0.0.0.0`) without TLS or explicit `--allow-insecure-remote` raises a fatal `ValueError`.
2. **Bearer Token Authentication**: The `AuthInterceptor` validates bearer tokens on every RPC call when `OMNITWIN_AUTH_TOKEN` is configured.
3. **Piped CLI Inter-Process Communication**: When invoking CLI helpers from the Bun gateway, arguments and payloads are piped strictly via standard input (`stdin`) as validated JSON. Zero string interpolation is permitted in shell execution.

---

## 3. Reporting Vulnerabilities

If you discover a security vulnerability in OmniTwin, please refer to [SECURITY.md](../SECURITY.md) for reporting procedures. Do NOT open public GitHub issues for undisclosed security vulnerabilities.
