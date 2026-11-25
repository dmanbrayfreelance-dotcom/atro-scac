import urllib.request
import json
import os
import sys

def test_api():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. Health Endpoint
    print("1. Testing /api/health...")
    with urllib.request.urlopen("http://127.0.0.1:8000/api/health") as res:
        assert res.status == 200
        health_data = json.loads(res.read().decode("utf-8"))
        print("   ✓ Health check passed:", health_data)

    # 2. Samples Endpoint
    print("\n2. Testing /api/samples...")
    with urllib.request.urlopen("http://127.0.0.1:8000/api/samples") as res:
        assert res.status == 200
        samples = json.loads(res.read().decode("utf-8"))
        print(f"   ✓ Samples verified: {len(samples)} samples available.")
        assert len(samples) >= 5

    # 3. Audit-DB Endpoint
    print("\n3. Testing /api/audit-db...")
    with urllib.request.urlopen("http://127.0.0.1:8000/api/audit-db") as res:
        assert res.status == 200
        refs = json.loads(res.read().decode("utf-8"))
        categories = {r.get("category", "audited_safe") for r in refs}
        print(f"   ✓ Audit-DB verified: {len(refs)} reference entries available across categories: {categories}")
        assert "audited_safe" in categories
        assert "known_vulnerable" in categories

    # 4. Analyze Endpoint
    print("\n4. Testing /api/analyze on vuln_roi_transfer_ownership.sol...")
    sample_path = os.path.join(base_dir, "data", "samples", "vuln_roi_transfer_ownership.sol")
    with open(sample_path, "r", encoding="utf-8") as f:
        code = f.read()

    payload = {
        "source_code": code,
        "filename": "vuln_roi_transfer_ownership.sol"
    }

    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/analyze",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req) as response:
        assert response.status == 200, f"Expected status 200, got {response.status}"
        data = json.loads(response.read().decode("utf-8"))

    print("=== ASTRO API End-to-End Analysis Results ===")
    print("Contract Filename:", data.get("filename"))
    print("Executive Verdict:", data["executive_summary"]["verdict"])
    print("Executive Risk Score:", data["executive_summary"]["overall_risk_score"])
    print("Overall Severity:", data["executive_summary"].get("overall_severity"))
    print("Vulnerable Functions:", data["executive_summary"]["vulnerable_functions_count"])
    print("Safe Functions:", data["executive_summary"]["safe_functions_count"])

    # Verify contract structures
    assert "contract_structures" in data, "Missing contract_structures in response"
    structs = data["contract_structures"]
    print("Contract structures extracted:", list(structs.keys()))

    for fn in data.get("function_results", []):
        audited_ref = fn.get("matched_audited_ref", {})
        vuln_pattern = fn.get("matched_vulnerable_pattern", {})
        print(f"\nFunction: {fn['signature']}")
        print(f"  - Verdict: {fn['verdict']}")
        print(f"  - Severity: {fn['severity_classification']} (Score: {fn['risk_score']})")
        print(f"  - Vulnerability Localization: {fn.get('vulnerability_localization')}")
        print(f"  - Pruning Summary: {fn.get('pruning_summary')}")
        print(f"  - Normalization Summary: {fn.get('normalization_summary')}")
        if audited_ref:
            print(f"  - Audited Safe Ref: {audited_ref.get('function_name')} (Sim_orig: {audited_ref.get('sim_orig')}, Sim_patch: {audited_ref.get('sim_patch')}, Gain: {audited_ref.get('delta_sim')})")
        if vuln_pattern:
            print(f"  - Matched Known Exploit Pattern: {vuln_pattern.get('exploit_name')} (Sim: {vuln_pattern.get('sim_orig')})")
        print(f"  - Actionable Remediation: {fn.get('secure_remediation', {}).get('recommended_guard')}")

        if fn['function_name'] == 'transferOwnership':
            assert fn['verdict'] == 'VULNERABLE'
            assert fn['severity_classification'] in ['Critical', 'High']
            assert fn.get('vulnerability_localization') is not None
            assert fn.get('secure_remediation') is not None

    # 5. History Endpoint
    print("\n5. Testing /api/history...")
    with urllib.request.urlopen("http://127.0.0.1:8000/api/history") as res:
        assert res.status == 200
        hist = json.loads(res.read().decode("utf-8"))
        print(f"   ✓ History verified: {len(hist)} scans logged.")
        assert len(hist) > 0

    # 6. SPA Routing Fallback
    print("\n6. Testing SPA Fallback for non-API route...")
    with urllib.request.urlopen("http://127.0.0.1:8000/scanner") as res:
        assert res.status == 200
        content_type = res.headers.get("Content-Type", "")
        print(f"   ✓ SPA Fallback verified: /scanner returned index.html ({content_type})")
        assert "text/html" in content_type

    print("\n=======================================================")
    print("🎉 ALL ASTRO E2E AUDIT & API TESTS PASSED WITH 100% SUCCESS!")
    print("=======================================================")

if __name__ == "__main__":
    test_api()
