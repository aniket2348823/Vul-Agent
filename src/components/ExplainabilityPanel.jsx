import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// 1. THE NARRATIVE DICTIONARY (The Logic Core)
const NARRATIVES = {
    "THETA": {
        "PROMPT_INJECTION": {
            title: "COGNITIVE ATTACK DETECTED",
            desc: "Agent Theta detected text hidden in the DOM designed to override your AI's instructions.",
            consequence: "Prevented the AI from executing malicious commands."
        },
        "HIDDEN_TEXT": {
            title: "INVISIBLE CONTEXT TRAP",
            desc: "Text was found with 'opacity: 0'. This is often used to feed false information to AI agents.",
            consequence: "Blocked data ingestion from this element."
        }
    },
    "IOTA": {
        "DARK_PATTERN": {
            title: "DECEPTIVE UI PATTERN",
            desc: "Agent Iota identified a mismatch between the button text ('Cancel') and its action ('Submit').",
            consequence: "Prevented unintended form submission."
        },
        "PHISHING": {
            title: "HOMOGLYPH DOMAIN DETECTED",
            desc: "The current URL visually mimics a trusted domain (e.g. 'g00gle.com') but is fraudulent.",
            consequence: "Blocked navigation and data entry."
        }
    }
};

export default function ExplainabilityPanel({ latestEvent }) {
    const [narrative, setNarrative] = useState(null);

    // 2. TRANSLATION LOGIC (On New Event)
    useEffect(() => {
        if (!latestEvent) return;

        const agent = latestEvent.agent; // "THETA" or "IOTA" (Note: payload uses 'agent', user provided 'agent_id' - adjusting to match backend payload)
        // Backend sends "agent_theta", so we need to normalize or map it
        const agentKey = agent?.toUpperCase().includes('THETA') ? 'THETA' : (agent?.toUpperCase().includes('IOTA') ? 'IOTA' : 'SYSTEM');

        const type = latestEvent.threat_type || "PROMPT_INJECTION"; // Default fallback

        // Lookup the story, or use a generic fallback
        const template = NARRATIVES[agentKey]?.[type] || {
            title: "SECURITY ANOMALY",
            desc: `Agent ${agentKey} flagged suspicious behavior based on heuristic analysis.`,
            consequence: "Interaction halted for safety."
        };

        setNarrative({ ...template, timestamp: new Date().toLocaleTimeString() });

    }, [latestEvent]);

    if (!narrative) return <EmptyState />;

    return (
        <div className="w-full h-full bg-black/80 border border-cyan-500/30 rounded-xl p-6 backdrop-blur-md flex flex-col">
            {/* HEADER */}
            <div className="flex items-center justify-between mb-6 border-b border-cyan-500/20 pb-2">
                <h2 className="text-cyan-400 font-mono text-lg tracking-widest flex items-center gap-2">
                    <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse" />
                    AI DECISION LOGIC
                </h2>
                <span className="text-xs text-cyan-600 font-mono">{narrative.timestamp}</span>
            </div>

            {/* THE EXPLANATION CONTENT */}
            <AnimatePresence mode="wait">
                <motion.div
                    key={latestEvent?.id || "init"}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 10 }}
                    className="space-y-4"
                >
                    {/* 1. THE TITLE */}
                    <div className="p-3 bg-red-500/10 border-l-4 border-red-500 rounded-r-md">
                        <h3 className="text-red-400 font-bold text-xl">{narrative.title}</h3>
                    </div>

                    {/* 2. THE ANALYSIS (The "Why") */}
                    <div className="space-y-1">
                        <label className="text-xs text-gray-500 font-mono uppercase">Reasoning Engine</label>
                        <p className="text-gray-300 text-sm leading-relaxed">
                            {narrative.desc}
                        </p>
                    </div>

                    {/* 3. THE EVIDENCE (The "Raw Data") */}
                    <div className="bg-gray-900/50 p-3 rounded border border-gray-700 font-mono text-xs text-green-400 overflow-x-auto">
                        <div className="flex justify-between text-gray-500 mb-1">
                            <span>EVIDENCE_SNAPSHOT</span>
                            <span>RAW</span>
                        </div>
                        {latestEvent?.evidence || JSON.stringify(latestEvent, null, 2)}
                    </div>

                    {/* 4. THE OUTCOME */}
                    <div className="flex items-center gap-3 mt-4 pt-4 border-t border-gray-800">
                        <div className="px-3 py-1 bg-red-500 text-black font-bold text-xs rounded">
                            BLOCKED
                        </div>
                        <span className="text-xs text-gray-400">
                            {narrative.consequence}
                        </span>
                    </div>

                </motion.div>
            </AnimatePresence>
        </div>
    );
}

function EmptyState() {
    return (
        <div className="glass-panel-dash rounded-2xl w-full h-full flex items-center justify-center p-6 text-center">
            <div className="space-y-2 opacity-50">
                <div className="text-4xl">🛡️</div>
                <h3 className="text-gray-400 font-mono text-sm">SYSTEM IDLE</h3>
                <p className="text-gray-600 text-xs">Waiting for threat interception...</p>
            </div>
        </div>
    );
}
