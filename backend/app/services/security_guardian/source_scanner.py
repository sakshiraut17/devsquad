"""Deterministic Source Code Vulnerability Scanner for DevSquad AI Security Guardian.

Combines Python AST static inspection with an optional Bandit analyzer.
"""

import ast
import json
import logging
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional
from app.schemas.security import SecurityCategory, SecurityFindingSchema, SecuritySeverity

logger = logging.getLogger("devsquad.security.source_scanner")


class ASTSecurityVisitor(ast.NodeVisitor):
    """AST visitor detecting deterministic security vulnerabilities in Python code."""

    def __init__(self, filename: str):
        self.filename = filename
        self.findings: List[Dict[str, Any]] = []

    def visit_Call(self, node: ast.Call):
        func_name = self._get_func_name(node.func)

        # Rule VULN-001: SQL Injection via unparameterized string formatting
        if func_name.endswith((".execute", ".executemany", ".raw")):
            if node.args:
                arg0 = node.args[0]
                if isinstance(arg0, ast.JoinedStr):  # f-string: f"SELECT ... {var}"
                    self.findings.append({
                        "rule_id": "VULN-001",
                        "title": "SQL Injection Risk (f-string formatting)",
                        "description": "SQL statement constructed dynamically using f-string without parameterization.",
                        "severity": SecuritySeverity.CRITICAL.value,
                        "line": node.lineno,
                        "remediation": "Use parameterized queries with bind variables (:param) instead of string interpolation.",
                    })
                elif isinstance(arg0, ast.BinOp) and isinstance(arg0.op, (ast.Mod, ast.Add)):  # % formatting or string concat
                    self.findings.append({
                        "rule_id": "VULN-001",
                        "title": "SQL Injection Risk (String formatting/concatenation)",
                        "description": "SQL statement constructed using '%' formatting or '+' concatenation.",
                        "severity": SecuritySeverity.CRITICAL.value,
                        "line": node.lineno,
                        "remediation": "Use parameterized queries with bind variables (:param) instead of string formatting.",
                    })

        # Rule VULN-002: Command Injection / Dangerous Shell Execution
        if func_name in ("subprocess.run", "subprocess.call", "subprocess.Popen", "subprocess.check_call", "subprocess.check_output"):
            has_shell = False
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    has_shell = True
            if has_shell:
                # If command argument is not a static constant string, flag as critical
                arg0 = node.args[0] if node.args else None
                if not isinstance(arg0, ast.Constant):
                    self.findings.append({
                        "rule_id": "VULN-002",
                        "title": "Command Injection Risk (shell=True with dynamic input)",
                        "description": f"Subprocess call '{func_name}' executed with shell=True and dynamic arguments.",
                        "severity": SecuritySeverity.CRITICAL.value,
                        "line": node.lineno,
                        "remediation": "Pass command arguments as an array [cmd, arg1, ...] and set shell=False.",
                    })

        if func_name in ("os.system", "os.popen"):
            arg0 = node.args[0] if node.args else None
            if not isinstance(arg0, ast.Constant):
                self.findings.append({
                    "rule_id": "VULN-002",
                    "title": "Dangerous Shell Execution (os.system / os.popen)",
                    "description": f"Executing system shell command via '{func_name}' with dynamic input.",
                    "severity": SecuritySeverity.CRITICAL.value,
                    "line": node.lineno,
                    "remediation": "Use subprocess.run with argument list and shell=False instead of os.system.",
                })

        if func_name in ("eval", "exec"):
            arg0 = node.args[0] if node.args else None
            if not isinstance(arg0, ast.Constant):
                self.findings.append({
                    "rule_id": "VULN-003",
                    "title": "Dynamic Code Execution (eval/exec)",
                    "description": f"Execution of dynamic Python code via '{func_name}'.",
                    "severity": SecuritySeverity.CRITICAL.value,
                    "line": node.lineno,
                    "remediation": "Refactor logic to use safe lookups, ast.literal_eval, or explicit dispatch tables.",
                })

        # Rule VULN-004: Insecure Deserialization
        if func_name in ("pickle.loads", "pickle.load", "_pickle.loads", "_pickle.load"):
            self.findings.append({
                "rule_id": "VULN-004",
                "title": "Insecure Deserialization (pickle)",
                "description": "Deserialization of untrusted byte streams using Python pickle enables arbitrary code execution.",
                "severity": SecuritySeverity.CRITICAL.value,
                "line": node.lineno,
                "remediation": "Use safe structured serialization formats such as JSON or Protocol Buffers instead of pickle.",
            })

        if func_name == "yaml.load":
            has_safe_loader = False
            for kw in node.keywords:
                if kw.arg == "Loader" and "SafeLoader" in getattr(kw.value, "id", ""):
                    has_safe_loader = True
            if not has_safe_loader:
                self.findings.append({
                    "rule_id": "VULN-004",
                    "title": "Insecure YAML Deserialization",
                    "description": "yaml.load used without explicit SafeLoader allows arbitrary object instantiation.",
                    "severity": SecuritySeverity.HIGH.value,
                    "line": node.lineno,
                    "remediation": "Use yaml.safe_load() or specify Loader=yaml.SafeLoader.",
                })

        # Rule VULN-005: Insecure Temporary File Creation
        if func_name == "tempfile.mktemp":
            self.findings.append({
                "rule_id": "VULN-005",
                "title": "Insecure Temporary File Creation (mktemp)",
                "description": "tempfile.mktemp is vulnerable to race conditions (symlink attacks).",
                "severity": SecuritySeverity.HIGH.value,
                "line": node.lineno,
                "remediation": "Use tempfile.NamedTemporaryFile() or tempfile.TemporaryDirectory() with context manager.",
            })

        # Rule VULN-006: Broken / Weak Cryptographic Primitives
        if func_name in ("hashlib.md5", "hashlib.sha1"):
            has_security_override = False
            for kw in node.keywords:
                if kw.arg == "usedforsecurity" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                    has_security_override = True
            if not has_security_override:
                self.findings.append({
                    "rule_id": "VULN-006",
                    "title": f"Weak Cryptographic Hash ({func_name})",
                    "description": f"Use of collision-vulnerable hash algorithm '{func_name}' in security context.",
                    "severity": SecuritySeverity.MEDIUM.value,
                    "line": node.lineno,
                    "remediation": "Use SHA-256 (hashlib.sha256) or pass usedforsecurity=False if purely for non-security checksums.",
                })

        self.generic_visit(node)

    def _get_func_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val_name = self._get_func_name(node.value)
            return f"{val_name}.{node.attr}" if val_name else node.attr
        return ""


