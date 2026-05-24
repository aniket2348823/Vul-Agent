# File Consolidation - Tasks

## Task List

- [ ] 1. Spec Documentation Consolidation
  - [ ] 1.1 Create merged STATUS.md file
  - [ ] 1.2 Update README.md with new structure
  - [ ] 1.3 Delete redundant status files
  - [ ] 1.4 Verify all links work

- [ ] 2. Planning Documentation Organization
  - [ ] 2.1 Create .planning/archive/ directory
  - [ ] 2.2 Move old implementation plans to archive
  - [ ] 2.3 Create archive README
  - [ ] 2.4 Verify current planning docs

- [ ] 3. Architecture Documentation
  - [ ] 3.1 Create docs/ directory
  - [ ] 3.2 Merge system_blueprint.md and architects_bible.md
  - [ ] 3.3 Create docs/ARCHITECTURE.md
  - [ ] 3.4 Update root README with links

- [ ] 4. Scripts Organization
  - [ ] 4.1 Create scripts/README.md
  - [ ] 4.2 Move root scripts to scripts/
  - [ ] 4.3 Update script references
  - [ ] 4.4 Test scripts from new location

- [ ] 5. Test Organization
  - [ ] 5.1 Create new test directory structure
  - [ ] 5.2 Create testsprite_tests/README.md
  - [ ] 5.3 Reorganize API tests
  - [ ] 5.4 Reorganize integration tests
  - [ ] 5.5 Reorganize security tests
  - [ ] 5.6 Move output files to output/
  - [ ] 5.7 Update pytest configuration
  - [ ] 5.8 Run full test suite

- [ ] 6. Root Cleanup
  - [ ] 6.1 Delete backend_structure.txt
  - [ ] 6.2 Review and organize data files
  - [ ] 6.3 Archive old agent versions
  - [ ] 6.4 Final verification

## Detailed Task Breakdown

### Task 1: Spec Documentation Consolidation

#### 1.1 Create merged STATUS.md file

**Description:** Merge 5 status files into single authoritative STATUS.md

**Input Files:**
- `FINAL_IMPLEMENTATION_STATUS.md`
- `FINAL_STATUS.md`
- `IMPLEMENTATION_COMPLETE.md`
- `IMPLEMENTATION_SUMMARY.md`
- `PHASE1_COMPLETE.md`
- `CODEBASE_AUDIT.md` (extract current issues)

**Output:** `.kiro/specs/openclaw-integration/STATUS.md`

**Steps:**
1. Read all 5 status files
2. Use `FINAL_IMPLEMENTATION_STATUS.md` as base structure
3. Add detailed agent breakdown from `FINAL_STATUS.md`
4. Add metrics from `IMPLEMENTATION_SUMMARY.md`
5. Add phase details from `PHASE1_COMPLETE.md`
6. Add current issues from `CODEBASE_AUDIT.md`
7. Organize into clear sections:
   - Executive Summary
   - Implementation Progress (by phase)
   - Component Status (table)
   - Metrics
   - Current Capabilities
   - Known Issues
   - Performance Metrics
   - Next Steps
   - Installation & Usage
   - Change Log
8. Write to STATUS.md
9. Review for completeness

**Acceptance Criteria:**
- Single STATUS.md file contains all unique information
- No information loss from original files
- Clear, well-organized structure
- All sections present and complete

#### 1.2 Update README.md with new structure

**Description:** Update README to reference new STATUS.md

**File:** `.kiro/specs/openclaw-integration/README.md`

**Changes:**
1. Update "What's Included" section to reference STATUS.md
2. Remove duplicate status information
3. Add clear links to all spec documents
4. Keep README focused on overview and quick start

**Acceptance Criteria:**
- README references STATUS.md for implementation status
- All document links work
- No duplicate information
- Clear navigation structure

#### 1.3 Delete redundant status files

**Description:** Remove the 5 merged status files

**Files to Delete:**
- `FINAL_IMPLEMENTATION_STATUS.md`
- `FINAL_STATUS.md`
- `IMPLEMENTATION_COMPLETE.md`
- `IMPLEMENTATION_SUMMARY.md`
- `PHASE1_COMPLETE.md`

