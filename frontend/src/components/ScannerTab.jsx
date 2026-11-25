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
  Sparkles,
  Layers,
  MapPin,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Sliders,
  Scissors
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
  const [expandedTransformIndex, setExpandedTransformIndex] = useState(null);
  const [showRelationships, setShowRelationships] = useState(true);

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
  const contractStructures = scanResult?.contract_structures || {};

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
                Two-Step Hungarian ACFG Matching (&alpha; = 0.80)
              </span>
            </div>
            <p className="text-xs text-purple-200/80 mt-1.5 max-w-3xl leading-relaxed">
              Compares target contract Attribute Control Flow Graphs against both <strong>Audited Safe Templates</strong> and <strong>Known Vulnerable Patterns</strong> to pinpoint omitted access control guards and candidate patch locations.
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
            { num: '01', title: 'Solidity AST & Relationships' },
            { num: '02', title: 'Modifier & Call Inlining' },
            { num: '03', title: 'ACFG & IFNG Building' },
            { num: '04', title: 'Hungarian Matching & Patch' },
            { num: '05', title: 'Dual DB Comparison & Voting' },
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

      {/* Contract Structural & Relationship Inspector */}
      {scanResult && Object.keys(contractStructures).length > 0 && (
        <div className="bg-[#100624] border border-purple-900/50 rounded-2xl p-5 shadow-lg">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-purple-900/50">
            <div className="flex items-center space-x-2">
              <Layers className="w-4 h-4 text-pink-400" />
              <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                Contract Relationship & Structural Model
              </h3>
            </div>
            <button
              onClick={() => setShowRelationships(!showRelationships)}
              className="text-xs text-purple-300 hover:text-white flex items-center space-x-1"
            >
              <span>{showRelationships ? 'Hide Details' : 'Show Details'}</span>
              {showRelationships ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          </div>

          {showRelationships && (
            <div className="space-y-4 text-xs">
              {Object.entries(contractStructures).map(([cName, cStruct]) => (
                <div key={cName} className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-white text-sm">Contract: {cName}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-950 text-purple-300 border border-purple-800">
                      {cStruct.state_variables?.length || 0} State Variables
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-pink-950/60 text-pink-300 border border-pink-800/60">
                      {cStruct.modifiers?.length || 0} Modifiers
                    </span>
                  </div>

                  {/* State Variables Pill Grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                    {cStruct.state_variables?.map((sv, idx) => (
                      <div key={idx} className="p-2.5 rounded-xl bg-[#090314] border border-purple-900/60 text-[11px] font-mono">
                        <div className="flex items-center justify-between text-purple-200">
                          <span className="text-purple-400 text-[10px]">{sv.type}</span>
                          <span className="font-bold text-white">{sv.name}</span>
                        </div>
                        {sv.written_by?.length > 0 && (
                          <div className="mt-1 text-[10px] text-pink-400">
                            Mutated by: {sv.written_by.join(', ')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Structural Relationships List */}
                  {cStruct.relationships?.length > 0 && (
                    <div className="p-3 rounded-xl bg-[#0a0316] border border-purple-900/40 text-[11px] font-mono space-y-1">
                      <span className="text-purple-400 font-bold block mb-1">Functional & Structural Edges:</span>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
                        {cStruct.relationships.map((rel, rIdx) => (
                          <div key={rIdx} className="flex items-center space-x-1.5 text-purple-200 truncate">
                            <span className="text-pink-400 font-bold">[{rel.type}]</span>
                            <span>{rel.description}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

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
                Functions Analyzed & Localized ({functionResults.length})
              </h4>
              <span className="text-xs text-purple-400/80">
                Evaluated against Audited Safe Templates & Known Vulnerable Patterns
              </span>
            </div>

            {functionResults.map((fn, index) => {
              const auditedRef = fn.matched_audited_ref || fn.best_reference;
              const vulnPat = fn.matched_vulnerable_pattern;
              const loc = fn.vulnerability_localization || {};
              const remed = fn.secure_remediation || fn.remediation;
              const pruning = fn.pruning_summary || {};
              const norm = fn.normalization_summary || {};
              const isVuln = fn.verdict === 'VULNERABLE';
              const isTransformExpanded = expandedTransformIndex === index;

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
                        <div className="flex items-center space-x-3 mt-1 text-xs text-purple-300/80">
                          <span>Contract: <strong className="text-white">{fn.contract_name}</strong></span>
                          {loc.start_line && (
                            <span className="flex items-center space-x-1 text-pink-400 font-mono">
                              <MapPin className="w-3 h-3" />
                              <span>Lines {loc.start_line}–{loc.end_line}</span>
                            </span>
                          )}
                          {fn.modifiers.length > 0 && (
                            <span className="text-purple-300 font-mono">
                              [modifiers: {fn.modifiers.join(', ')}]
                            </span>
                          )}
                        </div>
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
                        {isVuln ? `⚠️ ${fn.severity_classification || 'Critical'} (+1)` : '🛡️ Protected (-1)'}
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

                  {/* Dual Reference Comparison: Audited Template + Vulnerable Pattern */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 pt-1">
                    {/* A. Audited Safe Reference Comparison */}
                    <div className="p-3.5 rounded-xl bg-[#0c051a] border border-purple-900/60 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-mono text-purple-400 uppercase font-bold block">
                          Audited Secure Template Match
                        </span>
                        <span className="text-[10px] px-2 py-0.2 rounded-full bg-purple-950 border border-purple-800 text-purple-300 font-mono">
                          {auditedRef?.contract_name}
                        </span>
                      </div>

                      <div className="space-y-1.5 text-xs">
                        <div className="flex justify-between">
                          <span className="text-purple-300">Original Sim (Sim_orig):</span>
                          <span className="font-mono text-white font-bold">
                            {((auditedRef?.sim_orig || 0) * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-purple-950 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-purple-500 rounded-full"
                            style={{ width: `${Math.min(100, (auditedRef?.sim_orig || 0) * 100)}%` }}
                          />
                        </div>

                        <div className="flex justify-between pt-1">
                          <span className="text-purple-300">Patched Sim (Sim_patch):</span>
                          <span className="font-mono font-bold text-pink-400">
                            {((auditedRef?.sim_patch || 0) * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-purple-950 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full"
                            style={{ width: `${Math.min(100, (auditedRef?.sim_patch || 0) * 100)}%` }}
                          />
                        </div>

                        <div className="flex items-center justify-between text-[11px] pt-1 text-pink-400 font-mono font-bold">
                          <span>Similarity Delta (&Delta;Sim):</span>
                          <span>+{((auditedRef?.delta_sim || 0) * 100).toFixed(1)}%</span>
                        </div>

                        <p className="text-[11px] text-purple-300/80 italic pt-1">
                          {auditedRef?.structural_comparison || auditedRef?.reason}
                        </p>
                      </div>
                    </div>

                    {/* B. Known Vulnerable Exploit Pattern Match */}
                    <div className="p-3.5 rounded-xl bg-[#0c051a] border border-purple-900/60 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-mono text-purple-400 uppercase font-bold block">
                          Known Vulnerability Pattern
                        </span>
                        {vulnPat && (
                          <span
                            className={`text-[10px] px-2 py-0.2 rounded-full font-mono font-bold border ${
                              vulnPat.is_direct_pattern_match
                                ? 'bg-pink-500/20 text-pink-300 border-pink-500/40'
                                : 'bg-purple-950 text-purple-300 border-purple-800'
                            }`}
                          >
                            {vulnPat.is_direct_pattern_match ? 'Direct Exploit Match' : 'Corpus Match'}
                          </span>
                        )}
                      </div>

                      {vulnPat ? (
                        <div className="text-xs space-y-1.5">
                          <div className="flex justify-between">
                            <span className="text-purple-300">Exploit Type:</span>
                            <span className="font-bold text-pink-400">{vulnPat.vulnerability_type}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-purple-300">Topological Match:</span>
                            <span className="font-mono font-bold text-white">
                              {((vulnPat.sim_orig || 0) * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="w-full h-1.5 bg-purple-950 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-pink-500 rounded-full"
                              style={{ width: `${Math.min(100, (vulnPat.sim_orig || 0) * 100)}%` }}
                            />
                          </div>
                          <p className="text-[11px] text-purple-300/80 pt-1 leading-relaxed">
                            {vulnPat.comparison_notes}
                          </p>
                        </div>
                      ) : (
                        <p className="text-xs text-purple-400/80 italic pt-2">
                          No direct vulnerable pattern match. Evaluated primarily via audited template patch simulation.
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Transformation Metadata Accordion (Pruning & IFNG Normalization) */}
                  <div className="mt-3 pt-2">
                    <button
                      onClick={() => setExpandedTransformIndex(isTransformExpanded ? null : index)}
                      className="text-xs text-purple-400 hover:text-pink-300 flex items-center space-x-1.5 transition-colors font-mono"
                    >
                      <Scissors className="w-3.5 h-3.5" />
                      <span>
                        Transformation Summary: {pruning.removed_emits?.length || 0} events pruned,{' '}
                        {norm.ifng_node_groups?.length || 0} IFNG groups normalized
                      </span>
                      {isTransformExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    </button>

                    {isTransformExpanded && (
                      <div className="mt-2 p-3 rounded-xl bg-[#090314] border border-purple-900/50 text-[11px] font-mono space-y-2">
                        {pruning.removed_emits?.length > 0 && (
                          <div>
                            <span className="text-purple-400 font-bold block">Pruned Event Emissions (Noise Removal):</span>
                            <div className="space-y-0.5 text-purple-300">
                              {pruning.removed_emits.map((em, eIdx) => (
                                <div key={eIdx}>- {em}</div>
                              ))}
                            </div>
                          </div>
                        )}
                        {norm.ifng_node_groups?.length > 0 && (
                          <div className="pt-1">
                            <span className="text-purple-400 font-bold block">Normalized If-Form Node Groups (IFNG):</span>
                            <div className="space-y-1 text-purple-300">
                              {norm.ifng_node_groups.map((ifng, iIdx) => (
                                <div key={iIdx} className="bg-purple-950/40 p-1.5 rounded border border-purple-900/60">
                                  <span className="text-pink-400 font-bold">IF ({ifng.condition})</span>
                                  <span className="text-slate-400"> &rarr; REVERT (Node #{ifng.revert_node_id}) / ENDIF (Node #{ifng.endif_node_id})</span>
                                  {ifng.is_guard && <span className="ml-2 text-[9px] px-1 rounded bg-pink-500/20 text-pink-300">GUARD</span>}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Vulnerability Localization & Remediation Patch */}
                  {isVuln && remed && (
                    <div className="mt-4 pt-3 border-t border-purple-900/50 space-y-3">
                      {/* Localization bar */}
                      <div className="p-2.5 rounded-xl bg-pink-950/30 border border-pink-500/30 flex items-center justify-between text-xs font-mono">
                        <div className="flex items-center space-x-2 text-pink-300">
                          <MapPin className="w-4 h-4 text-pink-400 shrink-0" />
                          <span>
                            Vulnerability Location: <strong>{fn.function_name}</strong> (Lines {loc.start_line}–{loc.end_line}) &middot; {loc.missing_guard_location}
                          </span>
                        </div>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-pink-500/20 text-pink-200 border border-pink-500/40 font-bold uppercase">
                          {fn.severity_classification || 'Critical'}
                        </span>
                      </div>

                      {/* Actionable Steps */}
                      {remed.actionable_steps?.length > 0 && (
                        <div className="p-3 rounded-xl bg-[#090314] border border-purple-900/50 text-xs space-y-1">
                          <span className="text-purple-400 font-bold font-mono block">Actionable Security Recommendations:</span>
                          <ul className="space-y-1 text-purple-200">
                            {remed.actionable_steps.map((st, sIdx) => (
                              <li key={sIdx} className="flex items-start space-x-2">
                                <span className="text-pink-400">&bull;</span>
                                <span>{st}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Code Patch */}
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-bold text-pink-400 flex items-center space-x-1.5">
                            <Sparkles className="w-3.5 h-3.5 text-pink-400" />
                            <span>Remediation Code Patch</span>
                          </span>
                          <button
                            onClick={() => handleCopyCode(remed.patch_code, `patch-${index}`)}
                            className="flex items-center space-x-1 text-xs text-purple-300 hover:text-white transition-colors font-medium font-mono"
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
                          {remed.patch_code}
                        </pre>
                      </div>
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
