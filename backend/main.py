import os
import sys
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from extractor import SolidityExtractor, match_candidate_functions
from graph_builder import ACFGBuilder
from similarity_engine import ASTROSimilarityEngine
import storage

app = FastAPI(
    title="ASTRO: Smart Contract Access Control Auditor API",
    description="Vulnerability detection in smart contracts via ACFG graph similarity comparison",
    version="1.1.0"
)

# Enable CORS for frontend (supports Vercel, Render, and local development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "https://astro-scac.vercel.app",
        "http://localhost:5173",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    source_code: str
    contract_name: Optional[str] = None
    filename: Optional[str] = "Contract.sol"


class AuditDBEntry(BaseModel):
    contract_name: str
    function_name: str
    signature: str
    category: Optional[str] = "audited_safe"  # "audited_safe" or "known_vulnerable"
    parameters: Optional[List[str]] = []
    visibility: Optional[str] = "public"
    is_state_mutating: Optional[bool] = True
    guard_type: Optional[str] = "onlyOwner"
    guard_code: Optional[str] = ""
    vulnerability_type: Optional[str] = ""
    severity: Optional[str] = "Critical"
    description: Optional[str] = ""
    source_code: Optional[str] = ""
    acfg: Optional[Dict[str, Any]] = None


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ASTRO Smart Contract Auditor API",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/api/samples")
def list_samples():
    return storage.get_samples()


@app.get("/api/samples/{sample_id}")
def get_sample(sample_id: str):
    sample = storage.get_sample_by_id(sample_id)
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    return sample


@app.get("/api/audit-db")
def list_audit_db():
    return storage.get_reference_contracts()


@app.post("/api/audit-db")
def create_audit_db_entry(entry: AuditDBEntry):
    entry_dict = entry.model_dump()
    if not entry_dict.get("acfg") and entry_dict.get("source_code"):
        try:
            extractor = SolidityExtractor(entry_dict["source_code"])
            builder = ACFGBuilder(extractor.modifiers)
            for fn in extractor.candidate_functions:
                if fn.name == entry_dict["function_name"]:
                    entry_dict["acfg"] = builder.build_acfg(fn)
                    break
        except Exception as e:
            print(f"Failed to auto-generate ACFG for reference: {e}")

    saved = storage.add_reference_contract(entry_dict)
    return {"status": "success", "entry": saved}


@app.get("/api/history")
def list_history():
    return storage.get_history()


