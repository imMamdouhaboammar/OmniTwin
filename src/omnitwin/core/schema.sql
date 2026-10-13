-- Copyright 2026 Mamdouh Aboammar
-- SPDX-License-Identifier: Apache-2.0

-- Canonical SQLite Schema for OmniTwin Cognitive & Behavioral Engine
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    persona_id TEXT NOT NULL DEFAULT 'default',
    source_type TEXT NOT NULL CHECK(source_type IN ('conversation', 'whatsapp', 'telegram', 'youtube', 'article', 'book', 'interview', 'talk', 'profile', 'synthetic')),
    title TEXT NOT NULL,
    url TEXT,
    content_hash TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    raw_path TEXT
);

CREATE INDEX IF NOT EXISTS idx_meta_tenant_persona ON meta(tenant_id, persona_id);

CREATE TABLE IF NOT EXISTS ep (
    id TEXT PRIMARY KEY,
    meta_id TEXT NOT NULL REFERENCES meta(id) ON DELETE CASCADE,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    persona_id TEXT NOT NULL DEFAULT 'default',
    grp TEXT NOT NULL,
    vector TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN (
        'belief', 'heuristic', 'framework', 'stance', 'antipattern',
        'procedure', 'reasoning', 'anecdote', 'prediction', 'axiom',
        'relation', 'preference'
    )),
    subject TEXT,
    relation TEXT,
    object TEXT,
    text TEXT NOT NULL,
    tier TEXT NOT NULL CHECK(tier IN ('A', 'B', 'C')),
    confidence REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
    t_start INTEGER,
    deeplink TEXT,
    as_of TEXT
);

CREATE INDEX IF NOT EXISTS idx_ep_meta ON ep(meta_id);
CREATE INDEX IF NOT EXISTS idx_ep_tenant_persona ON ep(tenant_id, persona_id);
CREATE INDEX IF NOT EXISTS idx_ep_grp_vector ON ep(grp, vector);
CREATE INDEX IF NOT EXISTS idx_ep_tier ON ep(tier);

-- FTS5 Full Text Search index for candidate recall
CREATE VIRTUAL TABLE IF NOT EXISTS ep_fts USING fts5(
    text,
    subject,
    object,
    grp,
    vector,
    persona_id,
    tenant_id,
    content='ep',
    content_rowid='rowid'
);

-- FTS synchronization triggers
CREATE TRIGGER IF NOT EXISTS ep_ai AFTER INSERT ON ep BEGIN
    INSERT INTO ep_fts(rowid, text, subject, object, grp, vector, persona_id, tenant_id)
    VALUES (new.rowid, new.text, new.subject, new.object, new.grp, new.vector, new.persona_id, new.tenant_id);
END;

CREATE TRIGGER IF NOT EXISTS ep_ad AFTER DELETE ON ep BEGIN
    INSERT INTO ep_fts(ep_fts, rowid, text, subject, object, grp, vector, persona_id, tenant_id)
    VALUES ('delete', old.rowid, old.text, old.subject, old.object, old.grp, old.vector, old.persona_id, old.tenant_id);
END;

CREATE TRIGGER IF NOT EXISTS ep_au AFTER UPDATE ON ep BEGIN
    INSERT INTO ep_fts(ep_fts, rowid, text, subject, object, grp, vector, persona_id, tenant_id)
    VALUES ('delete', old.rowid, old.text, old.subject, old.object, old.grp, old.vector, old.persona_id, old.tenant_id);
    INSERT INTO ep_fts(rowid, text, subject, object, grp, vector, persona_id, tenant_id)
    VALUES (new.rowid, new.text, new.subject, new.object, new.grp, new.vector, new.persona_id, new.tenant_id);
END;

-- Temporal Milestones (life eras: Early Life, Career, Milestones)
CREATE TABLE IF NOT EXISTS life_milestones (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    persona_id TEXT NOT NULL DEFAULT 'default',
    era_title TEXT NOT NULL,
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL,
    summary_text TEXT NOT NULL,
    key_themes_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_milestones_tenant_persona ON life_milestones(tenant_id, persona_id);

-- Associative Neural Edges (Hebbian co-activation weights)
CREATE TABLE IF NOT EXISTS associative_edges (
    source_ep TEXT NOT NULL,
    target_ep TEXT NOT NULL,
    relation_type TEXT NOT NULL, -- ASSOCIATIVE_TRIGGERS, TEMPORAL_PRECEDES, CONTRADICTS_SUPERSEDES
    weight REAL DEFAULT 1.0,
    last_activated_unix REAL DEFAULT 0,
    PRIMARY KEY (source_ep, target_ep, relation_type)
);

CREATE INDEX IF NOT EXISTS idx_edges_source ON associative_edges(source_ep);
CREATE INDEX IF NOT EXISTS idx_edges_target ON associative_edges(target_ep);

-- Raw Episodic Event Chunks (Tier 0 Storage)
CREATE TABLE IF NOT EXISTS episodic_archive (
    event_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    persona_id TEXT NOT NULL DEFAULT 'default',
    era_id TEXT,
    timestamp_unix REAL NOT NULL,
    speaker TEXT NOT NULL,
    source_medium TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    consolidated_into_ep TEXT
);

CREATE INDEX IF NOT EXISTS idx_archive_tenant_persona ON episodic_archive(tenant_id, persona_id);

-- FTS5 index for Tier 0 fast keyword discovery
CREATE VIRTUAL TABLE IF NOT EXISTS episodic_archive_fts USING fts5(
    event_id UNINDEXED,
    raw_text,
    persona_id,
    tenant_id,
    content=episodic_archive,
    content_rowid=rowid
);

CREATE TRIGGER IF NOT EXISTS archive_ai AFTER INSERT ON episodic_archive BEGIN
    INSERT INTO episodic_archive_fts(rowid, event_id, raw_text, persona_id, tenant_id)
    VALUES (new.rowid, new.event_id, new.raw_text, new.persona_id, new.tenant_id);
END;

CREATE TRIGGER IF NOT EXISTS archive_ad AFTER DELETE ON episodic_archive BEGIN
    INSERT INTO episodic_archive_fts(episodic_archive_fts, rowid, event_id, raw_text, persona_id, tenant_id)
    VALUES ('delete', old.rowid, old.event_id, old.raw_text, old.persona_id, old.tenant_id);
END;

-- Runs and Deliveries table for "No ID, No Claim" verification
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    persona_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    intent TEXT NOT NULL,
    created_at TEXT NOT NULL,
    delivery_ep_ids TEXT NOT NULL, -- JSON array of selected EP IDs
    answer TEXT,
    verified INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_runs_tenant_persona ON runs(tenant_id, persona_id, user_id);

-- Dynamic State Table
CREATE TABLE IF NOT EXISTS dynamic_state (
    tenant_id TEXT NOT NULL DEFAULT 'default',
    persona_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    mood TEXT NOT NULL,
    energy REAL NOT NULL CHECK(energy >= 0.0 AND energy <= 1.0),
    conversation_appetite TEXT NOT NULL,
    current_mode TEXT NOT NULL,
    active_concerns_json TEXT NOT NULL,
    active_threads_json TEXT NOT NULL,
    relationship_state_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, persona_id, user_id)
);
