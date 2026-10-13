# Security Policy

OmniTwin takes the security, privacy, and integrity of cognitive state seriously. As a persistent behavioral continuity engine, securing sensitive memory and maintaining strict boundary isolation is paramount.

---

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

---

## Reporting a Vulnerability

If you discover a security vulnerability in OmniTwin, please do **NOT** open a public issue.

Instead, please report security concerns via:
1. **GitHub Private Security Advisory:** Open an advisory under `https://github.com/imMamdouhaboammar/OmniTwin/security/advisories/new`
2. **Direct Contact:** Contact the maintainers directly via repository owner profile.

We strive to acknowledge receipt of reports within 48 hours and provide a remediation plan or patch within 7 business days.

---

## Security Architecture & Invariants

1. **Localhost Binding by Default:** All sample servers, gRPC listeners, and web gateways bind to `127.0.0.1` by default. Exposing services to `0.0.0.0` requires explicit configuration and authentication.
2. **Boundary Isolation:** Biometric signals and personal data pass through schema-validated barriers. Raw biometric numbers never cross into LLM context or memory tables.
3. **Evidence Boundary Enforcement:** The Contour Engine strictly enforces "No ID, No Claim": no memory citation is valid unless present in the locked delivery slice.
4. **No Arbitrary Code Execution:** Subprocess calls use explicit argument lists without shell interpolation. User-supplied persona slugs and user IDs are sanitized against regex patterns (`^[a-zA-Z0-9_-]{1,64}$`).
5. **Cascading Deletion:** Memory deletions and supersessions cascade across relational tables, FTS5 indexes, and associative graph edges.
