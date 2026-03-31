-- VULAGENT ELITE DISTRIBUTED CLUSTER (SUPABASE SCHEMA)
-- Role: Single Source of Truth for Autonomous Intelligence Coordination

-- 1. Vulnerabilities (Verified Findings)
CREATE TABLE IF NOT EXISTS vulnerabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id VARCHAR(100) NOT NULL,
    endpoint TEXT NOT NULL,
    vuln_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL, -- LOW, MEDIUM, HIGH, CRITICAL
    evidence JSONB NOT NULL,
    validated_by VARCHAR(50), -- agent-alpha, agent-omega
    description TEXT,
    remediation_advice TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(scan_id, endpoint, vuln_type) -- Deduplication Constraint
);

-- 2. Exploit Results (Evidence of Successful Attacks)
CREATE TABLE IF NOT EXISTS exploit_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vuln_id UUID REFERENCES vulnerabilities(id) ON DELETE CASCADE,
    payload TEXT NOT NULL,
    worker_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL, -- EXPLOITED, BLOCKED, FAILED
    response_dump TEXT,
    execution_time_ms INTEGER,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Attack Graph (Relational Intelligence)
CREATE TABLE IF NOT EXISTS attack_graph (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL,
    target_id UUID NOT NULL,
    relationship_type VARCHAR(50) NOT NULL, -- PIVOT, DEPENDENCY, ESCALATION
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Remediation (AI-Generated Fixes)
CREATE TABLE IF NOT EXISTS remediation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vuln_id UUID REFERENCES vulnerabilities(id) ON DELETE CASCADE,
    strategy TEXT NOT NULL,
    code_fix TEXT,
    applied BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Patches (Deployment State)
CREATE TABLE IF NOT EXISTS patches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    remediation_id UUID REFERENCES remediation(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    diff_content TEXT,
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, DEPLOYED, REJECTED
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 6. CI/CD Logs (Validation Tracking)
CREATE TABLE IF NOT EXISTS ci_cd_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patch_id UUID REFERENCES patches(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL, -- BUILD, TEST, VALIDATE
    result VARCHAR(20) NOT NULL, -- PASS, FAIL
    logs TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Distributed Tasks (Node Coordination)
CREATE TABLE IF NOT EXISTS distributed_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id VARCHAR(100) NOT NULL,
    task_type VARCHAR(50) NOT NULL, -- RECON, FUZZ, EXPLOIT, PATCH
    target TEXT NOT NULL,
    priority INTEGER DEFAULT 5,
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, RUNNING, COMPLETED, FAILED
    locked_by VARCHAR(50), -- worker-id
    lock_time TIMESTAMPTZ,
    payload JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Optimization & Coordination Indexes
CREATE INDEX IF NOT EXISTS idx_vuln_endpoint ON vulnerabilities(endpoint);
CREATE INDEX IF NOT EXISTS idx_vuln_scan ON vulnerabilities(scan_id);
CREATE INDEX IF NOT EXISTS idx_exploit_vuln ON exploit_results(vuln_id);
CREATE INDEX IF NOT EXISTS idx_graph_source ON attack_graph(source_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON distributed_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_lock ON distributed_tasks(locked_by) WHERE locked_by IS NOT NULL;

-- Automatic Timestamp Management
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON distributed_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
