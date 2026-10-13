# OmniTwin Release Roadmap

This document outlines the version roadmap and planned development trajectory for OmniTwin.

---

## Current Release: v0.1.0 (Initial Public Distribution)

- [x] **Contour Access Layer**: "No ID, No Claim" invariant enforcement, empty citation guard, and semantic entailment checks.
- [x] **Hierarchical SQLite Memory**: Tier 0 Archive, Tier 1 Associative Graph, Tier 2 Hebbian Activation, Tier 3 JIT Aperture (< 450 tokens).
- [x] **Multi-Tenancy & Persona Scoping**: Strict `(tenant_id, persona_id)` isolation across all queries, indexes, and operations.
- [x] **Deterministic State Reducer**: Exponential salience decay, relational permission gates, and energy-attenuated appetite.
- [x] **East-West gRPC Service**: Low-latency RPC transport with bearer token authentication and localhost default binding.
- [x] **Twin Gateway (@omnitwin/gateway)**: Bun TypeScript HTTP REST and WebSocket streaming gateway with typing cadence emulation.
- [x] **Wearable Telemetry & Pacing**: RMSSD, Baevsky Stress Index, and non-clinical cognitive load tracking.
- [x] **Offline Simulator Provider**: Deterministic local generation safety net with zero external API dependencies.
- [x] **CLI Tool (`omnitwin`)**: Unified command-line interface for serving, querying, inspecting, and graph exporting.
- [x] **Complete Test Suite**: Unit, integration, and security verification tests passing 100% green.

---

## Planned: v0.2.0 (Cognitive Consolidation & Community Graphs)

- [ ] **Dream-Cycle Memory Reorganization**: Scheduled background jobs that cluster raw Tier 0 events into new Tier 1 Extract Points during idle periods.
- [ ] **Semantic Community Auto-Detection**: Unsupervised community detection (Louvain / Leiden) on cognitive graph nodes to map high-level themes.
- [ ] **Native FastMCP Tool Server Expansion**: Expanded Model Context Protocol (MCP) server endpoints for Claude Desktop, Cursor, and Windsurf integration.
- [ ] **Extended Multilingual Cadence**: Specialized cadence rules and tokenization profiles for Arabic dialects (Egyptian, Levantine, Gulf), Spanish, and French.

---

## Planned: v0.3.0 (Edge CRDT Sync & Distributed Replication)

- [ ] **CRDT Edge-to-Cloud Sync**: Conflict-free Replicated Data Types for multi-device state synchronization between mobile, desktop, and cloud nodes.
- [ ] **End-to-End Encrypted Knowledge Replication**: Zero-knowledge encryption for remote backup of persona cognitive stores.
- [ ] **On-Device Small Model Adapters**: Direct bindings for llama.cpp and Apple MLX for 100% offline edge inference on consumer hardware.

---

## Ecosystem & Integration Opportunities

### Rafiq Integration (Community Opportunity)

[Rafiq](https://github.com/imMamdouhaboammar/Rafiq-Bot) is a TypeScript/React companion
application whose inference, persona, and continuity architecture is architecturally aligned with
OmniTwin's cognitive layer. A real integration is a community opportunity:

- **v0.2.0 window** — Expose a lightweight REST endpoint in OmniTwin alongside the existing gRPC
  transport to make JavaScript integration straightforward.
- **Community contribution** — Build and validate the first `examples/integrations/rafiq/`
  working integration using synthetic personas.
- **Protocol alignment** — Agree on a JSON schema for the cognitive context payload that both
  projects can validate independently.

See [docs/integrations/rafiq.md](integrations/rafiq.md) for the full design specification and
current integration status.
