# Contributing to OmniTwin

Thank you for your interest in contributing to OmniTwin! We welcome contributions ranging from bug fixes, security audits, and documentation improvements to new cognitive adapters and benchmark integrations.

---

## 1. Development Principles

1. **Character & Persona Agnostic:** Never hardcode specific identities, real-world individuals, or cultural monocultures into the core engine. Personas are dynamic runtime data contracts.
2. **Grounding & Traceability:** "No ID, No Claim". Any cognitive claim must be traceable to explicit evidence in the delivery slice.
3. **Privacy First:** Never log, store, or transmit raw biometric readings or unredacted personal identifiers into conversational context or persistent prompt logs.
4. **Developer Certificate of Origin (DCO):** We use standard DCO sign-offs (`git commit -s`) to confirm contributors have the legal right to submit their contributions under the Apache-2.0 license.

---

## 2. Local Development Setup

### Prerequisites
- Python 3.9+ (Python 3.11 or 3.12 recommended)
- Bun 1.1+ (for the optional Twin Gateway)

### Setup Steps
```bash
# Clone the repository
git clone https://github.com/imMamdouhaboammar/OmniTwin.git
cd OmniTwin

# Install Python dependencies and package in editable mode
pip install -e ".[dev]"

# Optional: Set up the Twin Gateway
cd services/twin-gateway
bun install
```

---

## 3. Running Tests

Before submitting a Pull Request, verify that all test suites pass:

```bash
# Run Python core test suite
pytest

# Run Twin Gateway tests
cd services/twin-gateway
bun test
```

---

## 4. Code Standards & Headers

All new source files must include the standard Apache-2.0 SPDX header:

### Python:
```python
# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
```

### TypeScript:
```typescript
// Copyright 2026 Mamdouh Aboammar
// SPDX-License-Identifier: Apache-2.0
```

---

## 5. Pull Request Process

1. Open an issue first to discuss substantial architectural changes.
2. Fork the repository and create a feature branch (`git checkout -b feature/cognitive-feature`).
3. Ensure all unit and integration tests pass.
4. Fill in the PR template detailing the change, security impact, and test evidence.

---

## 6. Cross-Project Collaboration (OmniTwin & Rafiq)

OmniTwin and [Rafiq](https://github.com/imMamdouhaboammar/Rafiq-Bot) are independently maintained
open-source projects with natural complementary responsibilities. If you are working on a feature
that spans both, please follow these guidelines to avoid duplicate issues and keep each project
focused.

### Contribute to OmniTwin for

- Cognitive memory algorithms (hierarchical recall, associative graphs, FTS5 optimization)
- Evidence provenance and grounding verification (`ContourEngine`, "No ID, No Claim")
- Context compilation and aperture budgeting (`CognitivePromptCompiler`)
- Conversational move planning and social signal processing (`TurnPlanner`)
- Cognitive state models and relational gate logic (`StateReducer`)
- gRPC and transport interface extensions (`twin_engine.proto`)
- Engine-level multi-tenancy and persona isolation
- Biometric signal processing and allostatic pacing

Open issues at: https://github.com/imMamdouhaboammar/OmniTwin/issues

### Contribute to Rafiq for

- Companion UX and conversation rendering
- Persona creation, editing, and evolution UX
- Model integrations (Gemini API, Vertex AI, other providers)
- Application tools (web search, media workflows, group conversations)
- Browser-local persistence and session management
- UI localization and cultural adaptation
- End-user application behavior and feature parity

Open issues at: https://github.com/imMamdouhaboammar/Rafiq-Bot/issues

### For Cross-Project Bugs

1. Open the issue in the repository that owns the **failing component**.
   - If OmniTwin's API returns unexpected data → open in OmniTwin.
   - If Rafiq's UI renders incorrect output using correct data → open in Rafiq.
2. Reference the related issue in the other repository using a full URL
   (e.g., `Related: imMamdouhaboammar/Rafiq-Bot#42`).
3. Avoid opening duplicate issues in both repositories for the same root cause.
4. Proposed integration protocol changes should be discussed as an OmniTwin issue first,
   since OmniTwin owns the cognitive engine API.
