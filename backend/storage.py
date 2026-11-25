import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

# Resolve base directories
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
AUDITED_DB_FILE = os.path.join(DATA_DIR, "audited_db", "reference_contracts.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
SAMPLES_DIR = os.path.join(DATA_DIR, "samples")


def ensure_data_dirs():
    os.makedirs(os.path.join(DATA_DIR, "audited_db"), exist_ok=True)
    os.makedirs(SAMPLES_DIR, exist_ok=True)
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def get_reference_contracts() -> List[Dict[str, Any]]:
    ensure_data_dirs()
    if not os.path.exists(AUDITED_DB_FILE):
        return []
    try:
        with open(AUDITED_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading audited DB: {e}")
        return []


def save_reference_contracts(entries: List[Dict[str, Any]]) -> bool:
    ensure_data_dirs()
    try:
        with open(AUDITED_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving audited DB: {e}")
        return False


def add_reference_contract(entry: Dict[str, Any]) -> Dict[str, Any]:
    entries = get_reference_contracts()
    if not entry.get("id"):
        entry["id"] = f"ref-custom-{entry.get('function_name', 'fn')}-{len(entries) + 1}"
    entries.append(entry)
    save_reference_contracts(entries)
    return entry


def get_samples() -> List[Dict[str, Any]]:
    ensure_data_dirs()
    samples = []
    sample_meta = {
        "vuln_roi_transfer_ownership.sol": {
            "title": "Unprotected transferOwnership in High-Yield ROI DApp",
            "category": "High Risk - Vulnerable",
            "description": "Public transferOwnership function missing onlyOwner modifier, allowing any account to hijack contract ownership and siphon funds.",
            "expected_verdict": "VULNERABLE",
            "target_function": "transferOwnership"
        },
        "vuln_transfer_any_erc20.sol": {
            "title": "Unprotected transferAnyERC20Token Rescue Function",
            "category": "Critical Risk - Vulnerable",
            "description": "ERC20 token rescue function exposed publicly without admin authentication, allowing arbitrary third-party asset drainage.",
            "expected_verdict": "VULNERABLE",
            "target_function": "transferAnyERC20Token"
        },
        "vuln_unprotected_withdraw.sol": {
            "title": "Unrestricted Treasury withdraw",
            "category": "Critical Risk - Vulnerable",
            "description": "Native token withdrawal function missing caller authorization check, permitting any user to drain treasury reserves.",
            "expected_verdict": "VULNERABLE",
            "target_function": "withdraw"
        },
        "safe_ownable_vault.sol": {
            "title": "Safe Ownable Vault with Guards",
            "category": "Protected - Safe",
            "description": "Audited standard implementation employing onlyOwner and whenNotPaused modifiers on all privileged state mutations.",
            "expected_verdict": "SAFE",
            "target_function": "transferOwnership"
        },
        "safe_access_control_token.sol": {
            "title": "Safe Role-Based Access Control Governance Token",
            "category": "Protected - Safe",
            "description": "Secure token using OpenZeppelin-style AccessControl onlyRole checks for minting and role delegation.",
            "expected_verdict": "SAFE",
            "target_function": "mint"
        }
    }

    if os.path.exists(SAMPLES_DIR):
        for fname in sorted(os.listdir(SAMPLES_DIR)):
            if fname.endswith(".sol"):
                filepath = os.path.join(SAMPLES_DIR, fname)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                meta = sample_meta.get(fname, {
                    "title": fname,
                    "category": "Sample Contract",
                    "description": "Sample Solidity contract for ASTRO graph similarity audit.",
                    "expected_verdict": "UNKNOWN",
                    "target_function": "unknown"
                })
                samples.append({
                    "id": fname,
                    "filename": fname,
                    "title": meta["title"],
                    "category": meta["category"],
                    "description": meta["description"],
                    "expected_verdict": meta["expected_verdict"],
                    "target_function": meta["target_function"],
                    "source_code": content
                })
    return samples


def get_sample_by_id(sample_id: str) -> Optional[Dict[str, Any]]:
    samples = get_samples()
    for s in samples:
        if s["id"] == sample_id or s["filename"] == sample_id:
            return s
    return None


def get_history() -> List[Dict[str, Any]]:
    ensure_data_dirs()
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return sorted(data, key=lambda x: x.get("timestamp", ""), reverse=True)
    except Exception as e:
        print(f"Error reading history: {e}")
        return []


def save_history_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    ensure_data_dirs()
    if "id" not in entry:
        entry["id"] = f"scan-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
    if "timestamp" not in entry:
        entry["timestamp"] = datetime.utcnow().isoformat() + "Z"
    history = get_history()
    history.insert(0, entry)
    # keep last 50 scans
    history = history[:50]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")
    return entry
