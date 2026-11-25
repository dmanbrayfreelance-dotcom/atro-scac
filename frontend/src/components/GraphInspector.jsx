import React, { useState } from 'react';
import {
  GitFork,
  ArrowRight,
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  Info,
  Scissors,
  CheckCircle2,
  MapPin
} from 'lucide-react';

export default function GraphInspector({ functionResult, onClose }) {
  const [viewMode, setViewMode] = useState('comparison'); // 'comparison', 'patched', 'vulnerable_pattern', 'bipartite_mapping'
  const [selectedNode, setSelectedNode] = useState(null);

  if (!functionResult) return null;

  const targetACFG = functionResult.acfg || { nodes: [], edges: [] };
  const patchedACFG = functionResult.patched_acfg || targetACFG;
  const auditedRef = functionResult.matched_audited_ref || functionResult.best_reference;
  const vulnPat = functionResult.matched_vulnerable_pattern;
  const loc = functionResult.vulnerability_localization || {};
  const pruning = functionResult.pruning_summary || targetACFG.pruning_summary || {};
  const norm = functionResult.normalization_summary || targetACFG.normalization_summary || {};
  const nodeMapping = auditedRef?.node_mapping || [];

  const getNodeStyle = (type, isGuard) => {
    if (isGuard) {
      return 'border-2 border-pink-500 bg-pink-950/40 text-pink-100 shadow-md shadow-pink-950/30';
    }
    switch (type) {
      case 'ENTRY':
        return 'border-2 border-purple-400 bg-purple-950/40 text-white font-bold';
      case 'IF':
        return 'border border-purple-600/60 bg-[#160a2f] text-purple-100';
      case 'REVERT':
        return 'border-2 border-dashed border-pink-400 bg-pink-950/30 text-pink-200 font-mono';
      case 'ENDIF':
        return 'border border-purple-800 bg-[#120726] text-purple-300';
      case 'STATE_ASSIGN':
        return 'border border-purple-500/70 bg-[#170a33] text-purple-100';
      case 'CALL_EXTERNAL':
        return 'border-2 border-pink-600/70 bg-purple-950/60 text-white';
      case 'RETURN':
        return 'border border-purple-900 bg-[#0e051f] text-purple-400';
      default:
        return 'border border-purple-900 bg-[#100624] text-purple-300';
    }
  };

  const renderGraphColumn = (title, graph, isPatched = false, isReference = false, tag = null) => {
    const nodes = graph?.nodes || [];
    const edges = graph?.edges || [];

    return (
      <div className="flex-1 bg-[#0c051a] rounded-2xl border border-purple-900/60 p-4 flex flex-col min-w-[320px] shadow-sm">
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-purple-900/50">
          <div className="flex items-center space-x-2">
            <span className="font-bold text-xs text-white">{title}</span>
            {isPatched && (
              <span className="text-[9px] px-2 py-0.5 rounded-full border border-pink-500 bg-pink-500/20 text-pink-300 font-mono font-bold shadow-sm">
                + IFNG GUARD
              </span>
            )}
            {tag && (
              <span className="text-[9px] px-2 py-0.5 rounded-full border border-purple-600/60 bg-purple-950 text-purple-200 font-mono font-bold">
                {tag}
              </span>
            )}
          </div>
          <span className="text-xs font-mono text-purple-400">
            {nodes.length} nodes · {edges.length} edges
          </span>
        </div>

        {/* Nodes Flow */}
        <div className="space-y-2.5 overflow-y-auto max-h-[440px] pr-2">
          {nodes.map((node) => {
            const isSelected = selectedNode?.id === node.id && selectedNode?.isRef === isReference;
            return (
              <div
                key={node.id}
                onClick={() => setSelectedNode({ ...node, isRef: isReference })}
                className={`p-3 rounded-xl border text-xs cursor-pointer transition-all ${getNodeStyle(
                  node.type,
                  node.is_guard
                )} ${isSelected ? 'ring-2 ring-pink-500 scale-[1.01]' : 'hover:border-purple-500'}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-purple-950 text-purple-200 font-bold border border-purple-800">
                      #{node.id}
                    </span>
                    <span className="font-bold uppercase tracking-wider text-[10px]">
                      {node.type}
                    </span>
                  </div>
                  <div className="flex items-center space-x-1">
                    {node.is_guard && (
                      <span className="text-[9px] px-2 py-0.2 rounded-full border border-pink-500 bg-pink-500/30 text-pink-200 font-black">
                        GUARD
                      </span>
                    )}
                    {node.reads_sender && (
                      <span className="text-[9px] px-1.5 py-0.2 rounded bg-purple-950 text-purple-300 font-mono font-medium">
                        reads_sender
                      </span>
                    )}
                    {node.modifies_state && (
                      <span className="text-[9px] px-1.5 py-0.2 rounded bg-purple-950 text-pink-300 font-mono font-medium">
                        state_mut
                      </span>
                    )}
                  </div>
                </div>
                <div className="font-mono text-[11px] break-all bg-black/60 p-2 rounded-lg text-purple-100 border border-purple-950 shadow-inner">
                  {node.code}
                </div>
                {edges.filter(([u]) => u === node.id).length > 0 && (
                  <div className="mt-1.5 flex items-center space-x-1 text-[10px] text-purple-400">
                    <ArrowRight className="w-3 h-3 text-pink-400" />
                    <span>
                      leads to:{' '}
                      {edges
                        .filter(([u]) => u === node.id)
                        .map(([, v]) => `#${v}`)
                        .join(', ')}
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div className="bg-[#120726] border-2 border-purple-800/60 rounded-2xl w-full max-w-6xl max-h-[94vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-purple-900/50 bg-[#0c051a]">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-purple-600 to-pink-500 text-white shadow-md shadow-pink-500/20">
              <GitFork className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="font-black text-base text-white">
                  ACFG Graph Inspector & Structural Comparisons
                </h3>
                <span className="font-mono text-xs px-2.5 py-0.5 rounded-full bg-pink-500/10 text-pink-300 border border-pink-500/30 font-bold">
                  {functionResult.signature}
                </span>
                {loc.start_line && (
                  <span className="text-xs text-purple-300 flex items-center space-x-1">
                    <MapPin className="w-3 h-3 text-pink-400" />
                    <span>Lines {loc.start_line}–{loc.end_line}</span>
                  </span>
                )}
              </div>
              <p className="text-xs text-purple-300/80">
                Evaluating candidate Attribute Control Flow Graph transformations and bipartite node assignments
              </p>
            </div>
          </div>

          {/* Mode Switcher */}
          <div className="flex items-center space-x-1.5 bg-[#090314] p-1 rounded-xl border border-purple-900">
            <button
              onClick={() => setViewMode('comparison')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                viewMode === 'comparison'
                  ? 'bg-gradient-to-r from-purple-600 to-pink-500 text-white shadow-sm'
                  : 'text-purple-300 hover:text-white'
              }`}
            >
              Audited Safe Ref
            </button>
            <button
              onClick={() => setViewMode('patched')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                viewMode === 'patched'
                  ? 'bg-gradient-to-r from-purple-600 to-pink-500 text-white shadow-sm'
                  : 'text-purple-300 hover:text-white'
              }`}
            >
              Patch Test (G_T^patched)
            </button>
            {vulnPat && (
              <button
                onClick={() => setViewMode('vulnerable_pattern')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  viewMode === 'vulnerable_pattern'
                    ? 'bg-gradient-to-r from-purple-600 to-pink-500 text-white shadow-sm'
                    : 'text-purple-300 hover:text-white'
                }`}
              >
                Known Exploit Pattern
              </button>
            )}
            <button
              onClick={() => setViewMode('bipartite_mapping')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                viewMode === 'bipartite_mapping'
                  ? 'bg-gradient-to-r from-purple-600 to-pink-500 text-white shadow-sm'
                  : 'text-purple-300 hover:text-white'
              }`}
            >
              Hungarian Matrix
            </button>
          </div>

          <button
            onClick={onClose}
            className="text-purple-400 hover:text-white p-2 rounded-lg hover:bg-purple-950 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Executive Metrics Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 px-6 py-3 bg-[#0f0620] border-b border-purple-900/50 text-xs">
          <div>
            <span className="text-purple-400">Target Function:</span>
            <div className="font-mono font-bold text-white truncate">
              {functionResult.function_name} ({functionResult.visibility})
            </div>
          </div>
          <div>
            <span className="text-purple-400">Audited Safe Reference:</span>
            <div className="font-mono font-bold text-purple-200 truncate">
              {auditedRef?.contract_name} :: {auditedRef?.function_name}
            </div>
          </div>
          <div>
            <span className="text-purple-400">Hungarian Sim (Orig &rarr; Patch):</span>
            <div className="font-mono font-bold flex items-center space-x-1.5">
              <span className="text-purple-300">{((auditedRef?.sim_orig || 0) * 100).toFixed(1)}%</span>
              <span className="text-purple-500">&rarr;</span>
              <span className="text-pink-400 font-black">
                {((auditedRef?.sim_patch || 0) * 100).toFixed(1)}%
              </span>
              <span className="text-[10px] text-pink-300 font-bold ml-1">
                (+{((auditedRef?.delta_sim || 0) * 100).toFixed(1)}%)
              </span>
            </div>
          </div>
          <div>
            <span className="text-purple-400">Verdict & Severity:</span>
            <div className="flex items-center space-x-1 font-black">
              {functionResult.verdict === 'VULNERABLE' ? (
                <span className="text-pink-400 flex items-center space-x-1 font-bold">
                  <ShieldAlert className="w-3.5 h-3.5 text-pink-400" />
                  <span>VULNERABLE ({functionResult.severity_classification || 'Critical'})</span>
                </span>
              ) : (
                <span className="text-purple-200 flex items-center space-x-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-purple-300" />
                  <span>SAFE</span>
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Transformation summary pills */}
        <div className="px-6 py-2 bg-[#0a0316] border-b border-purple-900/40 text-[11px] font-mono flex flex-wrap items-center justify-between text-purple-300 gap-2">
          <div className="flex items-center space-x-3">
            <span className="flex items-center space-x-1 text-pink-400 font-bold">
              <Scissors className="w-3.5 h-3.5" />
              <span>Pruning:</span>
            </span>
            <span>{pruning.removed_emits?.length || 0} event emissions pruned</span>
            <span>&middot;</span>
            <span>{pruning.reconnected_edges || 0} control edges reconnected</span>
          </div>

          <div className="flex items-center space-x-3">
            <span className="text-purple-400 font-bold">Normalization:</span>
            <span>{norm.ifng_node_groups?.length || 0} If-Form Node Groups</span>
            <span>&middot;</span>
            <span>{norm.inlined_modifiers?.length || 0} modifiers inlined</span>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 bg-[#090314]">
          {viewMode === 'comparison' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {renderGraphColumn(
                `Target ACFG: ${functionResult.function_name}`,
                targetACFG,
                false,
                false,
                "Candidate"
              )}
              {renderGraphColumn(
                `Audited Safe ACFG: ${auditedRef?.contract_name || 'OpenZeppelin'}`,
                auditedRef?.acfg || targetACFG,
                false,
                true,
                "Audited Safe"
              )}
            </div>
          )}

          {viewMode === 'patched' && (
            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-pink-950/40 border-2 border-pink-500/40 text-xs text-pink-200 flex items-start space-x-3 shadow-md shadow-pink-950/30">
                <Sparkles className="w-4 h-4 text-pink-400 mt-0.5 shrink-0" />
                <div>
                  <span className="font-bold text-white">ASTRO Candidate Guard Insertion:</span> The similarity engine injects the synthetic candidate Access Control If-Form Node Group (<code className="text-pink-300 font-bold">IF (msg.sender == owner) &rarr; REVERT</code>) immediately after the ENTRY node, causing isomorphism with the audited reference to reach {((auditedRef?.sim_patch || 0) * 100).toFixed(1)}%.
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {renderGraphColumn(
                  `Patched Graph G_T^patched (Sim: ${((auditedRef?.sim_patch || 0) * 100).toFixed(1)}%)`,
                  patchedACFG,
                  true,
                  false,
                  "Patched"
                )}
                {renderGraphColumn(
                  `Audited Reference ACFG (${auditedRef?.contract_name})`,
                  auditedRef?.acfg || targetACFG,
                  false,
                  true,
                  "Audited Safe"
                )}
              </div>
            </div>
          )}

          {viewMode === 'vulnerable_pattern' && vulnPat && (
            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-pink-950/40 border-2 border-pink-500/40 text-xs text-pink-200 flex items-start space-x-3 shadow-md shadow-pink-950/30">
                <ShieldAlert className="w-4 h-4 text-pink-400 mt-0.5 shrink-0" />
                <div>
                  <span className="font-bold text-white">Known Exploit Pattern Alignment:</span> Comparing target against known exploit pattern '{vulnPat.vulnerability_type}'. Topological match score: {((vulnPat.sim_orig || 0) * 100).toFixed(1)}%.
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {renderGraphColumn(
                  `Target Contract ACFG: ${functionResult.function_name}`,
                  targetACFG,
                  false,
                  false,
                  "Candidate"
                )}
                {renderGraphColumn(
                  `Known Exploit Pattern: ${vulnPat.contract_name}`,
                  vulnPat.acfg || targetACFG,
                  false,
                  true,
                  "Known Vulnerable"
                )}
              </div>
            </div>
          )}

          {viewMode === 'bipartite_mapping' && (
            <div className="bg-[#120726] rounded-2xl border border-purple-900/60 p-5 shadow-sm">
              <div className="flex items-center justify-between mb-4 pb-2 border-b border-purple-900/50">
                <h4 className="font-bold text-xs text-white">
                  Hungarian Algorithm Optimal Node Assignment
                </h4>
                <span className="text-xs text-purple-400">
                  Threshold &alpha; = 0.80 &middot; Evaluated via scipy linear_sum_assignment
                </span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#0b0416] text-purple-300 font-mono uppercase text-[10px] border-b border-purple-900">
                    <tr>
                      <th className="py-2.5 px-3">Target Node (T)</th>
                      <th className="py-2.5 px-3">Target Code Snippet</th>
                      <th className="py-2.5 px-3">Ref Node (R)</th>
                      <th className="py-2.5 px-3">Reference Code Snippet</th>
                      <th className="py-2.5 px-3 text-right">Alignment Score S(u,v)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-purple-950 font-mono">
                    {nodeMapping.map((mapItem, i) => (
                      <tr key={i} className="hover:bg-purple-950/40">
                        <td className="py-2 px-3 text-pink-400 font-bold">
                          {mapItem.target_node_id !== null ? `#${mapItem.target_node_id}` : '—'}
                        </td>
                        <td className="py-2 px-3 text-purple-200 max-w-xs truncate font-medium">
                          {mapItem.target_code}
                        </td>
                        <td className="py-2 px-3 text-white font-bold">
                          {mapItem.reference_node_id !== null
                            ? `#${mapItem.reference_node_id}`
                            : '—'}
                        </td>
                        <td className="py-2 px-3 text-purple-300 max-w-xs truncate">
                          {mapItem.reference_code}
                        </td>
                        <td className="py-2 px-3 text-right">
                          <span
                            className={`px-2 py-0.5 rounded font-bold border ${
                              mapItem.similarity >= 0.8
                                ? 'bg-gradient-to-r from-purple-600 to-pink-500 text-white border-pink-400'
                                : mapItem.similarity >= 0.5
                                ? 'bg-purple-900 text-purple-200 border-purple-700'
                                : 'bg-black text-purple-400 border-purple-900'
                            }`}
                          >
                            {(mapItem.similarity * 100).toFixed(0)}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-purple-900/50 bg-[#0c051a] flex items-center justify-between text-xs text-purple-300">
          <div className="flex items-center space-x-2">
            <Info className="w-4 h-4 text-pink-400" />
            <span>
              ASTRO standardized If-Form Node Groups: IF &rarr; REVERT / ENDIF.
            </span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-purple-900 hover:bg-purple-800 text-white font-bold transition-colors shadow-sm border border-purple-700"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
