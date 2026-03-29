-- XYTHERION DISTRIBUTED CLUSTER (SUPABASE SCHEMA)
-- Role: Global data persistence and cluster orchestration.

-- 1. Attack Graph Table
CREATE TABLE IF NOT EXISTS attack_graph (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type VARCHAR(50) NOT NULL,
    target TEXT,
    vulnerability_score INTEGER DEFAULT 0,
    discovered_by VARCHAR(50),
    connections JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Task Assignments Table
CREATE TABLE IF NOT EXISTS task_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL,
    worker_id VARCHAR(50),
    target TEXT,
    task_type VARCHAR(50),
    priority INTEGER DEFAULT 5,
    status VARCHAR(20) DEFAULT 'pending',
    assigned_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    retry_count INTEGER DEFAULT 0,
    reassigned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Attack Results Table
CREATE TABLE IF NOT EXISTS attack_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL,
    worker_id VARCHAR(50),
    result JSONB NOT NULL,
    execution_time INTEGER,
    success BOOLEAN,
    vulnerabilities_found INTEGER DEFAULT 0,
    impact_score INTEGER DEFAULT 0,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Workers Table
CREATE TABLE IF NOT EXISTS workers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    worker_id VARCHAR(50) UNIQUE NOT NULL,
    specialty VARCHAR(50),
    capabilities JSONB DEFAULT '[]',
    status VARCHAR(20) DEFAULT 'offline',
    last_heartbeat TIMESTAMPTZ,
    current_tasks INTEGER DEFAULT 0,
    total_tasks_completed INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Attack Patterns Table
CREATE TABLE IF NOT EXISTS attack_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_key VARCHAR(100) UNIQUE NOT NULL,
    pattern_type VARCHAR(50),
    success_rate DECIMAL(5,4),
    avg_impact DECIMAL(5,2),
    usage_count INTEGER DEFAULT 0,
    last_used TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Optimization Indexes
CREATE INDEX IF NOT EXISTS idx_attack_graph_target ON attack_graph(target);
CREATE INDEX IF NOT EXISTS idx_task_assignments_status ON task_assignments(status);
CREATE INDEX IF NOT EXISTS idx_task_assignments_worker ON task_assignments(worker_id);

-- Automatic Timestamp Management
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_attack_graph_updated_at BEFORE UPDATE ON attack_graph
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_task_assignments_updated_at BEFORE UPDATE ON task_assignments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workers_updated_at BEFORE UPDATE ON workers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
