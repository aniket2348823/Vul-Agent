"""
SKILL LIBRARY
Persistent storage and management for agent skills.

This library:
1. CRUD operations for skills
2. Version control and skill evolution tracking
3. Skill search by type, confidence, tags
4. Skill validation and safety checks
5. Skill deprecation and lifecycle management
6. Import/export for skill sharing
"""

import time
import logging
import json
import shutil
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import asdict, dataclass, field

from backend.core.skill_extractor import Skill

logger = logging.getLogger("SkillLibrary")


@dataclass
class BrowserSkill:
    """Browser-specific skill with execution requirements"""
    skill_id: str
    name: str
    skill_type: str
    execution_context: str  # "browser_required", "http_only", "hybrid"
    browser_requirements: Dict[str, Any] = field(default_factory=dict)
    workflow_steps: List[Dict[str, Any]] = field(default_factory=list)
    evidence_requirements: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    required_capabilities: frozenset = field(default_factory=frozenset)
    success_rate: float = 0.0
    usage_count: int = 0
    confidence: float = 0.5
    deprecated: bool = False
    deprecation_reason: str = ""
    created_at: float = 0.0
    last_updated: float = 0.0
    tags: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)


class SkillLibrary:
    """
    Manages persistent storage and retrieval of agent skills.
    """
    
    def __init__(self, brain_dir: str = "brain"):
        self.brain_dir = Path(brain_dir)
        self.skills_dir = self.brain_dir / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        # Create category directories
        self.categories = ["payload", "endpoint", "chain", "evasion"]
        for category in self.categories:
            (self.skills_dir / category).mkdir(exist_ok=True)
        
        # Metadata index
        self.metadata_file = self.skills_dir / "metadata.json"
        self.metadata: Dict[str, Dict[str, Any]] = {}
        
        # Browser skill indexes
        self.capability_index: Dict[str, set] = {}  # capability -> set of skill_ids
        self.context_index: Dict[str, set] = {}  # context -> set of skill_ids
        self.framework_index: Dict[str, set] = {}  # framework -> set of skill_ids
        self.version_tracking: Dict[str, List[str]] = {}  # skill_name -> list of versions
        
        self._load_metadata()
        self._rebuild_indexes()
    
    def _load_metadata(self):
        """Load skill metadata index."""
        if self.metadata_file.exists():
            try:
                self.metadata = json.loads(self.metadata_file.read_text(encoding="utf-8"))
                logger.info(f"[SkillLibrary] Loaded {len(self.metadata)} skills from metadata")
            except Exception as e:
                logger.error(f"[SkillLibrary] Failed to load metadata: {e}")
                self.metadata = {}
        else:
            self.metadata = {}
    
    def _rebuild_indexes(self):
        """Rebuild indexes - implemented in extension"""
        pass
    
    def _save_metadata(self):
        """Save skill metadata index."""
        try:
            self.metadata_file.write_text(
                json.dumps(self.metadata, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"[SkillLibrary] Failed to save metadata: {e}")
    
    def add_skill(self, skill: Skill) -> bool:
        """
        Add a new skill to the library.
        Returns True if successful.
        """
        try:
            # Check if skill already exists
            if skill.skill_id in self.metadata:
                logger.warning(f"[SkillLibrary] Skill {skill.skill_id} already exists")
                return False
            
            # Determine category directory
            category = self._get_category(skill.skill_type)
            skill_file = self.skills_dir / category / f"{skill.skill_id}.json"
            
            # Save skill to file
            skill_file.write_text(
                json.dumps(asdict(skill), indent=2),
                encoding="utf-8"
            )
            
            # Update metadata index
            self.metadata[skill.skill_id] = {
                "name": skill.name,
                "skill_type": skill.skill_type,
                "confidence": skill.confidence,
                "success_rate": skill.success_rate,
                "version": skill.version,
                "created_at": skill.created_at,
                "tags": skill.tags,
                "file_path": str(skill_file.relative_to(self.skills_dir))
            }
            
            self._save_metadata()
            
            logger.info(f"[SkillLibrary] Added skill: {skill.name} ({skill.skill_id})")
            return True
            
        except Exception as e:
            logger.error(f"[SkillLibrary] Failed to add skill: {e}")
            return False
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """
        Retrieve a skill by ID.
        Returns None if not found.
        """
        if skill_id not in self.metadata:
            return None
        
        try:
            file_path = self.skills_dir / self.metadata[skill_id]["file_path"]
            skill_data = json.loads(file_path.read_text(encoding="utf-8"))
            return Skill(**skill_data)
        except Exception as e:
            logger.error(f"[SkillLibrary] Failed to load skill {skill_id}: {e}")
            return None
    
    def update_skill(self, skill: Skill) -> bool:
        """
        Update an existing skill.
        Increments version number.
        """
        if skill.skill_id not in self.metadata:
            logger.warning(f"[SkillLibrary] Cannot update non-existent skill {skill.skill_id}")
            return False
        
        try:
            # Increment version
            version_parts = skill.version.split(".")
            version_parts[-1] = str(int(version_parts[-1]) + 1)
            skill.version = ".".join(version_parts)
            skill.last_updated = time.time()
            
            # Save updated skill
            file_path = self.skills_dir / self.metadata[skill.skill_id]["file_path"]
            file_path.write_text(
                json.dumps(asdict(skill), indent=2),
                encoding="utf-8"
            )
            
            # Update metadata
            self.metadata[skill.skill_id].update({
                "confidence": skill.confidence,
                "success_rate": skill.success_rate,
                "version": skill.version,
                "last_updated": skill.last_updated
            })
            
            self._save_metadata()
            
            logger.info(f"[SkillLibrary] Updated skill: {skill.name} to v{skill.version}")
            return True
            
        except Exception as e:
            logger.error(f"[SkillLibrary] Failed to update skill: {e}")
            return False
    
    def delete_skill(self, skill_id: str) -> bool:
        """
        Delete a skill from the library.
        """
        if skill_id not in self.metadata:
            return False
        
        try:
            # Delete file
            file_path = self.skills_dir / self.metadata[skill_id]["file_path"]
            if file_path.exists():
                file_path.unlink()
            
            # Remove from metadata
            del self.metadata[skill_id]
            self._save_metadata()
            
            logger.info(f"[SkillLibrary] Deleted skill: {skill_id}")
            return True
            
        except Exception as e:
            logger.error(f"[SkillLibrary] Failed to delete skill: {e}")
            return False
    
    def search_skills(
        self,
        skill_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        min_success_rate: Optional[float] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Skill]:
        """
        Search for skills matching criteria.
        """
        results = []
        
        for skill_id, meta in self.metadata.items():
            # Apply filters
            if skill_type and meta["skill_type"] != skill_type:
                continue
            
            if min_confidence and meta["confidence"] < min_confidence:
                continue
            
            if min_success_rate and meta["success_rate"] < min_success_rate:
                continue
            
            if tags:
                skill_tags = set(meta.get("tags", []))
                if not any(tag in skill_tags for tag in tags):
                    continue
            
            # Load full skill
            skill = self.get_skill(skill_id)
            if skill:
                results.append(skill)
            
            if len(results) >= limit:
                break
        
        # Sort by confidence
        results.sort(key=lambda s: s.confidence, reverse=True)
        
        return results
    
    def get_all_skills(self) -> List[Skill]:
        """Get all skills in the library."""
        skills = []
        for skill_id in self.metadata.keys():
            skill = self.get_skill(skill_id)
            if skill:
                skills.append(skill)
        return skills
    
    def get_skills_by_type(self, skill_type: str) -> List[Skill]:
        """Get all skills of a specific type."""
        return self.search_skills(skill_type=skill_type, limit=1000)
    
    def get_top_skills(self, limit: int = 10) -> List[Skill]:
        """Get top skills by confidence and success rate."""
        all_skills = self.get_all_skills()
        
        # Sort by combined score
        all_skills.sort(
            key=lambda s: (s.confidence * 0.5 + s.success_rate * 0.5),
            reverse=True
        )
        
        return all_skills[:limit]

    def get_recommendations(
        self,
        *,
        target_url: Optional[str] = None,
        vuln_class: Optional[str] = None,
        skill_type: Optional[str] = None,
        min_confidence: float = 0.5,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Return ranked skill recommendations for planning.

        This is the READ path required by Architecture §6.7 and §29.2: Omega,
        Sigma, Beta, Gamma, Kappa, and the Planner query this before forming a
        plan (not only when stuck). Results are scored by confidence and
        historical success rate and returned as plain dicts so any consumer can
        use them without importing the Skill type.
        """
        candidates = self.search_skills(skill_type=skill_type, min_confidence=min_confidence, limit=1000)
        recs: List[Dict[str, Any]] = []
        needle = (vuln_class or skill_type or "").lower()
        target = (target_url or "").lower()
        for skill in candidates:
            score = (getattr(skill, "confidence", 0.5) * 0.5
                     + getattr(skill, "success_rate", 0.0) * 0.5)
            text = f"{getattr(skill, 'name', '')} {getattr(skill, 'description', '')} {getattr(skill, 'skill_type', '')}".lower()
            # Light relevance boost when the recommendation matches the query.
            if needle and needle in text:
                score += 0.25
            if target and target in text:
                score += 0.1
            recs.append({
                "skill_id": getattr(skill, "skill_id", ""),
                "name": getattr(skill, "name", ""),
                "skill_type": getattr(skill, "skill_type", ""),
                "description": getattr(skill, "description", ""),
                "confidence": getattr(skill, "confidence", 0.5),
                "success_rate": getattr(skill, "success_rate", 0.0),
                "score": round(score, 4),
            })
        recs.sort(key=lambda r: r["score"], reverse=True)
        return recs[:limit]
    
    def deprecate_skill(self, skill_id: str, reason: str) -> bool:
        """
        Mark a skill as deprecated.
        """
        skill = self.get_skill(skill_id)
        if not skill:
            return False
        
        # Add deprecation info to parameters
        skill.parameters["deprecated"] = True
        skill.parameters["deprecation_reason"] = reason
        skill.parameters["deprecated_at"] = time.time()
        
        return self.update_skill(skill)
    
    def export_skill(self, skill_id: str, export_path: str) -> bool:
        """
        Export a skill to a file for sharing.
        """
        skill = self.get_skill(skill_id)
        if not skill:
            return False
        
        try:
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            export_data = {
                "skill": asdict(skill),
                "exported_at": time.time(),
                "exported_from": "Antigravity V6"
            }
            
            export_file.write_text(
                json.dumps(export_data, indent=2),
                encoding="utf-8"
            )
            
            logger.info(f"[SkillLibrary] Exported skill {skill_id} to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"[SkillLibrary] Failed to export skill: {e}")
            return False
    
    def import_skill(self, import_path: str) -> Optional[str]:
        """
        Import a skill from a file.
        Returns skill_id if successful.
        """
        try:
            import_file = Path(import_path)
            if not import_file.exists():
                logger.error(f"[SkillLibrary] Import file not found: {import_path}")
                return None
            
            import_data = json.loads(import_file.read_text(encoding="utf-8"))
            skill_data = import_data.get("skill")
            
            if not skill_data:
                logger.error(f"[SkillLibrary] Invalid import file format")
                return None
            
            skill = Skill(**skill_data)
            
            # Reset usage stats for imported skill
            skill.times_used = 0
            skill.times_successful = 0
            skill.created_at = time.time()
            skill.last_updated = time.time()
            
            if self.add_skill(skill):
                logger.info(f"[SkillLibrary] Imported skill: {skill.name}")
                return skill.skill_id
            
            return None
            
        except Exception as e:
            logger.error(f"[SkillLibrary] Failed to import skill: {e}")
            return None
    
    def record_skill_usage(self, skill_id: str, success: bool):
        """
        Record usage of a skill for tracking effectiveness.
        """
        skill = self.get_skill(skill_id)
        if not skill:
            return
        
        skill.times_used += 1
        if success:
            skill.times_successful += 1
        
        # Update success rate
        if skill.times_used > 0:
            skill.success_rate = skill.times_successful / skill.times_used
        
        self.update_skill(skill)
    
    def _get_category(self, skill_type: str) -> str:
        """Get category directory for skill type."""
        if "payload" in skill_type:
            return "payload"
        elif "endpoint" in skill_type:
            return "endpoint"
        elif "chain" in skill_type:
            return "chain"
        elif "evasion" in skill_type:
            return "evasion"
        else:
            return "payload"  # Default
    
    def get_library_stats(self) -> Dict[str, Any]:
        """Get statistics about the skill library."""
        all_skills = self.get_all_skills()
        
        by_type = {}
        for skill in all_skills:
            by_type[skill.skill_type] = by_type.get(skill.skill_type, 0) + 1
        
        total_usage = sum(s.times_used for s in all_skills)
        total_success = sum(s.times_successful for s in all_skills)
        
        return {
            "total_skills": len(all_skills),
            "by_type": by_type,
            "total_usage": total_usage,
            "total_success": total_success,
            "overall_success_rate": total_success / total_usage if total_usage > 0 else 0.0,
            "avg_confidence": sum(s.confidence for s in all_skills) / len(all_skills) if all_skills else 0.0,
            "timestamp": time.time()
        }


# Global skill library instance
skill_library = SkillLibrary()


# ============================================================================
# BROWSER SKILL LIBRARY EXTENSION
# ============================================================================

class BrowserSkillLibraryExtension:
    """Extension for browser-specific skill management with indexing"""
    
    def __init__(self, skill_library: SkillLibrary):
        self.library = skill_library
    
    def _rebuild_indexes(self):
        """Rebuild all indexes from metadata"""
        self.library.capability_index.clear()
        self.library.context_index.clear()
        self.library.framework_index.clear()
        self.library.version_tracking.clear()
        
        for skill_id, meta in self.library.metadata.items():
            # Index by capabilities
            caps = meta.get("required_capabilities", [])
            if isinstance(caps, (list, set)):
                for cap in caps:
                    if cap not in self.library.capability_index:
                        self.library.capability_index[cap] = set()
                    self.library.capability_index[cap].add(skill_id)
            
            # Index by execution context
            context = meta.get("execution_context")
            if context:
                if context not in self.library.context_index:
                    self.library.context_index[context] = set()
                self.library.context_index[context].add(skill_id)
            
            # Index by framework
            browser_reqs = meta.get("browser_requirements", {})
            framework = browser_reqs.get("framework") if isinstance(browser_reqs, dict) else None
            if framework:
                if framework not in self.library.framework_index:
                    self.library.framework_index[framework] = set()
                self.library.framework_index[framework].add(skill_id)
            
            # Track versions
            name = meta.get("name", "")
            version = meta.get("version", "1.0.0")
            if name:
                if name not in self.library.version_tracking:
                    self.library.version_tracking[name] = []
                if version not in self.library.version_tracking[name]:
                    self.library.version_tracking[name].append(version)
    
    def add_browser_skill(
        self,
        skill: BrowserSkill,
        context_requirements: Dict[str, Any]
    ) -> bool:
        """
        Add a browser skill to the library with indexing.
        Returns True if successful.
        """
        try:
            # Validate version format (semver)
            version_parts = skill.version.split(".")
            if len(version_parts) != 3 or not all(p.isdigit() for p in version_parts):
                logger.error(f"[SkillLibrary] Invalid version format: {skill.version}")
                return False
            
            # Check for duplicates
            if skill.skill_id in self.library.metadata:
                logger.warning(f"[SkillLibrary] Browser skill {skill.skill_id} already exists")
                return False
            
            # Determine category directory
            category = self.library._get_category(skill.skill_type)
            skill_file = self.library.skills_dir / category / f"{skill.skill_id}.json"
            
            # Save skill to file
            skill_file.write_text(
                json.dumps(asdict(skill), indent=2, default=str),
                encoding="utf-8"
            )
            
            # Update metadata index
            self.library.metadata[skill.skill_id] = {
                "name": skill.name,
                "skill_type": skill.skill_type,
                "execution_context": skill.execution_context,
                "browser_requirements": skill.browser_requirements,
                "required_capabilities": list(skill.required_capabilities),
                "confidence": skill.confidence,
                "success_rate": skill.success_rate,
                "version": skill.version,
                "deprecated": skill.deprecated,
                "created_at": skill.created_at or time.time(),
                "tags": skill.tags + ["browser_automation"],
                "file_path": str(skill_file.relative_to(self.library.skills_dir))
            }
            
            # Update indexes
            for cap in skill.required_capabilities:
                if cap not in self.library.capability_index:
                    self.library.capability_index[cap] = set()
                self.library.capability_index[cap].add(skill.skill_id)
            
            if skill.execution_context:
                if skill.execution_context not in self.library.context_index:
                    self.library.context_index[skill.execution_context] = set()
                self.library.context_index[skill.execution_context].add(skill.skill_id)
            
            framework = skill.browser_requirements.get("framework")
            if framework:
                if framework not in self.library.framework_index:
                    self.library.framework_index[framework] = set()
                self.library.framework_index[framework].add(skill.skill_id)
            
            # Track version
            if skill.name not in self.library.version_tracking:
                self.library.version_tracking[skill.name] = []
            if skill.version not in self.library.version_tracking[skill.name]:
                self.library.version_tracking[skill.name].append(skill.version)
            
            self.library._save_metadata()
            
            logger.info(f"[SkillLibrary] Added browser skill: {skill.name} ({skill.skill_id})")
            return True
            
        except Exception as e:
            logger.error(f"[SkillLibrary] Failed to add browser skill: {e}")
            return False
    
    def search_browser_skills(
        self,
        agent_capabilities: List[str],
        context: Optional[str] = None,
        framework: Optional[str] = None,
        limit: int = 50
    ) -> List[BrowserSkill]:
        """
        Search for browser skills matching criteria using indexes.
        Returns skills that match agent capabilities.
        """
        # Start with all skills
        candidate_ids = set(self.library.metadata.keys())
        
        # Filter by context if provided
        if context and context in self.library.context_index:
            candidate_ids &= self.library.context_index[context]
        
        # Filter by framework if provided
        if framework and framework in self.library.framework_index:
            candidate_ids &= self.library.framework_index[framework]
        
        # Filter by capabilities (skill capabilities must be subset of agent capabilities)
        agent_caps_set = set(agent_capabilities)
        matching_skills = []
        
        for skill_id in candidate_ids:
            meta = self.library.metadata[skill_id]
            
            # Skip deprecated skills
            if meta.get("deprecated", False):
                continue
            
            # Check if skill capabilities are subset of agent capabilities
            skill_caps = set(meta.get("required_capabilities", []))
            if skill_caps.issubset(agent_caps_set):
                # Load full skill
                skill_file = self.library.skills_dir / meta["file_path"]
                try:
                    skill_data = json.loads(skill_file.read_text(encoding="utf-8"))
                    # Convert to BrowserSkill if it has browser fields
                    if "execution_context" in skill_data:
                        # Convert required_capabilities back to frozenset
                        if "required_capabilities" in skill_data:
                            skill_data["required_capabilities"] = frozenset(skill_data["required_capabilities"])
                        skill = BrowserSkill(**skill_data)
                        matching_skills.append(skill)
                except Exception as e:
                    logger.error(f"[SkillLibrary] Failed to load skill {skill_id}: {e}")
            
            if len(matching_skills) >= limit:
                break
        
        # Sort by success rate and usage
        matching_skills.sort(
            key=lambda s: (s.success_rate * 0.6 + (s.usage_count / 100) * 0.4),
            reverse=True
        )
        
        return matching_skills[:limit]
    
    def compose_workflows(
        self,
        workflow_skills: List[BrowserSkill]
    ) -> Optional[BrowserSkill]:
        """
        Compose multiple workflow skills into a single composed skill.
        Returns composed skill or None if incompatible.
        """
        if not workflow_skills:
            return None
        
        # Validate all are workflows
        for skill in workflow_skills:
            if not skill.workflow_steps:
                logger.error(f"[SkillLibrary] Skill {skill.name} is not a workflow")
                return None
        
        # Check compatibility (all must have compatible browser requirements)
        base_reqs = workflow_skills[0].browser_requirements
        for skill in workflow_skills[1:]:
            if skill.browser_requirements.get("framework") != base_reqs.get("framework"):
                logger.error(f"[SkillLibrary] Incompatible frameworks in workflow composition")
                return None
        
        # Merge workflow steps
        all_steps = []
        for skill in workflow_skills:
            all_steps.extend(skill.workflow_steps)
        
        # Merge success conditions
        all_conditions = []
        for skill in workflow_skills:
            if "success_conditions" in skill.parameters:
                all_conditions.extend(skill.parameters["success_conditions"])
        
        # Merge browser requirements
        merged_reqs = base_reqs.copy()
        for skill in workflow_skills:
            for key, value in skill.browser_requirements.items():
                if key == "stealth" or key == "session":
                    # Use OR logic for boolean requirements
                    merged_reqs[key] = merged_reqs.get(key, False) or value
                else:
                    merged_reqs[key] = value
        
        # Merge capabilities
        all_caps = set()
        for skill in workflow_skills:
            all_caps.update(skill.required_capabilities)
        
        # Create composed skill
        composed = BrowserSkill(
            skill_id=f"composed_{'_'.join(s.skill_id[:8] for s in workflow_skills)}",
            name=f"Composed: {' + '.join(s.name for s in workflow_skills)}",
            skill_type="composed_workflow",
            execution_context="browser_required",
            browser_requirements=merged_reqs,
            workflow_steps=all_steps,
            version="1.0.0",
            required_capabilities=frozenset(all_caps),
            success_rate=min(s.success_rate for s in workflow_skills),
            confidence=min(s.confidence for s in workflow_skills),
            created_at=time.time(),
            tags=["composed", "workflow"],
            parameters={"success_conditions": all_conditions}
        )
        
        logger.info(f"[SkillLibrary] Composed workflow from {len(workflow_skills)} skills")
        return composed
    
    def deprecate_skill(
        self,
        skill_id: str,
        reason: str,
        migration_path: Optional[str] = None
    ) -> bool:
        """
        Mark a skill as deprecated.
        """
        if skill_id not in self.library.metadata:
            return False
        
        # Update metadata
        self.library.metadata[skill_id]["deprecated"] = True
        self.library.metadata[skill_id]["deprecation_reason"] = reason
        if migration_path:
            self.library.metadata[skill_id]["migration_path"] = migration_path
        
        self.library._save_metadata()
        
        logger.info(f"[SkillLibrary] Deprecated skill {skill_id}: {reason}")
        return True


# Create global browser skill library extension
browser_skill_library = BrowserSkillLibraryExtension(skill_library)
