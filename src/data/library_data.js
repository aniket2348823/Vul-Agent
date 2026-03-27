// src/data/library_data.js

// ============================================================================
// SECTION 1: THE HIVE MIND (AGENTS)
// The 7 Sovereign Entities that control the swarm.
// ============================================================================
export const agents = [
    {
        id: "agent_omega",
        name: "Agent Omega",
        role: "The Orchestrator",
        description: "Strategic Command Center. Manages the high-level attack workflow, synchronizing the Scout and Breaker to ensure logical execution sequences.",
        color: "text-red-500",
        border: "border-red-500/50",
        bg_gradient: "from-red-500/10 to-transparent",
        capabilities: [
            "Attack Strategy Generation",
            "Workflow Synchronization",
            "Multi-Vector Coordination",
            "Global State Management"
        ]
    },
    {
        id: "agent_zeta",
        name: "Agent Zeta",
        role: "The Manager",
        description: "System Governance & Resource Controller. Monitors CPU/RAM usage, enforces throttling to prevent crashes, and holds the emergency Kill Switch.",
        color: "text-gray-400",
        border: "border-gray-400/50",
        bg_gradient: "from-gray-500/10 to-transparent",
        capabilities: [
            "PID Resource Throttling",
            "Anomaly Detection (Isolation Forest)",
            "Emergency Kill Switch",
            "Latency Governance"
        ]
    },
    {
        id: "agent_alpha",
        name: "Agent Alpha",
        role: "The Scout",
        description: "Reconnaissance & Mapping Specialist. Uses predictive pathing to discover hidden API routes and attack surfaces.",
        color: "text-blue-400",
        border: "border-blue-400/50",
        bg_gradient: "from-blue-500/10 to-transparent",
        capabilities: [
            "Predictive Crawling (LSTM)",
            "Tech Stack Fingerprinting",
            "Workflow Sequence Mapping",
            "Visual Recon (Computer Vision)"
        ]
    },
    {
        id: "agent_beta",
        name: "Agent Beta",
        role: "The Breaker",
        description: "Offensive Operations Commander. Executes payloads and mutations to bypass WAFs and exploit technical flaws.",
        color: "text-orange-500",
        border: "border-orange-500/50",
        bg_gradient: "from-orange-500/10 to-transparent",
        capabilities: [
            "Reinforcement Learning (Q-Table)",
            "Payload Mutation (Genetic Algo)",
            "Mass Assignment Injection",
            "Rate Limit Evasion"
        ]
    },
    {
        id: "agent_gamma",
        name: "Agent Gamma",
        role: "The Auditor",
        description: "Logic & Verification Analyst. Validates vulnerabilities using semantic analysis and entropy scoring to prevent false positives.",
        color: "text-purple-400",
        border: "border-purple-400/50",
        bg_gradient: "from-purple-500/10 to-transparent",
        capabilities: [
            "Diff Analysis (Levenshtein)",
            "Entropy Scoring",
            "Semantic Error Classification (BERT)",
            "Parameter Tampering"
        ]
    },
    {
        id: "agent_sigma",
        name: "Agent Sigma",
        role: "The Smith",
        description: "Generative Weaponssmith. Uses local LLMs to craft bespoke, context-aware payloads on the fly for specific targets.",
        color: "text-pink-400",
        border: "border-pink-400/50",
        bg_gradient: "from-pink-500/10 to-transparent",
        capabilities: [
            "LLM Payload Generation",
            "Context-Aware Prompting",
            "Polyglot Construction",
            "Code Analysis"
        ]
    },
    {
        id: "agent_kappa",
        name: "Agent Kappa",
        role: "The Librarian",
        description: "Long-Term Memory & RAG. Stores successful attack patterns in a Vector DB to recall exploits for similar targets.",
        color: "text-cyan-400",
        border: "border-cyan-400/50",
        bg_gradient: "from-cyan-500/10 to-transparent",
        capabilities: [
            "Vector Similarity Search",
            "Historical Exploit Retrieval",
            "Pattern Matching",
            "Knowledge Graphing"
        ]
    },
    {
        id: "THETA",
        name: "Agent Prism",
        role: "THE SENTINEL",
        description: "Defensive Text Analyst. Sanitizes inputs for Prompt Injection and Jailbreaks.",
        color: "text-emerald-500",
        border: "border-emerald-500/50",
        bg_gradient: "from-emerald-500/10 to-transparent",
        capabilities: [
            "Injection Shield",
            "Invisible Text Scan",
            "Jailbreak Detection",
            "Content Sanitization"
        ]
    },
    {
        id: "IOTA",
        name: "Agent Chi",
        role: "THE INSPECTOR",
        description: "Defensive UI Analyst. Detects Dark Patterns, Phishing, and Deceptive Buttons.",
        color: "text-emerald-500",
        border: "border-emerald-500/50",
        bg_gradient: "from-emerald-500/10 to-transparent",
        capabilities: [
            "Dark Pattern Hunter",
            "Phishing Radar",
            "Deceptive UX Scan",
            "Homoglyph Detection"
        ]
    }
];