**Steps:**
1. Verify STATUS.md is complete
2. Verify no external references to these files
3. Delete files
4. Commit changes

**Acceptance Criteria:**
- Files deleted
- No broken references
- Git history preserved

#### 1.4 Verify all links work

**Description:** Check all documentation links

**Steps:**
1. Check links in README.md
2. Check links in STATUS.md
3. Check links in design.md
4. Check links in requirements.md
5. Fix any broken links

**Acceptance Criteria:**
- All internal links work
- All cross-references correct
- No 404s

### Task 2: Planning Documentation Organization

#### 2.1 Create .planning/archive/ directory

**Description:** Create archive directory for old plans

**Steps:**
1. Create `.planning/archive/` directory
2. Verify directory created

**Acceptance Criteria:**
- Directory exists
- Proper permissions

#### 2.2 Move old implementation plans to archive

**Description:** Archive obsolete implementation plans

**Files to Move:**
- `implementation_plan_alpha_singularity_v6.md` → `.planning/archive/`
- `implementation_plan_deep_v2.md` → `.planning/archive/`
- `STARTUP_REBUILD_AND_ALPHA_IMPLEMENTATION_PLAN.md` → `.planning/archive/`

**Steps:**
1. Move each file to archive directory
2. Verify files moved successfully

**Acceptance Criteria:**
- Files in archive directory
- Root directory cleaner
- Files still accessible for reference

#### 2.3 Create archive README

**Description:** Document what's in the archive

**File:** `.planning/archive/README.md`

**Content:**
- Purpose of archive
- List of archived files with descriptions
- Reference to current planning docs

**Acceptance Criteria:**
- README created
- All archived files documented
- Clear explanation of archive purpose

#### 2.4 Verify current planning docs

**Description:** Ensure current docs are up to date

**Files:**
- `.planning/ROADMAP.md`
- `.planning/STATE.md`

**Steps:**
1. Review ROADMAP.md for accuracy
2. Review STATE.md for current state
3. Update if needed

**Acceptance Criteria:**
- Current docs accurate
- No outdated information
- Clear and actionable

### Task 3: Architecture Documentation

#### 3.1 Create docs/ directory

**Description:** Create documentation directory

**Steps:**
1. Create `docs/` directory in root
2. Verify directory created

**Acceptance Criteria:**
- Directory exists
- Proper location (root)

#### 3.2 Merge system_blueprint.md and architects_bible.md

**Description:** Combine architecture documents

**Input Files:**
- `system_blueprint.md`
- `architects_bible.md`

**Output:** `docs/ARCHITECTURE.md`

**Steps:**
1. Read both files
2. Identify overlapping content
3. Merge into unified structure:
   - System Overview
   - Architecture Principles
   - Component Architecture
   - Agent Architecture
   - Data Flow
   - Technology Stack
   - Design Patterns
   - Security Architecture
4. Remove duplicates
5. Organize logically

**Acceptance Criteria:**
- Single ARCHITECTURE.md file
- All unique content preserved
- Well-organized structure
- No duplication

#### 3.3 Create docs/ARCHITECTURE.md

**Description:** Write merged architecture document

**Steps:**
1. Create file with merged content
2. Add table of contents
3. Add diagrams if needed
4. Review for completeness

**Acceptance Criteria:**
- File created
- Complete architecture documentation
- Clear and comprehensive

#### 3.4 Update root README with links

**Description:** Link to new architecture doc

**File:** `README.md`

**Changes:**
1. Add link to `docs/ARCHITECTURE.md`
2. Remove or update references to old files
3. Add "Documentation" section if not present

**Acceptance Criteria:**
- README links to new docs
- No broken links
- Clear documentation structure

### Task 4: Scripts Organization

#### 4.1 Create scripts/README.md

**Description:** Document all utility scripts

**File:** `scripts/README.md`

**Content:**
- Overview of scripts directory
- Categorized list of scripts
- Usage examples
- Common workflows

**Acceptance Criteria:**
- README created
- All scripts documented
- Clear usage instructions

#### 4.2 Move root scripts to scripts/

**Description:** Relocate utility scripts

