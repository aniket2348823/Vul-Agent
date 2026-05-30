"""Parser for masscan JSON output (-oJ).

masscan -oJ emits a JSON array of records:
  [{"ip":"1.2.3.4","ports":[{"port":443,"proto":"tcp","status":"open"}]}, ...]
"""
from __future__ import annotations
from pathlib import Path

from backend.parsers.recon.base import ParsedEntity, safe_json_file, safe_lines


def parse_masscan_json(path: Path | str) -> list[ParsedEntity]:
    entities: list[ParsedEntity] = []
    seen: set[str] = set()
    data = safe_json_file(path)
    records = data if isinstance(data, list) else data.get("results", []) if isinstance(data, dict) else []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        ip = str(rec.get("ip", "")).strip()
        for p in rec.get("ports", []) or []:
            try:
                port = int(p.get("port", 0) or 0)
            except (ValueError, TypeError):
                continue
            if not ip or not port:
                continue
            key = f"{ip}:{port}"
            if key in seen:
                continue
            seen.add(key)
            entities.append(ParsedEntity(
                kind="open_port", label=key, confidence=0.9,
                properties={"host": ip, "port": port,
                            "protocol": str(p.get("proto", "tcp")),
                            "status": str(p.get("status", "open"))},
                source_tool="masscan", phase="dns_infrastructure"))
    return entities
