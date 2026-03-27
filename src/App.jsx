import React, { useState, useEffect } from 'react';
import Dashboard from './components/Dashboard';
import Scans from './components/Scans';
import NewScan from './components/NewScan';
import Settings from './components/Settings';
import Library from './components/Library';
import Login from './components/Login';
import SmoothScroll from './components/SmoothScroll';
import GlobalBackground from './components/GlobalBackground'; // Import Added
import { AnimatePresence } from 'framer-motion';

export default function App() {
    const [currentPage, setCurrentPage] = useState('dashboard');
    const [isLocked, setIsLocked] = useState(true); // Default to locked while checking
    const [checkingAuth, setCheckingAuth] = useState(true);

    // -- Font & Icon Loader --
    useEffect(() => {
        const links = [
            "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap",
            "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap",
            "https://fonts.googleapis.com/icon?family=Material+Icons+Outlined",
            "https://fonts.googleapis.com/icon?family=Material+Icons",
            "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap",
            "https://fonts.googleapis.com/icon?family=Material+Icons+Round"
        ];

        links.forEach(href => {
            if (!document.querySelector(`link[href="${href}"]`)) {
                const link = document.createElement('link');
                link.href = href;
                link.rel = 'stylesheet';
                document.head.appendChild(link);
            }
        });
    }, []);

    // -- Auth Check --
    useEffect(() => {
        checkAuth();
    }, []);

    const checkAuth = () => {
        fetch('http://127.0.0.1:8000/api/dashboard/auth/status')
            .then(res => res.json())
            .then(data => {
                if (data['2fa_required'] && !data.authenticated) {
                    setIsLocked(true);
                } else {
                    setIsLocked(false);
                }
                setCheckingAuth(false);
            })
            .catch(err => {
                console.error("Auth check failed", err);
                setIsLocked(false); // Fail open if backend down? Or locked? Let's fail open for dev, locked for prod.
                setCheckingAuth(false);
            });
    };

    // -- Navigation Helper --
    const navigate = (page) => {
        setCurrentPage(page);
        window.scrollTo(0, 0);
    };

    if (checkingAuth) {
        return <div className="min-h-screen bg-[#06070B]"></div>;
    }

    if (isLocked) {
        return <Login onLoginSuccess={() => setIsLocked(false)} />;
    }

    return (
        <SmoothScroll>
            {/* Transparent Star Overlay */}
            <GlobalBackground />

            {/* Shared Background for all pages to ensure continuity */}
            <div className="nebula-background"></div>

            <style>{`
        :root {
            --bg-deep: #06070B;
            --cyan-bloom: rgba(20, 184, 166, 0.25);
            --magenta-bloom: rgba(162, 28, 175, 0.20);
            --primary: #8A2BE2;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-deep);
            color: #e2e8f0;
        }

        /* --- UTILITIES & EFFECTS --- */
        .nebula-background {
            position: fixed;
            inset: 0;
            z-index: -2;
            pointer-events: none;
            background: 
                radial-gradient(circle at 0% 0%, var(--cyan-bloom) 0%, transparent 50%),
                radial-gradient(circle at 100% 100%, var(--magenta-bloom) 0%, transparent 50%),
                linear-gradient(180deg, #06070B 0%, #040508 100%);
        }
        
        .shadow-glow { box-shadow: 0 0 20px rgba(138, 43, 226, 0.15); }
        .shadow-glass { box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); }
        
        .metric-card {
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: inset 0 0 20px rgba(255,255,255,0.03);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 40px -10px rgba(0,0,0,0.5);
        }

        .glass-panel {
            background: rgba(11, 12, 20, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.06);
        }
        
        .glass-table th { font-weight: 400; color: #94a3b8; font-size: 0.85rem; padding-top: 1.25rem; padding-bottom: 1.25rem; }
        .glass-table td { vertical-align: middle; padding-top: 1rem; padding-bottom: 1rem; }

        /* Gradients defined in user config */
        .bg-card-gradient-purple { background: linear-gradient(135deg, rgba(30, 27, 75, 0.9) 0%, rgba(49, 46, 129, 0.4) 100%); }
        .bg-card-gradient-green { background: linear-gradient(135deg, rgba(6, 78, 59, 0.8) 0%, rgba(6, 95, 70, 0.3) 100%); }
        .bg-card-gradient-orange { background: linear-gradient(135deg, rgba(67, 20, 7, 0.9) 0%, rgba(124, 45, 18, 0.4) 100%); }
        .bg-card-gradient-red { background: linear-gradient(135deg, rgba(69, 10, 10, 0.9) 0%, rgba(127, 29, 29, 0.4) 100%); }

        .star { position: absolute; background: white; border-radius: 50%; }

        /* --- SCROLLBAR --- */
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: #06070B; }
        ::-webkit-scrollbar-thumb { background: #1e2130; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #31364a; }
        
        /* --- LEGACY STYLES (Kept for other pages) --- */
        .glass-panel-dash {
            background: rgba(18, 24, 38, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
        }
        .card-glow-purple { background: radial-gradient(circle at bottom right, rgba(168, 85, 247, 0.5), transparent 60%); }
        .card-glow-green { background: radial-gradient(circle at bottom right, rgba(34, 197, 94, 0.5), transparent 60%); }
        .card-glow-orange { background: radial-gradient(circle at bottom right, rgba(249, 115, 22, 0.5), transparent 60%); }
        .card-glow-red { background: radial-gradient(circle at bottom right, rgba(239, 68, 68, 0.5), transparent 60%); }
        @keyframes draw { from { stroke-dashoffset: 2000; } to { stroke-dashoffset: 0; } }
        .animate-draw { stroke-dasharray: 2000; animation: draw 2s ease-out forwards; }
        
        .glassmorphism-card {
             background-color: rgba(42, 46, 74, 0.9);
             border: 1px solid rgba(255, 255, 255, 0.08);
             position: relative;
        }
        .glassmorphism-card::before {
             content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0; border-radius: inherit; pointer-events: none;
             background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0) 60%);
        }
        .glow-element { box-shadow: 0 0 15px 3px rgba(155, 97, 255, 0.5), 0 0 5px 1px rgba(155, 97, 255, 0.6); }
        .text-glow { text-shadow: 0 0 8px rgba(155, 97, 255, 0.7); }
        .icon-glow { filter: drop-shadow(0 0 5px rgba(155, 97, 255, 0.7)); }
        
        .glass-card-lib {
            background: rgba(30, 35, 50, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .noise-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 0; opacity: 0.05;
            background-image: url(https://lh3.googleusercontent.com/aida-public/AB6AXuB1Rk5iZrbiz4M9YYaTmE2PCG6RczkwzwtiFuCKCNTBZ-Lie5z-ZKfH5a6sMbvR4JswvLkYh0_WS4QLJNEs5xe_rm3OHlVLGlQfN7Ynp11mI0ARa7hln4cEvGUBClC0kW6BOchJWYaJE5La4vTFnfuw5je-3CHm-W3Zhes-AhlxLh__DbzBMnlH2m_00WPCHqeoLiJeXQDpbULIJ1PpQfZLBiBgSHWF0IxKvfxyXw-pPuLz8X9ZUdHtSu-CbqA8sRMPUn7DVXooTp2i)
        }
        
        /* Settings Toggles */
        .toggle-checkbox:checked { right: 0; border-color: #8B5CF6; }
        .toggle-checkbox:checked + .toggle-label { background-color: #8B5CF6; }
      `}</style>

            {/* Render the specific page component based on state */}
            <AnimatePresence mode="wait">
                {currentPage === 'dashboard' && <Dashboard key="dashboard" navigate={navigate} />}
                {currentPage === 'scans' && <Scans key="scans" navigate={navigate} />}
                {currentPage === 'newscan' && <NewScan key="newscan" navigate={navigate} />}
                {currentPage === 'settings' && <Settings key="settings" navigate={navigate} />}
                {currentPage === 'library' && <Library key="library" navigate={navigate} />}
            </AnimatePresence>
        </SmoothScroll>
    );
}
