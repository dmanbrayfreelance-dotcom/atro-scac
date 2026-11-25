import numpy as np
from scipy.optimize import linear_sum_assignment
from typing import Dict, Any, List, Tuple, Optional
import re

from graph_builder import ACFGBuilder


class ASTROSimilarityEngine:
    """
    Two-step Bipartite Graph Similarity Engine using the Hungarian Algorithm
    (scipy.optimize.linear_sum_assignment) for detecting missing access control guards.
    Evaluates candidates against both audited secure reference templates and known vulnerable patterns.
    """

    ALPHA_THRESHOLD = 0.80

    @classmethod
    def compute_node_similarity(cls, node_t: Dict[str, Any], node_r: Dict[str, Any]) -> float:
        score = 0.0

        # 1. Type Match (0.35)
        type_t = node_t.get("type", "")
        type_r = node_r.get("type", "")
        if type_t == type_r:
            score += 0.35
        elif {type_t, type_r} <= {"EXPR", "STATE_ASSIGN", "CALL_EXTERNAL"}:
            score += 0.20
        elif {type_t, type_r} <= {"IF", "REQUIRE"}:
            score += 0.25

        # 2. Guard Flag Match (0.25)
        guard_t = node_t.get("is_guard", False)
        guard_r = node_r.get("is_guard", False)
        if guard_t == guard_r:
            score += 0.25

        # 3. Flags: reads_sender and modifies_state (0.25)
        flags_score = 0.0
        if node_t.get("reads_sender", False) == node_r.get("reads_sender", False):
            flags_score += 0.125
        if node_t.get("modifies_state", False) == node_r.get("modifies_state", False):
            flags_score += 0.125
        score += flags_score

        # 4. Token Overlap in code (0.15)
        tokens_t = set(re.findall(r'[a-zA-Z0-9_]+', node_t.get("code", "").lower()))
        tokens_r = set(re.findall(r'[a-zA-Z0-9_]+', node_r.get("code", "").lower()))
        if tokens_t and tokens_r:
            jaccard = len(tokens_t & tokens_r) / len(tokens_t | tokens_r)
            score += 0.15 * jaccard
        else:
            score += 0.05

        return min(max(score, 0.0), 1.0)

    @classmethod
    def compute_graph_similarity(
        cls,
        graph_t: Dict[str, Any],
        graph_r: Dict[str, Any]
    ) -> Tuple[float, List[Dict[str, Any]]]:
        nodes_t = graph_t.get("nodes", [])
        nodes_r = graph_r.get("nodes", [])

        if not nodes_t or not nodes_r:
            return 0.0, []

        n_t = len(nodes_t)
        n_r = len(nodes_r)
        dim = max(n_t, n_r)

        cost_matrix = np.ones((dim, dim), dtype=float)
        sim_matrix = np.zeros((dim, dim), dtype=float)

        for i in range(n_t):
            for j in range(n_r):
                sim = cls.compute_node_similarity(nodes_t[i], nodes_r[j])
                sim_matrix[i, j] = sim
                cost_matrix[i, j] = 1.0 - sim

        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        total_sim = 0.0
        node_mapping = []

        for r, c in zip(row_ind, col_ind):
            if r < n_t and c < n_r:
                sim = float(sim_matrix[r, c])
                total_sim += sim
                node_mapping.append({
                    "target_node_id": nodes_t[r].get("id"),
                    "target_code": nodes_t[r].get("code"),
                    "reference_node_id": nodes_r[c].get("id"),
                    "reference_code": nodes_r[c].get("code"),
                    "similarity": round(sim, 3)
                })
            elif r < n_t:
                node_mapping.append({
                    "target_node_id": nodes_t[r].get("id"),
                    "target_code": nodes_t[r].get("code"),
                    "reference_node_id": None,
                    "reference_code": "UNMATCHED",
                    "similarity": 0.0
                })
            elif c < n_r:
                node_mapping.append({
                    "target_node_id": None,
                    "target_code": "UNMATCHED",
                    "reference_node_id": nodes_r[c].get("id"),
                    "reference_code": nodes_r[c].get("code"),
                    "similarity": 0.0
                })

        normalized_sim = total_sim / float(dim)
        return round(float(normalized_sim), 4), node_mapping

    @classmethod
    def evaluate_against_audited_safe(
        cls,
        cand_func: Dict[str, Any],
        cand_acfg: Dict[str, Any],
        ref_entry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Step 1 (sim_orig) and Step 2 (sim_patch) against audited safe template.
        """
        ref_acfg = ref_entry.get("acfg", {})
        guard_code = ref_entry.get("guard_code", "require(msg.sender == owner);")
        guard_type = ref_entry.get("guard_type", "onlyOwner")

        target_has_guard = any(n.get("is_guard", False) for n in cand_acfg.get("nodes", []))

        # Step 1: sim_orig
        sim_orig, mapping_orig = cls.compute_graph_similarity(cand_acfg, ref_acfg)

        # Step 2: create patched graph & sim_patch
        patched_acfg = ACFGBuilder.patch_graph_with_guard(cand_acfg, guard_code)
        sim_patch, mapping_patch = cls.compute_graph_similarity(patched_acfg, ref_acfg)

        delta_sim = round(sim_patch - sim_orig, 4)

        if target_has_guard and sim_orig >= cls.ALPHA_THRESHOLD:
            vote = -1
            verdict = "SAFE"
            reason = f"Function implements verified `{guard_type}` access control matching audited reference `{ref_entry.get('contract_name')}`."
        elif not target_has_guard and (sim_patch >= cls.ALPHA_THRESHOLD or (sim_patch >= 0.70 and delta_sim > 0.15)):
            vote = 1
            verdict = "VULNERABLE"
            reason = f"Control flow matches audited `{ref_entry.get('function_name')}` but lacks required `{guard_type}` guard."
        elif not target_has_guard and delta_sim >= 0.20:
            vote = 1
            verdict = "VULNERABLE"
            reason = f"Candidate graph achieves {int(sim_patch*100)}% structural isomorphism upon inserting `{guard_type}` guard (+{round(delta_sim*100, 1)}% gain)."
        elif target_has_guard:
            vote = -1
            verdict = "SAFE"
            reason = "Function contains caller authorization guard."
        else:
            vote = 0
            verdict = "INCONCLUSIVE"
            reason = "Topology does not match audited template closely enough."

        structural_comparison = (
            f"Candidate graph matches audited template at {int(sim_orig*100)}% original similarity. "
            f"Upon candidate IFNG guard insertion, structural isomorphism reaches {int(sim_patch*100)}% "
            f"(+{int(delta_sim*100)}% gain), proving omitted access protection."
            if not target_has_guard else
            f"Candidate graph matches audited template with verified {guard_type} guard (similarity {int(sim_orig*100)}%)."
        )

        return {
            "ref_id": ref_entry.get("id"),
            "category": "audited_safe",
            "ref_contract": ref_entry.get("contract_name"),
            "ref_function": ref_entry.get("function_name"),
            "ref_guard_type": guard_type,
            "ref_guard_code": guard_code,
            "sim_orig": sim_orig,
            "sim_patch": sim_patch,
            "delta_sim": delta_sim,
            "vote": vote,
            "verdict": verdict,
            "reason": reason,
            "structural_comparison": structural_comparison,
            "target_has_guard": target_has_guard,
            "mapping_orig": mapping_orig,
            "mapping_patch": mapping_patch,
            "patched_acfg": patched_acfg
        }

    @classmethod
    def evaluate_against_vulnerable_pattern(
        cls,
        cand_func: Dict[str, Any],
        cand_acfg: Dict[str, Any],
        vuln_entry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Direct graph matching against a known documented exploit pattern.
        """
        vuln_acfg = vuln_entry.get("acfg", {})
        sim_orig, mapping = cls.compute_graph_similarity(cand_acfg, vuln_acfg)
        target_has_guard = any(n.get("is_guard", False) for n in cand_acfg.get("nodes", []))

        is_direct_match = (sim_orig >= 0.70) and not target_has_guard

        comparison_notes = (
            f"Strong topological alignment ({int(sim_orig*100)}% similarity) with known exploit pattern: "
            f"'{vuln_entry.get('vulnerability_type', 'Missing Access Control')}'. "
            f"Both lack caller authentication on state-mutating execution path."
            if is_direct_match else
            f"Comparison with known exploit pattern '{vuln_entry.get('vulnerability_type')}' showed {int(sim_orig*100)}% similarity."
        )

        return {
            "ref_id": vuln_entry.get("id"),
            "category": "known_vulnerable",
            "contract_name": vuln_entry.get("contract_name"),
            "function_name": vuln_entry.get("function_name"),
            "vulnerability_type": vuln_entry.get("vulnerability_type", "Missing Access Control"),
            "severity": vuln_entry.get("severity", "Critical"),
            "sim_orig": sim_orig,
            "is_direct_pattern_match": is_direct_match,
            "comparison_notes": comparison_notes,
            "node_mapping": mapping
        }

    @classmethod
    def aggregate_votes(
        cls,
        evaluations: List[Dict[str, Any]]
    ) -> Tuple[str, int, float, Optional[Dict[str, Any]]]:
        if not evaluations:
            return "UNKNOWN", 0, 0.0, None

        non_zero_evals = [e for e in evaluations if e.get("vote", 0) != 0]

        if len(non_zero_evals) > 1 and len(non_zero_evals) % 2 == 0:
            non_zero_evals.sort(key=lambda x: max(x.get("sim_orig", 0), x.get("sim_patch", 0)))
            non_zero_evals.pop(0)

        vote_sum = sum(e.get("vote", 0) for e in non_zero_evals)
        best_eval = max(evaluations, key=lambda x: max(x.get("sim_orig", 0), x.get("sim_patch", 0)))
        confidence = max(best_eval.get("sim_orig", 0), best_eval.get("sim_patch", 0))

        if vote_sum > 0:
            final_verdict = "VULNERABLE"
        elif vote_sum < 0:
            final_verdict = "SAFE"
        else:
            final_verdict = "SAFE" if best_eval.get("target_has_guard", False) else "LOW_CONFIDENCE"

        return final_verdict, vote_sum, round(confidence, 3), best_eval

    @classmethod
    def calculate_risk_score(
        cls,
        function_name: str,
        verdict: str,
        confidence: float,
        best_eval: Optional[Dict[str, Any]]
    ) -> Tuple[int, str]:
        if verdict != "VULNERABLE":
            return (0, "None") if verdict == "SAFE" else (15, "Low")

        fn_lower = function_name.lower()

        if any(k in fn_lower for k in ("ownership", "owner", "admin")):
            base_score = 95
            severity = "Critical"
        elif any(k in fn_lower for k in ("withdraw", "drain", "rescue", "transferany")):
            base_score = 92
            severity = "Critical"
        elif any(k in fn_lower for k in ("mint", "burn", "tokens")):
            base_score = 88
            severity = "High"
        elif any(k in fn_lower for k in ("fee", "pause", "role")):
            base_score = 80
            severity = "High"
        else:
            base_score = 75
            severity = "Medium"

        score = int(min(100, max(60, base_score * (0.8 + 0.2 * confidence))))
        return score, severity

    @classmethod
    def generate_remediation(
        cls,
        function_name: str,
        best_eval: Optional[Dict[str, Any]],
        signature: str
    ) -> Dict[str, Any]:
        guard_type = best_eval.get("ref_guard_type", "onlyOwner") if best_eval else "onlyOwner"
        ref_guard_code = best_eval.get("ref_guard_code", "require(msg.sender == owner);") if best_eval else "require(msg.sender == owner);"

        explanation = (
            f"The function `{function_name}` is publicly callable and mutates sensitive state, "
            f"but lacks caller authorization. In the audited reference template (`{best_eval.get('ref_contract', 'OpenZeppelin')}`), "
            f"this execution path is safeguarded by the `{guard_type}` access control guard. "
            f"Without this check, any unauthenticated external caller can invoke this privileged routine."
        )

        patch_code = (
            f"// Recommended Security Remediation Patch:\n"
            f"// Option 1: Attach standard access control modifier\n"
            f"function {signature} public {guard_type} {{\n"
            f"    // ... existing function implementation ...\n"
            f"}}\n\n"
            f"// Option 2: Add inline caller authentication check\n"
            f"{ref_guard_code}\n"
        )

        actionable_steps = [
            f"Step 1: Import and inherit verified OpenZeppelin Ownable or AccessControl contracts.",
            f"Step 2: Add `{guard_type}` modifier or inline `{ref_guard_code}` at the very beginning of `{function_name}`.",
            f"Step 3: Verify all parameter zero-address validations precede state variable writes."
        ]

        return {
            "explanation": explanation,
            "patch_code": patch_code,
            "recommended_guard": guard_type,
            "actionable_steps": actionable_steps
        }

    @classmethod
    def localize_vulnerability(
        cls,
        cand_func: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {
            "contract_name": cand_func.get("contract_name", "Contract"),
            "function_name": cand_func.get("name", "function"),
            "signature": cand_func.get("signature", ""),
            "start_line": cand_func.get("start_line", 1),
            "end_line": cand_func.get("end_line", 1),
            "missing_guard_location": "Function Entry Block (before state mutation)",
            "state_writes": cand_func.get("state_writes", []),
            "external_calls": cand_func.get("external_calls", [])
        }
