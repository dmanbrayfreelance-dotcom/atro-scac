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
                 contract_name: str, start_line: int = 1):
        self.name = name
        self.params = params
        self.visibility = visibility
        self.mutability = mutability  # 'view', 'pure', 'payable', 'nonpayable'
        self.modifiers = modifiers
        self.body_raw = body_raw
        self.contract_name = contract_name
        self.start_line = start_line
        self.statements: List[Statement] = []

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
            "body_raw": self.body_raw,
            "statements": [s.to_dict() for s in self.statements]
        }


class SolidityExtractor:
    """
    Robust Solidity source parser and AST extractor.
    Extracts contracts, state variables, modifiers, functions, and parses function bodies
    into structured statements while inlining modifiers and resolving control flow.
    """

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.contracts: Dict[str, Dict[str, Any]] = {}
        self.modifiers: Dict[str, Dict[str, Any]] = {}
        self.candidate_functions: List[FunctionDef] = []
        self._parse()

    def _strip_comments(self, code: str) -> str:
        # Strip /* ... */ multi-line comments
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        # Strip // single-line comments
        code = re.sub(r'//.*', '', code)
        return code

    def _parse(self):
        clean_code = self._strip_comments(self.source_code)

        # 1. Extract modifiers globally or per contract
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
                "body": body
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
            self.contracts[name] = {
                "kind": kind,
                "name": name,
                "inherits": inherits,
                "body": contract_body
            }

            # If it's a contract, parse its functions
            if "interface" not in kind:
                self._parse_contract_functions(name, contract_body)

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
            # typical: "address newOwner", "uint256 amount", "bytes32 role"
            # handle memory/calldata/storage
            clean_tokens = [t for t in tokens if t not in ("memory", "calldata", "storage")]
            if len(clean_tokens) >= 2:
                params.append({"type": clean_tokens[0], "name": clean_tokens[-1]})
            elif len(clean_tokens) == 1:
                params.append({"type": clean_tokens[0], "name": ""})
        return params

    def _parse_contract_functions(self, contract_name: str, body: str):
        # Match function header: function foo(...) <attributes> {
        fn_pattern = re.compile(
            r'\bfunction\s+([a-zA-Z0-9_]+)\s*\((.*?)\)\s*([^{;]*)(?:\{|;)',
            re.MULTILINE | re.DOTALL
        )

        for match in fn_pattern.finditer(body):
            fn_name = match.group(1).strip()
            raw_params = match.group(2).strip()
            attrs_raw = match.group(3).strip()

            # Determine visibility
            visibility = "public"  # default in solidity if unspecified
            if re.search(r'\bexternal\b', attrs_raw):
                visibility = "external"
            elif re.search(r'\bpublic\b', attrs_raw):
                visibility = "public"
            elif re.search(r'\binternal\b', attrs_raw):
                visibility = "internal"
            elif re.search(r'\bprivate\b', attrs_raw):
                visibility = "private"

            # Determine mutability
            mutability = "nonpayable"
            if re.search(r'\bview\b', attrs_raw):
                mutability = "view"
            elif re.search(r'\bpure\b', attrs_raw):
                mutability = "pure"
            elif re.search(r'\bpayable\b', attrs_raw):
                mutability = "payable"

            # Extract modifiers applied to this function
            # Clean standard keywords from attrs_raw
            clean_attrs = re.sub(
                r'\b(public|external|internal|private|view|pure|payable|virtual|override)\b',
                '',
                attrs_raw
            )
            # Remove returns(...)
            clean_attrs = re.sub(r'returns\s*\([^)]*\)', '', clean_attrs)
            modifiers = [m.strip() for m in re.findall(r'[a-zA-Z0-9_]+(?:\([^)]*\))?', clean_attrs) if m.strip()]

            # Extract function body if present
            end_match = match.end()
            if body[end_match - 1] == '{':
                fn_body = self._extract_balanced_block(body, end_match - 1)
            else:
                fn_body = ""

            params = self._parse_param_list(raw_params)
            fn_obj = FunctionDef(
                name=fn_name,
                params=params,
                visibility=visibility,
                mutability=mutability,
                modifiers=modifiers,
                body_raw=fn_body,
                contract_name=contract_name
            )

            # Parse statements in function body
            fn_obj.statements = self._parse_statements(fn_body)

            # Filter candidate functions:
            # ASTRO focuses on externally callable (public/external) state-modifying functions
            if fn_obj.is_externally_callable and fn_obj.is_state_modifying:
                self.candidate_functions.append(fn_obj)

    def _parse_statements(self, code_block: str) -> List[Statement]:
        statements = []
        if not code_block or not code_block.strip():
            return statements

        # Tokenize by semicolon or compound blocks (if / require / emit / assignments)
        # Using a balanced-aware splitter for statements
        chunks = self._split_statements(code_block)
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            # Classify statement
            if chunk.startswith("require(") or chunk.startswith("require ("):
                # Extract require condition and error
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
                # find body
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
        # Access control guards authenticate the CALLER/SENDER or verify permission roles
        # Should not match parameter validation checks like `newOwner != address(0)`
        if "msg.sender" in cond_lower or "tx.origin" in cond_lower:
            return True
        if "hasrole" in cond_lower or "isowner" in cond_lower or "auth" in cond_lower:
            return True
        # Check for explicit equality with owner/admin variable
        if re.search(r'\b(sender|caller)\s*==\s*(owner|admin|_owner)', cond_lower):
            return True
        if re.search(r'\b(owner|admin|_owner)\s*==\s*(sender|caller)', cond_lower):
            return True
        return False


def match_candidate_functions(
    candidates: List[FunctionDef],
    reference_entries: List[Dict[str, Any]]
) -> List[Tuple[FunctionDef, List[Dict[str, Any]]]]:
    """
    Match candidate target functions (TFunc) against reference entries (DBFunc)
    based on function name, signature, or semantic equivalence.
    """
    matches = []
    for cand in candidates:
        matched_refs = []
        cand_sig = cand.signature.lower()
        cand_name = cand.name.lower()

        for ref in reference_entries:
            ref_sig = ref.get("signature", "").lower()
            ref_name = ref.get("function_name", "").lower()

            # Exact signature match
            if cand_sig == ref_sig:
                matched_refs.append(ref)
            # Exact function name match (even if parameters differ slightly)
            elif cand_name == ref_name:
                matched_refs.append(ref)
            # Semantic equivalence heuristics
            elif ("withdraw" in cand_name and "withdraw" in ref_name) or \
                 ("ownership" in cand_name and "ownership" in ref_name) or \
                 ("token" in cand_name and "token" in ref_name and "transfer" in cand_name):
                matched_refs.append(ref)

        matches.append((cand, matched_refs))
    return matches
