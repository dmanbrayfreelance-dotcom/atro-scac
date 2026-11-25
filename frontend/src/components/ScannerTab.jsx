import React, { useState } from 'react';
import {
  Play,
  Upload,
  FileCode,
  ShieldAlert,
  ShieldCheck,
  CheckCircle,
  AlertTriangle,
  GitCompare,
  Copy,
  Check,
  RefreshCw,
  Sparkles
} from 'lucide-react';
import GraphInspector from './GraphInspector';

export default function ScannerTab({
  sourceCode,
  setSourceCode,
  contractName,
  setContractName,
  samples,
  handleScan,
  isScanning,
  scanResult,
  onLoadSample
}) {
  const [selectedFunctionForGraph, setSelectedFunctionForGraph] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);

  const handleCopyCode = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setContractName(file.name);
      const reader = new FileReader();
      reader.onload = (event) => {
        setSourceCode(event.target.result);
      };
      reader.readAsText(file);
    }
  };

  const executive = scanResult?.executive_summary;
  const functionResults = scanResult?.function_results || [];

  return (
    <div className="space-y-6">
      {/* Top Banner / Pipeline Stage Indicator */}
      <div className="bg-gradient-to-r from-[#120726] via-[#1a0a33] to-[#120726] border border-purple-800/40 rounded-2xl p-6 shadow-xl shadow-purple-950/20">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-pink-500 animate-ping" />
              <h2 className="text-base font-extrabold text-white tracking-tight">ASTRO Static Analysis Engine</h2>
              <span className="text-[10px] px-2.5 py-0.5 rounded-full border border-pink-500/40 bg-pink-500/10 text-pink-300 font-mono font-bold">
                Bipartite ACFG Similarity & Hungarian Matching (&alpha; = 0.80)
              </span>
            </div>
            <p className="text-xs text-purple-200/80 mt-1.5 max-w-3xl leading-relaxed">
              Detects omitted access control guards by comparing target control flow graphs against
              audited reference contracts with candidate guard patching.
            </p>
          </div>

          {/* Quick Sample Selector Dropdown */}
          <div className="flex items-center space-x-2">
            <span className="text-xs text-purple-200 font-semibold">Quick Sample:</span>
            <select
              className="bg-[#0b0416] border border-purple-700/60 text-xs text-purple-100 font-medium rounded-xl px-3 py-2 outline-none focus:border-pink-500 transition-colors shadow-inner"
              onChange={(e) => {
                if (e.target.value) {
                  onLoadSample(e.target.value);
                }
              }}
              defaultValue=""
            >
              <option value="" disabled>
                Select a benchmark contract...
              </option>
              {samples.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.expected_verdict === 'VULNERABLE' ? '⚠️ ' : '🛡️ '}
                  {s.title}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* 5-Step Pipeline Visualizer */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mt-5 pt-4 border-t border-purple-900/50 text-xs font-mono">
          {[
            { num: '01', title: 'Solidity AST Extraction' },
            { num: '02', title: 'Modifier Inlining' },
            { num: '03', title: 'ACFG & IFNG Building' },
            { num: '04', title: 'Hungarian Sim & Patch' },
            { num: '05', title: 'Vote Aggregation' },
          ].map((st, i) => (
            <div
              key={i}
              className={`p-2.5 rounded-xl border transition-all ${
                isScanning
                  ? 'border-pink-500 bg-pink-950/40 text-pink-200 animate-pulse font-bold'
                  : scanResult
                  ? 'border-purple-600/50 bg-purple-950/30 text-purple-200'
                  : 'border-purple-900/50 bg-[#0d051c] text-purple-300/60'
              }`}
            >
              <span className="text-[10px] text-pink-400 font-bold block">{st.num}</span>
              <span className="font-semibold text-[11px] leading-tight block">{st.title}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Editor & Upload Controls */}
      <div className="bg-[#120726] border border-purple-800/40 rounded-2xl overflow-hidden shadow-xl">
        {/* Editor Header */}
        <div className="flex flex-wrap items-center justify-between px-5 py-3 border-b border-purple-900/50 bg-[#0e0520]">
          <div className="flex items-center space-x-2.5">
            <FileCode className="w-4 h-4 text-pink-400" />
            <input
              type="text"
              value={contractName}
              onChange={(e) => setContractName(e.target.value)}
              placeholder="ContractName.sol"
              className="bg-transparent font-mono text-xs font-bold text-white outline-none focus:text-pink-300"
            />
          </div>

          <div className="flex items-center space-x-2 mt-2 sm:mt-0">
            <label className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-purple-950/60 hover:bg-purple-900/60 text-xs text-purple-200 font-semibold cursor-pointer transition-colors border border-purple-700/50">
              <Upload className="w-3.5 h-3.5 text-pink-400" />
              <span>Upload .sol</span>
              <input
                type="file"
                accept=".sol"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>

            <button
              onClick={() => setSourceCode('')}
              className="px-3 py-1.5 rounded-xl bg-purple-950/60 hover:bg-purple-900/60 text-xs text-purple-300 hover:text-white transition-colors border border-purple-850"
            >
              Clear
            </button>

            <button
              onClick={handleScan}
              disabled={isScanning || !sourceCode.trim()}
              className={`flex items-center space-x-2 px-5 py-1.5 rounded-xl text-xs font-bold transition-all shadow-md ${
                isScanning || !sourceCode.trim()
                  ? 'bg-purple-950/80 text-purple-400/50 cursor-not-allowed border border-purple-900'
                  : 'bg-gradient-to-r from-purple-600 via-pink-600 to-pink-500 hover:from-purple-500 hover:to-pink-400 text-white shadow-pink-500/30 active:scale-95'
              }`}
            >
              {isScanning ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Auditing Control Flow...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Run ASTRO Audit</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Solidity Source Editor */}
        <div className="relative font-mono text-xs">
          <textarea
            value={sourceCode}
            onChange={(e) => setSourceCode(e.target.value)}
            placeholder="// Paste Solidity smart contract code here or select a sample above..."
            className="w-full h-80 bg-[#090314] text-purple-100 p-4 font-mono text-xs leading-relaxed outline-none resize-y border-none focus:ring-0 selection:bg-pink-600 selection:text-white"
            spellCheck="false"
          />
        </div>
      </div>

      {/* Executive Risk Dashboard (Results) */}
      {scanResult && executive && (
        <div className="space-y-6 pt-1">
          <div
            className={`p-6 rounded-2xl border-2 transition-all shadow-xl ${
              executive.verdict === 'VULNERABLE'
                ? 'bg-gradient-to-r from-pink-950/50 via-[#180a33] to-[#180a33] border-pink-500/60 shadow-pink-950/40'
                : 'bg-gradient-to-r from-purple-950/50 via-[#180a33] to-[#180a33] border-purple-500/60 shadow-purple-950/40'
            }`}
          >
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
              {/* Verdict Indicator */}
              <div className="flex items-start space-x-4">
                <div
                  className={`p-3.5 rounded-2xl border ${
                    executive.verdict === 'VULNERABLE'
                      ? 'bg-pink-500/20 text-pink-400 border-pink-500/40 shadow-lg shadow-pink-500/20'
                      : 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                  }`}
                >
                  {executive.verdict === 'VULNERABLE' ? (
                    <ShieldAlert className="w-8 h-8" />
                  ) : (
                    <ShieldCheck className="w-8 h-8" />
                  )}
                </div>

                <div>
                  <div className="flex items-center space-x-3">
                    <h3 className="text-lg font-black text-white tracking-tight">
                      {executive.verdict === 'VULNERABLE'
                        ? 'CRITICAL ACCESS CONTROL VULNERABILITY DETECTED'
                        : 'ALL ACCESS CONTROL GUARDS VERIFIED SECURE'}
                    </h3>
                    <span
                      className={`text-xs px-2.5 py-0.5 rounded-full font-mono font-bold uppercase border ${
                        executive.verdict === 'VULNERABLE'
                          ? 'bg-pink-500/20 text-pink-300 border-pink-500/40'
                          : 'bg-purple-500/20 text-purple-200 border-purple-500/40'
                      }`}
                    >
                      {executive.overall_severity} Risk
                    </span>
                  </div>
                  <p className="text-xs text-purple-200/90 font-medium mt-1.5 max-w-2xl leading-relaxed">
                    {executive.message}
                  </p>
                </div>
              </div>

              {/* Stat Counters */}
              <div className="grid grid-cols-3 gap-3 shrink-0">
                <div className="p-3.5 rounded-2xl bg-[#0e0520] border border-purple-900/60 text-center min-w-[100px] shadow-sm">
                  <span className="text-[10px] text-purple-400 uppercase font-mono font-bold">Risk Score</span>
                  <div
                    className={`text-2xl font-black font-mono ${
                      executive.overall_risk_score > 70
                        ? 'text-pink-400'
                        : executive.overall_risk_score > 30
                        ? 'text-purple-300'
                        : 'text-white'
                    }`}
                  >
                    {executive.overall_risk_score}/100
                  </div>
                </div>

                <div className="p-3.5 rounded-2xl bg-[#0e0520] border border-purple-900/60 text-center min-w-[100px] shadow-sm">
                  <span className="text-[10px] text-purple-400 uppercase font-mono font-bold">Vulnerable</span>
                  <div className="text-2xl font-black font-mono text-pink-400">
                    {executive.vulnerable_functions_count}
                  </div>
                </div>

                <div className="p-3.5 rounded-2xl bg-[#0e0520] border border-purple-900/60 text-center min-w-[100px] shadow-sm">
                  <span className="text-[10px] text-purple-400 uppercase font-mono font-bold">Protected</span>
                  <div className="text-2xl font-black font-mono text-white">
                    {executive.safe_functions_count}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Per-Function Findings */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-wider text-purple-300 font-mono">
                Candidate Functions Analyzed ({functionResults.length})
              </h4>
              <span className="text-xs text-purple-400/80">
                Target functions matched against reference corpus
              </span>
            </div>

            {functionResults.map((fn, index) => {
              const bestRef = fn.best_reference;
              const isVuln = fn.verdict === 'VULNERABLE';

              return (
                <div
                  key={index}
                  className={`bg-[#130829] border rounded-2xl p-6 transition-all shadow-lg ${
                    isVuln
                      ? 'border-pink-500/60 hover:border-pink-400 shadow-pink-950/20'
                      : 'border-purple-800/50 hover:border-purple-600'
                  }`}
                >
                  {/* Function Header */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-purple-900/50 gap-3">
                    <div className="flex items-center space-x-3">
                      <div
                        className={`p-2 rounded-xl border ${
                          isVuln
                            ? 'bg-pink-500/20 text-pink-400 border-pink-500/40'
                            : 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                        }`}
                      >
                        {isVuln ? (
                          <AlertTriangle className="w-5 h-5 text-pink-400" />
                        ) : (
                          <CheckCircle className="w-5 h-5 text-purple-300" />
                        )}
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-mono font-bold text-base text-white">
                            {fn.signature}
                          </span>
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-950 border border-purple-700/60 text-purple-200 font-mono uppercase font-bold">
                            {fn.visibility}
                          </span>
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-pink-950/60 border border-pink-800/60 text-pink-300 font-mono font-medium">
                            State Modifying
                          </span>
                        </div>
                        <span className="text-xs text-purple-300/80">
                          Contract: <strong className="text-white">{fn.contract_name}</strong>
                          {fn.modifiers.length > 0 && (
                            <span className="ml-2 text-pink-400 font-mono font-semibold">
                              [modifiers: {fn.modifiers.join(', ')}]
                            </span>
                          )}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 self-start sm:self-auto">
                      <span
                        className={`text-xs px-3 py-1 rounded-full font-bold uppercase font-mono border ${
                          isVuln
                            ? 'bg-pink-500/20 text-pink-300 border-pink-500/40 shadow-sm'
                            : 'bg-purple-500/20 text-purple-200 border-purple-500/40'
                        }`}
                      >
                        {isVuln ? '⚠️ Missing Guard (+1)' : '🛡️ Protected (-1)'}
                      </span>

                      <button
                        onClick={() => setSelectedFunctionForGraph(fn)}
                        className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-purple-950 hover:bg-purple-900 text-purple-200 hover:text-white border border-purple-700 text-xs font-bold transition-colors shadow-sm"
                      >
                        <GitCompare className="w-3.5 h-3.5 text-pink-400" />
                        <span>Inspect ACFG</span>
                      </button>
                    </div>
                  </div>

                  {/* Similarity Metrics & ASTRO Details */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 pt-1">
                    {/* Sim Orig vs Patch */}
                    <div className="p-3.5 rounded-xl bg-[#0c051a] border border-purple-900/60 space-y-2">
                      <span className="text-[10px] font-mono text-purple-400 uppercase block font-bold">
                        ASTRO Two-Step Graph Similarity
                      </span>
                      <div className="space-y-1.5">
                        <div className="flex justify-between text-xs font-semibold">
                          <span className="text-purple-300">Original Sim (Sim_orig):</span>
                          <span className="font-mono text-white">
                            {(bestRef?.sim_orig * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div className="w-full h-2 bg-purple-950 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-purple-500 rounded-full"
                            style={{ width: `${Math.min(100, (bestRef?.sim_orig || 0) * 100)}%` }}
                          />
                        </div>

                        <div className="flex justify-between text-xs font-semibold pt-1">
                          <span className="text-purple-300">Patched Sim (Sim_patch):</span>
                          <span className="font-mono font-bold text-pink-400">
                            {(bestRef?.sim_patch * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div className="w-full h-2 bg-purple-950 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"
                            style={{ width: `${Math.min(100, (bestRef?.sim_patch || 0) * 100)}%` }}
                          />
                        </div>

                        <div className="flex items-center justify-between text-[11px] pt-1 text-pink-400 font-mono font-bold">
                          <span>Similarity Gain (&Delta;Sim):</span>
                          <span>+{(bestRef?.delta_sim * 100).toFixed(1)}%</span>
                        </div>
                      </div>
                    </div>

                    {/* Reference Match Details */}
                    <div className="p-3.5 rounded-xl bg-[#0c051a] border border-purple-900/60 space-y-1.5">
                      <span className="text-[10px] font-mono text-purple-400 uppercase block font-bold">
                        Audited Benchmark Match
                      </span>
                      <div className="text-xs space-y-1">
                        <div>
                          <span className="text-purple-400">Reference: </span>
                          <span className="font-semibold text-white">
                            {bestRef?.contract_name}
                          </span>
                        </div>
                        <div>
                          <span className="text-purple-400">Audited Guard: </span>
                          <span className="font-mono font-bold text-pink-400">
                            {bestRef?.guard_type}
                          </span>
                        </div>
                        <div>
                          <span className="text-purple-400">Voting Score: </span>
                          <span className="font-mono font-bold text-purple-200">
                            Sum = {fn.vote_sum} (Confidence: {(fn.confidence * 100).toFixed(0)}%)
                          </span>
                        </div>
                        <p className="text-[11px] text-purple-300/70 italic pt-1">{bestRef?.reason}</p>
                      </div>
                    </div>

                    {/* Remediation Summary */}
                    <div className="p-3.5 rounded-xl bg-[#0c051a] border border-purple-900/60 space-y-2">
                      <span className="text-[10px] font-mono text-purple-400 uppercase block font-bold">
                        Required Access Guard
                      </span>
                      {isVuln ? (
                        <div className="space-y-2">
                          <div className="text-xs text-pink-300 flex items-center space-x-1.5 font-bold">
                            <AlertTriangle className="w-4 h-4 shrink-0 text-pink-400" />
                            <span>Missing `{bestRef?.guard_type}` check</span>
                          </div>
                          <div className="relative font-mono text-[10px] bg-black/60 p-2 rounded-lg border border-purple-800 text-purple-200 shadow-inner">
                            <code>{bestRef?.guard_code}</code>
                            <button
                              onClick={() => handleCopyCode(bestRef?.guard_code, index)}
                              className="absolute top-1.5 right-1.5 p-1 rounded bg-purple-900/80 hover:bg-purple-800 text-purple-300 hover:text-white"
                              title="Copy code"
                            >
                              {copiedIndex === index ? (
                                <Check className="w-3 h-3 text-pink-400" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="text-xs text-purple-200 font-semibold flex items-center space-x-2 pt-2">
                          <CheckCircle className="w-4 h-4 shrink-0 text-pink-400" />
                          <span>Caller authorization guard verified intact.</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Remediation Patch Accordion */}
                  {isVuln && fn.remediation && (
                    <div className="mt-4 pt-3 border-t border-purple-900/50">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-bold text-pink-400 flex items-center space-x-1.5">
                          <Sparkles className="w-3.5 h-3.5 text-pink-400" />
                          <span>Recommended Solidity Patch</span>
                        </span>
                        <button
                          onClick={() => handleCopyCode(fn.remediation.patch_code, `patch-${index}`)}
                          className="flex items-center space-x-1 text-xs text-purple-300 hover:text-white transition-colors font-medium"
                        >
                          {copiedIndex === `patch-${index}` ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-pink-400" />
                              <span className="text-pink-400 font-bold">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5" />
                              <span>Copy Patch</span>
                            </>
                          )}
                        </button>
                      </div>
                      <pre className="font-mono text-xs bg-black/80 p-3.5 rounded-xl border border-purple-900/80 text-pink-200 overflow-x-auto shadow-inner">
                        {fn.remediation.patch_code}
                      </pre>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Graph Inspector Modal */}
      {selectedFunctionForGraph && (
        <GraphInspector
          functionResult={selectedFunctionForGraph}
          onClose={() => setSelectedFunctionForGraph(null)}
        />
      )}
    </div>
  );
}
