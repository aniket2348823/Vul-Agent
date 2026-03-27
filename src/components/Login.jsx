import React, { useState } from 'react';
import { motion } from 'framer-motion';

const Login = ({ onLoginSuccess }) => {
    const [token, setToken] = useState('');
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const handleLogin = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setError('');

        try {
            const res = await fetch('http://127.0.0.1:8000/api/dashboard/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token })
            });
            const data = await res.json();

            if (data.status === 'success') {
                onLoginSuccess();
            } else {
                setError(data.message || 'Verification Failed');
            }
        } catch (err) {
            setError("Connection Error");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center relative font-[Inter]" style={{ fontFamily: "'Inter', sans-serif" }}>
            <div className="absolute inset-0 z-0 bg-black">
                <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 to-black/80"></div>
                <div className="noise-overlay opacity-10"></div>
            </div>

            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="relative z-10 w-full max-w-md p-8 glass-panel-dash rounded-2xl border border-white/10 shadow-2xl backdrop-blur-xl"
            >
                <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">VigilAgent</h1>
                    <p className="text-gray-400 text-sm">Hyper-Mind Security Protocol Active</p>
                </div>

                <div className="flex justify-center mb-8">
                    <div className="w-16 h-16 rounded-full bg-purple-500/10 flex items-center justify-center border border-purple-500/30 shadow-[0_0_15px_rgba(168,85,247,0.3)]">
                        <span className="material-icons text-purple-400 text-3xl">lock</span>
                    </div>
                </div>

                <form onSubmit={handleLogin} className="flex flex-col gap-4">
                    <div>
                        <label className="text-xs text-gray-500 uppercase tracking-widest font-semibold pl-1 mb-2 block">2FA Authenticator Code</label>
                        <input
                            type="text"
                            value={token}
                            onChange={(e) => setToken(e.target.value)}
                            placeholder="000 000"
                            maxLength={6}
                            autoFocus
                            className="w-full bg-black/40 border border-white/10 focus:border-purple-500 rounded-lg px-4 py-4 text-center text-2xl tracking-[0.5em] font-mono text-white transition-all outline-none placeholder-white/10"
                        />
                    </div>

                    {error && (
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="text-red-400 text-xs text-center bg-red-500/10 py-2 rounded border border-red-500/20"
                        >
                            {error}
                        </motion.div>
                    )}

                    <button
                        type="submit"
                        disabled={isLoading || token.length < 6}
                        className="w-full mt-4 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 rounded-lg shadow-lg transition-all"
                    >
                        {isLoading ? 'Verifying...' : 'Access Console'}
                    </button>
                </form>
            </motion.div>
        </div>
    );
};

export default Login;
