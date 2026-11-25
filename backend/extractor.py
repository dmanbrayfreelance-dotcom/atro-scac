import re
from typing import List, Dict, Any, Optional, Tuple


class Statement:
    def __init__(self, raw_code: str, stmt_type: str, details: Dict[str, Any] = None):
        self.raw_code = raw_code.strip()
        self.stmt_type = stmt_type
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_code": self.raw_code,
            "stmt_type": self.stmt_type,
            "details": self.details
        }


class FunctionDef:
    def __init__(self, name: str, params: List[Dict[str, str]], visibility: str,
                 mutability: str, modifiers: List[str], body_raw: str,
                 contract_name: str, start_line: int = 1, end_line: int = 1):
        self.name = name
        self.params = params
        self.visibility = visibility
        self.mutability = mutability  # 'view', 'pure', 'payable', 'nonpayable'
        self.modifiers = modifiers
        self.body_raw = body_raw
        self.contract_name = contract_name
        self.start_line = start_line
        self.end_line = end_line
        self.statements: List[Statement] = []
        self.state_writes: List[str] = []
        self.internal_calls: List[str] = []
        self.external_calls: List[str] = []

    @property
    def signature(self) -> str:
        param_types = [p.get("type", "uint256") for p in self.params]
        return f"{self.name}({','.join(param_types)})"

    @property
    def is_externally_callable(self) -> bool:
        return self.visibility in ("public", "external")

    @property
    def is_state_modifying(self) -> bool:
        return self.mutability not in ("view", "pure")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "signature": self.signature,
            "contract_name": self.contract_name,
            "visibility": self.visibility,
            "mutability": self.mutability,
            "modifiers": self.modifiers,
            "params": self.params,
            "is_externally_callable": self.is_externally_callable,
            "is_state_modifying": self.is_state_modifying,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "body_raw": self.body_raw,
            "state_writes": self.state_writes,
            "internal_calls": self.internal_calls,
            "external_calls": self.external_calls,
            "statements": [s.to_dict() for s in self.statements]
        }


class StateVariable:
    def __init__(self, name: str, var_type: str, visibility: str = "internal"):
        self.name = name
        self.var_type = var_type
        self.visibility = visibility
        self.written_by: List[str] = []
        self.guarded_by: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.var_type,
            "visibility": self.visibility,
            "written_by": list(set(self.written_by)),
            "guarded_by": list(set(self.guarded_by))
        }


