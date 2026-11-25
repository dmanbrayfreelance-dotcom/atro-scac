import React from 'react';
import { ShieldAlert, Database, History, FileCode2, Cpu } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, apiOnline }) {
  const tabs = [
    { id: 'scanner', label: 'Code Scanner', icon: FileCode2 },
    { id: 'samples', label: 'Sample Contracts', icon: ShieldAlert, badge: '5' },
    { id: 'auditdb', label: 'Audited Reference DB', icon: Database },
    { id: 'history', label: 'Audit History', icon: History },
  ];

  return (
    <header className="border-b border-purple-900/40 bg-[#0c051c]/95 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Title */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('scanner')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 via-pink-500 to-rose-400 p-0.5 shadow-lg shadow-pink-500/20 flex items-center justify-center">
              <div className="w-full h-full bg-[#090314] rounded-[10px] flex items-center justify-center">
                <Cpu className="w-5 h-5 text-pink-400 animate-pulse" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-lg tracking-tight text-white">ASTRO</span>
                <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border border-pink-500/30 bg-pink-500/10 text-pink-300 font-mono font-bold">
                  ACFG Graph Sim
                </span>
              </div>
              <p className="text-[11px] text-purple-300/70">Smart Contract Access Control Auditor</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center space-x-1 sm:space-x-2">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-purple-600 via-purple-500 to-pink-500 text-white shadow-md shadow-pink-500/25'
                      : 'text-purple-200 hover:text-white hover:bg-purple-950/40 border border-transparent'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white' : 'text-pink-400'}`} />
                  <span className="hidden md:inline">{tab.label}</span>
                  {tab.badge && (
                    <span
                      className={`text-[9px] px-1.5 py-0.2 rounded-full font-mono font-bold ${
                        isActive
                          ? 'bg-white/20 text-white'
                          : 'bg-purple-950 text-pink-300 border border-purple-800'
                      }`}
                    >
                      {tab.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Backend Status */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-purple-950/60 border border-purple-800/50 text-xs">
              <span
                className={`w-2 h-2 rounded-full ${
                  apiOnline ? 'bg-pink-400 animate-ping' : 'bg-purple-700'
                }`}
              />
              <span className="text-purple-300/70 hidden sm:inline">Engine:</span>
              <span className="text-pink-300 font-mono font-semibold">
                {apiOnline ? 'Online (8000)' : 'Offline'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
