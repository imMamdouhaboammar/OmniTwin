# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import os
import re
import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from omnitwin.core.pii_firewall import PIIFirewall


class ChatIngestionEngine:
    """
    Parses, sanitizes, and extracts empirical behavioral cadences from conversation exports.
    Adheres strictly to the PII Firewall and extracts statistical style distributions.
    """

    TIMESTAMP_PATTERNS = [
        # [DD/MM/YYYY, HH:MM:SS] Sender: Message
        re.compile(r"^\[(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\]\s*([^:]+):\s*(.*)$"),
        # DD/MM/YYYY, HH:MM - Sender: Message
        re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\s*-\s*([^:]+):\s*(.*)$"),
        # MM/DD/YY, HH:MM - Sender: Message
        re.compile(r"^(\d{1,2}/\d{1,2}/\d{2}),?\s+(\d{1,2}:\d{2}(?:\s*[APap][Mm])?)\s*-\s*([^:]+):\s*(.*)$"),
    ]

    IGNORED_SYSTEM_PATTERNS = [
        re.compile(r"end-to-end encrypted", re.IGNORECASE),
        re.compile(r"<Media omitted>", re.IGNORECASE),
        re.compile(r"<الملفات الوسائط مستبعدة>", re.IGNORECASE),
        re.compile(r"Missed voice call", re.IGNORECASE),
        re.compile(r"Missed video call", re.IGNORECASE),
        re.compile(r"This message was deleted", re.IGNORECASE),
        re.compile(r"تم حذف هذه الرسالة", re.IGNORECASE),
        re.compile(r"You deleted this message", re.IGNORECASE),
    ]

    def __init__(self, firewall: Optional[PIIFirewall] = None):
        self.firewall = firewall or PIIFirewall()

    def parse_timestamp(self, date_str: str, time_str: str) -> Optional[datetime]:
        """Attempts to parse varied date and time formats into a Python datetime."""
        date_str = date_str.strip()
        time_str = time_str.strip().replace("\u202f", " ")

        date_formats = ["%d/%m/%Y", "%m/%d/%Y", "%d/%m/%y", "%m/%d/%y"]
        time_formats = ["%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p", "%I:%M%p"]

        for df in date_formats:
            for tf in time_formats:
                combo = f"{date_str} {time_str}"
                try:
                    return datetime.strptime(combo, f"{df} {tf}")
                except ValueError:
                    continue
        return None

    def parse_chat_content(self, text: str) -> List[Dict[str, Any]]:
        """
        Parses conversation text exports into structured message objects.
        Merges multiline messages and runs text through PII sanitization.
        """
        lines = text.splitlines()
        messages: List[Dict[str, Any]] = []
        current_msg: Optional[Dict[str, Any]] = None

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            matched = False
            for pat in self.TIMESTAMP_PATTERNS:
                m = pat.match(line_str)
                if m:
                    date_part, time_part, sender, body = m.groups()
                    sender = sender.strip()
                    body = body.strip()

                    is_system = any(sp.search(body) for sp in self.IGNORED_SYSTEM_PATTERNS)
                    if is_system:
                        matched = True
                        break

                    dt = self.parse_timestamp(date_part, time_part)
                    sanitized_body, redactions = self.firewall.sanitize_text(body)

                    if current_msg:
                        messages.append(current_msg)

                    current_msg = {
                        "date_str": date_part,
                        "time_str": time_part,
                        "timestamp": dt.timestamp() if dt else 0.0,
                        "sender": sender,
                        "text": sanitized_body,
                        "redactions": redactions,
                        "char_count": len(sanitized_body),
                        "word_count": len(sanitized_body.split()),
                    }
                    matched = True
                    break

            if not matched and current_msg:
                # Append multiline continuation
                sanitized_continuation, redacts = self.firewall.sanitize_text(line_str)
                current_msg["text"] += "\n" + sanitized_continuation
                current_msg["redactions"].extend(redacts)
                current_msg["char_count"] = len(current_msg["text"])
                current_msg["word_count"] = len(current_msg["text"].split())

        if current_msg:
            messages.append(current_msg)

        return messages

    def group_into_bursts(self, messages: List[Dict[str, Any]], burst_threshold_seconds: float = 120.0) -> List[Dict[str, Any]]:
        """Groups sequential messages from the same sender within a time threshold into single turns."""
        if not messages:
            return []

        bursts: List[Dict[str, Any]] = []
        current_burst: Dict[str, Any] = {
            "sender": messages[0]["sender"],
            "messages": [messages[0]],
            "start_time": messages[0]["timestamp"],
            "end_time": messages[0]["timestamp"],
        }

        for msg in messages[1:]:
            same_sender = msg["sender"] == current_burst["sender"]
            time_delta = msg["timestamp"] - current_burst["end_time"]
            within_window = time_delta <= burst_threshold_seconds

            if same_sender and within_window:
                current_burst["messages"].append(msg)
                current_burst["end_time"] = msg["timestamp"]
            else:
                bursts.append(current_burst)
                current_burst = {
                    "sender": msg["sender"],
                    "messages": [msg],
                    "start_time": msg["timestamp"],
                    "end_time": msg["timestamp"],
                }

        bursts.append(current_burst)
        return bursts

    def compute_empirical_cadence(
        self,
        messages: List[Dict[str, Any]],
        target_speaker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extracts empirical cadence metrics for the target character.
        Produces character lengths, word counts, and multi-bubble burst distributions.
        """
        if not messages:
            return {"messages_total_parsed": 0, "target_messages": 0, "observed_style": {}}

        if target_speaker:
            target_norm = target_speaker.lower()
            target_msgs = [m for m in messages if target_norm in m["sender"].lower()]
        else:
            # Pick most frequent speaker if not specified
            speaker_counts: Dict[str, int] = {}
            for m in messages:
                speaker_counts[m["sender"]] = speaker_counts.get(m["sender"], 0) + 1
            target_speaker = max(speaker_counts.keys(), key=lambda k: speaker_counts[k])
            target_msgs = [m for m in messages if m["sender"] == target_speaker]

        target_text_msgs = [m for m in target_msgs if m["char_count"] > 0]

        if not target_text_msgs:
            return {
                "messages_total_parsed": len(messages),
                "target_messages": len(target_msgs),
                "target_text_messages": 0,
                "observed_style": {},
            }

        char_counts = [m["char_count"] for m in target_text_msgs]
        word_counts = [m["word_count"] for m in target_text_msgs]

        le_10 = sum(1 for c in char_counts if c <= 10) / len(char_counts)
        le_20 = sum(1 for c in char_counts if c <= 20) / len(char_counts)
        le_40 = sum(1 for c in char_counts if c <= 40) / len(char_counts)

        # Compute bursts
        bursts = self.group_into_bursts(messages)
        target_norm = target_speaker.lower()
        target_bursts = [b for b in bursts if target_norm in b["sender"].lower()]
        burst_bubble_counts = [len(b["messages"]) for b in target_bursts] if target_bursts else [1]

        single_bubble_ratio = sum(1 for bc in burst_bubble_counts if bc == 1) / len(burst_bubble_counts)
        multi_bubble_ratio = 1.0 - single_bubble_ratio

        return {
            "messages_total_parsed": len(messages),
            "target_speaker": target_speaker,
            "target_messages": len(target_msgs),
            "target_text_messages": len(target_text_msgs),
            "target_bursts_count": len(target_bursts),
            "observed_style": {
                "mean_chars_per_bubble": round(statistics.mean(char_counts), 1),
                "median_chars_per_bubble": round(statistics.median(char_counts), 1),
                "mean_words_per_bubble": round(statistics.mean(word_counts), 1),
                "median_words_per_bubble": round(statistics.median(word_counts), 1),
                "bubbles_le_10_chars_ratio": round(le_10, 3),
                "bubbles_le_20_chars_ratio": round(le_20, 3),
                "bubbles_le_40_chars_ratio": round(le_40, 3),
                "single_bubble_burst_ratio": round(single_bubble_ratio, 3),
                "multi_bubble_burst_ratio": round(multi_bubble_ratio, 3),
                "mean_bubbles_per_burst": round(statistics.mean(burst_bubble_counts), 2),
            },
        }
