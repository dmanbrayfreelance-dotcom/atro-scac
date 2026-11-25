import numpy as np
from scipy.optimize import linear_sum_assignment
from typing import Dict, Any, List, Tuple, Optional
import re

from graph_builder import ACFGBuilder


class ASTROSimilarityEngine:
    """
    Two-step Bipartite Graph Similarity Engine using the Hungarian Algorithm
    (scipy.optimize.linear_sum_assignment) for detecting missing access control guards.
    """

    ALPHA_THRESHOLD = 0.80

    @classmethod
    def compute_node_similarity(cls, node_t: Dict[str, Any], node_r: Dict[str, Any]) -> float:
        """
        Computes similarity between target node T and reference node R.
        Weights:
        - Node Type Match: 0.35
        - Guard Attribute Match: 0.25
        - State/Sender Flag Match: 0.25
        - Text / Token Overlap: 0.15
        """
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
        """
        Calculates bipartite graph similarity between graph_t and graph_r
        using the Hungarian algorithm (linear_sum_assignment).
        Returns:
            similarity: float in [0.0, 1.0]
            node_mapping: list of matched pairs with individual scores
        """
        nodes_t = graph_t.get("nodes", [])
        nodes_r = graph_r.get("nodes", [])

        if not nodes_t or not nodes_r:
            return 0.0, []

        n_t = len(nodes_t)
        n_r = len(nodes_r)
        dim = max(n_t, n_r)

        # Build cost matrix (dim x dim, padded with 1.0 for dummy nodes)
        cost_matrix = np.ones((dim, dim), dtype=float)
        sim_matrix = np.zeros((dim, dim), dtype=float)

        for i in range(n_t):
            for j in range(n_r):
                sim = cls.compute_node_similarity(nodes_t[i], nodes_r[j])
                sim_matrix[i, j] = sim
                cost_matrix[i, j] = 1.0 - sim

        # Hungarian algorithm optimal assignment
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

        # Normalized similarity
        normalized_sim = total_sim / float(dim)
        return round(float(normalized_sim), 4), node_mapping

    @classmethod
    def evaluate_candidate(
        cls,
        cand_func: Dict[str, Any],
        cand_acfg: Dict[str, Any],
        ref_entry: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Runs Step 1 (sim_orig) and Step 2 (sim_patch) against an audited reference entry.
        Applies the ASTRO decision criteria.
        """
        ref_acfg = ref_entry.get("acfg", {})
        guard_code = ref_entry.get("guard_code", "require(msg.sender == owner);")

        # Check if candidate currently has any access guard
        target_has_guard = any(n.get("is_guard", False) for n in cand_acfg.get("nodes", []))

        # Step 1: sim_orig
        sim_orig, mapping_orig = cls.compute_graph_similarity(cand_acfg, ref_acfg)

        # Step 2: create patched graph & sim_patch
        patched_acfg = ACFGBuilder.patch_graph_with_guard(cand_acfg, guard_code)
        sim_patch, mapping_patch = cls.compute_graph_similarity(patched_acfg, ref_acfg)

        delta_sim = round(sim_patch - sim_orig, 4)

        # ASTRO Decision Logic
        # Case A: Candidate already has guard and matches reference well -> SAFE (-1)
        if target_has_guard and sim_orig >= cls.ALPHA_THRESHOLD:
            vote = -1
            verdict = "SAFE"
            reason = "Function already implements verified access control guard matching audited reference."
        # Case B: Candidate lacks guard, but patched graph matches reference above threshold -> VULNERABLE (+1)
        elif not target_has_guard and (sim_patch >= cls.ALPHA_THRESHOLD or (sim_patch >= 0.70 and delta_sim > 0.15)):
            vote = 1
            verdict = "VULNERABLE"
            reason = f"Function structure matches audited {ref_entry.get('function_name')} but omits required access control check: {ref_entry.get('guard_type', 'guard')}."
        # Case C: Even if target_has_guard is False, check if delta_sim demonstrates significant similarity gain from guard
        elif not target_has_guard and delta_sim >= 0.20:
            vote = 1
            verdict = "VULNERABLE"
            reason = f"High similarity increase (+{round(delta_sim*100, 1)}%) upon inserting access guard indicates omitted protection."
        elif target_has_guard:
            vote = -1
            verdict = "SAFE"
            reason = "Function contains sender authorization guards."
        else:
            vote = 0
            verdict = "INCONCLUSIVE"
            reason = "Control flow does not match reference pattern closely enough to determine missing guard."

        return {
            "ref_id": ref_entry.get("id"),
            "ref_contract": ref_entry.get("contract_name"),
            "ref_function": ref_entry.get("function_name"),
            "ref_guard_type": ref_entry.get("guard_type"),
            "ref_guard_code": ref_entry.get("guard_code"),
            "sim_orig": sim_orig,
            "sim_patch": sim_patch,
            "delta_sim": delta_sim,
            "vote": vote,
            "verdict": verdict,
            "reason": reason,
            "target_has_guard": target_has_guard,
            "mapping_orig": mapping_orig,
            "mapping_patch": mapping_patch,
            "patched_acfg": patched_acfg
        }

    @classmethod
    def aggregate_votes(
        cls,
        evaluations: List[Dict[str, Any]]
    ) -> Tuple[str, int, float, Optional[Dict[str, Any]]]:
        """
        Aggregates votes across multiple reference entries.
        Rule: Drop lowest score when non-zero count is even to avoid ties.
        Returns: (final_verdict, aggregated_vote_sum, confidence, best_ref_eval)
        """
        if not evaluations:
            return "UNKNOWN", 0, 0.0, None

        # Filter non-zero votes
        non_zero_evals = [e for e in evaluations if e["vote"] != 0]

        # If count of non-zero votes is even, drop the one with lowest confidence (smallest max(sim_orig, sim_patch))
        if len(non_zero_evals) > 1 and len(non_zero_evals) % 2 == 0:
            non_zero_evals.sort(key=lambda x: max(x["sim_orig"], x["sim_patch"]))
            non_zero_evals.pop(0)

        vote_sum = sum(e["vote"] for e in non_zero_evals)

        # Best evaluation
        best_eval = max(evaluations, key=lambda x: max(x["sim_orig"], x["sim_patch"]))
        confidence = max(best_eval["sim_orig"], best_eval["sim_patch"])

        if vote_sum > 0:
            final_verdict = "VULNERABLE"
        elif vote_sum < 0:
            final_verdict = "SAFE"
        else:
            final_verdict = "SAFE" if best_eval["target_has_guard"] else "LOW_CONFIDENCE"

        return final_verdict, vote_sum, round(confidence, 3), best_eval

    @classmethod
    def calculate_risk_score(
        cls,
        function_name: str,
        verdict: str,
        confidence: float,
        best_eval: Optional[Dict[str, Any]]
    ) -> Tuple[int, str]:
        """
        Calculates executive risk score (0-100) and severity level based on verdict,
        function sensitivity, and missing guard type.
        """
        if verdict != "VULNERABLE":
            return (0, "Informational") if verdict == "SAFE" else (15, "Low")

        fn_lower = function_name.lower()

        # Sensitivity tiers
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

        # Confidence modifier
        score = int(min(100, max(60, base_score * (0.8 + 0.2 * confidence))))
        return score, severity

    @classmethod
    def generate_remediation(
        cls,
        function_name: str,
        best_eval: Optional[Dict[str, Any]],
        signature: str
    ) -> Dict[str, str]:
        """
        Produces detailed remediation explanation and recommended Solidity code patch.
        """
        guard_type = best_eval.get("ref_guard_type", "onlyOwner") if best_eval else "onlyOwner"
        ref_guard_code = best_eval.get("ref_guard_code", "require(msg.sender == owner);") if best_eval else "require(msg.sender == owner);"

        explanation = (
            f"The function `{function_name}` is externally callable and modifies sensitive contract state, "
            f"but lacks authorization checks. In the audited reference contract (`{best_eval.get('ref_contract', 'OpenZeppelin')}`), "
            f"this execution path is safeguarded by an access control guard (`{guard_type}`). "
            f"Without this guard, any arbitrary address on the blockchain can invoke this function."
        )

        patch_code = (
            f"// Recommended Remediation Patch:\n"
            f"// Option 1: Add access control modifier\n"
            f"function {signature} public {guard_type} {{\n"
            f"    // ... existing implementation ...\n"
            f"}}\n\n"
            f"// Option 2: Add inline validation at function entry\n"
            f"{ref_guard_code}\n"
        )

        return {
            "explanation": explanation,
            "patch_code": patch_code,
            "recommended_guard": guard_type
        }
