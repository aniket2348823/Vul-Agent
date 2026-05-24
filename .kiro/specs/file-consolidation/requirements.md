# File Consolidation - Requirements

## Overview

After comprehensive analysis of the Antigravity V5 codebase, this specification identifies opportunities to merge, consolidate, and eliminate redundant files to improve maintainability, reduce confusion, and streamline the project structure.

## 1. Spec Documentation Consolidation

### 1.1 Redundant Status Documentation

**Current State:**
The `.kiro/specs/openclaw-integration/` directory contains 5 overlapping status/summary documents:
- `FINAL_IMPLEMENTATION_STATUS.md`
- `FINAL_STATUS.md`
- `IMPLEMENTATION_COMPLETE.md`
- `IMPLEMENTATION_SUMMARY.md`
- `PHASE1_COMPLETE.md`

**Problem:**
- All documents describe the same implementation completion status
- Significant content duplication (80%+ overlap)
- Confusing for developers to know which document is authoritative
- Maintenance burden when updating status

**Acceptance Criteria:**
- [ ] Merge all 5 status documents into a single `STATUS.md` file
- [ ] Single source of truth for implementation status
- [ ] Preserve all unique information from each document
- [ ] Include clear sections: Executive Summary, Phase Status, Metrics, Next Steps
- [ ] Delete redundant files after merge

### 1.2 Consolidate Spec Documentation

**Current State:**
- `CODEBASE_AUDIT.md` - Contains audit findings and recommendations
- `DEEP_INTEGRATION_SUMMARY.md` - Contains agent-by-agent integration details
- `README.md` - Contains overview and quick start

**Problem:**
- Some overlap between audit and integration summary
- README duplicates information from other docs

**Acceptance Criteria:**
- [ ] Keep `README.md` as entry point (overview, quick start, links)
- [ ] Merge `CODEBASE_AUDIT.md` findings into `STATUS.md` (current state section)
- [ ] Keep `DEEP_INTEGRATION_SUMMARY.md` as detailed reference
- [ ] Ensure no duplication between files
- [ ] Each file has clear, distinct purpose

## 2. Test File Organization

### 2.1 Consolidate TestSprite Tests

**Current State:**
The `testsprite_tests/` directory contains 50+ test files with inconsistent naming:
- `TC001_*.py` through `TC011_*.py` (numbered test cases)
- `test_*.py` (pytest-style tests)
- Multiple output files (`.txt`, `.md`)
- Duplicate test implementations

**Problem:**
- Difficult to navigate and find specific tests
- Inconsistent naming conventions
- Test duplication
- Output files mixed with test code

**Acceptance Criteria:**
- [ ] Group tests by functional area (api, agents, integration, e2e)
- [ ] Standardize naming: `test_<area>_<feature>.py`
- [ ] Move output files to `testsprite_tests/output/` subdirectory
- [ ] Identify and merge duplicate tests
- [ ] Create test suite organization document

### 2.2 Merge Core Test Files

**Current State:**
- `backend/core/test_browser_infrastructure.py`
- `backend/core/test_browser_optimization.py`

**Problem:**
- Both test browser-related functionality
- Could be organized better

**Acceptance Criteria:**
- [ ] Keep separate if testing distinct components
- [ ] OR merge into `backend/core/tests/` directory with multiple files
- [ ] Ensure clear test organization
- [ ] Add test discovery configuration

## 3. Planning Documentation

### 3.1 Consolidate Planning Files

**Current State:**
Root directory contains multiple planning documents:
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `implementation_plan_alpha_singularity_v6.md`
- `implementation_plan_deep_v2.md`
- `STARTUP_REBUILD_AND_ALPHA_IMPLEMENTATION_PLAN.md`
- `system_blueprint.md`
- `architects_bible.md`

**Problem:**
- Multiple overlapping implementation plans
- Unclear which is current/authoritative
- Historical documents mixed with current plans

**Acceptance Criteria:**
- [ ] Archive old implementation plans to `.planning/archive/`
- [ ] Keep only current roadmap and state in `.planning/`
- [ ] Consolidate `system_blueprint.md` and `architects_bible.md` into single architecture doc
- [ ] Clear naming: `ARCHITECTURE.md`, `ROADMAP.md`, `STATE.md`

## 4. Agent File Organization

### 4.1 Agent Version Management

**Current State:**
- `backend/agents/alpha.py` (current)
- `backend/agents/alpha_v6/` (directory with old version)

**Problem:**
- Old version directory creates confusion
- Unclear if v6 is newer or older than current

**Acceptance Criteria:**
- [ ] Archive `alpha_v6/` to `backend/agents/archive/` if not needed
- [ ] OR clearly document version relationship
- [ ] Remove if obsolete

## 5. Configuration Files

### 5.1 Environment Configuration

**Current State:**
- `.env` (actual config - gitignored)
- `.env.example` (template)