class SourceCodeScanner:
    """Scans code files and unified diffs for source code vulnerabilities."""

    def __init__(self, scanner_version: str = "1.0.0"):
        self.version = scanner_version
        self.bandit_available = self._check_bandit()

    def _check_bandit(self) -> bool:
        try:
            import bandit
            return True
        except ImportError:
            return False

    def scan_code(
        self,
        file_path: str,
        code_content: str,
        run_id: str,
        patch_revision: int,
        patch_hash: str,
        base_commit_sha: Optional[str] = None,
    ) -> List[SecurityFindingSchema]:
        """Perform AST static vulnerability inspection on Python source."""
        findings: List[SecurityFindingSchema] = []
        if not file_path.endswith(".py") or not code_content.strip():
            return findings

        # 1. Deterministic AST Analysis
        try:
            tree = ast.parse(code_content, filename=file_path)
            visitor = ASTSecurityVisitor(file_path)
            visitor.visit(tree)

            lines = code_content.splitlines()
            for raw_finding in visitor.findings:
                line_no = raw_finding.get("line", 1)
                evidence = lines[line_no - 1].strip() if 0 < line_no <= len(lines) else None

                findings.append(
                    SecurityFindingSchema(
                        run_id=run_id,
                        patch_revision=patch_revision,
                        patch_hash=patch_hash,
                        base_commit_sha=base_commit_sha,
                        category=SecurityCategory.SOURCE_VULNERABILITY.value,
                        rule_id=raw_finding["rule_id"],
                        title=raw_finding["title"],
                        description=raw_finding["description"],
                        severity=raw_finding["severity"],
                        confidence="HIGH",
                        file_path=file_path,
                        line_start=line_no,
                        line_end=line_no,
                        evidence_redacted=evidence,
                        remediation=raw_finding.get("remediation"),
                        scanner_name="ast_security_visitor",
                        scanner_version=self.version,
                        is_blocking=raw_finding["severity"] in (SecuritySeverity.CRITICAL.value, SecuritySeverity.HIGH.value),
                        status="ACTIVE",
                    )
                )
        except SyntaxError as syn_err:
            logger.warning(f"[source_scanner] Syntax error parsing {file_path}: {syn_err}")

        # 2. Bandit Execution (if available and no AST finding already covers line)
        if self.bandit_available:
            bandit_findings = self._run_bandit(
                file_path=file_path,
                code_content=code_content,
                run_id=run_id,
                patch_revision=patch_revision,
                patch_hash=patch_hash,
                base_commit_sha=base_commit_sha,
            )
            # Deduplicate by line & rule prefix
            existing_lines = {f.line_start for f in findings}
            for b_finding in bandit_findings:
                if b_finding.line_start not in existing_lines:
                    findings.append(b_finding)

        return findings

    def _run_bandit(
        self,
        file_path: str,
        code_content: str,
        run_id: str,
        patch_revision: int,
        patch_hash: str,
        base_commit_sha: Optional[str] = None,
    ) -> List[SecurityFindingSchema]:
        findings: List[SecurityFindingSchema] = []
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp.write(code_content)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ["bandit", "-f", "json", "-q", tmp_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            data = json.loads(result.stdout) if result.stdout else {}
            for item in data.get("results", []):
                sev = item.get("issue_severity", "LOW").upper()
                line = item.get("line_number", 1)
                findings.append(
                    SecurityFindingSchema(
                        run_id=run_id,
                        patch_revision=patch_revision,
                        patch_hash=patch_hash,
                        base_commit_sha=base_commit_sha,
                        category=SecurityCategory.SOURCE_VULNERABILITY.value,
                        rule_id=f"BANDIT-{item.get('test_id', 'UNKNOWN')}",
                        title=item.get("test_name", "Bandit Security Finding"),
                        description=item.get("issue_text", ""),
                        severity=sev if sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW") else "MEDIUM",
                        confidence=item.get("issue_confidence", "MEDIUM").upper(),
                        file_path=file_path,
                        line_start=line,
                        line_end=line,
                        evidence_redacted=item.get("code", "").strip(),
                        remediation=item.get("more_info", "Follow secure coding practices."),
                        scanner_name="bandit",
                        scanner_version="1.9.4",
                        is_blocking=sev in ("CRITICAL", "HIGH"),
                        status="ACTIVE",
                    )
                )
        except Exception as exc:
            logger.warning(f"[source_scanner] Bandit scan failed or timed out: {exc}")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        return findings
