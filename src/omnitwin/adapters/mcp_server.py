# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

from omnitwin.core.contour import ContourEngine
from omnitwin.core.state_reducer import StateReducer
from omnitwin.core.turn_planner import TurnPlanner
from omnitwin.core.graphify import CognitiveGraphEngine
from omnitwin.core.context_compiler import CognitivePromptCompiler
from omnitwin.core.biometrics import BiometricProcessor


class OmniTwinMCPServer:
    """
    Standard Model Context Protocol (MCP) Server for OmniTwin.
    Exposes persona cognition, associative neural graph walk, relational boundaries,
    and 'No ID, No Claim' verification tools to external LLMs and AI agents.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.contour = ContourEngine(db_path)
        self.reducer = StateReducer(db_path)
        self.planner = TurnPlanner(self.contour, self.reducer)
        self.graph_engine = CognitiveGraphEngine(db_path)
        self.compiler = CognitivePromptCompiler(self.contour, self.reducer, self.planner)
        self.bio_processor = BiometricProcessor()

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "omnitwin_get_cognitive_pack",
                "description": "Compiles a token-thrifty (under 450 tokens) Cognitive State Context Pack for an AI to consume before replying as the digital twin.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "persona_id": {"type": "string", "description": "Persona identifier (e.g. 'companion', 'alex')"},
                        "user_id": {"type": "string", "description": "Interlocutor ID"},
                        "user_message": {"type": "string", "description": "Incoming user message"},
                        "tenant_id": {"type": "string", "description": "Tenant ID (default: 'default')"},
                    },
                    "required": ["persona_id", "user_id", "user_message"],
                },
            },
            {
                "name": "omnitwin_walk_neural_graph",
                "description": "Performs associative spreading activation through the cognitive neural graph starting from a node or community.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "community_id": {"type": "string", "description": "Target community (e.g. 'communication', 'core_personality', 'guardrails')"},
                        "persona_id": {"type": "string", "description": "Persona ID"},
                        "limit": {"type": "integer", "description": "Max nodes to return (default: 8)"},
                    },
                    "required": ["community_id"],
                },
            },
            {
                "name": "omnitwin_get_relational_boundary",
                "description": "Retrieves the calibrated trust, closeness, teasing permission, and romantic limits for a specific user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "persona_id": {"type": "string", "description": "Persona identifier"},
                        "user_id": {"type": "string", "description": "User identifier"},
                        "tenant_id": {"type": "string", "description": "Tenant identifier"},
                    },
                    "required": ["persona_id", "user_id"],
                },
            },
            {
                "name": "omnitwin_verify_grounding",
                "description": "Enforces the 'No ID, No Claim' safety gate. Verifies that all assertions in the twin's proposed reply are backed by authorized extract point IDs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "run_id": {"type": "string", "description": "Active turn run ID"},
                        "cited_ep_ids": {"type": "array", "items": {"type": "string"}, "description": "Cited extract point IDs"},
                        "proposed_reply": {"type": "string", "description": "Raw model reply to verify for semantic grounding"},
                    },
                    "required": ["run_id", "cited_ep_ids"],
                },
            },
            {
                "name": "omnitwin_ingest_biometrics",
                "description": "Ingests real-time wearable R-R interval streams to calculate HRV RMSSD and dynamically clamp twin conversational energy.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "persona_id": {"type": "string"},
                        "user_id": {"type": "string"},
                        "rr_intervals_ms": {"type": "array", "items": {"type": "number"}},
                    },
                    "required": ["persona_id", "user_id", "rr_intervals_ms"],
                },
            },
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pid = arguments.get("persona_id") or arguments.get("character_slug") or "default"
        uid = arguments.get("user_id") or "default_user"
        tenant_id = arguments.get("tenant_id", "default")

        if tool_name == "omnitwin_get_cognitive_pack":
            return self.compiler.compile_ai_context(
                persona_id=pid,
                user_id=uid,
                user_message=arguments["user_message"],
                tenant_id=tenant_id,
            )

        elif tool_name == "omnitwin_walk_neural_graph":
            comm_id = arguments["community_id"]
            limit = arguments.get("limit", 8)
            subgraph = self.graph_engine.get_subgraph(comm_id, persona_id=pid, tenant_id=tenant_id)
            subgraph["nodes"] = subgraph["nodes"][:limit]
            return subgraph

        elif tool_name == "omnitwin_get_relational_boundary":
            state = self.reducer.get_or_seed_state(
                persona_id=pid,
                user_id=uid,
                tenant_id=tenant_id,
            )
            return {
                "persona_id": pid,
                "user_id": uid,
                "mood": state.get("mood"),
                "energy": state.get("energy"),
                "relationship_state": state.get("relationship_state", {}),
            }

        elif tool_name == "omnitwin_verify_grounding":
            ok, missing, reason = self.contour.verify_turn(
                run_id=arguments["run_id"],
                cited_ep_ids=arguments.get("cited_ep_ids", []),
                raw_response=arguments.get("proposed_reply"),
            )
            return {
                "verified": ok,
                "missing_ids": missing,
                "reason": reason,
            }

        elif tool_name == "omnitwin_ingest_biometrics":
            res = self.reducer.reduce_biometric_telemetry(
                persona_id=pid,
                user_id=uid,
                rr_intervals_ms=arguments["rr_intervals_ms"],
                tenant_id=tenant_id,
            )
            return res

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def run_stdio(self) -> None:
        """Runs the standard MCP JSON-RPC 2.0 loop over stdin/stdout."""
        for line in sys.stdin:
            line_str = line.strip()
            if not line_str:
                continue

            try:
                request = json.loads(line_str)
                req_id = request.get("id")
                method = request.get("method")
                params = request.get("params", {})

                if method == "tools/list":
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {"tools": self.get_tool_definitions()},
                    }
                elif method == "tools/call":
                    tool_name = params.get("name")
                    args = params.get("arguments", {})
                    result = self.call_tool(tool_name, args)
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]},
                    }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32601, "message": f"Method not found: {method}"},
                    }

                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()

            except Exception as e:
                err_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32000, "message": str(e)},
                }
                sys.stdout.write(json.dumps(err_response, ensure_ascii=False) + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    db_file = os.environ.get("OMNITWIN_DB", "omnitwin.db")
    server = OmniTwinMCPServer(db_file)

    if len(sys.argv) > 1 and sys.argv[1] == "--tools":
        print(json.dumps(server.get_tool_definitions(), ensure_ascii=False, indent=2))
    else:
        server.run_stdio()
