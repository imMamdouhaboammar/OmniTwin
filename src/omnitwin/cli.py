# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
"""
OmniTwin CLI: Command-Line Interface for OmniTwin Cognitive Continuity Engine
=============================================================================
Provides commands for running the gRPC server, importing persona packs,
querying memory, inspecting dynamic state, and exporting knowledge graphs.
"""

import argparse
import json
import logging
import os
import sys
from typing import List, Optional

from omnitwin import __version__, __license__
from omnitwin.core.hierarchical_memory import HierarchicalMemory
from omnitwin.core.contour import ContourEngine
from omnitwin.core.importer import PersonaImporter
from omnitwin.core.state_reducer import StateReducer
from omnitwin.core.turn_planner import TurnPlanner
from omnitwin.core.generator import CognitiveGenerator
from omnitwin.core.graphify import CognitiveGraphEngine


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_version(args: argparse.Namespace) -> int:
    print(f"OmniTwin v{__version__} - Cognitive Continuity for AI Agents")
    print(f"License: {__license__}")
    print("Copyright (c) 2026 Mamdouh Aboammar. All rights reserved.")
    print("Repository: https://github.com/imMamdouhaboammar/OmniTwin")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from omnitwin.server import serve
    setup_logging(args.verbose)
    print(f"Starting OmniTwin gRPC server on {args.host}:{args.port}...")
    serve(
        db_path=args.db,
        host=args.host,
        port=args.port,
        auth_token=args.auth_token,
        allow_insecure_remote=args.allow_insecure_remote,
    )
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    setup_logging(args.verbose)
    db_dir = os.path.dirname(os.path.abspath(args.db))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    contour = ContourEngine(args.db)
    contour.init_schema()
    print(f"Initialized clean OmniTwin SQLite schema at: {args.db}")

    if args.persona:
        importer = PersonaImporter(args.db)
        count = importer.import_from_file(
            file_path=args.persona,
            tenant_id=args.tenant_id,
            persona_id=args.persona_id,
        )
        print(f"Imported {count} nodes for persona '{args.persona_id}' (tenant '{args.tenant_id}') from {args.persona}")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    setup_logging(args.verbose)
    if not os.path.exists(args.file):
        print(f"Error: Persona file not found: {args.file}", file=sys.stderr)
        return 1

    importer = PersonaImporter(args.db)
    count = importer.import_from_file(
        file_path=args.file,
        tenant_id=args.tenant_id,
        persona_id=args.persona_id,
    )
    print(f"Successfully imported {count} nodes into persona '{args.persona_id}' (tenant: '{args.tenant_id}').")
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    setup_logging(args.verbose)
    contour = ContourEngine(args.db)
    reducer = StateReducer(args.db)
    planner = TurnPlanner(contour, reducer)
    generator = CognitiveGenerator(contour=contour, reducer=reducer, planner=planner)

    tenant_id = args.tenant_id
    persona_id = args.persona_id
    user_id = args.user_id

    result = generator.execute_turn(
        persona_id=persona_id,
        user_id=user_id,
        user_message=args.message,
        tenant_id=tenant_id,
    )

    print("\n--- OmniTwin Response ---")
    print(result.get("raw_answer", ""))
    print("------------------------")
    print(f"Grounded: {result.get('grounded')}")
    print(f"Contour Verified: {result.get('verified')}")
    citations = result.get("citations", [])
    print(f"Citations: {', '.join(citations) if citations else 'None'}")
    if not result.get("verified"):
        print(f"Rejection Reason: {result.get('rejection_reason')}")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    setup_logging(args.verbose)
    memory = HierarchicalMemory(db_path=args.db)
    tenant_id = args.tenant_id
    persona_id = args.persona_id

    print(f"=== Inspecting Persona: {persona_id} (Tenant: {tenant_id}) ===")
    episodes = memory.search_episodes(query="", tenant_id=tenant_id, persona_id=persona_id, limit=100)
    print(f"Total Episodic Memory (EP) Nodes: {len(episodes)}")
    for ep in episodes[:10]:
        print(f"  [{ep.get('id')}] {ep.get('title', 'Untitled')} (tier: {ep.get('tier', 'standard')})")
    if len(episodes) > 10:
        print(f"  ... and {len(episodes) - 10} more.")

    reducer = StateReducer(args.db)
    state = reducer.get_or_seed_state(persona_id, args.user_id, tenant_id=tenant_id)
    print(f"\nDynamic State for User '{args.user_id}':")
    rel = state.get("relationship_state", {})
    print(f"  Mood: {state.get('mood')} | Energy: {state.get('energy', 0.0):.2f}")
    print(f"  Role: {rel.get('role')} | Closeness: {rel.get('closeness', 0.0):.2f} | Trust: {rel.get('trust', 0.0):.2f}")
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    setup_logging(args.verbose)
    engine = CognitiveGraphEngine(args.db)
    tenant_id = args.tenant_id
    persona_id = args.persona_id

    graph_data = engine.build_graph(persona_id=persona_id, tenant_id=tenant_id)

    if args.format == "mermaid":
        mermaid_text = engine.generate_mermaid(graph_data)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(mermaid_text)
            print(f"Mermaid diagram saved to: {args.output}")
        else:
            print(mermaid_text)
    elif args.format == "d3":
        paths = engine.export_all(graph_data, output_dir=os.path.dirname(args.output) if args.output else ".")
        print(f"Exported interactive D3 graph to: {paths['html']}")
    else:
        out_json = json.dumps(graph_data, indent=2, ensure_ascii=False)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out_json)
            print(f"Graph JSON saved to: {args.output}")
        else:
            print(out_json)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="omnitwin",
        description="OmniTwin: Open-Source Cognitive Continuity Engine for AI Agents",
    )
    parser.add_argument("--version", action="store_true", help="Show OmniTwin version and exit")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")
    parser.add_argument("--db", default=os.getenv("OMNITWIN_DB_PATH", "omnitwin.db"), help="Path to SQLite database file")

    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # serve
    p_serve = subparsers.add_parser("serve", help="Run the gRPC cognitive-core service")
    p_serve.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    p_serve.add_argument("--port", type=int, default=50051, help="Port to listen on (default: 50051)")
    p_serve.add_argument("--auth-token", default=os.getenv("OMNITWIN_AUTH_TOKEN"), help="Required bearer auth token")
    p_serve.add_argument("--allow-insecure-remote", action="store_true", help="Permit binding to 0.0.0.0 without TLS (not recommended)")

    # init
    p_init = subparsers.add_parser("init", help="Initialize a fresh database schema and optional persona")
    p_init.add_argument("--persona", help="Optional path to persona JSON pack to import immediately")
    p_init.add_argument("--tenant-id", default="default", help="Tenant ID (default: default)")
    p_init.add_argument("--persona-id", default="default_twin", help="Persona ID (default: default_twin)")

    # import
    p_import = subparsers.add_parser("import", help="Import a persona JSON pack into the database")
    p_import.add_argument("file", help="Path to persona JSON file")
    p_import.add_argument("--tenant-id", default="default", help="Tenant ID")
    p_import.add_argument("--persona-id", default="default_twin", help="Persona ID")

    # query
    p_query = subparsers.add_parser("query", help="Execute a single grounded query against a persona")
    p_query.add_argument("message", help="User message to submit to the twin")
    p_query.add_argument("--tenant-id", default="default", help="Tenant ID")
    p_query.add_argument("--persona-id", default="default_twin", help="Persona ID")
    p_query.add_argument("--user-id", default="cli_user", help="User ID")

    # inspect
    p_inspect = subparsers.add_parser("inspect", help="Inspect memories and dynamic state of a persona")
    p_inspect.add_argument("--tenant-id", default="default", help="Tenant ID")
    p_inspect.add_argument("--persona-id", default="default_twin", help="Persona ID")
    p_inspect.add_argument("--user-id", default="cli_user", help="User ID to view state for")

    # graph
    p_graph = subparsers.add_parser("graph", help="Export visual knowledge graph of persona memories")
    p_graph.add_argument("--tenant-id", default="default", help="Tenant ID")
    p_graph.add_argument("--persona-id", default="default_twin", help="Persona ID")
    p_graph.add_argument("--format", choices=["mermaid", "d3", "json"], default="mermaid", help="Output format")
    p_graph.add_argument("-o", "--output", help="Output file path (default: stdout)")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version or args.subcommand == "version":
        return cmd_version(args)

    if not args.subcommand:
        parser.print_help()
        return 0

    commands = {
        "serve": cmd_serve,
        "init": cmd_init,
        "import": cmd_import,
        "query": cmd_query,
        "inspect": cmd_inspect,
        "graph": cmd_graph,
    }

    handler = commands.get(args.subcommand)
    if handler:
        try:
            return handler(args)
        except Exception as e:
            print(f"Error executing '{args.subcommand}': {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
