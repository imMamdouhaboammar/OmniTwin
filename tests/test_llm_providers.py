# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
"""
Tests for LLM Providers & Offline Simulation:
1. OfflineSimulatorProvider deterministic grounded generation.
2. Abstract base provider interface compliance.
3. Fallback routing behavior.
"""

from omnitwin.adapters.llm_provider import (
    BaseLLMProvider,
    OfflineSimulatorProvider,
    get_default_provider,
)


class DummyCustomProvider(BaseLLMProvider):
    @property
    def name(self) -> str:
        return "dummy-custom"

    def is_available(self) -> bool:
        return True

    def generate(self, system_prompt: str, user_message: str, **kwargs) -> str:
        return f"Echo: {user_message}"


def test_offline_simulator_is_available():
    simulator = OfflineSimulatorProvider()
    assert simulator.is_available() is True
    assert simulator.name == "offline-simulator"


def test_offline_simulator_generation():
    simulator = OfflineSimulatorProvider()
    reply = simulator.generate(
        system_prompt="You are a helpful assistant.",
        user_message="Hello there!",
    )
    assert len(reply) > 0
    assert isinstance(reply, str)


def test_custom_provider_conformance():
    provider = DummyCustomProvider()
    assert provider.name == "dummy-custom"
    assert provider.is_available() is True
    output = provider.generate("system", "Test input")
    assert output == "Echo: Test input"


def test_get_default_provider_returns_active():
    default_p = get_default_provider()
    assert isinstance(default_p, BaseLLMProvider)
    assert default_p.is_available() is True
