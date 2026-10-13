## Description
<!-- Provide a clear, detailed explanation of what this change does and why it was introduced. -->

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds capability)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Security / Privacy enhancement
- [ ] Documentation update

## Invariants & Security Checklist
- [ ] **No Personal / Private Data:** Verified that no personal records, phone numbers, real-person prompts, or private datasets are committed.
- [ ] **Boundary Isolation:** Biometric signals and personal identity data follow schema validation and do not leak into long-term prompts or traces.
- [ ] **Grounding Invariant:** Verified that "No ID, No Claim" is strictly preserved.
- [ ] **License & Attribution:** Verified that new original files contain the SPDX Apache-2.0 header and third-party contributions are documented.
- [ ] **Tests Passing:** Added unit/integration tests and verified all suites pass locally.