@app.post("/api/analyze")
def analyze_contract(req: AnalyzeRequest):
    source_code = req.source_code.strip()
    if not source_code:
        raise HTTPException(status_code=400, detail="Solidity source code cannot be empty.")

    try:
        # 1. Parse Solidity & extract structural AST metadata
        extractor = SolidityExtractor(source_code)
        candidates = extractor.candidate_functions

        if not candidates:
            return {
                "scan_id": f"scan-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "filename": req.filename,
                "executive_summary": {
                    "verdict": "SAFE",
                    "overall_risk_score": 0,
                    "overall_severity": "None",
                    "total_functions_analyzed": 0,
                    "vulnerable_functions_count": 0,
                    "safe_functions_count": 0,
                    "message": "No externally callable state-modifying functions detected in the provided contract."
                },
                "contract_relationships": {},
                "function_results": [],
                "contracts_detected": list(extractor.contracts.keys())
            }

        # 2. Retrieve audited reference database (both safe templates and known vulnerable patterns)
        reference_db = storage.get_reference_contracts()
        safe_refs_all = [r for r in reference_db if r.get("category", "audited_safe") == "audited_safe"]
        vuln_refs_all = [r for r in reference_db if r.get("category") == "known_vulnerable"]

        # 3. Build ACFGs, map relationships, and run dual reference comparisons
        builder = ACFGBuilder(extractor.modifiers)
        function_results = []
        vuln_count = 0
        safe_count = 0
        max_risk_score = 0
        overall_severity = "None"

        # Contract structure summary (functions, modifiers, state variables, relationships)
        contract_structures = {
            c_name: extractor.get_contract_summary(c_name)
            for c_name in extractor.contracts.keys()
        }

        # Match candidates against reference DB
        matched_pairs = match_candidate_functions(candidates, reference_db)

        for cand_fn, matched_refs in matched_pairs:
            cand_dict = cand_fn.to_dict()
            cand_acfg = builder.build_acfg(cand_fn)

            # Separate matched references by category
            safe_refs_pool = [r for r in matched_refs if r.get("category", "audited_safe") == "audited_safe"] or safe_refs_all
            vuln_refs_pool = [r for r in matched_refs if r.get("category") == "known_vulnerable"] or vuln_refs_all

            # A. Evaluate against audited safe templates
            safe_evaluations = []
            for s_ref in safe_refs_pool:
                eval_res = ASTROSimilarityEngine.evaluate_against_audited_safe(
                    cand_func=cand_dict,
                    cand_acfg=cand_acfg,
                    ref_entry=s_ref
                )
                safe_evaluations.append(eval_res)

            verdict, vote_sum, confidence, best_safe_eval = ASTROSimilarityEngine.aggregate_votes(safe_evaluations)

            # B. Evaluate against known vulnerable exploit patterns
            vuln_evaluations = []
            for v_ref in vuln_refs_pool:
                v_res = ASTROSimilarityEngine.evaluate_against_vulnerable_pattern(
                    cand_func=cand_dict,
                    cand_acfg=cand_acfg,
                    vuln_entry=v_ref
                )
                vuln_evaluations.append(v_res)

            best_vuln_eval = max(vuln_evaluations, key=lambda x: x.get("sim_orig", 0)) if vuln_evaluations else None

            # If direct match with known vulnerable pattern confirms vulnerability
            if best_vuln_eval and best_vuln_eval.get("is_direct_pattern_match") and verdict != "SAFE":
                verdict = "VULNERABLE"
                confidence = max(confidence, best_vuln_eval.get("sim_orig", 0.85))

            # C. Severity Classification & Risk Score
            risk_score, severity = ASTROSimilarityEngine.calculate_risk_score(
                function_name=cand_fn.name,
                verdict=verdict,
                confidence=confidence,
                best_eval=best_safe_eval
            )

            # D. Secure Remediation & Actionable Guidance
            secure_remediation = ASTROSimilarityEngine.generate_remediation(
                function_name=cand_fn.name,
                best_eval=best_safe_eval,
                signature=cand_fn.signature
            )

            # E. Vulnerability Localization
            localization = ASTROSimilarityEngine.localize_vulnerability(cand_dict)

            if verdict == "VULNERABLE":
                vuln_count += 1
            else:
                safe_count += 1

            if risk_score > max_risk_score:
                max_risk_score = risk_score
                overall_severity = severity

            fn_summary = {
                "contract_name": cand_fn.contract_name,
                "function_name": cand_fn.name,
                "signature": cand_fn.signature,
                "visibility": cand_fn.visibility,
                "mutability": cand_fn.mutability,
                "modifiers": cand_fn.modifiers,
                "verdict": verdict,
                "risk_score": risk_score,
                "severity_classification": severity,
                "severity": severity,
                "confidence": confidence,
                "vote_sum": vote_sum,
                "target_has_guard": best_safe_eval["target_has_guard"] if best_safe_eval else False,
                "acfg": cand_acfg,
                "patched_acfg": best_safe_eval.get("patched_acfg") if best_safe_eval else None,
                "pruning_summary": cand_acfg.get("pruning_summary", {}),
                "normalization_summary": cand_acfg.get("normalization_summary", {}),
                "vulnerability_localization": localization,
                "secure_remediation": secure_remediation,
                "remediation": secure_remediation,  # backward compatibility
                "matched_audited_ref": {
                    "ref_id": best_safe_eval.get("ref_id"),
                    "contract_name": best_safe_eval.get("ref_contract"),
                    "function_name": best_safe_eval.get("ref_function"),
                    "guard_type": best_safe_eval.get("ref_guard_type"),
                    "guard_code": best_safe_eval.get("ref_guard_code"),
                    "sim_orig": best_safe_eval.get("sim_orig"),
                    "sim_patch": best_safe_eval.get("sim_patch"),
                    "delta_sim": best_safe_eval.get("delta_sim"),
                    "reason": best_safe_eval.get("reason"),
                    "structural_comparison": best_safe_eval.get("structural_comparison"),
                    "node_mapping": best_safe_eval.get("mapping_orig" if verdict == "SAFE" else "mapping_patch", [])
                } if best_safe_eval else None,
                "matched_vulnerable_pattern": best_vuln_eval,
                "best_reference": {
                    "ref_id": best_safe_eval.get("ref_id"),
                    "contract_name": best_safe_eval.get("ref_contract"),
                    "function_name": best_safe_eval.get("ref_function"),
                    "guard_type": best_safe_eval.get("ref_guard_type"),
                    "guard_code": best_safe_eval.get("ref_guard_code"),
                    "sim_orig": best_safe_eval.get("sim_orig"),
                    "sim_patch": best_safe_eval.get("sim_patch"),
                    "delta_sim": best_safe_eval.get("delta_sim"),
                    "reason": best_safe_eval.get("reason"),
                    "structural_comparison": best_safe_eval.get("structural_comparison"),
                    "node_mapping": best_safe_eval.get("mapping_orig" if verdict == "SAFE" else "mapping_patch", [])
                } if best_safe_eval else None
            }
            function_results.append(fn_summary)

        # 4. Overall Contract Executive Summary
        overall_verdict = "VULNERABLE" if vuln_count > 0 else "SAFE"
        scan_id = f"scan-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        timestamp = datetime.utcnow().isoformat() + "Z"

        scan_record = {
            "id": scan_id,
            "timestamp": timestamp,
            "filename": req.filename or "Contract.sol",
            "executive_summary": {
                "verdict": overall_verdict,
                "overall_risk_score": max_risk_score,
                "overall_severity": overall_severity,
                "total_functions_analyzed": len(candidates),
                "vulnerable_functions_count": vuln_count,
                "safe_functions_count": safe_count,
                "message": (
                    f"ASTRO static analysis detected {vuln_count} vulnerable function(s) with missing access control guards."
                    if vuln_count > 0 else
                    "All analyzed state-modifying functions satisfy access control specifications."
                )
            },
            "contract_structures": contract_structures,
            "function_results": function_results,
            "contracts_detected": list(extractor.contracts.keys()),
            "source_code_snippet": source_code[:500] + ("..." if len(source_code) > 500 else "")
        }

        # 5. Persist to History
        storage.save_history_entry(scan_record)

        return scan_record

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"ASTRO Analysis Pipeline encountered an error: {str(e)}"
        )


@app.post("/api/analyze/upload")
async def analyze_file_upload(file: UploadFile = File(...)):
    content = await file.read()
    try:
        source_code = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Uploaded file must be a UTF-8 text/Solidity file.")
    req = AnalyzeRequest(source_code=source_code, filename=file.filename)
    return analyze_contract(req)


# ==========================================
# Production Static Files & SPA Fallback
# ==========================================
FRONTEND_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")
FRONTEND_ASSETS = os.path.join(FRONTEND_DIST, "assets")

if os.path.exists(FRONTEND_ASSETS):
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS), name="assets")

if os.path.exists(FRONTEND_DIST):
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_file = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend index.html not found")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
