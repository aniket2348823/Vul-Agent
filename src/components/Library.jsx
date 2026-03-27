import React, { useState, useEffect } from 'react';
import Navigation from './Navigation';
import { motion } from 'framer-motion';
import { LIQUID_SPRING } from '../lib/constants';
import { agents, modules } from '../data/library_data';

const Library = ({ navigate }) => {

    return (
        <div className="font-[Inter] min-h-screen relative overflow-x-hidden transition-colors duration-300" style={{ fontFamily: "'Inter', sans-serif" }}>

            <div className="relative z-10 flex flex-col min-h-screen">
                <Navigation navigate={navigate} activePage="library" />

                <main className="flex-grow px-8 py-8 max-w-[1400px] mx-auto w-full">
                    {/* SECTION 1: THE HIVE MIND (AGENTS) */}
                    <div className="mb-12">
                        <div className="mb-8">
                            <h1 className="text-3xl font-bold text-white mb-2">The Hive Mind</h1>
                            <p className="text-gray-400 text-sm font-light tracking-wide opacity-80">The 7 Sovereign Entities that orchestrate the swarm.</p>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                            {agents.map((agent, i) => (
                                <motion.div
                                    key={agent.id}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ ...LIQUID_SPRING, delay: i * 0.1 }}
                                    className="glass-card-lib rounded-xl p-6 flex flex-col h-full hover:border-purple-500/30 transition-all duration-300 group relative overflow-hidden"
                                >
                                    <div className={`absolute inset-0 bg-gradient-to-br ${agent.bg_gradient} opacity-0 group-hover:opacity-10 transition-opacity`}></div>

                                    <div className="flex justify-between items-start mb-2 relative z-10">
                                        <h3 className={`text-lg font-bold ${agent.color} group-hover:text-purple-300 transition-colors`}>{agent.name}</h3>
                                        <span className={`text-[10px] bg-white/5 px-2 py-1 rounded text-gray-400 border border-white/5 uppercase tracking-wider`}>{agent.role}</span>
                                    </div>

                                    <p className="text-gray-400 text-xs mb-4 leading-relaxed flex-grow relative z-10">{agent.description}</p>

                                    <div className="flex flex-wrap gap-2 mb-6 relative z-10">
                                        {agent.capabilities.map((cap, idx) => (
                                            <span key={idx} className="px-3 py-1 rounded-full text-[10px] font-medium bg-[rgba(45,212,191,0.1)] border border-[rgba(45,212,191,0.3)] text-[#99f6e4]">{cap}</span>
                                        ))}
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>

                    {/* SECTION 2: THE ARSENAL (MODULES) */}
                    <div className="mb-10">
                        <div className="mb-8 border-t border-white/10 pt-8">
                            <h1 className="text-3xl font-bold text-white mb-2">The Arsenal</h1>
                            <p className="text-gray-400 text-sm font-light tracking-wide opacity-80">Advanced attack modules and logic probes.</p>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {modules.map((mod, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ ...LIQUID_SPRING, delay: i * 0.05 }}
                                    className="glass-card-lib rounded-xl p-6 flex flex-col h-full hover:border-purple-500/30 transition-all duration-300 group"
                                >
                                    <div className="flex justify-between items-start mb-2">
                                        <h3 className="text-lg font-semibold text-white group-hover:text-purple-300 transition-colors">{mod.title}</h3>
                                        <span className="text-[10px] bg-white/5 px-2 py-1 rounded text-gray-400 border border-white/5">{mod.agent}</span>
                                    </div>
                                    <p className="text-gray-400 text-xs mb-4 leading-relaxed flex-grow">{mod.description}</p>

                                    <div className="flex flex-wrap gap-2 mb-6">
                                        {mod.tags.map(tag => (
                                            <span key={tag} className="px-3 py-1 rounded-full text-[10px] font-medium bg-[rgba(45,212,191,0.1)] border border-[rgba(45,212,191,0.3)] text-[#99f6e4]">{tag}</span>
                                        ))}
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>

                </main>

                <footer className="w-full py-6 text-center text-xs text-gray-600 font-light">
                    VigilAgent API Endpoint Scanning System
                </footer>
            </div>
        </div>
    );
};

export default Library;
