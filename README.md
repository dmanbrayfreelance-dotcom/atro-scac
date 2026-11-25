# atro-scac

# ASTRO: Detecting Access Control Vulnerabilities in Smart Contracts via Graph Similarity Comparison

ASTRO is an advanced static analysis framework and full-stack web application designed to automatically detect missing access control vulnerabilities in Ethereum and EVM-compatible smart contracts. By transforming candidate smart contract functions into standardized Attribute Control Flow Graphs (ACFGs) and performing two-step bipartite graph matching against a reference corpus of verified audited contracts, ASTRO pinpoints unprotected sensitive state transitions (such as hijacked ownership, unauthorized minting, and unrestricted fund withdrawals).

---

## 🔬 Scientific & Methodological Architecture

### 1. The Access Control Problem in Smart Contracts
Decentralized applications frequently require privileged administrative functions (e.g. `transferOwnership`, `withdraw`, `pause`, `mint`, `setFee`). Vulnerable contracts occur when developers accidentally omit caller authorization checks (such as OpenZeppelin `onlyOwner`, `require(msg.sender == owner)`, or Role-Based Access Control `hasRole(...)`).

### 2. ASTRO Graph Representation (ACFG)
- **Function Decomposition:** Extracts externally callable (`public` / `external`) state-modifying functions (excluding `view` and `pure`).
- **Modifier Inlining:** Analyzes attached modifiers (`onlyOwner`, `onlyRole`, custom modifiers), resolves statement bodies, and inlines logic directly into function control flow while stripping `_` placeholders.
- **If-Form Node Group (IFNG) Normalization:** Standardizes disparate check patterns (`require(...)`, `assert(...)`, `if (...) revert(...)`) into canonical three-node groups:
  - `IF` node: Evaluates condition and flags caller attributes (`reads_sender`, `is_guard`).
  - `REVERT` node: Failure edge.
  - `ENDIF` node: Continuation join edge.
- **ASTRO Pruning Rules:** Event emissions (`emit Transfer(...)`) and non-access-control logging are cleanly removed, and incoming predecessor edges are reconnected directly to outgoing successor edges.
- **Sequential BFS Re-ordering:** Nodes are indexed via Breadth-First Search traversal starting from `ENTRY (node 0)`.

### 3. Two-Step Bipartite Similarity Matching with Hungarian Algorithm
1. **Original Graph Matching ($Sim_{\text{orig}}$):**
   Given candidate target graph $G_T$ and reference audited graph $G_R$, ASTRO builds a cost matrix based on node type, guard attributes, state flags, and edge connectivity compatibility. The Hungarian algorithm (`scipy.optimize.linear_sum_assignment`) computes the optimal bijection between $V(G_T)$ and $V(G_R)$.
2. **Candidate Guard Patching ($Sim_{\text{patch}}$):**
   If $G_T$ lacks an access guard, ASTRO synthesizes a candidate Access Control IFNG guard inserted immediately after `ENTRY` to yield $G_T^{\text{patched}}$, and recalculates bipartite similarity $Sim_{\text{patch}} = \text{Sim}(G_T^{\text{patched}}, G_R)$.
3. **ASTRO Decision Rule ($\alpha = 0.80$):**
   - If $G_T$ already has access guards and $Sim_{\text{orig}} \ge \alpha \implies$ **SAFE (Vote: -1)**
   - If $G_T$ lacks access guards, and $Sim_{\text{patch}} \ge \alpha$ with significant gain ($\Delta Sim > 0.15$) $\implies$ **VULNERABLE (Vote: +1)**
   - Unrelated logic $\implies$ **INCONCLUSIVE (Vote: 0)**
4. **Vote Aggregation:**
   Target functions are compared against multiple database entries. When the non-zero vote count is even, the lowest-confidence vote is dropped to break ties. If $\sum \text{Votes} > 0$, the function is classified as **VULNERABLE**.

---

## 📁 Repository Structure

```
astro-smart-contract-auditor/
├── README.md                           # Comprehensive documentation & architecture guide
├── backend/
│   ├── requirements.txt                # Python backend dependencies
│   ├── main.py                         # FastAPI REST application & endpoints
│   ├── extractor.py                    # Resilient Solidity AST & candidate function extractor
│   ├── graph_builder.py                # ACFG builder, IFNG normalization & pruning rules
│   ├── similarity_engine.py            # Hungarian matching, patch testing & vote aggregation
│   └── storage.py                      # Data persistence for reference DB & scan history
├── frontend/
│   ├── package.json                    # Frontend dependencies (React, Vite, Tailwind, Lucide)
│   ├── vite.config.js                  # Vite configuration (port 5173)
│   ├── index.html                      # HTML root
│   └── src/
│       ├── main.jsx                    # React entry point
│       ├── index.css                   # Tailwind styling
│       ├── App.jsx                     # Top-level application orchestrator
│       ├── api.js                      # Axios API service client
│       └── components/
│           ├── Navbar.jsx              # Navigation header with system health status
│           ├── ScannerTab.jsx          # Solidity editor, scan controls, executive cards & patches
│           ├── SamplesTab.jsx          # 1-click test benchmark corpus (3 vulnerable, 2 safe)
│           ├── AuditDbTab.jsx          # Audited reference database explorer & registrar
│           ├── HistoryTab.jsx          # Historical scan logs and reports
│           └── GraphInspector.jsx      # Side-by-side ACFG graph comparison & Hungarian matrix
└── data/
    ├── audited_db/
    │   └── reference_contracts.json    # Audited safe reference corpus with precomputed ACFGs
    ├── samples/
    │   ├── vuln_roi_transfer_ownership.sol # Vulnerable ROI DApp (missing onlyOwner)
    │   ├── vuln_transfer_any_erc20.sol     # Vulnerable token rescuer (unprotected external transfer)
    │   ├── vuln_unprotected_withdraw.sol   # Vulnerable treasury (unprotected native balance drain)
    │   ├── safe_ownable_vault.sol          # Safe Ownable vault with modifier guards
    │   └── safe_access_control_token.sol   # Safe RBAC token with onlyRole guards
    └── history.json                    # Audit execution history
```

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.10+
- Node.js v18+ & npm

### 1. Start the Backend API Server
```bash
cd astro-smart-contract-auditor/backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
The FastAPI documentation will be available at `http://localhost:8000/docs`.

### 2. Start the Frontend Application
```bash
cd astro-smart-contract-auditor/frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🧪 Benchmark Sample Contracts

1. **`vuln_roi_transfer_ownership.sol` (Vulnerable - Critical):**
   High-yield staking DApp where `transferOwnership` omits `onlyOwner`, allowing arbitrary callers to claim contract ownership.
2. **`vuln_transfer_any_erc20.sol` (Vulnerable - Critical):**
   Liquidity manager exposing `transferAnyERC20Token` publicly without authorization, allowing attackers to drain third-party tokens.
3. **`vuln_unprotected_withdraw.sol` (Vulnerable - Critical):**
   Treasury contract allowing any user to withdraw arbitrary amounts of ETH balance.
4. **`safe_ownable_vault.sol` (Safe - Protected):**
   Reference implementation enforcing `onlyOwner` modifiers and zero-address validation.
5. **`safe_access_control_token.sol` (Safe - Protected):**
   Role-based access control governance token implementing OpenZeppelin `onlyRole` guards.

---

## 🛡️ License
MIT License.
