"""
PROBLEM 18 FIX: Lambda Agent — PRE-CODE SCANNER
Detects vulnerabilities in source code before deployment.
Layer 1: Regex pattern scan (fast, broad)
Layer 2: AST deep scan (Python only, structural analysis)
"""

import ast
import re
import time
from typing import List, Dict


class LambdaAgent:
    """PRE-CODE SCANNER — Detects vulnerabilities in source code before deployment."""

    PATTERNS = [
        {
            "type": "SQL Injection",
            "pattern": r'(execute|cursor\.execute)\s*\(\s*["\'].*[\+%]',
            "message": "String concatenation in SQL query. Use parameterized queries.",
            "severity": "CRITICAL"
        },
        {
            "type": "Hardcoded Secret",
            "pattern": r'(password|secret|api_key|token|key)\s*=\s*["\'][^"\']{6,}["\']',
            "message": "Hardcoded secret detected. Use environment variables.",
            "severity": "HIGH"
        },
        {
            "type": "Command Injection",
            "pattern": r'(os\.system|subprocess\.call|subprocess\.run)\s*\(.*shell\s*=\s*True',
            "message": "shell=True with dynamic input enables command injection.",
            "severity": "CRITICAL"
        },
        {
            "type": "Insecure Deserialization",
            "pattern": r'pickle\.loads\s*\(|yaml\.load\s*\([^,)]+\)',
            "message": "Unsafe deserialization. Use pickle with caution or yaml.safe_load.",
            "severity": "HIGH"
        },
        {
            "type": "XSS Risk",
            "pattern": r'render_template_string\s*\(.*request\.',
            "message": "User input in template render — potential XSS.",
            "severity": "HIGH"
        },
        {
            "type": "Path Traversal",
            "pattern": r'open\s*\(\s*.*request\.',
            "message": "User input in file open — path traversal risk.",
            "severity": "HIGH"
        },
        {
            "type": "Weak Crypto",
            "pattern": r'hashlib\.md5|hashlib\.sha1',
            "message": "MD5/SHA1 are cryptographically broken. Use SHA-256 or better.",
            "severity": "MEDIUM"
        },
        {
            "type": "Debug Mode",
            "pattern": r'debug\s*=\s*True|DEBUG\s*=\s*True',
            "message": "Debug mode enabled. Disable before production.",
            "severity": "MEDIUM"
        },
        {
            "type": "SSRF Risk",
            "pattern": r'requests\.(get|post|put|delete)\s*\(\s*.*request\.',
            "message": "User input directly in HTTP request — potential SSRF.",
            "severity": "HIGH"
        },
        {
            "type": "Insecure Random",
            "pattern": r'random\.random\(\)|random\.randint\(',
            "message": "Using non-cryptographic random for security-sensitive operation. Use secrets module.",
            "severity": "MEDIUM"
        },
    ]

    def __init__(self, agent_id: str = "agent_lambda", bus=None):
        self.agent_id = agent_id
        self.bus = bus

    async def analyze(self, code: str, language: str = "python") -> List[Dict]:
        """Analyze source code for security vulnerabilities."""
        findings = []
        lines = code.split("\n")

        # Layer 1 — Regex pattern scan (all languages)
        for i, line in enumerate(lines, start=1):
            for rule in self.PATTERNS:
                if re.search(rule["pattern"], line, re.IGNORECASE):
                    findings.append({
                        "line": i,
                        "type": rule["type"],
                        "message": rule["message"],
                        "severity": rule["severity"],
                        "code_snippet": line.strip()[:120],
                        "source": "regex"
                    })

        # Layer 2 — AST deep scan (Python only)
        if language == "python":
            try:
                tree = ast.parse(code)
                findings.extend(self._ast_scan(tree))
            except SyntaxError:
                pass  # incomplete code while typing — skip silently

        # Deduplicate by (line, type)
        seen = set()
        unique = []
        for f in findings:
            key = (f["line"], f["type"])
            if key not in seen:
                seen.add(key)
                unique.append(f)

        return unique

    def _ast_scan(self, tree) -> List[Dict]:
        """Deep structural analysis of Python AST."""
        findings = []
        for node in ast.walk(tree):
            # eval() / exec() usage
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ["eval", "exec"]:
                    findings.append({
                        "line": node.lineno,
                        "type": "Code Injection",
                        "message": f"{node.func.id}() with dynamic input is dangerous.",
                        "severity": "CRITICAL",
                        "code_snippet": f"{node.func.id}() at line {node.lineno}",
                        "source": "ast"
                    })
                # __import__ usage
                if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                    findings.append({
                        "line": node.lineno,
                        "type": "Dynamic Import",
                        "message": "__import__() can be used for code injection. Use importlib instead.",
                        "severity": "MEDIUM",
                        "code_snippet": f"__import__() at line {node.lineno}",
                        "source": "ast"
                    })

            # Assert usage (disabled in optimized Python)
            if isinstance(node, ast.Assert):
                findings.append({
                    "line": node.lineno,
                    "type": "Unreliable Security Check",
                    "message": "assert statements are disabled with python -O. Do not use for security checks.",
                    "severity": "MEDIUM",
                    "code_snippet": f"assert at line {node.lineno}",
                    "source": "ast"
                })

            # Global variable assignments of sensitive names
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.upper() in ["PASSWORD", "SECRET_KEY", "API_KEY", "TOKEN"]:
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            findings.append({
                                "line": node.lineno,
                                "type": "Hardcoded Secret (AST)",
                                "message": f"Sensitive variable '{target.id}' assigned a string literal.",
                                "severity": "HIGH",
                                "code_snippet": f"{target.id} = '...' at line {node.lineno}",
                                "source": "ast"
                            })

        return findings
