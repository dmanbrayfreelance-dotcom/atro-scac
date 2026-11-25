import React, { useState } from 'react';
import { Database, Plus, Search, GitBranch } from 'lucide-react';
import { addAuditDbEntry } from '../api';

export default function AuditDbTab({ auditDb, onRefreshDb }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [newEntry, setNewEntry] = useState({
    contract_name: '',
    function_name: '',
    signature: '',
    guard_type: 'onlyOwner',
    guard_code: 'require(msg.sender == owner, "Caller is not the owner");',
    description: '',
    source_code: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const filtered = auditDb.filter(
    (e) =>
      e.function_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.contract_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.guard_type.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newEntry.contract_name || !newEntry.function_name) return;
    setIsSubmitting(true);
    try {
      await addAuditDbEntry(newEntry);
      setShowAddModal(false);
      setNewEntry({
        contract_name: '',
        function_name: '',
        signature: '',
        guard_type: 'onlyOwner',
        guard_code: 'require(msg.sender == owner, "Caller is not the owner");',
        description: '',
        source_code: '',
      });
      if (onRefreshDb) onRefreshDb();
    } catch (err) {
      console.error('Failed to create reference entry:', err);
      alert('Error adding entry to database: ' + err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-[#120726] border border-purple-800/40 rounded-2xl p-6 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-purple-600 to-pink-500 text-white shadow-md shadow-pink-500/20">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-extrabold text-white">Audited Reference Database</h2>
              <p className="text-xs text-purple-300/80">
                Corpus of benchmark smart contracts and precomputed Attribute Control Flow Graphs (ACFG)
              </p>
            </div>
          </div>

          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-purple-600 via-pink-600 to-pink-500 hover:from-purple-500 hover:to-pink-400 text-white text-xs font-bold transition-all shadow-md shadow-pink-500/30 self-start sm:self-auto"
          >
            <Plus className="w-4 h-4" />
            <span>Add Reference Function</span>
          </button>
        </div>

        {/* Search */}
        <div className="mt-5 relative">
          <Search className="w-4 h-4 text-purple-400 absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder="Search by function name, contract, or guard type..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-[#0b0416] border border-purple-800/70 rounded-xl pl-10 pr-4 py-2 text-xs text-purple-100 placeholder-purple-400/60 outline-none focus:border-pink-500 transition-colors shadow-inner"
          />
        </div>
      </div>

      {/* References Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filtered.map((entry) => (
          <div
            key={entry.id}
            className="bg-[#130829] border border-purple-800/50 rounded-2xl p-6 hover:border-pink-500/50 hover:shadow-lg transition-all flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-purple-900/50">
                <span className="font-mono text-sm font-bold text-white">
                  {entry.function_name}
                </span>
                <span className="text-[10px] px-2.5 py-0.5 rounded-full border border-pink-500/40 bg-pink-500/10 text-pink-300 font-mono font-bold">
                  {entry.guard_type}
                </span>
              </div>

              <div className="space-y-2 mb-4">
                <div>
                  <span className="text-[10px] text-purple-400 uppercase font-mono font-bold block">
                    Contract:
                  </span>
                  <span className="text-xs font-bold text-purple-200">{entry.contract_name}</span>
                </div>

                <div>
                  <span className="text-[10px] text-purple-400 uppercase font-mono font-bold block">
                    Signature:
                  </span>
                  <code className="text-xs font-mono text-purple-100 bg-[#0b0416] px-2 py-1 rounded-lg block truncate border border-purple-900">
                    {entry.signature}
                  </code>
                </div>

                <div>
                  <span className="text-[10px] text-purple-400 uppercase font-mono font-bold block">
                    Access Control Guard Logic:
                  </span>
                  <code className="text-[11px] font-mono text-pink-300 bg-pink-950/30 border border-pink-800/40 p-2 rounded-lg block break-all font-semibold">
                    {entry.guard_code}
                  </code>
                </div>

                {entry.description && (
                  <p className="text-xs text-purple-300/80 pt-1 leading-relaxed">
                    {entry.description}
                  </p>
                )}
              </div>
            </div>

            {/* Footer with ACFG node counts */}
            <div className="pt-3 border-t border-purple-900/40 flex items-center justify-between text-xs font-mono text-purple-400">
              <span className="flex items-center space-x-1.5 font-medium">
                <GitBranch className="w-3.5 h-3.5 text-pink-400" />
                <span>
                  ACFG: {entry.acfg?.nodes?.length || 0} nodes ·{' '}
                  {entry.acfg?.edges?.length || 0} edges
                </span>
              </span>
              <span className="text-[10px] text-purple-200 font-bold bg-purple-950 px-2 py-0.5 rounded-full border border-purple-800">
                Audited Safe
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Modal to Add New Reference */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="bg-[#120726] border-2 border-purple-800/60 rounded-2xl w-full max-w-xl p-6 shadow-2xl">
            <h3 className="text-base font-black text-white mb-1">Register Audited Reference Function</h3>
            <p className="text-xs text-purple-300/80 mb-4">
              Add a verified secure implementation to expand the ASTRO similarity matching corpus.
            </p>

            <form onSubmit={handleCreate} className="space-y-4 text-xs font-mono">
              <div>
                <label className="text-purple-200 font-bold block mb-1">Contract Name:</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. OpenZeppelin_ERC20"
                  value={newEntry.contract_name}
                  onChange={(e) => setNewEntry({ ...newEntry, contract_name: e.target.value })}
                  className="w-full bg-[#0b0416] border border-purple-800 rounded-lg p-2.5 text-white outline-none focus:border-pink-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-purple-200 font-bold block mb-1">Function Name:</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. mint"
                    value={newEntry.function_name}
                    onChange={(e) => {
                      const fn = e.target.value;
                      setNewEntry({
                        ...newEntry,
                        function_name: fn,
                        signature: `${fn}()`,
                      });
                    }}
                    className="w-full bg-[#0b0416] border border-purple-800 rounded-lg p-2.5 text-white outline-none focus:border-pink-500"
                  />
                </div>

                <div>
                  <label className="text-purple-200 font-bold block mb-1">Signature:</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. mint(address,uint256)"
                    value={newEntry.signature}
                    onChange={(e) => setNewEntry({ ...newEntry, signature: e.target.value })}
                    className="w-full bg-[#0b0416] border border-purple-800 rounded-lg p-2.5 text-white outline-none focus:border-pink-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-purple-200 font-bold block mb-1">Guard Type:</label>
                  <input
                    type="text"
                    required
                    placeholder="onlyOwner, onlyRole, requiresAuth"
                    value={newEntry.guard_type}
                    onChange={(e) => setNewEntry({ ...newEntry, guard_type: e.target.value })}
                    className="w-full bg-[#0b0416] border border-purple-800 rounded-lg p-2.5 text-white outline-none focus:border-pink-500"
                  />
                </div>

                <div>
                  <label className="text-purple-200 font-bold block mb-1">Guard Check Statement:</label>
                  <input
                    type="text"
                    required
                    placeholder='require(msg.sender == owner, "Unauthorized");'
                    value={newEntry.guard_code}
                    onChange={(e) => setNewEntry({ ...newEntry, guard_code: e.target.value })}
                    className="w-full bg-[#0b0416] border border-purple-800 rounded-lg p-2.5 text-white outline-none focus:border-pink-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-purple-200 font-bold block mb-1">Source Code Snippet:</label>
                <textarea
                  rows={4}
                  placeholder="function transferOwnership(...) public onlyOwner { ... }"
                  value={newEntry.source_code}
                  onChange={(e) => setNewEntry({ ...newEntry, source_code: e.target.value })}
                  className="w-full bg-[#0b0416] border border-purple-800 rounded-lg p-2.5 text-white outline-none focus:border-pink-500 font-mono"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-lg bg-purple-950 hover:bg-purple-900 text-purple-200 font-semibold border border-purple-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-lg bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-500 hover:to-pink-400 text-white font-bold font-sans transition-colors shadow-md shadow-pink-500/30"
                >
                  {isSubmitting ? 'Saving...' : 'Save to DB'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
