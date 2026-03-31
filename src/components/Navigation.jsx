import React from 'react';
import { motion, LayoutGroup } from 'framer-motion';
import { LIQUID_SPRING } from '../lib/constants';

const Navigation = ({ navigate, activePage }) => {
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

                        {/* Links Section */}
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

                        {/* Icons Section */}
                        <div className="flex items-center gap-5">
                            <button className="text-gray-400 hover:text-white transition-colors">
                                <span className="material-symbols-outlined text-[22px]">notifications</span>
                            </button>
                            <button className="text-gray-400 hover:text-white transition-colors">
                                <span className="material-symbols-outlined text-[22px]">account_circle</span>
                            </button>
                        </div>
                    </div>
                </LayoutGroup>
            </div>
        </nav>
    );
};

export default Navigation;
