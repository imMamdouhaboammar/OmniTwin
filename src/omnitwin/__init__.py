# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
"""
OmniTwin: Cognitive Continuity for AI Agents
============================================
A generalized, character-agnostic cognitive continuity engine providing:
- Identity grounding & contour verification
- Hierarchical episodic & semantic memory
- Relational state tracking & cadence adaptation
- Local-first, provider-agnostic cognitive architecture
"""

__version__ = "0.1.0"
__author__ = "Mamdouh Aboammar"
__license__ = "Apache-2.0"

from omnitwin.core.hierarchical_memory import HierarchicalBillionScaleMemory, HierarchicalMemory
from omnitwin.core.contour import ContourEngine
from omnitwin.core.state_reducer import StateReducer
from omnitwin.core.turn_planner import TurnPlanner
from omnitwin.core.context_compiler import CognitivePromptCompiler
from omnitwin.core.generator import CognitiveGenerator
from omnitwin.core.biometrics import BiometricProcessor
from omnitwin.core.importer import PersonaImporter, import_persona_pack
from omnitwin.core.graphify import CognitiveGraphEngine, CognitiveGraphifier

# Friendly public aliases
ContourVerifier = ContourEngine
ContextCompiler = CognitivePromptCompiler
BiometricSignalProcessor = BiometricProcessor

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "HierarchicalMemory",
    "HierarchicalBillionScaleMemory",
    "ContourEngine",
    "ContourVerifier",
    "StateReducer",
    "TurnPlanner",
    "CognitivePromptCompiler",
    "ContextCompiler",
    "CognitiveGenerator",
    "BiometricProcessor",
    "BiometricSignalProcessor",
    "PersonaImporter",
    "import_persona_pack",
    "CognitiveGraphEngine",
    "CognitiveGraphifier",
]
