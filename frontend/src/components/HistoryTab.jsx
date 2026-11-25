import React from 'react';
import { History, ShieldAlert, ShieldCheck, ArrowRight, FileCode } from 'lucide-react';

export default function HistoryTab({ history, onSelectScan }) {
  if (!history || history.length === 0) {
    return (
      <div className="bg-[#120726] border border-purple-800/40 rounded-2xl p-12 text-center shadow-xl">
        <History className="w-10 h-10 text-purple-400 mx-auto mb-3" />
        <h3 className="text-sm font-bold text-white">No Audits Recorded Yet</h3>
        <p className="text-xs text-purple-300/70 mt-1 max-w-sm mx-auto">
          Run your first ASTRO static analysis in the Code Scanner tab to see detailed historical reports here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-[#120726] border border-purple-800/40 rounded-2xl p-6 shadow-xl">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-purple-600 to-pink-500 text-white shadow-md shadow-pink-500/20">
            <History className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-extrabold text-white">Audit Execution History</h2>
            <p className="text-xs text-purple-300/80">
              Audit logs, vulnerability classifications, and risk trajectories for analyzed contracts
            </p>
          </div>
        </div>
      </div>

      {/* History Table */}
      <div className="bg-[#130829] border border-purple-800/50 rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#0b0416] text-purple-300 font-mono uppercase text-[10px] border-b border-purple-900">
              <tr>
                <th className="py-3 px-4">Contract Filename</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">ASTRO Verdict</th>
                <th className="py-3 px-4">Risk Score</th>
                <th className="py-3 px-4">Vulnerable / Safe</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-purple-950">
              {history.map((item) => {
                const exec = item.executive_summary || {};
                const isVuln = exec.verdict === 'VULNERABLE';

                return (
                  <tr key={item.id} className="hover:bg-purple-950/30 transition-colors">
                    <td className="py-3 px-4">
                      <div className="flex items-center space-x-2">
                        <FileCode className="w-4 h-4 text-pink-400" />
                        <span className="font-mono font-semibold text-white">
                          {item.filename || 'Contract.sol'}
                        </span>
                      </div>
                    </td>

                    <td className="py-3 px-4 text-purple-300 font-mono">
                      {new Date(item.timestamp).toLocaleString()}
                    </td>

                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full font-mono text-[10px] font-bold uppercase border ${
                          isVuln
                            ? 'bg-pink-500/20 text-pink-300 border-pink-500/40'
                            : 'bg-purple-500/20 text-purple-200 border-purple-500/40'
                        }`}
                      >
                        {isVuln ? (
                          <>
                            <ShieldAlert className="w-3 h-3 text-pink-400" />
                            <span>Vulnerable</span>
                          </>
                        ) : (
                          <>
                            <ShieldCheck className="w-3 h-3 text-purple-300" />
                            <span>Safe</span>
                          </>
                        )}
                      </span>
                    </td>

                    <td className="py-3 px-4 font-mono font-bold">
                      <span className={isVuln ? 'text-pink-400' : 'text-purple-200'}>
                        {exec.overall_risk_score}/100
                      </span>
                    </td>

                    <td className="py-3 px-4 font-mono">
                      <span className="text-pink-400 font-bold">{exec.vulnerable_functions_count || 0}</span>
                      <span className="text-purple-600"> / </span>
                      <span className="text-purple-200 font-bold">{exec.safe_functions_count || 0}</span>
                      <span className="text-purple-400 text-[10px] ml-1">
                        ({exec.total_functions_analyzed || 0} total)
                      </span>
                    </td>

                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => onSelectScan(item)}
                        className="inline-flex items-center space-x-1 px-3 py-1 rounded-xl bg-purple-950/80 hover:bg-purple-900 text-pink-300 hover:text-white font-bold transition-colors border border-purple-800"
                      >
                        <span>View Report</span>
                        <ArrowRight className="w-3 h-3 text-pink-400" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
