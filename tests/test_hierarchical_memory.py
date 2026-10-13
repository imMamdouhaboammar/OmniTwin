# Copyright 2026 Mamdouh Aboammar
# SPDX-License-Identifier: Apache-2.0
"""
Tests for Hierarchical Cognitive Memory Engine:
1. Multi-Tenant and Persona Boundary Isolation: Zero cross-tenant data leakage.
2. FTS5 Indexing & Search: Fast lexical and phrase recall.
3. Node Supersession: Contradiction edge creation and active flag toggling.
4. Cascading Deletion: Full purge of persona data across all relational tiers.
"""

import os
import tempfile
import pytest

from omnitwin.core.hierarchical_memory import HierarchicalMemory


@pytest.fixture
def temp_memory():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    memory = HierarchicalMemory(db_path)
    yield memory, db_path
    if os.path.exists(db_path):
        os.remove(db_path)


def test_tenant_and_persona_scoping(temp_memory):
    memory, _ = temp_memory

    # Seed Tenant 1 / Persona 1
    memory.index_ep(
        ep_id="ep_tenant1_01",
        meta_id="meta_t1",
        grp="identity",
        vector="career",
        kind="belief",
        text="Works as a cloud architect in Tokyo.",
        tenant_id="tenant_alpha",
        persona_id="persona_one",
    )

    # Seed Tenant 2 / Persona 2
    memory.index_ep(
        ep_id="ep_tenant2_01",
        meta_id="meta_t2",
        grp="identity",
        vector="career",
        kind="belief",
        text="Works as a botanical researcher in Oslo.",
        tenant_id="tenant_beta",
        persona_id="persona_two",
    )

    # Search as tenant_alpha
    results_alpha = memory.search_episodes(
        query="architect",
        tenant_id="tenant_alpha",
        persona_id="persona_one",
    )
    assert len(results_alpha) == 1
    assert results_alpha[0]["id"] == "ep_tenant1_01"

    # Search for "botanical" as tenant_alpha (should return 0 results)
    cross_results = memory.search_episodes(
        query="botanical",
        tenant_id="tenant_alpha",
        persona_id="persona_one",
    )
    assert len(cross_results) == 0

    # Search as tenant_beta
    results_beta = memory.search_episodes(
        query="botanical",
        tenant_id="tenant_beta",
        persona_id="persona_two",
    )
    assert len(results_beta) == 1
    assert results_beta[0]["id"] == "ep_tenant2_01"


def test_node_supersession(temp_memory):
    memory, _ = temp_memory

    # Old belief
    memory.index_ep(
        ep_id="ep_old_belief",
        meta_id="meta_01",
        grp="preferences",
        vector="editor",
        kind="preference",
        text="Prefers using Vim exclusively.",
        tenant_id="tenant_test",
        persona_id="persona_test",
    )

    # Superseding belief
    success = memory.supersede_ep(
        old_ep_id="ep_old_belief",
        new_ep={
            "id": "ep_new_belief",
            "grp": "preferences",
            "vector": "editor",
            "kind": "preference",
            "text": "Switched to Neovim with Lua configs.",
        },
        persona_id="persona_test",
        tenant_id="tenant_test",
    )
    assert success

    # Verify old node confidence is deprecated and edge created
    with memory._get_connection() as conn:
        old_row = conn.execute("SELECT confidence FROM ep WHERE id = 'ep_old_belief';").fetchone()
        assert old_row["confidence"] == 0.05

        # Check edge created
        edge_row = conn.execute(
            "SELECT * FROM associative_edges WHERE source_ep = 'ep_new_belief' AND target_ep = 'ep_old_belief';"
        ).fetchone()
        assert edge_row is not None
        assert edge_row["relation_type"] == "CONTRADICTS_SUPERSEDES"


def test_cascading_persona_deletion(temp_memory):
    memory, _ = temp_memory

    # Seed memories for persona_to_delete
    for i in range(5):
        memory.index_ep(
            ep_id=f"ep_del_{i}",
            meta_id=f"meta_del_{i}",
            grp="test",
            vector="test",
            kind="belief",
            text=f"Sample memory node {i}",
            tenant_id="tenant_test",
            persona_id="persona_to_delete",
        )

    # Seed memories for keeper_persona
    memory.index_ep(
        ep_id="ep_keep_01",
        meta_id="meta_keep_01",
        grp="test",
        vector="test",
        kind="belief",
        text="Keeper memory node",
        tenant_id="tenant_test",
        persona_id="keeper_persona",
    )

    # Delete persona_to_delete
    deleted_count = memory.delete_persona(tenant_id="tenant_test", persona_id="persona_to_delete")
    assert deleted_count == 5

    # Verify all nodes of deleted persona are gone
    remaining_deleted = memory.search_episodes("", tenant_id="tenant_test", persona_id="persona_to_delete")
    assert len(remaining_deleted) == 0

    # Verify keeper persona nodes remain untouched
    remaining_keeper = memory.search_episodes("", tenant_id="tenant_test", persona_id="keeper_persona")
    assert len(remaining_keeper) == 1
