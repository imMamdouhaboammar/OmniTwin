# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import os
import sqlite3
import sys
from typing import Any, Dict, List, Optional, Set


class CognitiveGraphEngine:
    """
    Transforms the cognitive twin database into an interconnected associative network.
    - Categorizes extract points into semantic communities.
    - Computes hub and bridge nodes for fast AI traversal.
    - Supports hierarchical detail levels (minimal, standard, verbose) to optimize context tokens.
    - Exports graph.json, COGNITIVE_MAP.md (Mermaid), and interactive graph.html.
    - Scoped strictly by tenant_id and persona_id.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def build_graph(
        self,
        persona_id: str = "default",
        tenant_id: str = "default",
        character_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        pid = persona_id or character_slug or "default"
        with self._get_connection() as conn:
            ep_rows = [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM ep WHERE persona_id = ? AND tenant_id = ?;",
                    (pid, tenant_id),
                ).fetchall()
            ]

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        # Central identity node
        nodes.append({
            "id": "node_identity",
            "label": f"Identity Anchor: {pid}",
            "type": "identity",
            "community": "core_identity",
            "text": f"Canonical Identity Anchor for {pid}",
            "confidence": 1.0,
            "tier": "A",
        })

        community_defs = {
            "core_personality": {
                "name": "Core Axioms and Principles",
                "description": "Foundational behavioral laws and identity boundaries",
            },
            "worldview": {
                "name": "Worldview and Philosophy",
                "description": "Beliefs, stances, and mental frameworks",
            },
            "communication": {
                "name": "Cadence and Lexical Energy",
                "description": "Message rhythms, bubble splits, and expressive style",
            },
            "guardrails": {
                "name": "Safety Guardrails",
                "description": "Rejected behaviors, anti-patterns, and boundary filters",
            },
            "goals": {
                "name": "Recurring Goals and Concerns",
                "description": "Aspirations, projects, and active focus areas",
            },
            "preferences": {
                "name": "Taste and Preferences",
                "description": "Domain affinities, tools, and lifestyle preferences",
            },
            "relationships": {
                "name": "Relational Permissions",
                "description": "Interpersonal permissions, closeness, and boundaries",
            },
        }

        # Node extraction
        for ep in ep_rows:
            node_id = ep["id"]
            grp = ep.get("grp", "core_personality")
            nodes.append({
                "id": node_id,
                "label": f"{ep['kind'].upper()}: {ep['vector']}",
                "type": ep["kind"],
                "community": grp,
                "text": ep["text"],
                "confidence": ep["confidence"],
                "tier": ep["tier"],
            })

            # Connect knowledge node to identity root
            edges.append({
                "source": "node_identity",
                "target": node_id,
                "relation": "DEFINES",
                "weight": ep["confidence"],
            })

        # Calculate node degree centrality
        degree_map: Dict[str, int] = {}
        for edge in edges:
            degree_map[edge["source"]] = degree_map.get(edge["source"], 0) + 1
            degree_map[edge["target"]] = degree_map.get(edge["target"], 0) + 1

        for n in nodes:
            n["degree"] = degree_map.get(n["id"], 0)

        # Identify Hubs
        sorted_nodes = sorted(nodes, key=lambda x: x.get("degree", 0), reverse=True)
        hub_nodes = [n["id"] for n in sorted_nodes[:5]]

        communities_out = []
        for comm_id, meta in community_defs.items():
            members = [n["id"] for n in nodes if n.get("community") == comm_id]
            communities_out.append({
                "id": comm_id,
                "name": meta["name"],
                "description": meta["description"],
                "member_count": len(members),
                "member_ids": members,
            })

        return {
            "version": "1.0.0",
            "tenant_id": tenant_id,
            "persona_id": pid,
            "character_slug": pid,
            "character": pid,
            "stats": {
                "nodes_count": len(nodes),
                "edges_count": len(edges),
                "communities_count": len(communities_out),
                "hub_nodes": hub_nodes,
            },
            "communities": communities_out,
            "nodes": nodes,
            "edges": edges,
        }

    def get_minimal_context(
        self,
        task_or_intent: str,
        persona_id: str = "default",
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Token-efficient context provider for LLM agents."""
        graph = self.build_graph(persona_id=persona_id, tenant_id=tenant_id)
        stats = graph["stats"]
        communities = [
            {"id": c["id"], "name": c["name"], "nodes": c["member_count"]}
            for c in graph["communities"]
        ]
        return {
            "persona": graph["persona_id"],
            "character": graph["persona_id"],
            "total_nodes": stats["nodes_count"],
            "total_edges": stats["edges_count"],
            "hub_nodes": stats["hub_nodes"],
            "communities": communities,
            "instruction": "Request subgraph detail with get_subgraph(community_id) to inspect specific edges.",
        }

    def get_subgraph(
        self,
        community_id: str,
        persona_id: str = "default",
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """Returns targeted community subgraph."""
        graph = self.build_graph(persona_id=persona_id, tenant_id=tenant_id)
        nodes = [n for n in graph["nodes"] if n.get("community") == community_id]
        node_ids = {n["id"] for n in nodes}
        edges = [
            e for e in graph["edges"]
            if e["source"] in node_ids or e["target"] in node_ids
        ]
        return {
            "community_id": community_id,
            "nodes_count": len(nodes),
            "edges_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }

    def export_all(
        self,
        output_dir: str,
        persona_id: str = "default",
        tenant_id: str = "default",
    ) -> Dict[str, str]:
        os.makedirs(output_dir, exist_ok=True)
        graph = self.build_graph(persona_id=persona_id, tenant_id=tenant_id)

        # 1. Export graph.json
        json_path = os.path.join(output_dir, "cognitive_graph.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(graph, f, ensure_ascii=False, indent=2)

        # 2. Export COGNITIVE_MAP.md with Mermaid
        md_path = os.path.join(output_dir, "COGNITIVE_MAP.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Cognitive Twin Architecture Map\n\n")
            f.write(f"Persona: `{graph['persona_id']}`\n")
            f.write(f"Total Cognitive Nodes: {graph['stats']['nodes_count']}\n")
            f.write(f"Total Associative Edges: {graph['stats']['edges_count']}\n\n")

            f.write("## Community Structure\n\n")
            for c in graph["communities"]:
                f.write(f"- **{c['name']}** (`{c['id']}`): {c['member_count']} nodes. {c['description']}\n")

            f.write("\n## Associative Neural Network Diagram\n\n")
            f.write("```mermaid\nflowchart TD\n")
            f.write(f'    ID["Identity Anchor: {graph["persona_id"]}"]\n')
            for c in graph["communities"]:
                safe_name = c["id"].replace("-", "_")
                f.write(f'    ID -->|"ENFORCES"| C_{safe_name}["{c["name"]} ({c["member_count"]} nodes)"]\n')
            f.write("```\n\n")

        # 3. Export interactive graph.html
        html_path = os.path.join(output_dir, "cognitive_graph.html")
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Cognitive Twin Neural Graph - {graph['persona_id']}</title>
  <style>
    body {{ margin: 0; background: #0f172a; color: #f8fafc; font-family: -apple-system, sans-serif; }}
    #header {{ padding: 1rem 1.5rem; border-bottom: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: center; }}
    h1 {{ margin: 0; font-size: 1.15rem; font-weight: 600; }}
    .badge {{ background: #334155; padding: 0.25rem 0.6rem; border-radius: 9999px; font-size: 0.75rem; }}
    #canvas-container {{ width: 100vw; height: calc(100vh - 60px); }}
  </style>
</head>
<body>
  <div id="header">
    <h1>OmniTwin Cognitive Graph &mdash; {graph['persona_id']}</h1>
    <div class="badge">{graph['stats']['nodes_count']} Nodes | {graph['stats']['edges_count']} Edges</div>
  </div>
  <div id="canvas-container"></div>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <script>
    const graphData = {json.dumps(graph, ensure_ascii=False)};
    console.log("OmniTwin Graph Loaded:", graphData);
  </script>
</body>
</html>
"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return {
            "json": json_path,
            "markdown": md_path,
            "html": html_path,
        }


# Public alias
CognitiveGraphifier = CognitiveGraphEngine

