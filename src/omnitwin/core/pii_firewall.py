# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


class PIIFirewall:
    """
    Privacy and Sanitization Firewall for OmniTwin Cognitive Agents.
    Enforces canonical safety and privacy invariants:
    - Strips local and international phone numbers.
    - Strips private addresses and physical location coordinates.
    - Rejects explicit intimate history from being recorded as permanent identity.
    - Prevents unverified clinical psychiatric diagnoses from contaminating traits.
    """

    PHONE_PATTERNS = [
        re.compile(r"\b\+?[1-9]\d{1,2}\s*[\d\s-]{7,12}\d\b"),
        re.compile(r"\+20\s*(?:1[0125]\d{8}|\d{9,10})"),
        re.compile(r"\b01[0125]\d{8}\b"),
        re.compile(r"\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b"),
    ]

    LOCATION_PATTERNS = [
        re.compile(r"\b(?:street|st\.|ave|avenue|apartment|apt\.|building|road|rd\.|blvd)\s+[\w\s]{2,25}\b", re.IGNORECASE),
        re.compile(r"\b\d{1,5}\s+[\w\s]{2,20}\s+(?:street|st|avenue|ave|rd|road|blvd)\b", re.IGNORECASE),
        re.compile(r"\b(?:شارع|ش\.|عمارة|ميدان|بلوك|شقة)\s+[\w\s]{2,25}\b", re.IGNORECASE),
    ]

    FORBIDDEN_IDENTITY_PATTERNS = [
        re.compile(r"\b(?:sexual act|explicit intercourse|erotic roleplay)\b", re.IGNORECASE),
        re.compile(r"\b(?:مص|زب|طيز|كس|شرموط|سكس|نيك|دعارة)\b", re.IGNORECASE),
    ]

    CLINICAL_DIAGNOSIS_PATTERNS = [
        re.compile(r"\b(?:borderline|bpd|narcissistic|npd|bipolar|schizo|psychopathic)\b", re.IGNORECASE),
        re.compile(r"\b(?:مرض نفسي|اضطراب شخصية حدية|نرجسية مرضية|فصام)\b", re.IGNORECASE),
    ]

    def sanitize_text(self, text: str) -> Tuple[str, List[str]]:
        """
        Redacts sensitive PII from incoming message text.
        Returns redacted text and a list of detected redaction categories.
        """
        redactions = []
        cleaned = text

        for pattern in self.PHONE_PATTERNS:
            if pattern.search(cleaned):
                cleaned = pattern.sub("[REDACTED_PHONE]", cleaned)
                redactions.append("phone_number")

        for pattern in self.LOCATION_PATTERNS:
            if pattern.search(cleaned):
                cleaned = pattern.sub("[REDACTED_ADDRESS]", cleaned)
                redactions.append("physical_address")

        return cleaned, list(set(redactions))

    def validate_extract_point(self, ep: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Audits an extract point before insertion into the knowledge store.
        Rejects explicit intimate narratives or clinical diagnoses.
        """
        text = ep.get("text", "")
        tier = ep.get("tier", "C")

        # 1. Reject explicit intimate history
        for pattern in self.FORBIDDEN_IDENTITY_PATTERNS:
            if pattern.search(text):
                return False, "Violation: Explicit intimate history cannot be canonicalized."

        # 2. Reject interpretive psychological hypotheses treated as clinical diagnoses
        for pattern in self.CLINICAL_DIAGNOSIS_PATTERNS:
            if pattern.search(text):
                return False, "Violation: Clinical psychological labels cannot be persisted as traits."

        # 3. Reject high-confidence claims from uncorroborated Tier C files
        if tier == "C" and ep.get("confidence", 0.0) > 0.40:
            return False, "Violation: Tier C interpretive hypotheses must have confidence <= 0.40."

        return True, "VALID"