**Files to Move:**
- `fix_agents.py` → `scripts/`
- `fix_remaining.py` → `scripts/`
- `graphify_scan.py` → `scripts/`
- `upgrade_agents.py` → `scripts/`
- `verify_refactor.py` → `scripts/`

**Steps:**
1. Move each file
2. Verify files moved
3. Check for any hardcoded paths in scripts

**Acceptance Criteria:**
- Files in scripts/ directory
- Root directory cleaner
- Scripts still functional

#### 4.3 Update script references

**Description:** Update any references to moved scripts

**Steps:**
1. Search codebase for script references
2. Update paths in documentation
3. Update paths in other scripts
4. Update CI/CD if applicable

**Acceptance Criteria:**
- All references updated
- No broken imports
- Documentation accurate

#### 4.4 Test scripts from new location

**Description:** Verify scripts work after move

**Steps:**
1. Test each moved script
2. Verify functionality unchanged
3. Fix any path issues

**Acceptance Criteria:**
- All scripts execute successfully
- No errors
- Same functionality as before

### Task 5: Test Organization

#### 5.1 Create new test directory structure

**Description:** Set up organized test structure

**Directories to Create:**
- `testsprite_tests/api/`
- `testsprite_tests/agents/`
- `testsprite_tests/integration/`
- `testsprite_tests/security/`
- `testsprite_tests/performance/`
- `testsprite_tests/output/`

**Steps:**
1. Create each directory
2. Verify structure

**Acceptance Criteria:**
- All directories created
- Proper hierarchy
- Ready for test migration

#### 5.2 Create testsprite_tests/README.md

**Description:** Document test organization

**File:** `testsprite_tests/README.md`

**Content:**
- Test suite overview
- Directory structure explanation
- How to run tests
- Test categories
- Contributing guidelines

**Acceptance Criteria:**
- README created
- Clear test organization
- Usage instructions

#### 5.3 Reorganize API tests

**Description:** Move API tests to api/ directory

**Test Files:**
- `TC001_get_dashboard_stats_success.py` → `api/test_dashboard.py`
- `TC002_get_dashboard_scans_success.py` → `api/test_dashboard.py` (merge)
- `TC003_post_attack_fire_valid_payload.py` → `api/test_attack.py`
- `TC004_post_attack_fire_invalid_payload.py` → `api/test_attack.py` (merge)
- `TC002_post_api_recon_ingest_*.py` → `api/test_recon.py`
- `TC004_get_api_reports_pdf_*.py` → `api/test_reports.py`

**Steps:**
1. Create consolidated test files
2. Merge related tests
3. Update test names
4. Verify tests run

**Acceptance Criteria:**
- Tests organized by endpoint
- Related tests merged
- All tests pass
- Clear naming

#### 5.4 Reorganize integration tests

**Description:** Move integration tests

**Test Files:**
- `TC010_End_to_End_Backend_Workflow_Execution.py` → `integration/test_full_workflow.py`
- `test_full_pipeline.py` → `integration/test_full_workflow.py` (merge)
- `test_full_project.py` → `integration/test_full_workflow.py` (merge)

**Steps:**
1. Create consolidated integration tests
2. Merge related tests
3. Update test names
4. Verify tests run

**Acceptance Criteria:**
- Integration tests organized
- Related tests merged
- All tests pass

#### 5.5 Reorganize security tests

**Description:** Move security tests

**Test Files:**
- `TC003_Auth_Flow__Privilege_Escalation_Simulation.py` → `security/test_auth.py`
- `TC004_AI_OpenRouter_LLM_Logic__Hallucination_Flow.py` → `security/test_injection.py`
- `test_guardrails.py` → `security/test_guardrails.py`

**Steps:**
1. Move security tests
2. Organize by security concern
3. Verify tests run

**Acceptance Criteria:**
- Security tests organized
- Clear categorization
- All tests pass

#### 5.6 Move output files to output/

**Description:** Organize test output files

**Files to Move:**
- `pytest_*.txt` → `output/`
- `extracted_failures.md` → `output/`
- `*.txt` (test outputs) → `output/`

**Steps:**
1. Move all output files
2. Update .gitignore if needed
3. Verify no test dependencies broken