**Status:** ✅ This is correct - no changes needed

### 5.2 Project Configuration

**Current State:**
Multiple config files in root:
- `package.json` (Node.js)
- `requirements.txt` (Python root)
- `backend/requirements.txt` (Python backend)
- `pytest.ini`
- `sonar-project.properties`
- `tailwind.config.js`
- `vite.config.js`
- `postcss.config.js`

**Status:** ✅ These are all necessary - no changes needed

## 6. Output and Generated Files

### 6.1 Scan States and Reports

**Current State:**
- `scan_states/` - Contains scan state files
- `reports/` - Contains 200+ PDF reports
- `data/scans/` - Contains scan data

**Problem:**
- Potentially redundant storage
- Large number of files

**Acceptance Criteria:**
- [ ] Verify if `data/scans/` and `scan_states/` serve different purposes
- [ ] If redundant, consolidate into single directory
- [ ] Consider archiving old reports (>30 days)
- [ ] Add cleanup script for old scan data

### 6.2 Build Artifacts

**Current State:**
- `dist/` - Build output
- `node_modules/` - Dependencies
- `__pycache__/` - Python cache
- `.pytest_cache/` - Test cache

**Status:** ✅ These are standard build artifacts - ensure .gitignore is correct

## 7. Documentation Files

### 7.1 Root Documentation

**Current State:**
- `README.md` (main)
- `PROJECT.md`
- `VUL_AGENT_MANIFEST.md`
- `backend_structure.txt`
- `backend_structure_utf8.txt`

**Problem:**
- `backend_structure.txt` and `backend_structure_utf8.txt` are duplicates
- Multiple project description files

**Acceptance Criteria:**
- [ ] Remove `backend_structure.txt` (keep UTF-8 version)
- [ ] Consolidate `PROJECT.md` and `VUL_AGENT_MANIFEST.md` into `README.md` or separate docs folder
- [ ] Create `docs/` directory for detailed documentation
- [ ] Keep `README.md` as main entry point

## 8. Utility Scripts

### 8.1 Script Organization

**Current State:**
Root directory contains utility scripts:
- `fix_agents.py`
- `fix_remaining.py`
- `graphify_scan.py`
- `start_vulagent.py`
- `upgrade_agents.py`
- `verify_refactor.py`

**Problem:**
- Scripts scattered in root
- Unclear purpose of some scripts

**Acceptance Criteria:**
- [ ] Move utility scripts to `scripts/` directory
- [ ] Add README in `scripts/` explaining each script
- [ ] Remove obsolete scripts (fix_*, verify_refactor if no longer needed)

## 9. Data Files

### 9.1 Brain Data

**Current State:**
- `brain/episodes/`
- `brain/exploit_vectors.json`
- `brain/memory.json`
- `brain/notifications.json`
- `brain/semantic_patterns.json`

**Status:** ✅ Well organized - no changes needed

### 9.2 Miscellaneous Data

**Current State:**
- `graph.json`
- `keyring.json`
- `prd.json`
- `stats.json`
- `user_config.json`

**Problem:**
- Data files in root directory

**Acceptance Criteria:**
- [ ] Move to `data/` directory if not actively used by application
- [ ] OR keep in root if required by application startup
- [ ] Document purpose of each file

## 10. Legacy and Archive

### 10.1 Legacy Directory

**Current State:**
- `legacy/` directory exists but is empty

**Acceptance Criteria:**
- [ ] Move old/obsolete files to `legacy/`
- [ ] Add README explaining what's archived
- [ ] OR remove if not needed

## Summary of Consolidation Opportunities

### High Priority (Immediate Impact):
1. **Spec Documentation** - Merge 5 status files into 1 (saves confusion)
2. **Planning Docs** - Archive old plans, consolidate architecture docs
3. **Root Scripts** - Move to `scripts/` directory
4. **Duplicate Files** - Remove `backend_structure.txt`

### Medium Priority (Maintenance):
5. **Test Organization** - Reorganize testsprite tests
6. **Documentation** - Create `docs/` directory structure
7. **Agent Archives** - Clean up old agent versions

### Low Priority (Optional):
8. **Scan Data** - Consolidate scan storage if redundant
9. **Data Files** - Organize root data files
10. **Legacy** - Populate or remove legacy directory

## Success Metrics

- [ ] Reduce file count in root directory by 30%
- [ ] Reduce spec documentation files from 11 to 5
- [ ] Single source of truth for implementation status
- [ ] Clear directory structure with purpose-based organization
- [ ] Improved developer onboarding (easier to find files)
- [ ] Reduced maintenance burden (fewer files to update)

## Non-Goals

- Do NOT merge files that serve different purposes
- Do NOT consolidate configuration files (they're necessary)
- Do NOT remove build artifacts or dependencies
- Do NOT merge code files (agents, core modules, etc.)
- Focus on documentation and organizational improvements only
