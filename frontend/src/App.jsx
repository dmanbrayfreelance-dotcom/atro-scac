import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import ScannerTab from './components/ScannerTab';
import SamplesTab from './components/SamplesTab';
import AuditDbTab from './components/AuditDbTab';
import HistoryTab from './components/HistoryTab';
import {
  analyzeContract,
  getSamples,
  getAuditDb,
  getHistory,
  checkHealth,
} from './api';

export default function App() {
  const [activeTab, setActiveTab] = useState('scanner');
  const [apiOnline, setApiOnline] = useState(false);

  // Scanner state
  const [sourceCode, setSourceCode] = useState('');
  const [contractName, setContractName] = useState('HighYieldROIInvestment.sol');
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState(null);

  // App data state
  const [samples, setSamples] = useState([]);
  const [auditDb, setAuditDb] = useState([]);
  const [history, setHistory] = useState([]);

  // Check health and load initial data
  const loadInitialData = async () => {
    try {
      const health = await checkHealth();
      setApiOnline(health.status === 'healthy');
    } catch {
      setApiOnline(false);
    }

    try {
      const [samplesData, dbData, historyData] = await Promise.all([
        getSamples(),
        getAuditDb(),
        getHistory(),
      ]);
      setSamples(samplesData);
      setAuditDb(dbData);
      setHistory(historyData);

      // Default load first vulnerable sample if source is empty
      if (samplesData.length > 0 && !sourceCode) {
        const defaultSample = samplesData.find((s) => s.id.includes('vuln_roi')) || samplesData[0];
        setSourceCode(defaultSample.source_code);
        setContractName(defaultSample.filename);
      }
    } catch (err) {
      console.error('Failed to load initial data:', err);
    }
  };

  useEffect(() => {
    loadInitialData();
    const interval = setInterval(async () => {
      try {
        const health = await checkHealth();
        setApiOnline(health.status === 'healthy');
      } catch {
        setApiOnline(false);
      }
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleScan = async () => {
    if (!sourceCode.trim()) return;
    setIsScanning(true);
    try {
      const result = await analyzeContract(sourceCode, contractName);
      setScanResult(result);
      // Refresh history
      const updatedHistory = await getHistory();
      setHistory(updatedHistory);
    } catch (err) {
      console.error('Scan error:', err);
      alert('Analysis failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsScanning(false);
    }
  };

  const handleLoadSample = (sampleId) => {
    const s = samples.find((x) => x.id === sampleId);
    if (s) {
      setSourceCode(s.source_code);
      setContractName(s.filename);
      setActiveTab('scanner');
    }
  };

  const handleRunSample = async (sample) => {
    setSourceCode(sample.source_code);
    setContractName(sample.filename);
    setActiveTab('scanner');
    setIsScanning(true);
    try {
      const result = await analyzeContract(sample.source_code, sample.filename);
      setScanResult(result);
      const updatedHistory = await getHistory();
      setHistory(updatedHistory);
    } catch (err) {
      console.error('Scan error:', err);
      alert('Analysis failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsScanning(false);
    }
  };

  const handleSelectHistoryScan = (scanItem) => {
    setScanResult(scanItem);
    if (scanItem.source_code_snippet) {
      setContractName(scanItem.filename);
    }
    setActiveTab('scanner');
  };

  return (
    <div className="min-h-screen bg-[#090314] text-white flex flex-col font-['Plus_Jakarta_Sans',sans-serif]">
      {/* Navigation Bar */}
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} apiOnline={apiOnline} />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'scanner' && (
          <ScannerTab
            sourceCode={sourceCode}
            setSourceCode={setSourceCode}
            contractName={contractName}
            setContractName={setContractName}
            samples={samples}
            handleScan={handleScan}
            isScanning={isScanning}
            scanResult={scanResult}
            onLoadSample={handleLoadSample}
          />
        )}

        {activeTab === 'samples' && (
          <SamplesTab
            samples={samples}
            onLoadSample={handleLoadSample}
            onRunSample={handleRunSample}
          />
        )}

        {activeTab === 'auditdb' && (
          <AuditDbTab
            auditDb={auditDb}
            onRefreshDb={async () => {
              const data = await getAuditDb();
              setAuditDb(data);
            }}
          />
        )}

        {activeTab === 'history' && (
          <HistoryTab history={history} onSelectScan={handleSelectHistoryScan} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-purple-900/40 bg-[#0c051a] py-6 text-xs text-purple-300/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <span className="font-extrabold text-white">ASTRO</span>
            <span>·</span>
            <span>Detecting Access Control Vulnerabilities via ACFG Graph Similarity</span>
          </div>
          <div className="font-mono text-[11px] text-purple-400/80">
            Bipartite Hungarian Matching &middot; Threshold &alpha; = 0.80 &middot; Fast Static Analysis
          </div>
        </div>
      </footer>
    </div>
  );
}
