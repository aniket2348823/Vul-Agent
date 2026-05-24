import React, { useState } from 'react';
import { motion, LayoutGroup, AnimatePresence } from 'framer-motion';
import { LIQUID_SPRING } from '../lib/constants';

const Navigation = ({ navigate, activePage }) => {
    const [mobileOpen, setMobileOpen] = useState(false);

    return (
        <nav className="relative z-10 w-full pt-6 pb-2">
            <div className="max-w-7xl mx-auto px-6 lg:px-8">
                <LayoutGroup>
                    <div className="flex items-center justify-between h-16">
                        {/* Logo Section */}
                        <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('dashboard')}>
                            <motion.div layout to="position" className="text-purple-400">
                                <span className="material-symbols-outlined text-2xl">auto_awesome</span>
                            </motion.div>
                            {/* Enforce Space Grotesk specifically for the logo to maintain branding symmetry across all pages */}
                            <span className="font-medium text-lg text-white tracking-wide" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>Vulagent Scanner</span>
                        </div>

                        {/* Desktop Links */}
                        <div className="hidden md:flex items-center space-x-1">
                            {['dashboard', 'scans', 'library', 'settings'].map((page) => (
                                <div key={page} className="relative flex flex-col items-center">
                                    <button
                                        onClick={() => navigate(page)}
                                        className={`${activePage === page ? 'text-white' : 'text-gray-400 hover:text-white'} px-4 py-2 text-sm font-medium transition-colors capitalize`}
                                    >
                                        {page}
                                    </button>
                                    {activePage === page && (
                                        <motion.div
                                            layoutId="nav-pill"
                                            className="h-0.5 w-6 bg-[#8A2BE2] rounded-full shadow-[0_0_10px_#8A2BE2] mt-[-2px] absolute bottom-0"
                                            transition={LIQUID_SPRING}
                                        />
                                    )}
                                </div>
                            ))}
                        </div>

                        {/* Icons + Mobile Hamburger */}
                        <div className="flex items-center gap-5">
                            <button className="text-gray-400 hover:text-white transition-colors hidden md:block">
                                <span className="material-symbols-outlined text-[22px]">notifications</span>
                            </button>
                            <button className="text-gray-400 hover:text-white transition-colors hidden md:block">
                                <span className="material-symbols-outlined text-[22px]">account_circle</span>
                            </button>
                            {/* Mobile hamburger */}
                            <button
                                className="md:hidden text-gray-300 hover:text-white transition-colors"
                                onClick={() => setMobileOpen(prev => !prev)}
                                aria-label="Toggle mobile menu"
                            >
                                <span className="material-symbols-outlined text-[26px]">
                                    {mobileOpen ? 'close' : 'menu'}
                                </span>
                            </button>
                        </div>
                    </div>
                </LayoutGroup>

                {/* Mobile Drawer */}
                <AnimatePresence>
                    {mobileOpen && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.2 }}
                            className="md:hidden overflow-hidden border-t border-white/10 mt-2"
                        >
                            <div className="flex flex-col py-3 gap-1">
                                {['dashboard', 'scans', 'library', 'settings'].map((page) => (
                                    <button
                                        key={page}
                                        onClick={() => { navigate(page); setMobileOpen(false); }}
                                        className={`${activePage === page ? 'text-white bg-purple-600/20' : 'text-gray-400 hover:text-white hover:bg-white/5'} px-4 py-3 text-sm font-medium transition-colors capitalize rounded-lg text-left`}
                                    >
                                        {page}
                                    </button>
                                ))}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </nav>
    );
};

export default Navigation;
