import React, { useEffect, useRef, useState } from 'react';
import Navigation from './Navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { LIQUID_SPRING } from '../lib/constants';

const Scans = ({ navigate }) => {
    const starsRef = useRef(null);

    const [scans, setScans] = useState([]);
    const [progressMap, setProgressMap] = useState({}); // Real-time report progress
    const messageBuffer = useRef([]);
    const lastFlush = useRef(Date.now());
    const wsRef = useRef(null);
    const backendHost = '127.0.0.1:8000';

    const fetchScans = async () => {
        try {
            const res = await fetch(`http://${backendHost}/api/dashboard/scans`);
            const data = await res.json();
            setScans(data);
        } catch (err) {
            console.error("Failed to fetch scans:", err);
        }
    };

    // WebSocket & Initial Fetch
    useEffect(() => {
        fetchScans();

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${backendHost}/stream?client_type=ui`;

        wsRef.current = new WebSocket(wsUrl);
        wsRef.current.onopen = () => console.log("Scans: Connected to Real-time Stream");

        const flushBuffer = () => {
            if (messageBuffer.current.length === 0) return;

            const messages = [...messageBuffer.current];
            messageBuffer.current = [];

            let shouldFetch = false;
            const newProgress = { ...progressMap };

            messages.forEach(data => {
                // 1. Progress Updates (SCAN_UPDATE with progress field)
                if (data.type === 'SCAN_UPDATE' && data.payload?.progress) {
                    newProgress[data.payload.id] = data.payload.progress;
                }

                // 2. Scan Status Update (Trigger Fetch)
                if (['SCAN_UPDATE', 'GI5_COMPLETE', 'REPORT_READY'].includes(data.type)) {
                    shouldFetch = true;
                }

                // 3. Auto-download generated PDF report
                if (data.type === 'GI5_LOG' && data.payload && data.payload.includes('REPORT GENERATED:')) {
                    const parts = data.payload.split(/[\\/]/);
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
            });

            if (Object.keys(newProgress).length > Object.keys(progressMap).length || 
                JSON.stringify(newProgress) !== JSON.stringify(progressMap)) {
                setProgressMap(prev => ({ ...prev, ...newProgress }));
            }

            if (shouldFetch) {
                fetchScans();
            }
        };

        const throttleInterval = setInterval(flushBuffer, 800);

        wsRef.current.onmessage = (event) => {
            try {
                const parsed = JSON.parse(event.data);
                if (parsed.type === "BATCH" && Array.isArray(parsed.payload)) {
                    messageBuffer.current.push(...parsed.payload);
                } else {
                    messageBuffer.current.push(parsed);
                }
            } catch (e) {
                console.error("WS Error", e);
            }
        };

        // --- FIXED POLLING: Check for both Finalizing and Completed-not-ready ---
        const pollInterval = setInterval(() => {
            const needsRefresh = scans.some(s =>
                s.status === 'Finalizing' ||
                (s.status === 'Completed' && !s.report_ready)
            );
            if (needsRefresh) {
                fetchScans();
            }
        }, 5000); // Increased to 5s to reduce overhead

        return () => {
            if (wsRef.current) wsRef.current.close();
            clearInterval(pollInterval);
            clearInterval(throttleInterval);
        };
    }, [scans, progressMap]);

    // Live Duration Timer - Removed (Was causing lag and excessive re-renders)
    // useEffect(() => { ... }, []);

    // Stars effect moved to GlobalBackground
    // useEffect(() => {
    //     if (starsRef.current) {
    //        ... removed ...
    //     }
    // }, []);

    const [downloading, setDownloading] = useState(null); // Track which scan is downloading

    const handleWipeHistory = async () => {
        if (!confirm("Are you sure you want to PERMANENTLY wipe all scan history? This cannot be undone.")) return;
        try {
            const response = await fetch(`http://${backendHost}/api/dashboard/reset`, { method: 'POST' });
            if (response.ok) {
                fetchScans();
                alert("Scan history wiped successfully.");
            }
        } catch (error) {
            console.error('Error wiping history:', error);
        }
    };

    const handleDownloadPdf = async (scanId) => {
        setDownloading(scanId);
        try {
            const response = await fetch(`http://${backendHost}/api/reports/pdf/${scanId}`);
            if (!response.ok) throw new Error('Download failed');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `scan_report_${scanId}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Error downloading PDF:', error);
            alert('Failed to download PDF report. Ensure backend is running.');
        } finally {
            setDownloading(null);
        }
    };

    return (
        <div className="min-h-screen relative overflow-x-hidden text-gray-200">
            <div className="stars-container fixed top-0 left-0 w-full h-full z-[-1] overflow-hidden pointer-events-none"></div>

            <div className="relative z-10 flex flex-col min-h-screen">
                <Navigation navigate={navigate} activePage="scans" />

                <main className="relative z-10 max-w-7xl mx-auto px-6 lg:px-8 py-8 w-full flex-grow">
                    <motion.div
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ ...LIQUID_SPRING, duration: 0.5 }}
                        className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8"
                    >
                        <div>
                            <h1 className="text-[32px] font-semibold text-white mb-2">Scans</h1>
                            <p className="text-gray-400 text-sm font-light tracking-wide opacity-80">View and manage your past and running security assessments.</p>
                        </div>
                        <div className="flex bg-black/20 p-1 rounded-xl border border-white/5 shadow-inner self-start md:self-end">
                            <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={handleWipeHistory}
                                className="px-4 py-2 rounded-lg text-xs font-medium text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-all flex items-center gap-2"
                            >
                                <span className="material-symbols-outlined text-sm">delete_sweep</span>
                                Wipe History
                            </motion.button>
                            <div className="w-[1px] h-4 bg-white/10 self-center mx-1"></div>
                            <motion.button
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                                onClick={() => navigate('newscan')}
                                className="bg-[#8A2BE2] hover:bg-[#7c26cc] text-white px-5 py-2.5 rounded-lg text-sm font-medium flex items-center gap-2 shadow-glow transition-all will-change-transform"
                            >
                                <span className="material-symbols-outlined text-sm">add</span>
                                New Scan
                            </motion.button>
                        </div>
                    </motion.div>

                    <div className="glass-panel-fast rounded-2xl overflow-hidden shadow-glass">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left text-sm whitespace-nowrap glass-table">
                                <thead>
                                    <tr className="border-b border-white/5">
                                        <th className="pl-8 pr-6">Status</th>
                                        <th className="px-6">Scan Name</th>
                                        <th className="px-6">Target Scope</th>
                                        <th className="px-6">Modules</th>
                                        <th className="px-6">Duration</th>
                                        <th className="px-6 pr-8">
                                            <div className="flex items-center gap-1 cursor-pointer hover:text-white transition-colors">
                                                Completed
                                                <span className="material-symbols-outlined text-xs">arrow_downward</span>
                                            </div>
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/5 text-gray-300">
                                    <AnimatePresence mode='popLayout'>
                                        {scans.length === 0 ? (
                                            <motion.tr
                                                initial={{ opacity: 0 }}
                                                animate={{ opacity: 1 }}
                                                exit={{ opacity: 0 }}
                                            >
                                                <td colSpan="6" className="text-center py-8 text-gray-500">
                                                    No scans recorded. Launch a new scan to see results here.
                                                </td>
                                            </motion.tr>
                                        ) : (
                                            scans.map((scan, index) => (
                                                <motion.tr
                                                    key={scan.id}
                                                    initial={{ opacity: 0, y: 10 }}
                                                    animate={{ opacity: 1, y: 0 }}
                                                    transition={{
                                                        duration: 0.3,
                                                        delay: index * 0.05,
                                                        ease: "easeOut"
                                                    }}
                                                    className="hover:bg-white/[0.02] transition-colors group relative"
                                                >
                                                    <td className="pl-8 pr-6 py-5">
                                                        <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border ${scan.status === 'Running'
                                                            ? 'bg-[#1e2338] text-blue-400 border-blue-500/30'
                                                            : scan.status === 'Finalizing'
                                                                ? 'bg-[#251e38] text-purple-400 border-purple-500/30'
                                                                : scan.status === 'Completed' || scan.status === 'Fired'
                                                                    ? 'bg-[#1a2f30] text-teal-400 border-teal-500/30'
                                                                    : 'bg-[#2f1a1a] text-red-400 border-red-500/30'
                                                            }`}>
                                                            <span className={`w-1.5 h-1.5 rounded-full ${scan.status === 'Running' ? 'bg-blue-500 shadow-[0_0_6px_#3b82f6] animate-pulse' :
                                                                scan.status === 'Finalizing' ? 'bg-purple-500 shadow-[0_0_6px_#a855f7] animate-pulse' :
                                                                    scan.status === 'Completed' || scan.status === 'Fired' ? 'bg-teal-400' : 'bg-red-400'
                                                                }`}></span>
                                                            {scan.status}
                                                        </span>
                                                    </td>
                                                    <td className="px-6 py-5 font-medium text-white">{scan.name || "Untitled Scan"}</td>
                                                    <td className="px-6 py-5 text-gray-400 font-mono text-xs tracking-wide truncate max-w-[200px]" title={scan.scope}>
                                                        {scan.scope}
                                                    </td>
                                                    <td className="px-6 py-5">
                                                        <div className="flex gap-1.5">
                                                            <div className="w-7 h-7 rounded bg-[#252038] flex items-center justify-center border border-purple-500/20 group-hover:border-purple-500/40 transition-colors" title="Modules">
                                                                <span className="material-symbols-outlined text-purple-400 text-[14px]">bug_report</span>
                                                            </div>
                                                            {/* Dynamic modules could be here */}
                                                        </div>
                                                    </td>
                                                    <td className="px-6 py-5 text-gray-300 font-mono">
                                                        {scan.status === 'Running' ? (
                                                            <span className="text-blue-300 relative">
                                                                <span className="absolute -left-3 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-blue-500 animate-ping opacity-75"></span>
                                                                {scan.duration} (Live)
                                                            </span>
                                                        ) : scan.duration}
                                                    </td>
                                                    <td className="px-6 pr-8 py-5">
                                                        <div className="flex items-center justify-between gap-6">
                                                            <span className="text-gray-400 text-xs">{scan.timestamp}</span>
                                                            <motion.button
                                                                whileHover={{ scale: 1.05 }}
                                                                whileTap={{ scale: 0.95 }}
                                                                onClick={() => handleDownloadPdf(scan.id)}
                                                                disabled={(scan.status === 'Running' || !scan.report_ready) || downloading === scan.id}
                                                                title={(scan.status === 'Finalizing' || (scan.status === 'Completed' && !scan.report_ready)) ? "AI is finalizing the forensic report..." : "Download PDF Report"}
                                                                className={`px-3 py-1.5 rounded-md text-[11px] font-medium flex items-center gap-1.5 shadow-[0_0_10px_rgba(138,43,226,0.2)] transition-all ${(scan.status === 'Running' || !scan.report_ready)
                                                                    ? 'bg-gray-700 text-gray-400 cursor-not-allowed opacity-50 shadow-none'
                                                                    : 'bg-[#8A2BE2] text-white hover:bg-[#9d47ff]'
                                                                    } ${downloading === scan.id ? 'opacity-70 cursor-wait' : ''}`}
                                                            >
                                                                <span className={`material-symbols-outlined text-sm ${downloading === scan.id || ((scan.status === 'Finalizing' || (scan.status === 'Completed' && !scan.report_ready))) ? 'animate-spin' : ''}`}>
                                                                    {downloading === scan.id ? 'sync' : ((scan.status === 'Finalizing' || (scan.status === 'Completed' && !scan.report_ready)) ? 'hourglass_empty' : 'download')}
                                                                </span>
                                                                {downloading === scan.id 
                                                                    ? 'Downloading...' 
                                                                    : ((scan.status === 'Finalizing' || (scan.status === 'Completed' && !scan.report_ready)) 
                                                                        ? (progressMap[scan.id] || 'Finalizing AI Report...') 
                                                                        : 'PDF Download')}
                                                            </motion.button>
                                                        </div>
                                                    </td>
                                                </motion.tr>
                                            ))
                                        )}
                                    </AnimatePresence>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </main>

                <footer className="mt-8 pb-8 text-center text-xs text-gray-500 font-light">
                    <p>Vulagent Scanner Intelligence Backbone © 2024</p>
                </footer>
            </div>
        </div>
    );
};

export default Scans;
