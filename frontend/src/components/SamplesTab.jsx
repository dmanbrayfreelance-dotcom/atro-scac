import React from 'react';
import { ShieldAlert, ShieldCheck, Play, FileCode2 } from 'lucide-react';

export default function SamplesTab({ samples, onLoadSample, onRunSample }) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-[#120726] border border-purple-800/40 rounded-2xl p-6 shadow-xl">
        <div className="flex items-center space-x-3 mb-1">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-purple-600 to-pink-500 text-white shadow-md shadow-pink-500/20">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-extrabold text-white">Smart Contract Test Benchmark Corpus</h2>
            <p className="text-xs text-purple-300/80">
              Pre-loaded smart contracts demonstrating common access control vulnerabilities and safe audited baselines
            </p>
          </div>
        </div>
      </div>

      {/* Grid of Samples */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {samples.map((sample) => {
          const isVuln = sample.expected_verdict === 'VULNERABLE';

          return (
            <div
              key={sample.id}
              className={`bg-[#130829] border rounded-2xl p-6 flex flex-col justify-between transition-all hover:border-pink-400 shadow-lg ${
                isVuln
                  ? 'border-pink-500/60 shadow-pink-950/20'
                  : 'border-purple-800/50 hover:border-purple-600'
              }`}
            >
              <div>
                {/* Header & Badges */}
                <div className="flex items-center justify-between mb-3">
                  <span
                    className={`text-[10px] uppercase font-mono font-extrabold px-2.5 py-0.5 rounded-full border ${
                      isVuln
                        ? 'bg-pink-500/20 text-pink-300 border-pink-500/40'
                        : 'bg-purple-500/20 text-purple-200 border-purple-500/40'
                    }`}
                  >
                    {sample.category}
                  </span>

                  <span className="font-mono text-xs text-purple-300/60 font-semibold">{sample.filename}</span>
                </div>

                <h3 className="text-base font-black text-white mb-2 leading-snug">{sample.title}</h3>

                <p className="text-xs text-purple-200/80 mb-4 line-clamp-3 leading-relaxed">
                  {sample.description}
                </p>

                {/* Target Function Pill */}
                <div className="mb-4 p-2.5 rounded-xl bg-[#0b0416] border border-purple-900/60 text-xs font-mono">
                  <span className="text-purple-400 block text-[10px] uppercase font-bold">ASTRO Target Function:</span>
                  <span className="text-pink-300 font-black">{sample.target_function}()</span>
                </div>

                {/* Code Preview snippet */}
                <div className="relative mb-4">
                  <pre className="font-mono text-[10px] bg-black/70 p-3 rounded-xl border border-purple-900/60 text-purple-200 overflow-hidden max-h-24 shadow-inner">
                    {sample.source_code.slice(0, 280)}...
                  </pre>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-2 pt-3 border-t border-purple-900/40">
                <button
                  onClick={() => onLoadSample(sample.id)}
                  className="flex items-center justify-center space-x-1.5 px-3 py-2 rounded-xl bg-purple-950/60 hover:bg-purple-900/60 text-purple-200 text-xs font-bold transition-colors border border-purple-800"
                >
                  <FileCode2 className="w-3.5 h-3.5 text-pink-400" />
                  <span>Load in Editor</span>
                </button>

                <button
                  onClick={() => onRunSample(sample)}
                  className="flex items-center justify-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-black transition-all bg-gradient-to-r from-purple-600 via-pink-600 to-pink-500 hover:from-purple-500 hover:to-pink-400 text-white active:scale-95 shadow-md shadow-pink-500/30"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Instant Audit</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
