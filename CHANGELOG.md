# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-13

### Added
- **Initial Public Open-Source Release** of OmniTwin.
- **Hierarchical Cognitive Memory Engine:**
  - Multi-tier memory model: Tier 0 disk archive (FTS5 BM25 recall), Tier 1 associative graphs & life milestones, Tier 2 Hebbian spreading activation, and Tier 3 Just-In-Time context compilation (< 450 tokens).
  - Exact relational tenant and persona scoping to prevent memory leakage across twins.
  - Cascading deletion and memory supersession engine updating derived FTS5 and graph edges.
- **Contour Grounding Engine:**
  - Strict enforcement of "No ID, No Claim" invariant.
  - Verification rejecting empty citation sets on unsupported autobiographical assertions.
  - Semantic claim verification between cited evidence and generated responses.
- **Multi-Provider LLM Integration:**
  - Pluggable provider architecture supporting local PI Gateway, OpenRouter, Google Cloud Vertex / Gemini, and deterministic Offline Simulator.
  - Graceful fallback and offline testing capabilities.
- **Social Move Planning & Cognitive Pacing:**
  - 15 discrete conversational move types and empirical cadence modeling.
  - Autonomic regulation and allostatic load tracking for conversational fatigue pacing.
- **High-Performance gRPC & REST Gateway:**
  - Native Protobuf schemas (`twin_engine.proto`) and east-west gRPC transport.
  - Bun-powered Twin Gateway with WebSocket typing indicator stream and realistic bubble splitting.
  - Safe localhost-first network binding defaults.
- **Comprehensive Synthetic Persona Fixtures & Test Suite:**
  - Fully character-agnostic synthetic test fixtures (`alex_cognitive_companion.json`).
  - Unit and integration test coverage across memory, planning, reduction, verification, and safety.
