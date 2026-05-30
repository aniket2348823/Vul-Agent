"""Parser for dalfox JSON output (--format json).

dalfox emits a JSON array of PoC objects:
  [{"type":"V","inject_type":"inHTML","poc":"http://host?q=<script>","param":"q",
    "severity":"High","cwe":"CWE-79","message_str":"..."}]
Confirmed reflected/DOM XSS becomes a vulnerability candidate.
"""
from __future__ import annotations
from pathlib import Path
from urllib.parse import urlparse

from backend.parsers.recon.base import ParsedEntity, safe_json_file, safe_json_lines


def parse_dalfox_json(path: Path | str) -> list[ParsedEntity]:
    entities: list[ParsedEntity] = []
    data = safe_json_file(path)
    rows = data if isinstance(data, list) else []
    if not rows:
        # dalfox can also stream JSONL
        rows = list(safe_json_lines(path))
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        poc = str(row.get("poc", row.get("data", ""))).strip()
        param = str(row.get("param", ""))
        if not poc or poc in seen:
            continue
        seen.add(poc)
        host = (urlparse(poc).hostname or "").lower()
        entities.append(ParsedEntity(
            kind="vulnerability_candidate", label=f"XSS:{param}@{host}" if param else f"XSS@{host}",
            confidence=0.7,
            properties={"vuln_type": "xss", "poc": poc, "param": param,
                        "inject_type": str(row.get("inject_type", "")),
                        "severity": str(row.get("severity", "")),
                        "cwe": str(row.get("cwe", "CWE-79")),
                        "host": host, "source": "dalfox"},
            source_tool="dalfox", phase="template_validation"))
    return entities