// ============================================================================
// SECTION 2: THE ARSENAL (MODULES)
// The weapons used by the agents.
// ============================================================================
export const modules = [
    // --- A. LOGIC ASSASSINS (Business Logic) ---
    {
        id: "logic_tycoon",
        title: "The Tycoon",
        description: "Advanced parameter tampering engine. Detects financial logic flaws by injecting negative values, decimal overflows, and currency swaps to trick business rules.",
        agent: "Agent Gamma",
        category: "LOGIC",
        tags: ["Financial", "Tampering", "Logic"],
        stats: { stealth: 9, speed: 8, impact: 10 },
        ai_logic: "Uses Isolation Forest to detect if server response deviates from standard checkout flow when parameters are mutated."
    },
    {
        id: "logic_escalator",
        title: "The Escalator",
        description: "Mass Assignment vulnerability scanner. Attempts to inject privileged fields (e.g., 'is_admin', 'role') into standard API update requests to elevate privileges.",
        agent: "Agent Beta",
        category: "LOGIC",
        tags: ["Privilege", "Mass Assignment", "Auth"],
        stats: { stealth: 7, speed: 9, impact: 10 },
        ai_logic: "Uses NLP to predict likely hidden administrative field names based on API naming conventions."
    },
    {
        id: "logic_skipper",
        title: "The Skipper",
        description: "Workflow bypass detection. Maps multi-step processes (e.g., Cart -> Pay -> Receipt) and attempts to skip critical steps to achieve unauthorized states.",
        agent: "Agent Alpha",
        category: "LOGIC",
        tags: ["Workflow", "Bypass", "Sequence"],
        stats: { stealth: 8, speed: 6, impact: 9 },
        ai_logic: "Builds a dependency graph of API endpoints and uses graph traversal algorithms to find shortcuts."
    },
    {
        id: "logic_doppelganger",
        title: "Doppelganger (IDOR)",
        description: "Automated detection of Insecure Direct Object Reference vulnerabilities by manipulating resource IDs across multiple synchronized user sessions.",
        agent: "Agent Gamma",
        category: "LOGIC",
        tags: ["IDOR", "Auth", "Access Control"],
        stats: { stealth: 6, speed: 7, impact: 8 },
        ai_logic: "Maintains two active user sessions and uses Cosine Similarity to compare resource access patterns."
    },
    {
        id: "logic_chronomancer",
        title: "Chronomancer",
        description: "Race Condition testing engine for transactional API endpoints. Uses precise packet synchronization to exploit concurrency limits.",
        agent: "Agent Beta",
        category: "LOGIC",
        tags: ["Race Condition", "Concurrency", "Timing"],
        stats: { stealth: 5, speed: 10, impact: 7 },
        ai_logic: "Analyzes server response times to predict the optimal millisecond window for packet flooding."
    },

    // --- B. INFRASTRUCTURE BREAKERS (Technical) ---
    {
        id: "tech_sqli",
        title: "SQL Injection Probe",
        description: "Deep injection testing for SQL, NoSQL, and GraphQL. Uses mutation fuzzing to bypass WAF filters and dump database contents.",
        agent: "Agent Beta",
        category: "TECHNICAL",
        tags: ["Injection", "Database", "Critical"],
        stats: { stealth: 4, speed: 8, impact: 10 },
        ai_logic: "Uses Q-Learning (RL) to adapt payloads based on specific WAF error responses."
    },
    {
        id: "tech_jwt",
        title: "JWT Token Cracker",
        description: "Cryptographic analysis of JSON Web Tokens. Tests for 'None' algorithm, weak secrets, and key confusion attacks.",
        agent: "Agent Beta",
        category: "TECHNICAL",
        tags: ["Crypto", "Auth", "Tokens"],
        stats: { stealth: 8, speed: 5, impact: 9 },
        ai_logic: "Uses pattern recognition to identify likely signing keys based on developer habits."
    },
    {
        id: "tech_fuzzer",
        title: "API Fuzzer (REST)",
        description: "High-velocity fuzzing for RESTful endpoints. Injects garbage data, huge strings, and malformed JSON to trigger unhandled exceptions.",
        agent: "Agent Beta",
        category: "TECHNICAL",
        tags: ["Fuzzing", "Stability", "DoS"],
        stats: { stealth: 2, speed: 10, impact: 5 },
        ai_logic: "Uses a Genetic Algorithm to evolve fuzzing strings that cause the longest server processing times."
    },
    {
        id: "tech_auth_bypass",
        title: "Auth Bypass Tester",
        description: "Systematic testing of authentication gates. Tries method flipping (POST->GET), header stripping, and default credential stuffing.",
        agent: "Agent Alpha",
        category: "TECHNICAL",
        tags: ["Auth", "Bypass", "Config"],
        stats: { stealth: 6, speed: 9, impact: 8 },
        ai_logic: "Uses Predictive Pathing to guess unprotected administrative routes."
    }
];
