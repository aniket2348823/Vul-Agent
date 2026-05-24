# Utility Scripts

This directory contains utility scripts for development, maintenance, testing, and operations of the Antigravity V5 penetration testing system.

## 📁 Script Categories

### 🔧 Development & Maintenance

#### `fix_agents.py`
**Purpose:** Fix agent import issues and code problems  
**Usage:** `python scripts/fix_agents.py`  
**Description:** Automatically repairs common agent implementation issues, import errors, and code structure problems.

#### `fix_remaining.py`
**Purpose:** Fix remaining code issues after refactoring  
**Usage:** `python scripts/fix_remaining.py`  
**Description:** Addresses residual issues from major refactoring operations.

#### `verify_refactor.py`
**Purpose:** Verify refactoring correctness  
**Usage:** `python scripts/verify_refactor.py`  
**Description:** Validates that refactored code maintains expected behavior and doesn't introduce regressions.

#### `upgrade_agents.py`
**Purpose:** Upgrade agent implementations  
**Usage:** `python scripts/upgrade_agents.py`  
**Description:** Applies upgrades and improvements to agent code, ensuring compatibility with latest architecture.

---

### 📊 Data & Visualization

#### `graphify_scan.py`
**Purpose:** Generate scan visualization graphs  
**Usage:** `python scripts/graphify_scan.py [scan_id]`  
**Description:** Creates visual representations of scan data, attack paths, and vulnerability relationships.

#### `get_metrics.py`
**Purpose:** Collect system metrics  
**Usage:** `python scripts/get_metrics.py`  
**Description:** Gathers performance metrics, scan statistics, and system health data.

---

### 🧪 Testing

#### `generate_massive_tests.py`
**Purpose:** Generate load test suites  
**Usage:** `python scripts/generate_massive_tests.py [count]`  
**Description:** Creates large-scale test suites for stress testing and performance validation.

#### `extract_failures.py`
**Purpose:** Extract test failures from logs  
**Usage:** `python scripts/extract_failures.py [log_file]`  
**Description:** Parses test output logs and extracts failure information for analysis.

---

### 🔐 Security & Operations

#### `run_scanner.py`
**Purpose:** Run security scanner  
**Usage:** `python scripts/run_scanner.py [target]`  
**Description:** Executes the penetration testing scanner against specified targets.

#### `change_pw.py`
**Purpose:** Change user password  
**Usage:** `python scripts/change_pw.py [username]`  
**Description:** Updates user passwords in the system database.

#### `gen_token.py`
**Purpose:** Generate authentication tokens  
**Usage:** `python scripts/gen_token.py [user_id]`  
**Description:** Creates JWT or API tokens for authentication and authorization.

---

### 🐛 Issue Management

#### `get_issues.py`
**Purpose:** Fetch GitHub issues  
**Usage:** `python scripts/get_issues.py`  
**Description:** Retrieves open issues from the GitHub repository for tracking and analysis.

---

## 🚀 Common Workflows

### After Major Refactoring
```bash
# 1. Fix any agent issues
python scripts/fix_agents.py

# 2. Fix remaining code problems
python scripts/fix_remaining.py

# 3. Verify refactoring correctness
python scripts/verify_refactor.py

# 4. Run tests to ensure everything works
pytest tests/
```

### Performance Analysis
```bash
# 1. Collect system metrics
python scripts/get_metrics.py

# 2. Generate visualization
python scripts/graphify_scan.py [scan_id]
```

### Load Testing
```bash
# 1. Generate test suite
python scripts/generate_massive_tests.py 1000

# 2. Run tests
pytest testsprite_tests/

# 3. Extract failures if any
python scripts/extract_failures.py pytest_output.txt
```

### Security Operations
```bash
# 1. Generate auth token
python scripts/gen_token.py admin

# 2. Run scanner
python scripts/run_scanner.py https://target.example.com

# 3. Visualize results
python scripts/graphify_scan.py [scan_id]
```

---

## 📝 Script Development Guidelines

When adding new scripts to this directory:

1. **Naming Convention:** Use snake_case (e.g., `my_new_script.py`)
2. **Documentation:** Include docstring at top of file explaining purpose
3. **Help Text:** Add `--help` argument with argparse
4. **Error Handling:** Use try/except for robust error handling
5. **Logging:** Use Python logging module for output
6. **Update README:** Add entry to this README with usage instructions

### Example Script Template

```python
#!/usr/bin/env python3
"""
Script Name: my_new_script.py
Purpose: Brief description of what this script does
Author: Your Name
Date: YYYY-MM-DD
"""

import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument("target", help="Target parameter")
    parser.add_argument("--option", help="Optional parameter")
    args = parser.parse_args()
    
    try:
        # Script logic here
        logger.info(f"Processing {args.target}")
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
```

---

## 🔗 Related Documentation

- **Main README:** `../README.md`
- **Architecture:** `../docs/ARCHITECTURE.md`
- **Development Guide:** `../docs/DEVELOPMENT.md` (if exists)
- **Testing Guide:** `../testsprite_tests/README.md`

---

## 📞 Support

For issues with scripts or to request new utility scripts, please:
1. Check existing GitHub issues
2. Create a new issue with the `scripts` label
3. Contact the development team

---

**Last Updated:** May 24, 2026  
**Total Scripts:** 12  
**Maintained By:** Antigravity V5 Development Team
