-- Alpha V6 Deep Recon Database Schema Extensions
-- Run this in Supabase SQL Editor to create the new tables

-- Recon Relationships (entity-to-entity links)
CREATE TABLE IF NOT EXISTS recon_relationships (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    src_entity_id TEXT NOT NULL,
    dst_entity_id TEXT NOT NULL,
    relationship TEXT NOT NULL,
    confidence REAL DEFAULT 0.0,
    evidence JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (src_entity_id, dst_entity_id, relationship)
);

CREATE INDEX IF NOT EXISTS idx_recon_rel_scan ON recon_relationships(scan_id);
CREATE INDEX IF NOT EXISTS idx_recon_rel_src ON recon_relationships(src_entity_id);
CREATE INDEX IF NOT EXISTS idx_recon_rel_dst ON recon_relationships(dst_entity_id);

-- Recon Tool Outputs (per-tool execution tracking)
CREATE TABLE IF NOT EXISTS recon_tool_outputs (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    phase TEXT NOT NULL,
    parser_version TEXT DEFAULT 'v1',
    raw_artifact_id TEXT,
    normalized_count INTEGER DEFAULT 0,
    status TEXT NOT NULL,
    errors JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recon_tool_scan ON recon_tool_outputs(scan_id);

-- Recon OOB Interactions (Interactsh callbacks)
CREATE TABLE IF NOT EXISTS recon_oob_interactions (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    provider TEXT NOT NULL DEFAULT 'interactsh',
    interaction_type TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    source_endpoint TEXT DEFAULT '',
    raw JSONB DEFAULT '{}',
    severity TEXT DEFAULT 'high',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recon_oob_scan ON recon_oob_interactions(scan_id);
CREATE INDEX IF NOT EXISTS idx_recon_oob_corr ON recon_oob_interactions(correlation_id);

-- Add phase tracking columns to recon_runs if not present
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='recon_runs' AND column_name='current_phase') THEN
        ALTER TABLE recon_runs ADD COLUMN current_phase TEXT DEFAULT 'initialization';
        ALTER TABLE recon_runs ADD COLUMN phase_data JSONB DEFAULT '{}';
    END IF;
END $$;