**Acceptance Criteria:**
- Output files in output/ directory
- Tests still generate output correctly
- Clean test directory

#### 5.7 Update pytest configuration

**Description:** Update test discovery

**File:** `pytest.ini`

**Changes:**
1. Update testpaths
2. Update python_files pattern
3. Verify test discovery works

**Acceptance Criteria:**
- Pytest finds all tests
- Test discovery works
- No missing tests

#### 5.8 Run full test suite

**Description:** Verify all tests still work

**Steps:**
1. Run `pytest testsprite_tests/`
2. Verify all tests discovered
3. Check for failures
4. Fix any issues

**Acceptance Criteria:**
- All tests discovered
- All tests pass (or same pass rate as before)
- No new failures from reorganization

### Task 6: Root Cleanup

#### 6.1 Delete backend_structure.txt

**Description:** Remove duplicate file

**File:** `backend_structure.txt`

**Steps:**
1. Verify `backend_structure_utf8.txt` exists
2. Verify content is same
3. Delete `backend_structure.txt`

**Acceptance Criteria:**
- Duplicate file removed
- UTF-8 version retained
- No references to deleted file

#### 6.2 Review and organize data files

**Description:** Organize root data files

**Files:**
- `graph.json`
- `keyring.json`
- `prd.json`
- `stats.json`
- `user_config.json`

**Steps:**
1. Determine if files are actively used
2. Move to `data/` if appropriate
3. OR document why they're in root
4. Update references if moved

**Acceptance Criteria:**
- Data files organized
- Application still works
- Clear file locations

#### 6.3 Archive old agent versions

**Description:** Clean up old agent code

**Directory:** `backend/agents/alpha_v6/`

**Steps:**
1. Verify if still needed
2. If not needed, move to `backend/agents/archive/`
3. If needed, document relationship to current version

**Acceptance Criteria:**
- Old versions archived or documented
- Clear version management
- No confusion about current code

#### 6.4 Final verification

**Description:** Comprehensive check of all changes

**Steps:**
1. Run full test suite
2. Verify all imports work
3. Check all documentation links
4. Review file structure
5. Test key workflows
6. Get team review

**Acceptance Criteria:**
- All tests pass
- No broken imports
- No broken links
- Clean file structure
- Team approval

## Task Execution Order

### Phase 1 (Day 1): High Priority Documentation
1. Task 1.1 - Create STATUS.md
2. Task 1.2 - Update README
3. Task 1.3 - Delete redundant files
4. Task 1.4 - Verify links

### Phase 2 (Day 1): Planning & Architecture
5. Task 2.1 - Create archive directory
6. Task 2.2 - Move old plans
7. Task 2.3 - Create archive README
8. Task 3.1 - Create docs directory
9. Task 3.2-3.3 - Merge architecture docs
10. Task 3.4 - Update root README

### Phase 3 (Day 2): Scripts
11. Task 4.1 - Create scripts README
12. Task 4.2 - Move scripts
13. Task 4.3 - Update references
14. Task 4.4 - Test scripts

### Phase 4 (Day 2-3): Tests
15. Task 5.1 - Create test structure
16. Task 5.2 - Create test README
17. Task 5.3 - Reorganize API tests
18. Task 5.4 - Reorganize integration tests
19. Task 5.5 - Reorganize security tests
20. Task 5.6 - Move output files
21. Task 5.7 - Update pytest config
22. Task 5.8 - Run full test suite

### Phase 5 (Day 3): Cleanup
23. Task 6.1 - Delete duplicates
24. Task 6.2 - Organize data files
25. Task 6.3 - Archive old versions
26. Task 6.4 - Final verification

## Estimated Timeline

- **Phase 1:** 2 hours
- **Phase 2:** 2 hours
- **Phase 3:** 1 hour
- **Phase 4:** 4 hours
- **Phase 5:** 2 hours

**Total:** ~11 hours (1.5 days)

## Success Metrics

- [ ] Spec documentation reduced from 11 to 6 files
- [ ] Root directory has 30% fewer files
- [ ] All tests pass after reorganization
- [ ] No broken links or imports
- [ ] Clear directory structure
- [ ] Team approval
