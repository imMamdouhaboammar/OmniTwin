# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
"""
Tests for Ingestion & PII Privacy Firewall:
1. Redaction of international and local phone numbers.
2. Redaction of physical residential addresses.
3. Rejection of explicit intimate narrative or clinical diagnostic labels.
4. Validation and ingestion of synthetic persona packs.
"""

import os
import tempfile
import pytest

from omnitwin.core.pii_firewall import PIIFirewall
from omnitwin.core.contour import ContourEngine
from omnitwin.core.importer import PersonaImporter


def test_pii_phone_redaction():
    firewall = PIIFirewall()
    text = "Call me back at +20 1012345678 or my US number 415-555-2671 later today."
    cleaned, redactions = firewall.sanitize_text(text)

    assert "[REDACTED_PHONE]" in cleaned
    assert "+20 1012345678" not in cleaned
    assert "415-555-2671" not in cleaned
    assert "phone_number" in redactions


def test_pii_address_redaction():
    firewall = PIIFirewall()
    text = "The meetup is at 742 Evergreen Terrace street apartment 4B."
    cleaned, redactions = firewall.sanitize_text(text)

    assert "[REDACTED_ADDRESS]" in cleaned
    assert "physical_address" in redactions


def test_clinical_label_rejection():
    firewall = PIIFirewall()
    bad_ep = {
        "text": "Subject was diagnosed with borderline personality disorder and narcissism.",
        "tier": "A",
        "confidence": 0.9,
    }
    is_valid, reason = firewall.validate_extract_point(bad_ep)
    assert not is_valid
    assert "Clinical psychological labels" in reason


def test_persona_pack_ingestion():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        contour = ContourEngine(db_path)
        contour.init_schema()

        # Path to synthetic persona
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        persona_path = os.path.join(repo_root, "examples", "synthetic-persona", "alex_cognitive_companion.json")

        importer = PersonaImporter(db_path)
        imported_count = importer.import_from_file(persona_path, tenant_id="tenant_01", persona_id="alex")

        assert imported_count > 0

        # Verify DB records
        with contour._get_connection() as conn:
            meta_count = conn.execute("SELECT COUNT(*) as c FROM meta WHERE persona_id = 'alex';").fetchone()["c"]
            ep_count = conn.execute("SELECT COUNT(*) as c FROM ep WHERE persona_id = 'alex';").fetchone()["c"]
            assert meta_count >= 1
            assert ep_count == imported_count
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
