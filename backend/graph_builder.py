import networkx as nx
from typing import List, Dict, Any, Tuple, Optional
from collections import deque
import re

from extractor import FunctionDef, Statement


class ACFGNode:
    def __init__(self, node_id: int, node_type: str, code: str,
                 is_guard: bool = False, reads_sender: bool = False,
                 modifies_state: bool = False):
        self.id = node_id
        self.type = node_type  # 'ENTRY', 'IF', 'REVERT', 'ENDIF', 'STATE_ASSIGN', 'CALL_EXTERNAL', 'RETURN', 'EXPR'
        self.code = code
        self.is_guard = is_guard
        self.reads_sender = reads_sender
        self.modifies_state = modifies_state

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "code": self.code,
            "is_guard": self.is_guard,
            "reads_sender": self.reads_sender,
            "modifies_state": self.modifies_state
        }


class ACFGBuilder:
    """
    Builds Attribute Control Flow Graphs (ACFG) for Solidity functions.
    Handles modifier inlining, If-Form Node Group (IFNG) normalization,
    pruning of non-access-control noise (emits/logs) with edge reconnection,
    and sequential BFS re-indexing.
    """

    def __init__(self, modifiers_db: Dict[str, Dict[str, Any]] = None):
        self.modifiers_db = modifiers_db or {}

    def build_acfg(self, func: FunctionDef) -> Dict[str, Any]:
        """
        Constructs the ACFG for a given function definition.
        """
        G = nx.DiGraph()
        node_counter = 0

        # 1. Create ENTRY node
        entry_node = ACFGNode(
            node_id=node_counter,
            node_type="ENTRY",
            code=f"ENTRY {func.signature}",
            is_guard=False,
            reads_sender=False,
            modifies_state=False
        )
        G.add_node(entry_node.id, data=entry_node)
        node_counter += 1
        current_tail = entry_node.id

        # 2. Inline modifiers
        inlined_statements = self._inline_modifiers(func)

        # 3. Process statements into CFG with IFNG normalization
        for stmt in inlined_statements:
            current_tail, node_counter = self._add_statement_to_graph(
                G, stmt, current_tail, node_counter
            )

        # 4. Add final RETURN node if not terminated
        return_node = ACFGNode(
            node_id=node_counter,
            node_type="RETURN",
            code="RETURN",
            is_guard=False,
            reads_sender=False,
            modifies_state=False
        )
        G.add_node(return_node.id, data=return_node)
        G.add_edge(current_tail, return_node.id)
        node_counter += 1

        # 5. Apply ASTRO Pruning Rules (remove emits & noise, reconnect control edges cleanly)
        G = self._apply_pruning_rules(G)

        # 6. Sequential BFS reordering
        return self._reorder_graph_bfs(G, root_id=0)

    def _inline_modifiers(self, func: FunctionDef) -> List[Statement]:
        """
        Inlines modifier checks into the function statement list,
        replacing the `_` placeholder with the actual function statements.
        """
        pre_statements = []
        post_statements = []

        for mod_call in func.modifiers:
            # Extract modifier name and arguments
            mod_match = re.match(r'([a-zA-Z0-9_]+)(?:\((.*?)\))?', mod_call.strip())
            if not mod_match:
                continue
            mod_name = mod_match.group(1)
            mod_args_raw = mod_match.group(2) or ""

            # Check if defined in contract
            if mod_name in self.modifiers_db:
                mod_def = self.modifiers_db[mod_name]
                mod_body = mod_def.get("body", "")
                mod_stmts = self._extract_modifier_stmts(mod_body, mod_name, mod_args_raw)
                pre_statements.extend(mod_stmts)
            else:
                # Standard well-known modifiers
                if mod_name == "onlyOwner":
                    pre_statements.append(Statement(
                        "require(msg.sender == owner, \"Ownable: caller is not the owner\")",
                        "REQUIRE",
                        {
                            "condition": "msg.sender == owner",
                            "error": "\"Ownable: caller is not the owner\"",
                            "is_guard": True
                        }
                    ))
                elif mod_name == "onlyRole":
                    role_arg = mod_args_raw.strip() if mod_args_raw else "DEFAULT_ADMIN_ROLE"
                    pre_statements.append(Statement(
                        f"require(hasRole({role_arg}, msg.sender), \"AccessControl: unauthorized\")",
                        "REQUIRE",
                        {
                            "condition": f"hasRole({role_arg}, msg.sender)",
                            "error": "\"AccessControl: unauthorized\"",
                            "is_guard": True
                        }
                    ))
                elif mod_name == "whenNotPaused":
                    pre_statements.append(Statement(
                        "require(!paused, \"Pausable: paused\")",
                        "REQUIRE",
                        {
                            "condition": "!paused",
                            "error": "\"Pausable: paused\"",
                            "is_guard": False
                        }
                    ))
                elif "auth" in mod_name.lower():
                    pre_statements.append(Statement(
                        "require(msg.sender == owner, \"UNAUTHORIZED\")",
                        "REQUIRE",
                        {
                            "condition": "msg.sender == owner",
                            "error": "\"UNAUTHORIZED\"",
                            "is_guard": True
                        }
                    ))

        return pre_statements + func.statements + post_statements

    def _extract_modifier_stmts(self, body: str, mod_name: str, args_raw: str) -> List[Statement]:
        stmts = []
        clean = re.sub(r'/\*.*?\*/', '', body, flags=re.DOTALL)
        clean = re.sub(r'//.*', '', clean)
        raw_lines = [l.strip() for l in clean.split(";") if l.strip() and l.strip() != "_"]
        for line in raw_lines:
            if "require" in line:
                m = re.search(r'require\s*\((.*?)\)', line)
                cond = m.group(1) if m else line
                is_guard = any(k in cond.lower() for k in ("msg.sender", "owner", "admin", "hasrole", "role"))
                stmts.append(Statement(line, "REQUIRE", {
                    "condition": cond,
                    "error": "revert",
                    "is_guard": is_guard
                }))
        return stmts

    def _add_statement_to_graph(self, G: nx.DiGraph, stmt: Statement,
                                tail_id: int, counter: int) -> Tuple[int, int]:
        """
        Normalizes access checks into If-Form Node Groups (IFNG):
        IF -> REVERT (fail) & IF -> ENDIF (pass)
        """
        code = stmt.raw_code
        reads_sender = "msg.sender" in code or "tx.origin" in code
        modifies_state = stmt.details.get("modifies_state", False) or \
                         any(op in code for op in ("=", "+=", "-=", "*=", "transfer(", "send("))

        if stmt.stmt_type in ("REQUIRE", "ASSERT"):
            is_guard = stmt.details.get("is_guard", False) or \
                       any(k in code.lower() for k in ("msg.sender", "tx.origin", "hasrole", "onlyowner", "isowner")) or \
                       bool(re.search(r'\b(caller|sender)\s*==\s*(owner|admin|_owner)', code.lower()))

            cond = stmt.details.get("condition", code)
            err = stmt.details.get("error", "Revert")

            # IF node
            if_node = ACFGNode(
                node_id=counter,
                node_type="IF",
                code=f"IF ({cond})",
                is_guard=is_guard,
                reads_sender=reads_sender,
                modifies_state=False
            )
            G.add_node(if_node.id, data=if_node)
            G.add_edge(tail_id, if_node.id)
            counter += 1

            # REVERT node (fail path)
            revert_node = ACFGNode(
                node_id=counter,
                node_type="REVERT",
                code=f"REVERT {err}".strip(),
                is_guard=is_guard,
                reads_sender=reads_sender,
                modifies_state=False
            )
            G.add_node(revert_node.id, data=revert_node)
            G.add_edge(if_node.id, revert_node.id)
            counter += 1

            # ENDIF node (join / success path)
            endif_node = ACFGNode(
                node_id=counter,
                node_type="ENDIF",
                code="ENDIF",
                is_guard=is_guard,
                reads_sender=False,
                modifies_state=False
            )
            G.add_node(endif_node.id, data=endif_node)
            G.add_edge(if_node.id, endif_node.id)
            counter += 1

            return endif_node.id, counter

        elif stmt.stmt_type == "IF_BLOCK":
            is_guard = stmt.details.get("is_guard", False)
            cond = stmt.details.get("condition", "cond")
            inner_body = stmt.details.get("inner_body", "")

            # If inner body contains revert, normalize directly to IFNG
            if "revert" in inner_body.lower():
                if_node = ACFGNode(
                    node_id=counter,
                    node_type="IF",
                    code=f"IF ({cond})",
                    is_guard=is_guard,
                    reads_sender=reads_sender,
                    modifies_state=False
                )
                G.add_node(if_node.id, data=if_node)
                G.add_edge(tail_id, if_node.id)
                counter += 1

                revert_node = ACFGNode(
                    node_id=counter,
                    node_type="REVERT",
                    code="REVERT",
                    is_guard=is_guard,
                    reads_sender=reads_sender,
                    modifies_state=False
                )
                G.add_node(revert_node.id, data=revert_node)
                G.add_edge(if_node.id, revert_node.id)
                counter += 1

                endif_node = ACFGNode(
                    node_id=counter,
                    node_type="ENDIF",
                    code="ENDIF",
                    is_guard=is_guard,
                    reads_sender=False,
                    modifies_state=False
                )
                G.add_node(endif_node.id, data=endif_node)
                G.add_edge(if_node.id, endif_node.id)
                counter += 1

                return endif_node.id, counter
            else:
                generic_node = ACFGNode(
                    node_id=counter,
                    node_type="EXPR",
                    code=code,
                    is_guard=False,
                    reads_sender=reads_sender,
                    modifies_state=modifies_state
                )
                G.add_node(generic_node.id, data=generic_node)
                G.add_edge(tail_id, generic_node.id)
                counter += 1
                return generic_node.id, counter

        elif stmt.stmt_type == "EMIT":
            # EMIT node - will be pruned in pruning step
            emit_node = ACFGNode(
                node_id=counter,
                node_type="EMIT",
                code=code,
                is_guard=False,
                reads_sender=False,
                modifies_state=False
            )
            G.add_node(emit_node.id, data=emit_node)
            G.add_edge(tail_id, emit_node.id)
            counter += 1
            return emit_node.id, counter

        elif stmt.stmt_type == "CALL_EXTERNAL":
            call_node = ACFGNode(
                node_id=counter,
                node_type="CALL_EXTERNAL",
                code=code,
                is_guard=False,
                reads_sender=reads_sender,
                modifies_state=True
            )
            G.add_node(call_node.id, data=call_node)
            G.add_edge(tail_id, call_node.id)
            counter += 1
            return call_node.id, counter

        elif stmt.stmt_type == "STATE_ASSIGN":
            assign_node = ACFGNode(
                node_id=counter,
                node_type="STATE_ASSIGN",
                code=code,
                is_guard=False,
                reads_sender=reads_sender,
                modifies_state=True
            )
            G.add_node(assign_node.id, data=assign_node)
            G.add_edge(tail_id, assign_node.id)
            counter += 1
            return assign_node.id, counter

        elif stmt.stmt_type == "RETURN":
            ret_node = ACFGNode(
                node_id=counter,
                node_type="RETURN",
                code=code,
                is_guard=False,
                reads_sender=False,
                modifies_state=False
            )
            G.add_node(ret_node.id, data=ret_node)
            G.add_edge(tail_id, ret_node.id)
            counter += 1
            return ret_node.id, counter

        else:
            expr_node = ACFGNode(
                node_id=counter,
                node_type="EXPR",
                code=code,
                is_guard=False,
                reads_sender=reads_sender,
                modifies_state=modifies_state
            )
            G.add_node(expr_node.id, data=expr_node)
            G.add_edge(tail_id, expr_node.id)
            counter += 1
            return expr_node.id, counter

    def _apply_pruning_rules(self, G: nx.DiGraph) -> nx.DiGraph:
        """
        Prunes event emissions (EMIT nodes) and non-access-control noise.
        Re-connects predecessors directly to successors.
        """
        nodes_to_prune = []
        for n, d in G.nodes(data=True):
            data: ACFGNode = d.get("data")
            if data and data.type == "EMIT":
                nodes_to_prune.append(n)

        for n in nodes_to_prune:
            preds = list(G.predecessors(n))
            succs = list(G.successors(n))
            for p in preds:
                for s in succs:
                    if p != s:
                        G.add_edge(p, s)
            G.remove_node(n)

        return G

    def _reorder_graph_bfs(self, G: nx.DiGraph, root_id: int = 0) -> Dict[str, Any]:
        """
        Re-indexes nodes sequentially using Breadth-First Search (BFS) starting from root.
        """
        if root_id not in G:
            root_id = list(G.nodes())[0] if G.nodes() else 0

        visited = set()
        queue = deque([root_id])
        visited.add(root_id)
        bfs_order = []

        while queue:
            curr = queue.popleft()
            bfs_order.append(curr)
            for neighbor in sorted(G.successors(curr)):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        # Include any remaining disconnected nodes if any
        for n in G.nodes():
            if n not in visited:
                bfs_order.append(n)
                visited.add(n)

        old_to_new = {old: new for new, old in enumerate(bfs_order)}

        reordered_nodes = []
        for old_id in bfs_order:
            node_data: ACFGNode = G.nodes[old_id].get("data")
            if node_data:
                node_dict = node_data.to_dict()
                node_dict["id"] = old_to_new[old_id]
                reordered_nodes.append(node_dict)

        reordered_edges = []
        for u, v in G.edges():
            if u in old_to_new and v in old_to_new:
                reordered_edges.append([old_to_new[u], old_to_new[v]])

        return {
            "nodes": reordered_nodes,
            "edges": reordered_edges
        }

    @staticmethod
    def patch_graph_with_guard(graph_dict: Dict[str, Any], guard_condition: str = "msg.sender == owner") -> Dict[str, Any]:
        """
        Inserts a synthetic candidate Access Control If-Form Node Group (IFNG)
        right after the ENTRY node of the graph, simulating the patch test.
        """
        orig_nodes = graph_dict.get("nodes", [])
        orig_edges = graph_dict.get("edges", [])

        if not orig_nodes:
            return graph_dict

        # Construct new graph with IFNG guard inserted after ENTRY (node 0)
        entry_node = orig_nodes[0]
        # Nodes:
        # 0: ENTRY
        # 1: IF (guard) [guard=True]
        # 2: REVERT [guard=True]
        # 3: ENDIF [guard=True]
        # 4+: shifted orig nodes from index 1 onward (+3 to their indices)
        patched_nodes = [entry_node]
        patched_nodes.append({
            "id": 1,
            "type": "IF",
            "code": f"IF ({guard_condition})",
            "is_guard": True,
            "reads_sender": True,
            "modifies_state": False
        })
        patched_nodes.append({
            "id": 2,
            "type": "REVERT",
            "code": "REVERT \"Unauthorized: caller is not authorized\"",
            "is_guard": True,
            "reads_sender": True,
            "modifies_state": False
        })
        patched_nodes.append({
            "id": 3,
            "type": "ENDIF",
            "code": "ENDIF",
            "is_guard": True,
            "reads_sender": False,
            "modifies_state": False
        })

        shift = 3
        for node in orig_nodes[1:]:
            new_node = dict(node)
            new_node["id"] = node["id"] + shift
            patched_nodes.append(new_node)

        # Edges
        patched_edges = [
            [0, 1],  # ENTRY -> IF
            [1, 2],  # IF -> REVERT
            [1, 3]   # IF -> ENDIF
        ]

        # Shift original edges:
        # Original edges from node 0 (ENTRY) to X now go from 3 (ENDIF) to X + shift
        for u, v in orig_edges:
            if u == 0:
                patched_edges.append([3, v + shift])
            else:
                patched_edges.append([u + shift, v + shift])

        return {
            "nodes": patched_nodes,
            "edges": patched_edges
        }
