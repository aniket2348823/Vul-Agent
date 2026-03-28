import React, { useState, useEffect, useRef } from 'react';
import Navigation from './Navigation';
import { motion } from 'framer-motion';
import { LIQUID_SPRING } from '../lib/constants';


const MAX_THREAT_ROWS = 400;

const Dashboard = ({ navigate }) => {
    const [stats, setStats] = useState({
        metrics: { total_scans: 0, active_scans: 0, vulnerabilities: 0, critical: 0 },
        v6_metrics: {
            injections_blocked: 0,
            deceptive_ui_blocked: 0,
            risk_score: 0
        },
        graph_data: [],
        threat_feed: []
    });

    const [latestThreat, setLatestThreat] = useState(null);
    const [scanActive, setScanActive] = useState(false);
    const [scanTargetUrl, setScanTargetUrl] = useState('');

    // CRITICAL FIX: Use refs so flushBuffer always sees current values (no stale closures)
    const scanActiveRef = useRef(false);
    const scanTargetUrlRef = useRef('');

    // Keep refs in sync with state
    useEffect(() => { scanActiveRef.current = scanActive; }, [scanActive]);
    useEffect(() => { scanTargetUrlRef.current = scanTargetUrl; }, [scanTargetUrl]);

    const wsRef = useRef(null);
    const statsBuffer = useRef([]);
    const bufferTimer = useRef(null);
    const requestCountRef = useRef(0);

    // Helper: Extract domain from URL for matching
    const extractDomain = (url) => {
        try {
            const cleaned = url.replace(/^https?:\/\//, '');
            return cleaned.split('/')[0].split(':')[0].toLowerCase();
        } catch {
            return '';
        }
    };

    const flushBuffer = () => {
        const events = statsBuffer.current;
        if (events.length === 0) return;
        statsBuffer.current = [];

        setStats(prev => {
            let nextState = { ...prev };
            events.forEach(data => {
                // SCAN LIFECYCLE: Start populating on scan start, clear on complete
                if (data.type === 'SCAN_UPDATE') {
                    const status = data.payload?.status;
                    if (status === 'Running' || status === 'Initializing') {
                        setScanActive(true);
                        scanActiveRef.current = true;
                        // Store target URL for filtering
                        if (data.payload?.target_url) {
                            setScanTargetUrl(data.payload.target_url);
                            scanTargetUrlRef.current = data.payload.target_url;
                        }
                        // Clear previous data when a NEW scan starts
                        if (status === 'Initializing') {
                            nextState.threat_feed = [];
                            nextState.graph_data = [];
                            requestCountRef.current = 0;
                        }
                    } else if (status === 'Completed' || status === 'Finalizing') {
                        setScanActive(false);
                        scanActiveRef.current = false;
                        setScanTargetUrl('');
                        scanTargetUrlRef.current = '';
                        // Clear threat feed and graph when scan completes
                        nextState.threat_feed = [];
                        nextState.graph_data = [];
                        requestCountRef.current = 0;
                    }
                }

                if (data.type === 'VULN_UPDATE') {
                    nextState.metrics = data.payload.metrics || data.payload;
                }
                else if (['LIVE_THREAT_LOG', 'ATTACK_HIT', 'VULN_CONFIRMED', 'LOG', 'JOB_ASSIGNED', 'RECON_PACKET', 'KEY_CAPTURE', 'LIVE_ATTACK_FEED'].includes(data.type)) {
                    if (data.type === 'LIVE_THREAT_LOG') {
                        setLatestThreat(data.payload);
                    }
                    const defaultV6 = { injections_blocked: 0, deceptive_ui_blocked: 0, risk_score: 0 };
                    const currentV6 = nextState.v6_metrics || defaultV6;
                    const newMetrics = { ...currentV6 };

                    // --- DYNAMIC RISK SCORING: Derive risk from severity, not hardcoded ---
                    const severityToRisk = (sev) => {
                        const map = { 'CRITICAL': 95, 'HIGH': 75, 'MEDIUM': 50, 'LOW': 25, 'INFO': 10 };
                        return map[sev?.toUpperCase()] || 30;
                    };

                    let threat = data.payload;
                    if (data.type === 'ATTACK_HIT' || data.type === 'JOB_ASSIGNED') {
                        threat = {
                            timestamp: new Date().toLocaleTimeString(),
                            agent: data.source || 'agent_beta',
                            threat_type: data.type === 'JOB_ASSIGNED' ? 'JOB DISPATCHED' : 'ATTACK GENERATED',
                            url: data.payload?.url || data.payload?.target || (typeof data.payload === 'string' ? data.payload.substring(0, 40) : 'System Action'),
                            severity: 'INFO',
                            risk_score: severityToRisk('INFO')
                        };
                    } else if (data.type === 'VULN_CONFIRMED') {
                        const confirmedSev = data.payload?.severity || 'CRITICAL';
                        threat = {
                            timestamp: new Date().toLocaleTimeString(),
                            agent: data.source || 'agent_gamma',
                            threat_type: data.payload?.type || 'VULNERABILITY',
                            url: data.payload?.url || data.payload?.id || 'Confirmed Exploit',
                            severity: confirmedSev,
                            risk_score: severityToRisk(confirmedSev)
                        };
                    } else if (data.type === 'LOG') {
                        threat = {
                            timestamp: new Date().toLocaleTimeString(),
                            agent: data.source || 'system',
                            threat_type: 'SYSTEM LOG',
                            url: typeof data.payload === 'string' ? data.payload.substring(0, 60) : 'Log Entry',
                            severity: 'LOW',
                            risk_score: severityToRisk('LOW')
                        };
                    } else if (data.type === 'RECON_PACKET') {
                        threat = {
                            timestamp: new Date().toLocaleTimeString(),
                            agent: 'spy_v2',
                            threat_type: 'TRAFFIC INTERCEPTED',
                            url: data.payload?.url || 'Unknown Endpoint',
                            severity: data.payload?.severity || 'INFO',
                            risk_score: data.payload?.risk_score || severityToRisk(data.payload?.severity || 'INFO')
                        };
                    } else if (data.type === 'KEY_CAPTURE') {
                        threat = {
                            timestamp: new Date().toLocaleTimeString(),
                            agent: 'synapse_v2',
                            threat_type: 'CREDENTIAL LEAK',
                            url: data.payload?.url || 'Sensitive Header',
                            severity: 'HIGH',
                            risk_score: severityToRisk('HIGH')
                        };
                    } else if (data.type === 'LIVE_ATTACK_FEED') {
                        const attackSev = data.payload?.severity || 'HIGH';
                        threat = {
                            timestamp: data.payload.timestamp || new Date().toLocaleTimeString(),
                            agent: data.payload.agent || 'agent_sigma',
                            threat_type: `[ATTACK] ${data.payload.arsenal?.toUpperCase() || 'GENERAL'}`,
                            url: data.payload.url || 'Target Endpoint',
                            severity: attackSev,
                            risk_score: data.payload.risk_score || severityToRisk(attackSev),
                            action: data.payload.action,
                            payload_data: data.payload.payload
                        };
                    }

                    if (['PROMPT_INJECTION', 'INVISIBLE_TEXT', 'HIDDEN_TEXT'].includes(threat.threat_type)) {
                        newMetrics.injections_blocked += 1;
                    } else if (['DECEPTIVE_UI', 'PHISHING', 'ROACH_MOTEL', 'DARK_PATTERN_BLOCK'].includes(threat.threat_type)) {
                        newMetrics.deceptive_ui_blocked += 1;
                    }

                    // --- DYNAMIC RISK: Weighted moving average, more reactive to new events ---
                    let incomingScore = threat.risk_score || severityToRisk(threat.severity);
                    let prevScore = newMetrics.risk_score || 0;
                    newMetrics.risk_score = prevScore === 0 ? incomingScore : Math.round(0.45 * incomingScore + 0.55 * prevScore);

                    nextState.v6_metrics = newMetrics;

                    // --- SCAN-AWARE FEED FILTERING (V7 FIX: Show all events during active scan) ---
                    // During active scan: Show ALL scanner events (they're all relevant to the current operation)
                    // When no scan is active: don't show noise
                    let shouldAddToFeed = false;

                    const currentScanActive = scanActiveRef.current;
                    const currentTargetUrl = scanTargetUrlRef.current;

                    if (currentScanActive) {
                        // During active scan: show ALL events from agents
                        // These are ALL related to the current scan operation
                        shouldAddToFeed = true;
                    } else if (data.type === 'VULN_CONFIRMED') {
                        // Always show confirmed vulns even when no scan is active
                        shouldAddToFeed = true;
                    }
                    // When no scan is active and event is not a confirmed vuln, don't add noise

                    if (shouldAddToFeed) {
                        const updatedFeed = [threat, ...(nextState.threat_feed || [])];
                        nextState.threat_feed = updatedFeed.length > MAX_THREAT_ROWS 
                            ? updatedFeed.slice(0, MAX_THREAT_ROWS) 
                            : updatedFeed;
                    }
                    
                    // Sync graph with request count (Request Activity) - only during active scan
                    if (currentScanActive) {
                        requestCountRef.current += 1;
                        const requestPoint = requestCountRef.current;
                        nextState.graph_data = [...(nextState.graph_data || []), requestPoint].slice(-60);
                    }
                }
            });
            return nextState;
        });
    };

    useEffect(() => {
        const backendHost = window.location.hostname === 'localhost' ? 'localhost:8000' : '127.0.0.1:8000';
        const fetchStats = async () => {
            try {
                const res = await fetch(`http://${backendHost}/api/dashboard/stats`);
                const data = await res.json();

                setStats(prev => ({
                    ...prev,
                    ...data,
                    // Preserve live threat_feed and graph_data during scan
                    threat_feed: prev.threat_feed.length > 0 ? prev.threat_feed : (data.threat_feed || []),
                    graph_data: prev.graph_data.length > 0 ? prev.graph_data : (data.graph_data || []),
                    v6_metrics: data.v6_metrics || { injections_blocked: 0, deceptive_ui_blocked: 0, risk_score: 0 }
                }));
                
                // Detect if there's an active scan
                if (data.metrics?.active_scans > 0) {
                    setScanActive(true);
                    scanActiveRef.current = true;
                }
            } catch (e) {
                console.error("Failed to fetch dashboard stats", e);
            }
        };

        fetchStats();
        const interval = setInterval(fetchStats, 5000);

        let reconnectTimer = null;

        const connectWs = () => {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${backendHost}/stream?client_type=ui`;

            wsRef.current = new WebSocket(wsUrl);
            wsRef.current.onopen = () => console.log("Dashboard: Connected to Real-time Stream");

            wsRef.current.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    statsBuffer.current.push(data);

                    // Auto-download generated PDF report
                    if (data.type === 'GI5_LOG' && data.payload && data.payload.includes('REPORT GENERATED:')) {
                        const parts = data.payload.split(/\\|\//);
                        const filename = parts[parts.length - 1];
                        const url = `http://${backendHost}/api/reports/download/${filename}`;

                        const a = document.createElement('a');
                        a.href = url;
                        a.target = '_blank';
                        a.download = filename;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                    }

                    if (!bufferTimer.current) {
                        bufferTimer.current = requestAnimationFrame(() => {
                            flushBuffer();
                            bufferTimer.current = null;
                        });
                    }
                } catch (e) {
                    console.error("WS Graph Error", e);
                }
            };

            wsRef.current.onclose = () => {
                console.log("Dashboard: WS Connection closed. Reconnecting in 3 seconds...");
                reconnectTimer = setTimeout(connectWs, 3000);
            };
        };

        connectWs();

        return () => {
            clearInterval(interval);
            clearTimeout(reconnectTimer);
            if (wsRef.current) {
                wsRef.current.onclose = null;
                wsRef.current.close();
            }
        };
    }, []);

    const generateGraphPath = React.useCallback((data) => {
        if (!data || data.length === 0) return "";
        const maxVal = Math.max(...data, 1);
        const width = 1000;
        const height = 300;
        const pointWidth = width / Math.max(data.length - 1, 1);
        let path = `M0,${height} `;
        data.forEach((val, i) => {
            const x = i * pointWidth;
            const y = height - (val / maxVal) * (height * 0.8);
            path += `L${x},${y} `;
        });
        path += `L${width},${height} Z`;
        return path;
    }, []);

    const generateLinePath = React.useCallback((data) => {
        if (!data || data.length === 0) return "";
        const maxVal = Math.max(...data, 1);
        const width = 1000;
        const height = 300;
        const pointWidth = width / Math.max(data.length - 1, 1);
        let d = "";
        data.forEach((val, i) => {
            const x = i * pointWidth;
            const y = height - (val / maxVal) * (height * 0.8);
            if (i === 0) d += `M${x},${y}`;
            else d += ` L${x},${y}`;
        });
        return d;
    }, []);

    return (
        <div className="min-h-screen relative overflow-x-hidden" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
            <div className="relative z-10 flex flex-col min-h-screen">
                <Navigation navigate={navigate} activePage="dashboard" />

                <main className="flex-grow px-6 pb-6 w-full max-w-7xl mx-auto space-y-6">
                    <motion.div
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ ...LIQUID_SPRING, duration: 0.5 }}
                        className="mt-4 mb-6"
                    >
                        <h1 className="text-3xl font-bold mb-1 text-white">Dashboard</h1>
                        <p className="text-gray-400 text-sm">View and manage your security assessments overview.</p>
                    </motion.div>

                    {stats && (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                            {[
                                { title: 'Injections Blocked', value: stats?.v6_metrics?.injections_blocked || 0, icon: 'shield', color: 'purple', glow: 'card-glow-purple', bgIcon: 'bg-purple-500/20 text-purple-300', trend: 0 },
                                { title: 'Deceptive UI', value: stats?.v6_metrics?.deceptive_ui_blocked || 0, icon: 'visibility_off', color: 'orange', glow: 'card-glow-orange', bgIcon: 'bg-orange-500/20 text-orange-300', trend: 0 },
                                {
                                    title: 'Live Risk Score',
                                    value: (stats?.v6_metrics?.risk_score || 0) + '%',
                                    icon: 'speed',
                                    color: (stats?.v6_metrics?.risk_score || 0) > 80 ? 'red' : 'green',
                                    glow: (stats?.v6_metrics?.risk_score || 0) > 80 ? 'card-glow-red' : 'card-glow-green',
                                    bgIcon: (stats?.v6_metrics?.risk_score || 0) > 80 ? 'bg-red-500/20 text-red-300' : 'bg-green-500/20 text-green-300',
                                    trend: 0
                                },
                                { title: 'Active Scans', value: stats?.metrics?.active_scans || 0, icon: 'sensors', color: 'blue', glow: 'card-glow-blue', bgIcon: 'bg-blue-500/20 text-blue-300', isLive: true, trend: 0 }
                            ].map((item, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    transition={{ ...LIQUID_SPRING, delay: i * 0.1 }}
                                    whileHover={{ scale: 1.02, y: -5, transition: { duration: 0.2 } }}
                                    className="glass-panel-dash p-5 rounded-2xl relative overflow-hidden group"
                                >
                                    <div className={`absolute inset-0 ${item.glow} transition-opacity duration-300 opacity-60 group-hover:opacity-100`}></div>
                                    <div className="flex justify-between items-start mb-4 relative z-10">
                                        <div className={`p-2 rounded-lg ${item.color.startsWith('bg') ? item.color : `${item.color.replace('text-', 'bg-').replace('500', '500/20')}`} ${item.bgIcon ? '' : 'text-' + item.color + '-300'}`}>
                                            <span className={`material-symbols-outlined text-xl ${item.bgIcon ? '' : 'text-current'}`}>{item.icon}</span>
                                        </div>
                                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${item.trend >= 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                            LIVE
                                        </span>
                                    </div>
                                    <div className="relative z-10">
                                        <h3 className="text-gray-400 text-sm font-medium">{item.title}</h3>
                                        <p className="text-2xl font-bold text-white mt-1">{item.value}</p>
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    )}

                    {/* REQUEST ACTIVITY GRAPH — Synced with Live Threat Monitor */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ ...LIQUID_SPRING, delay: 0.2 }}
                        className="glass-panel-dash rounded-2xl p-6 relative overflow-hidden flex flex-col h-[380px]"
                    >
                        <div className="flex justify-between items-center mb-4 relative z-10">
                            <h2 className="text-sm font-medium text-gray-200">Request Activity</h2>
                            <div className="flex items-center gap-3">
                                {scanActive && (
                                    <span className="flex items-center gap-1.5 text-[10px] font-mono text-green-400">
                                        <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse shadow-[0_0_6px_rgba(74,222,128,0.6)]"></span>
                                        SCANNING
                                    </span>
                                )}
                                <span className="text-[10px] font-mono text-gray-500">
                                    {stats.graph_data.length > 0 ? `${requestCountRef.current} requests` : 'Idle'}
                                </span>
                            </div>
                        </div>
                        <div className="flex-grow w-full h-full relative z-0 mt-2">
                            {stats?.graph_data && Array.isArray(stats.graph_data) && stats.graph_data.length > 0 ? (
                                <svg className="w-full h-full drop-shadow-[0_0_15px_rgba(139,92,246,0.3)]" preserveAspectRatio="none" viewBox="0 0 1000 300">
                                    <defs>
                                        <linearGradient id="lineGradient" x1="0%" x2="100%" y1="0%" y2="0%">
                                            <stop offset="0%" stopColor="#d946ef"></stop>
                                            <stop offset="50%" stopColor="#8b5cf6"></stop>
                                            <stop offset="100%" stopColor="#06b6d4"></stop>
                                        </linearGradient>
                                        <linearGradient id="areaGradient" x1="0%" x2="0%" y1="0%" y2="100%">
                                            <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.4"></stop>
                                            <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0"></stop>
                                        </linearGradient>
                                    </defs>
                                    <path
                                        className="transition-all duration-300 ease-in-out"
                                        d={generateGraphPath(stats.graph_data)}
                                        fill="url(#areaGradient)"
                                        opacity="0.8"
                                    ></path>
                                    <path
                                        className="transition-all duration-300 ease-in-out"
                                        d={generateLinePath(stats.graph_data)}
                                        fill="none"
                                        stroke="url(#lineGradient)"
                                        strokeLinecap="round"
                                        strokeWidth="3"
                                    ></path>
                                </svg>
                            ) : (
                                <div className="flex items-center justify-center h-full text-gray-600 opacity-40">
                                    <div className="text-center">
                                        <span className="material-symbols-outlined text-3xl block mb-2">show_chart</span>
                                        <p className="text-xs font-mono">Waiting for scan to start...</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </motion.div>

                    {/* REQUEST MONITORING — Adaptive 400-row rolling window */}
                    <div className="grid grid-cols-1 gap-6 h-[500px]">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ ...LIQUID_SPRING, delay: 0.3 }}
                            className="glass-panel-dash rounded-2xl p-0 relative overflow-hidden flex flex-col h-full"
                        >
                            <div className="p-4 border-b border-white/10 bg-black/20 flex justify-between items-center">
                                <h3 className="text-sm font-medium text-gray-200 flex items-center gap-2">
                                    <span className={`w-2 h-2 rounded-full ${scanActive ? 'bg-red-500 animate-pulse shadow-[0_0_10px_red]' : 'bg-gray-600'}`}></span>
                                    REQUEST MONITORING
                                </h3>
                                <div className="flex gap-4 text-xs font-mono text-gray-500">
                                    <span className="text-gray-600">{stats.threat_feed.length} / {MAX_THREAT_ROWS} max</span>
                                    <span>STATUS: {scanActive ? 'ONLINE' : 'STANDBY'}</span>
                                </div>
                            </div>

                            {/* TABLE HEADER */}
                            <div className="grid grid-cols-12 gap-2 px-4 py-2 bg-black/40 text-[10px] font-mono text-gray-500 uppercase tracking-wider border-b border-white/5">
                                <div className="col-span-2">Time</div>
                                <div className="col-span-2">Agent</div>
                                <div className="col-span-2">Threat Type</div>
                                <div className="col-span-4">Target / Payload</div>
                                <div className="col-span-1">Severity</div>
                                <div className="col-span-1 text-right">Risk</div>
                            </div>

                            <div className="flex-grow overflow-y-auto font-mono text-xs bg-black/40 relative">
                                <div className="absolute inset-0 pointer-events-none bg-[url('https://media.giphy.com/media/oEI9uBYSzLpBK/giphy.gif')] opacity-[0.02]"></div>

                                {stats.threat_feed && stats.threat_feed.length > 0 ? stats.threat_feed.map((item, idx) => {
                                    let agentName = "UNKNOWN";
                                    let agentColor = "text-gray-400";

                                    if (item.agent?.includes('theta')) { agentName = "THE SENTINEL"; agentColor = "text-purple-400"; }
                                    else if (item.agent?.includes('iota')) { agentName = "THE INSPECTOR"; agentColor = "text-orange-400"; }
                                    else if (item.agent?.includes('beta')) { agentName = "BETA (BREAKER)"; agentColor = "text-red-400"; }
                                    else if (item.agent?.includes('alpha')) { agentName = "ALPHA (SCOUT)"; agentColor = "text-cyan-400"; }
                                    else if (item.agent?.includes('gamma')) { agentName = "GAMMA (TYCOON)"; agentColor = "text-yellow-400"; }
                                    else if (item.agent?.includes('omega')) { agentName = "OMEGA (STRAT)"; agentColor = "text-pink-400"; }
                                    else if (item.agent?.includes('zeta')) { agentName = "ZETA (CORTEX)"; agentColor = "text-indigo-400"; }
                                    else if (item.agent?.includes('sigma')) { agentName = "SIGMA (SMITH)"; agentColor = "text-green-400"; }
                                    else if (item.agent?.includes('kappa')) { agentName = "KAPPA (LIBRARIAN)"; agentColor = "text-teal-400"; }
                                    else if (item.agent?.includes('alpha_recon')) { agentName = "ALPHA (RECON)"; agentColor = "text-cyan-400"; }
                                    else if (item.agent?.includes('planner')) { agentName = "PLANNER"; agentColor = "text-amber-400"; }
                                    else if (item.agent?.includes('Orchestrator')) { agentName = "ORCHESTRATOR"; agentColor = "text-fuchsia-400"; }

                                    return (
                                        <motion.div
                                            key={`threat-${idx}`}
                                            initial={{ x: -20, opacity: 0 }}
                                            animate={{ x: 0, opacity: 1 }}
                                            transition={{ duration: 0.15 }}
                                            className={`grid grid-cols-12 gap-2 px-4 py-2 border-b border-white/5 hover:bg-white/5 transition-colors items-center ${item.severity === 'CRITICAL' ? 'bg-red-500/5' : ''}`}
                                        >
                                            <div className="col-span-2 text-gray-500">{item.timestamp}</div>
                                            <div className={`col-span-2 font-bold ${agentColor}`}>{agentName}</div>
                                            <div className="col-span-2 text-gray-300 truncate" title={item.threat_type}>{item.threat_type}</div>
                                            <div className="col-span-4 text-gray-400 truncate font-light" title={item.payload_data || item.url}>
                                                {item.action ? (
                                                    <span className="text-blue-400 font-medium">[{item.action}] </span>
                                                ) : null}
                                                {item.payload_data || item.url}
                                            </div>
                                            <div className="col-span-1">
                                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${item.severity === 'CRITICAL' ? 'bg-red-500 text-black' :
                                                    item.severity === 'HIGH' ? 'bg-orange-500 text-black' :
                                                        item.severity === 'MEDIUM' ? 'bg-yellow-500 text-black' :
                                                        item.severity === 'LOW' ? 'bg-green-500 text-black' :
                                                        'bg-blue-500 text-black'
                                                    }`}>
                                                    {item.severity}
                                                </span>
                                            </div>
                                            <div className="col-span-1 text-right font-bold text-white">
                                                {item.risk_score || 0}%
                                            </div>
                                        </motion.div>
                                    );
                                }) : (
                                    <div className="flex flex-col items-center justify-center h-full text-gray-600 opacity-50">
                                        <span className="material-icons text-4xl mb-2">security</span>
                                        <p>SYSTEM SECURE // NO ACTIVE THREATS</p>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    </div>
                </main>

                <footer className="w-full text-center py-6 text-xs text-gray-600 relative z-10">
                    VigilAgent API Endpoint Scanning System
                </footer>
            </div>
        </div>
    );
};

export default Dashboard;