class SolidityExtractor:
    """
    Robust Solidity source parser and AST extractor.
    Extracts contracts, state variables, modifiers, functions, and maps their
    structural relationships (calls, state writes, modifier guards).
    """

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.contracts: Dict[str, Dict[str, Any]] = {}
        self.modifiers: Dict[str, Dict[str, Any]] = {}
        self.state_variables: Dict[str, List[StateVariable]] = {}
        self.candidate_functions: List[FunctionDef] = []
        self.all_functions: List[FunctionDef] = []
        self.contract_relationships: Dict[str, List[Dict[str, Any]]] = {}
        self._parse()

    def _strip_comments(self, code: str) -> str:
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        code = re.sub(r'//.*', '', code)
        return code

    def _parse(self):
        clean_code = self._strip_comments(self.source_code)

        # 1. Extract modifiers globally
        modifier_pattern = re.compile(
            r'modifier\s+([a-zA-Z0-9_]+)\s*(?:\((.*?)\))?\s*\{',
            re.MULTILINE
        )
        for match in modifier_pattern.finditer(clean_code):
            mod_name = match.group(1)
            params_raw = match.group(2) or ""
            start_pos = match.end()
            body = self._extract_balanced_block(clean_code, start_pos - 1)
            self.modifiers[mod_name] = {
                "name": mod_name,
                "params": self._parse_param_list(params_raw),
                "body": body,
                "guarded_functions": []
            }

        # 2. Extract Contracts
        contract_pattern = re.compile(
            r'\b(contract|abstract\s+contract|library|interface)\s+([a-zA-Z0-9_]+)(?:\s+is\s+([^{]+))?\s*\{',
            re.MULTILINE
        )
        for match in contract_pattern.finditer(clean_code):
            kind = match.group(1).strip()
            name = match.group(2).strip()
            inherits = [b.strip() for b in match.group(3).split(",")] if match.group(3) else []
            start_pos = match.end()
            contract_body = self._extract_balanced_block(clean_code, start_pos - 1)

            # Calculate contract start line in original source
            start_line = self.source_code[:match.start()].count('\n') + 1

            self.contracts[name] = {
                "kind": kind,
                "name": name,
                "inherits": inherits,
                "body": contract_body,
                "start_line": start_line
            }

            if "interface" not in kind:
                # Extract state variables
                state_vars = self._parse_state_variables(contract_body)
                self.state_variables[name] = state_vars

                # Extract functions
                self._parse_contract_functions(name, contract_body, state_vars)

                # Build relationships for this contract
                self._build_relationships(name)

    def _extract_balanced_block(self, text: str, open_brace_pos: int) -> str:
        depth = 0
        in_string = False
        string_char = ''
        i = open_brace_pos

        while i < len(text):
            c = text[i]
            if in_string:
                if c == '\\':
                    i += 2
                    continue
                elif c == string_char:
                    in_string = False
            else:
                if c in ("'", '"'):
                    in_string = True
                    string_char = c
                elif c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        return text[open_brace_pos + 1:i]
            i += 1
        return text[open_brace_pos + 1:]

    def _parse_param_list(self, raw_params: str) -> List[Dict[str, str]]:
        params = []
        if not raw_params or not raw_params.strip():
            return params
        for part in raw_params.split(","):
            part = part.strip()
            if not part:
                continue
            tokens = part.split()
            clean_tokens = [t for t in tokens if t not in ("memory", "calldata", "storage")]
            if len(clean_tokens) >= 2:
                params.append({"type": clean_tokens[0], "name": clean_tokens[-1]})
            elif len(clean_tokens) == 1:
                params.append({"type": clean_tokens[0], "name": ""})
        return params

    def _parse_state_variables(self, body: str) -> List[StateVariable]:
        state_vars = []
        # Pattern for state variable declarations (excluding functions, modifiers, events, structs)
        lines = [line.strip() for line in body.split(';') if line.strip()]
        for line in lines:
            line_clean = line.strip()
            if any(line_clean.startswith(kw) for kw in (
                "function", "modifier", "event", "struct", "enum", "constructor", "mapping"
            )):
                if line_clean.startswith("mapping"):
                    m = re.search(r'mapping\s*\(.*?\)\s*(public|private|internal)?\s*([a-zA-Z0-9_]+)', line_clean)
                    if m:
                        vis = m.group(1) or "internal"
                        vname = m.group(2)
                        state_vars.append(StateVariable(vname, "mapping", vis))
                continue

            # Standard types: address, uint256, bool, bytes32, string, etc.
            var_match = re.search(
                r'\b(address|uint256|uint8|uint|int|bool|bytes32|string|bytes)\b\s*(?:\[.*?\])?\s*(public|private|internal|constant|immutable)?\s*(?:public|private|internal|constant|immutable)?\s*([a-zA-Z0-9_]+)',
                line_clean
            )
            if var_match:
                vtype = var_match.group(1)
                vis = var_match.group(2) or "internal"
                vname = var_match.group(3)
                state_vars.append(StateVariable(vname, vtype, vis))

        return state_vars

    def _parse_contract_functions(self, contract_name: str, body: str, state_vars: List[StateVariable]):
        fn_pattern = re.compile(
            r'\bfunction\s+([a-zA-Z0-9_]+)\s*\((.*?)\)\s*([^{;]*)(?:\{|;)',
            re.MULTILINE | re.DOTALL
        )

        for match in fn_pattern.finditer(body):
            fn_name = match.group(1).strip()
            raw_params = match.group(2).strip()
            attrs_raw = match.group(3).strip()

            visibility = "public"
            if re.search(r'\bexternal\b', attrs_raw):
                visibility = "external"
            elif re.search(r'\bpublic\b', attrs_raw):
                visibility = "public"
            elif re.search(r'\binternal\b', attrs_raw):
                visibility = "internal"
            elif re.search(r'\bprivate\b', attrs_raw):
                visibility = "private"

            mutability = "nonpayable"
            if re.search(r'\bview\b', attrs_raw):
                mutability = "view"
            elif re.search(r'\bpure\b', attrs_raw):
                mutability = "pure"
            elif re.search(r'\bpayable\b', attrs_raw):
                mutability = "payable"

            clean_attrs = re.sub(
                r'\b(public|external|internal|private|view|pure|payable|virtual|override)\b',
                '',
                attrs_raw
            )
            clean_attrs = re.sub(r'returns\s*\([^)]*\)', '', clean_attrs)
            modifiers = [m.strip() for m in re.findall(r'[a-zA-Z0-9_]+(?:\([^)]*\))?', clean_attrs) if m.strip()]

            end_match = match.end()
            if body[end_match - 1] == '{':
                fn_body = self._extract_balanced_block(body, end_match - 1)
            else:
                fn_body = ""

            # Calculate precise line numbers in source
            func_search_str = f"function {fn_name}"
            func_idx = self.source_code.find(func_search_str)
            if func_idx != -1:
                start_line = self.source_code[:func_idx].count('\n') + 1
            else:
                start_line = 1
            end_line = start_line + max(1, fn_body.count('\n'))

            params = self._parse_param_list(raw_params)
            fn_obj = FunctionDef(
                name=fn_name,
                params=params,
                visibility=visibility,
                mutability=mutability,
                modifiers=modifiers,
                body_raw=fn_body,
                contract_name=contract_name,
                start_line=start_line,
                end_line=end_line
            )

            # Track modifiers applied
            for mod in modifiers:
                mod_name = mod.split('(')[0].strip()
                if mod_name in self.modifiers:
                    self.modifiers[mod_name]["guarded_functions"].append(fn_name)

            # Parse statements
            fn_obj.statements = self._parse_statements(fn_body)

            # Analyze state writes and calls
            for sv in state_vars:
                # Check if this function modifies this state variable
                pattern = rf'\b{sv.name}\s*(\=|\+\=|\-\=|\*\=|\/\=)'
                if re.search(pattern, fn_body):
                    fn_obj.state_writes.append(sv.name)
                    sv.written_by.append(fn_name)
                    if modifiers:
                        sv.guarded_by.extend(modifiers)

            # Detect external calls
            for call_kw in (".transfer(", ".send(", ".call{", ".call(", "IERC20("):
                if call_kw in fn_body:
                    fn_obj.external_calls.append(call_kw)

            # Detect internal calls
            internal_candidates = [
                f.name for f in self.all_functions if f.contract_name == contract_name
            ]
            for ic in internal_candidates:
                if ic != fn_name and f"{ic}(" in fn_body:
                    fn_obj.internal_calls.append(ic)

            self.all_functions.append(fn_obj)
            if fn_obj.is_externally_callable and fn_obj.is_state_modifying:
                self.candidate_functions.append(fn_obj)

    def _build_relationships(self, contract_name: str):
        rels = []
        c_funcs = [f for f in self.all_functions if f.contract_name == contract_name]
        c_state_vars = self.state_variables.get(contract_name, [])

        for fn in c_funcs:
            # Modifiers applied
            for mod in fn.modifiers:
                rels.append({
                    "source": fn.name,
                    "target": mod,
                    "type": "APPLIES_MODIFIER",
                    "description": f"Function `{fn.name}` is guarded by modifier `{mod}`."
                })
            # State writes
            for sw in fn.state_writes:
                rels.append({
                    "source": fn.name,
                    "target": sw,
                    "type": "MODIFIES_STATE",
                    "description": f"Function `{fn.name}` mutates state variable `{sw}`."
                })
            # External calls
            for ec in fn.external_calls:
                rels.append({
                    "source": fn.name,
                    "target": ec.replace("(", "").strip(),
                    "type": "EXTERNAL_CALL",
                    "description": f"Function `{fn.name}` performs external call `{ec}`."
                })
            # Internal calls
            for ic in fn.internal_calls:
                rels.append({
                    "source": fn.name,
                    "target": ic,
                    "type": "CALLS_INTERNAL",
                    "description": f"Function `{fn.name}` invokes internal routine `{ic}`."
                })

        self.contract_relationships[contract_name] = rels

    def _parse_statements(self, code_block: str) -> List[Statement]:
        statements = []
        if not code_block or not code_block.strip():
            return statements

        chunks = self._split_statements(code_block)
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            if chunk.startswith("require(") or chunk.startswith("require ("):
                inner = self._extract_parenthesized_content(chunk, "require")
                parts = self._split_comma_args(inner)
                cond = parts[0] if parts else inner
                err = parts[1] if len(parts) > 1 else ""
                statements.append(Statement(chunk, "REQUIRE", {
                    "condition": cond,
                    "error": err,
                    "is_guard": self._is_access_control_condition(cond)
                }))

            elif chunk.startswith("assert(") or chunk.startswith("assert ("):
                inner = self._extract_parenthesized_content(chunk, "assert")
                statements.append(Statement(chunk, "ASSERT", {
                    "condition": inner,
                    "is_guard": self._is_access_control_condition(inner)
                }))

            elif chunk.startswith("if (") or chunk.startswith("if("):
                cond = self._extract_parenthesized_content(chunk, "if")
                body_idx = chunk.find(")")
                rest = chunk[body_idx + 1:].strip() if body_idx != -1 else ""
                statements.append(Statement(chunk, "IF_BLOCK", {
                    "condition": cond,
                    "inner_body": rest,
                    "is_guard": self._is_access_control_condition(cond)
                }))

            elif chunk.startswith("emit ") or chunk.startswith("emit("):
                statements.append(Statement(chunk, "EMIT", {"event": chunk}))

            elif chunk.startswith("return ") or chunk == "return" or chunk.startswith("return;"):
                statements.append(Statement(chunk, "RETURN", {"expr": chunk}))

            elif chunk.startswith("revert(") or chunk.startswith("revert ") or chunk == "revert;":
                statements.append(Statement(chunk, "REVERT", {"reason": chunk}))

            elif any(op in chunk for op in ("=", "+=", "-=", "*=", "/=")):
                statements.append(Statement(chunk, "STATE_ASSIGN", {
                    "assignment": chunk,
                    "modifies_state": True
                }))

            elif any(call in chunk for call in (".transfer(", ".send(", ".call{", ".call(")):
                statements.append(Statement(chunk, "CALL_EXTERNAL", {
                    "call": chunk,
                    "is_transfer": True,
                    "modifies_state": True
                }))

            else:
                statements.append(Statement(chunk, "EXPR", {"code": chunk}))

        return statements

    def _split_statements(self, block: str) -> List[str]:
        statements = []
        current = []
        depth_paren = 0
        depth_brace = 0
        in_string = False
        string_char = ''

        i = 0
        while i < len(block):
            c = block[i]
            if in_string:
                current.append(c)
                if c == '\\':
                    i += 1
                    if i < len(block):
                        current.append(block[i])
                elif c == string_char:
                    in_string = False
            else:
                if c in ('"', "'"):
                    in_string = True
                    string_char = c
                    current.append(c)
                elif c == '(':
                    depth_paren += 1
                    current.append(c)
                elif c == ')':
                    depth_paren -= 1
                    current.append(c)
                elif c == '{':
                    depth_brace += 1
                    current.append(c)
                elif c == '}':
                    depth_brace -= 1
                    current.append(c)
                    if depth_brace == 0 and depth_paren == 0:
                        statements.append(''.join(current).strip())
                        current = []
                elif c == ';' and depth_brace == 0 and depth_paren == 0:
                    current.append(c)
                    statements.append(''.join(current).strip())
                    current = []
                else:
                    current.append(c)
            i += 1

        if current:
            rem = ''.join(current).strip()
            if rem:
                statements.append(rem)
        return statements

    def _extract_parenthesized_content(self, text: str, prefix: str) -> str:
        idx = text.find(prefix)
        if idx == -1:
            return ""
        open_pos = text.find("(", idx)
        if open_pos == -1:
            return ""
        depth = 0
        for i in range(open_pos, len(text)):
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
                if depth == 0:
                    return text[open_pos + 1:i].strip()
        return text[open_pos + 1:].strip()

    def _split_comma_args(self, text: str) -> List[str]:
        args = []
        current = []
        depth = 0
        in_str = False
        str_c = ''
        for c in text:
            if in_str:
                current.append(c)
                if c == str_c:
                    in_str = False
            else:
                if c in ('"', "'"):
                    in_str = True
                    str_c = c
                    current.append(c)
                elif c in ('(', '[', '{'):
                    depth += 1
                    current.append(c)
                elif c in (')', ']', '}'):
                    depth -= 1
                    current.append(c)
                elif c == ',' and depth == 0:
                    args.append(''.join(current).strip())
                    current = []
                else:
                    current.append(c)
        if current:
            args.append(''.join(current).strip())
        return args

    def _is_access_control_condition(self, cond: str) -> bool:
        cond_lower = cond.lower()
        if "msg.sender" in cond_lower or "tx.origin" in cond_lower:
            return True
        if "hasrole" in cond_lower or "isowner" in cond_lower or "auth" in cond_lower:
            return True
        if re.search(r'\b(sender|caller)\s*==\s*(owner|admin|_owner)', cond_lower):
            return True
        if re.search(r'\b(owner|admin|_owner)\s*==\s*(sender|caller)', cond_lower):
            return True
        return False

    def get_contract_summary(self, contract_name: str) -> Dict[str, Any]:
        """
        Returns structural representation of contract, state variables, and relationships.
        """
        state_vars = [sv.to_dict() for sv in self.state_variables.get(contract_name, [])]
        rels = self.contract_relationships.get(contract_name, [])
        c_funcs = [
            f.to_dict() for f in self.all_functions if f.contract_name == contract_name
        ]
        return {
            "contract_name": contract_name,
            "state_variables": state_vars,
            "relationships": rels,
            "functions": c_funcs,
            "modifiers": [
                {"name": name, "guarded_functions": data.get("guarded_functions", [])}
                for name, data in self.modifiers.items()
            ]
        }


def match_candidate_functions(
    candidates: List[FunctionDef],
    reference_entries: List[Dict[str, Any]]
) -> List[Tuple[FunctionDef, List[Dict[str, Any]]]]:
    matches = []
    for cand in candidates:
        matched_refs = []
        cand_sig = cand.signature.lower()
        cand_name = cand.name.lower()

        for ref in reference_entries:
            ref_sig = ref.get("signature", "").lower()
            ref_name = ref.get("function_name", "").lower()

            if cand_sig == ref_sig:
                matched_refs.append(ref)
            elif cand_name == ref_name:
                matched_refs.append(ref)
            elif ("withdraw" in cand_name and "withdraw" in ref_name) or \
                 ("ownership" in cand_name and "ownership" in ref_name) or \
                 ("token" in cand_name and "token" in ref_name and "transfer" in cand_name):
                matched_refs.append(ref)

        matches.append((cand, matched_refs))
    return matches
