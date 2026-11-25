import urllib.request
import json
import os

def test_api():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sample_path = os.path.join(base_dir, "data", "samples", "vuln_roi_transfer_ownership.sol")
    
    with open(sample_path, "r", encoding="utf-8") as f:
        code = f.read()

    payload = {
        "source_code": code,
        "filename": "vuln_roi_transfer_ownership.sol"
    }

    req = urllib.request.Request(
        "http://localhost:8000/api/analyze",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req) as response:
        assert response.status == 200, f"Expected status 200, got {response.status}"
        data = json.loads(response.read().decode("utf-8"))

    print("=== ASTRO API End-to-End Test Results ===")
    print("Contract Filename:", data.get("filename"))
    print("Executive Verdict:", data["executive_summary"]["verdict"])
    print("Executive Risk Score:", data["executive_summary"]["overall_risk_score"])
    print("Vulnerable Functions:", data["executive_summary"]["vulnerable_functions_count"])
    print("Safe Functions:", data["executive_summary"]["safe_functions_count"])
    
    for fn in data.get("function_results", []):
        best_ref = fn.get("best_reference", {})
        print(f"\nFunction: {fn['signature']}")
        print(f"  - Verdict: {fn['verdict']}")
        print(f"  - Severity: {fn['severity']} (Score: {fn['risk_score']})")
        print(f"  - Original Similarity (Sim_orig): {best_ref.get('sim_orig')}")
        print(f"  - Patched Similarity (Sim_patch): {best_ref.get('sim_patch')}")
        print(f"  - Similarity Delta (+Gain): {best_ref.get('delta_sim')}")
        print(f"  - Missing Guard: {best_ref.get('guard_type')}")
        print(f"  - Remediation Check: {best_ref.get('guard_code')}")

    # Test samples endpoint
    with urllib.request.urlopen("http://localhost:8000/api/samples") as res:
        samples = json.loads(res.read().decode("utf-8"))
        print(f"\nSamples API verified: {len(samples)} samples available.")

    # Test audit-db endpoint
    with urllib.request.urlopen("http://localhost:8000/api/audit-db") as res:
        refs = json.loads(res.read().decode("utf-8"))
        print(f"Audit-DB API verified: {len(refs)} reference entries available.")

    # Test history endpoint
    with urllib.request.urlopen("http://localhost:8000/api/history") as res:
        hist = json.loads(res.read().decode("utf-8"))
        print(f"History API verified: {len(hist)} scans logged.")

if __name__ == "__main__":
    test_api()
