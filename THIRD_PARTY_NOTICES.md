# Third-Party Notices and Attribution

OmniTwin is an open-source project licensed under the Apache License, Version 2.0.
This document provides attribution and information regarding third-party software, libraries, and conceptual inspirations referenced by or used with OmniTwin.

---

## 1. Architectural Inspirations

### Harlo Architectural Concepts
- **Concepts Referenced:** Biometric boundary isolation ("Rule 9 / ADR-0001" conceptual design), allostatic load modeling combining software interaction pacing with physiological sensors.
- **Upstream License:** Apache License, Version 2.0
- **Notice:** The upstream Harlo source code tree (`Harlo-master`) is **explicitly excluded** from the OmniTwin repository distribution. OmniTwin provides its own clean, character-agnostic allostasis and physiological pacing adapter (`omnitwin.adapters.allostasis_adapter`) that can optionally interface with external Harlo daemons or independent sensor providers via generic schemas and interfaces. OmniTwin claims no ownership or patent rights over Harlo or its proprietary algorithms.

---

## 2. Mathematical Formulations and Scientific Literature

### Heart Rate Variability (HRV) & Stress Metrics
- **RMSSD (Root Mean Square of Successive Differences):** Standard time-domain metric widely established in biomedical literature (Task Force of the European Society of Cardiology and the North American Society of Pacing and Electrophysiology, 1996).
- **Baevsky Stress Index ($SI$):** Mathematical formula developed by Prof. Roman Baevsky (Institute of Biomedical Problems, Moscow, 1984) for cardiovascular autonomic balance:
  $$SI = \frac{AM_0}{2 \cdot M_0 \cdot \Delta RR}$$
- **Medical & Diagnostic Disclaimer:** Implementation in OmniTwin (`omnitwin.core.biometrics`) is strictly for conversational pacing and behavioral state simulation in AI agents. It does **not** provide clinical diagnosis, medical evaluation, or physiological ground truth.

---

## 3. Runtime Dependencies and Libraries

The following dependencies are used by OmniTwin according to their respective open-source licenses:

| Component | License | Purpose | Canonical Link |
| :--- | :--- | :--- | :--- |
| **SQLite / FTS5** | Public Domain (Blessing) | Embedded relational database and BM25 full-text indexing | https://sqlite.org |
| **gRPC & Protobuf** | Apache-2.0 / BSD-3-Clause | High-performance RPC transport and schema compilation | https://grpc.io |
| **Bun** | MIT | Fast JavaScript/TypeScript runtime for the Twin Gateway | https://bun.sh |
| **FastMCP** | MIT | Model Context Protocol server interface | https://modelcontextprotocol.io |
| **jsonschema** | MIT | JSON schema validation for boundary barriers | https://github.com/python-jsonschema/jsonschema |
| **PyYAML** | MIT | Configuration file parsing | https://pyyaml.org |

---

## 4. Modified Files and Upstream Rights

All original files authored for OmniTwin carry the copyright notice:
`Copyright 2026 Mamdouh Aboammar` under the Apache License 2.0.
Any contributions, modifications, or derivatives must preserve applicable license and copyright notices in accordance with Section 4 of Apache-2.0.
