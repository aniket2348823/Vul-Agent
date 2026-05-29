"""
Skill ingestion loader (Architecture §5.3.1, §5.3.6)
================================================================================
Skill ingestion pipeline:
  repo -> scanner -> metadata extractor -> classifier -> risk classifier
       -> agent mapper -> tool resolver -> catalog

  - Loads index.json when present.
  - Scans every skills/*/SKILL.md.
  - Parses YAML frontmatter + markdown body.
  - Normalizes into SkillMeta, classifies domain + risk, maps to agents/tools.
  - Caches compiled metadata in the catalog. Source files stay READ-ONLY.

Skill sources are discovered from configured roots (workspace `.agents/skills`,
optional external roots). LLM prompt snippets are generated at runtime only.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

from backend.skills.catalog import SkillCatalog, SkillMeta, skill_catalog
from backend.skills.classifier import (
    classify_domain, classify_risk, is_offensive, needs_network,
)
from backend.skills.mapper import agents_for_domain, map_required_tools
from backend.skills.policy import PromotionState, RiskClass

logger = logging.getLogger("vigilagent.skills.loader")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Default skill roots (Architecture §5.3 important source folders).
_DEFAULT_ROOTS = [
    _PROJECT_ROOT / ".agents" / "skills",
    _PROJECT_ROOT / "generated_skills",
]

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Split a SKILL.md file into (frontmatter dict, body)."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text, body = parts[1], parts[2]
            if yaml is not None:
                try:
                    fm = yaml.safe_load(fm_text) or {}
                    if isinstance(fm, dict):
                        return fm, body
                except Exception:
                    pass
    return {}, content


def _meta_from_skill_md(path: Path) -> Optional[SkillMeta]:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Could not read skill %s: %s", path, exc)
        return None

    fm, body = _parse_frontmatter(content)
    name = str(fm.get("name") or path.parent.name)
    description = str(fm.get("description") or "")
    metadata = fm.get("metadata", {}) if isinstance(fm.get("metadata"), dict) else {}
    abstract = str(metadata.get("abstract") or "")
    goal = description.split(".")[0] if description else name

    # Text corpus used for classification (frontmatter + body head).
    corpus = " ".join([name, description, abstract, body[:2000]])

    domain = classify_domain(corpus)
    risk = classify_risk(corpus)
    offensive = is_offensive(corpus)
    network = needs_network(corpus)

    skill_id = _slugify(name)
    meta = SkillMeta(
        skill_id=skill_id,
        name=name,
        goal=goal,
        domain=domain,
        description=description,
        source_path=str(path),
        required_tools=map_required_tools(corpus),
        risk_class=risk,
        offensive=offensive,
        requires_network=network,
        changes_remote_state=risk in (RiskClass.INTRUSIVE_VALIDATION, RiskClass.DISABLED_BY_DEFAULT),
        requires_approval=risk in (RiskClass.INTRUSIVE_VALIDATION,),
        attack=list(metadata.get("attack", []) or fm.get("attack", []) or []),
        owasp=list(metadata.get("owasp", []) or fm.get("owasp", []) or []),
        nist=list(metadata.get("nist", []) or fm.get("nist", []) or []),
        agent_targets=agents_for_domain(domain),
        promotion_state=PromotionState.ACTIVE if str(path).find("generated_skills") == -1 else PromotionState.CANDIDATE,
        version=str(metadata.get("version") or fm.get("version") or "1.0.0"),
        author=str(metadata.get("author") or fm.get("author") or ""),
        raw_frontmatter=fm,
    )
    return meta


class SkillLoader:
    """Scans skill roots and populates the catalog (Architecture §5.3.1)."""

    def __init__(self, roots: list[Path] | None = None, catalog: SkillCatalog | None = None) -> None:
        self.roots = roots or _DEFAULT_ROOTS
        self.catalog = catalog or skill_catalog

    def load_all(self) -> int:
        """Ingest every SKILL.md under the configured roots. Returns count."""
        count = 0
        for root in self.roots:
            if not root.exists():
                continue
            # Optional index.json (Architecture §5.3 / §5.3.6).
            index = root / "index.json"
            if index.exists():
                self._load_index(index)
            for skill_md in root.rglob("SKILL.md"):
                meta = _meta_from_skill_md(skill_md)
                if meta:
                    self.catalog.upsert(meta)
                    count += 1
        logger.info("[SkillLoader] ingested %d skills into catalog", count)
        return count

    def _load_index(self, index_path: Path) -> None:
        try:
            data = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            return
        # index.json may carry ATT&CK/OWASP mappings keyed by skill name; we
        # merge those into any matching catalog entries after loading.
        self._pending_index = data if isinstance(data, dict) else {}


# Global loader.
skill_loader = SkillLoader()


def ingest_skills() -> int:
    """Convenience entrypoint to (re)build the skill catalog."""
    return skill_loader.load_all()
