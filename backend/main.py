import os
import sys
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from extractor import SolidityExtractor, match_candidate_functions
from graph_builder import ACFGBuilder
from similarity_engine import ASTROSimilarityEngine
import storage

app = FastAPI(
    title="ASTRO: Smart Contract Access Control Auditor API",
    description="Vulnerability detection in smart contracts via ACFG graph similarity comparison",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    parameters: Optional[List[str]] = []
    visibility: Optional[str] = "public"
    is_state_mutating: Optional[bool] = True
    guard_type: str
    guard_code: str
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
    # If no precomputed ACFG is provided, attempt to build one from source_code
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
        # 1. Parse Solidity & extract candidate functions
        extractor = SolidityExtractor(source_code)
        candidates = extractor.candidate_functions

        if not candidates:
            # Fallback check: if no functions were filtered as externally callable state modifying,
            # inspect if any functions exist at all
            all_fns = []
            for c_name, c_info in extractor.contracts.items():
                pass
            return {
                "scan_id": f"scan-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "filename": req.filename,
                "executive_summary": {
                    "verdict": "SAFE",
                    "overall_risk_score": 0,
                    "overall_severity": "Informational",
                    "total_functions_analyzed": 0,
                    "vulnerable_functions_count": 0,
                    "safe_functions_count": 0,
                    "message": "No externally callable state-modifying functions detected in the provided contract."
                },
                "function_results": [],
                "contracts_detected": list(extractor.contracts.keys())
            }

        # 2. Retrieve audited reference database
        reference_db = storage.get_reference_contracts()

        # 3. Build ACFGs and run ASTRO graph similarity pipeline
        builder = ACFGBuilder(extractor.modifiers)
        function_results = []
        vuln_count = 0
        safe_count = 0
        max_risk_score = 0
        overall_severity = "Informational"

        # Match candidate functions against DB
        matched_pairs = match_candidate_functions(candidates, reference_db)

        for cand_fn, matched_refs in matched_pairs:
            cand_dict = cand_fn.to_dict()
            # Build target ACFG
            cand_acfg = builder.build_acfg(cand_fn)

            # If no direct match in reference DB, fall back to comparing against all DB functions
            # to detect similar access control sensitive operations
            refs_to_compare = matched_refs if matched_refs else reference_db

            evaluations = []
            for ref in refs_to_compare:
                eval_res = ASTROSimilarityEngine.evaluate_candidate(
                    cand_func=cand_dict,
                    cand_acfg=cand_acfg,
                    ref_entry=ref
                )
                evaluations.append(eval_res)

            # Vote aggregation across reference entries
            verdict, vote_sum, confidence, best_eval = ASTROSimilarityEngine.aggregate_votes(evaluations)
            risk_score, severity = ASTROSimilarityEngine.calculate_risk_score(
                function_name=cand_fn.name,
                verdict=verdict,
                confidence=confidence,
                best_eval=best_eval
            )
            remediation = ASTROSimilarityEngine.generate_remediation(
                function_name=cand_fn.name,
                best_eval=best_eval,
                signature=cand_fn.signature
            )

            if verdict == "VULNERABLE":
                vuln_count += 1
            else:
                safe_count += 1

            if risk_score > max_risk_score:
                max_risk_score = risk_score
                overall_severity = severity

            # Format result for this function
            fn_summary = {
                "contract_name": cand_fn.contract_name,
                "function_name": cand_fn.name,
                "signature": cand_fn.signature,
                "visibility": cand_fn.visibility,
                "mutability": cand_fn.mutability,
                "modifiers": cand_fn.modifiers,
                "verdict": verdict,
                "risk_score": risk_score,
                "severity": severity,
                "confidence": confidence,
                "vote_sum": vote_sum,
                "target_has_guard": best_eval["target_has_guard"] if best_eval else False,
                "acfg": cand_acfg,
                "patched_acfg": best_eval.get("patched_acfg") if best_eval else None,
                "best_reference": {
                    "ref_id": best_eval.get("ref_id"),
                    "contract_name": best_eval.get("ref_contract"),
                    "function_name": best_eval.get("ref_function"),
                    "guard_type": best_eval.get("ref_guard_type"),
                    "guard_code": best_eval.get("ref_guard_code"),
                    "sim_orig": best_eval.get("sim_orig"),
                    "sim_patch": best_eval.get("sim_patch"),
                    "delta_sim": best_eval.get("delta_sim"),
                    "reason": best_eval.get("reason"),
                    "node_mapping": best_eval.get("mapping_orig" if verdict == "SAFE" else "mapping_patch", [])
                } if best_eval else None,
                "all_evaluations": [
                    {
                        "ref_contract": e["ref_contract"],
                        "ref_function": e["ref_function"],
                        "sim_orig": e["sim_orig"],
                        "sim_patch": e["sim_patch"],
                        "delta_sim": e["delta_sim"],
                        "vote": e["vote"],
                        "verdict": e["verdict"]
                    }
                    for e in evaluations[:5]  # top 5
                ],
                "remediation": remediation
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
