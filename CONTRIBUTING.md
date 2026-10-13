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
