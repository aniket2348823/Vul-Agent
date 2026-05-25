# Contributing to Antigravity V5

Thank you for your interest in contributing to Antigravity V5! This document provides guidelines and instructions for contributing to the project.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Code Style](#code-style)
5. [Testing Requirements](#testing-requirements)
6. [Pull Request Process](#pull-request-process)
7. [Commit Guidelines](#commit-guidelines)
8. [Documentation](#documentation)
9. [Issue Reporting](#issue-reporting)

---

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Prioritize security and quality
- Maintain professional communication

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Publishing private information
- Unprofessional conduct

---

## Getting Started

### Prerequisites

**Required**:
- Python 3.10+
- Node.js 18+
- Git
- Playwright browsers

**Recommended**:
- VS Code or PyCharm
- Docker (for testing)
- Redis (for distributed features)

### Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/antigravity-v5.git
cd antigravity-v5

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/antigravity-v5.git
```

---

## Development Setup

### 1. Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
pip install -r tests/requirements-test.txt
```

### 2. Install Node Dependencies

```bash
npm install
```

### 3. Install Playwright Browsers

```bash
playwright install chromium
```

### 4. Configure Environment

```bash
# Copy example environment file
copy .env.example .env

# Edit .env with your settings
# Required variables:
# - OPENAI_API_KEY (for AI features)
# - GEMINI_API_KEY (optional)
# - REDIS_URL (optional, for distributed features)
```

### 5. Initialize Database

```bash
python backend/db_migrate.py
```

### 6. Run Tests

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/unit/
pytest tests/integration/

# Run with coverage
pytest --cov=backend --cov-report=html
```

### 7. Start Development Server

```bash
# Backend
python backend/main.py

# Frontend (separate terminal)
npm run dev
```

---

## Code Style

### Python Style Guide

We follow **PEP 8** with some modifications:

**Line Length**: 100 characters (not 79)

**Imports**:
```python
# Standard library
import asyncio
import json
from typing import Dict, List, Optional

# Third-party
import aiohttp
from playwright.async_api import Page

# Local
from backend.core.state import StateManager
from backend.agents.alpha import AlphaAgent
```

**Type Hints**: Required for all functions
```python
async def scan_endpoint(url: str, timeout: int = 30) -> Dict[str, any]:
    """Scan endpoint for vulnerabilities.
    
    Args:
        url: Target URL to scan
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary containing scan results
    """
    pass
```

**Docstrings**: Required for all public functions
```python
def process_findings(findings: List[Dict]) -> List[Dict]:
    """Process and deduplicate findings.
    
    Args:
        findings: List of raw findings
        
    Returns:
        List of processed, deduplicated findings
        
    Raises:
        ValueError: If findings list is empty
    """
    pass
```

**Error Handling**: Always use specific exceptions
```python
# ❌ BAD
try:
    result = await operation()
except:
    pass

# ✅ GOOD
try:
    result = await operation()
except TimeoutError:
    logger.error("Operation timed out")
    raise
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    return None
```

### JavaScript/React Style Guide

We follow **Airbnb JavaScript Style Guide**:

**Components**: Use functional components with hooks
```javascript
// ✅ GOOD
function ScanResults({ scanId }) {
  const [results, setResults] = useState([]);
  
  useEffect(() => {
    fetchResults(scanId).then(setResults);
  }, [scanId]);
  
  return <div>{/* ... */}</div>;
}
```

**Naming**:
- Components: PascalCase (`ScanResults`)
- Functions: camelCase (`fetchResults`)
- Constants: UPPER_SNAKE_CASE (`API_BASE_URL`)

### Code Formatting

**Python**: Use `black` and `isort`
```bash
# Format code
black backend/
isort backend/

# Check formatting
black --check backend/
isort --check backend/
```

**JavaScript**: Use `prettier`
```bash
# Format code
npm run format

# Check formatting
npm run format:check
```

---

## Testing Requirements

### Test Coverage

**Minimum Requirements**:
- Unit tests: 80% coverage
- Integration tests: Critical paths covered
- All new features must include tests

### Writing Tests

**Unit Tests**: Test individual components
```python
# tests/unit/test_my_feature.py
import pytest
from backend.core.my_feature import MyFeature

@pytest.fixture
def feature():
    """Create feature instance."""
    return MyFeature()

async def test_basic_operation(feature):
    """Test basic operation."""
    result = await feature.process("input")
    assert result == "expected"

async def test_error_handling(feature):
    """Test error handling."""
    with pytest.raises(ValueError):
        await feature.process(None)
```

**Integration Tests**: Test component interactions
```python
# tests/integration/test_workflow.py
import pytest
from backend.core.orchestrator import Orchestrator
from backend.agents.alpha import AlphaAgent

@pytest.fixture
async def orchestrator():
    """Create orchestrator with dependencies."""
    orch = Orchestrator()
    await orch.initialize()
    yield orch
    await orch.cleanup()

async def test_scan_workflow(orchestrator):
    """Test complete scan workflow."""
    result = await orchestrator.run_scan("https://example.com")
    assert result["status"] == "completed"
    assert len(result["findings"]) > 0
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_my_feature.py

# Run specific test
pytest tests/unit/test_my_feature.py::test_basic_operation

# Run with coverage
pytest --cov=backend --cov-report=html

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x
```

### Test Best Practices

1. **Isolation**: Tests should not depend on each other
2. **Cleanup**: Always clean up resources (use fixtures)
3. **Mocking**: Mock external dependencies
4. **Assertions**: Use specific assertions
5. **Documentation**: Document test purpose

---

## Pull Request Process

### 1. Create Feature Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/my-feature
# or
git checkout -b fix/bug-description
```

### 2. Make Changes

- Write code following style guide
- Add tests for new functionality
- Update documentation
- Run tests locally

### 3. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add endpoint scanning feature"

# See commit guidelines below
```

### 4. Push to Fork

```bash
git push origin feature/my-feature
```

### 5. Create Pull Request

1. Go to GitHub repository
2. Click "New Pull Request"
3. Select your branch
4. Fill out PR template:
   - Description of changes
   - Related issues
   - Testing performed
   - Screenshots (if UI changes)

### 6. Code Review

- Address reviewer feedback
- Make requested changes
- Push updates to same branch
- PR will update automatically

### 7. Merge

- Maintainer will merge when approved
- Delete feature branch after merge

---

## Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```bash
# Feature
git commit -m "feat(agents): add CSRF bypass testing to Beta agent"

# Bug fix
git commit -m "fix(browser): resolve context leak in orchestrator"

# Documentation
git commit -m "docs(api): add usage examples for StateManager"

# Test
git commit -m "test(agents): add unit tests for Alpha agent"

# With body
git commit -m "feat(security): add rate limiting

Implements token bucket rate limiter with per-IP tracking.
Configurable limits and automatic cleanup.

Closes #123"
```

---

## Documentation

### Code Documentation

**Required**:
- Docstrings for all public functions/classes
- Type hints for all function parameters
- Inline comments for complex logic

**Example**:
```python
async def scan_target(
    url: str,
    depth: int = 3,
    timeout: int = 30
) -> Dict[str, any]:
    """Scan target URL for vulnerabilities.
    
    Performs comprehensive security scan including:
    - Endpoint discovery
    - Parameter analysis
    - Vulnerability testing
    
    Args:
        url: Target URL to scan (must be HTTPS)
        depth: Maximum crawl depth (default: 3)
        timeout: Request timeout in seconds (default: 30)
        
    Returns:
        Dictionary containing:
        - scan_id: Unique scan identifier
        - findings: List of discovered vulnerabilities
        - status: Scan status (completed/failed)
        
    Raises:
        ValueError: If URL is invalid
        TimeoutError: If scan exceeds timeout
        
    Example:
        >>> result = await scan_target("https://example.com")
        >>> print(result["scan_id"])
        'scan-abc123'
    """
    pass
```

### User Documentation

When adding features, update:
- `docs/API_REFERENCE.md` - API documentation
- `docs/USAGE_EXAMPLES.md` - Usage examples
- `README.md` - If user-facing changes

---

## Issue Reporting

### Bug Reports

**Include**:
- Clear description of bug
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Python version, etc.)
- Error messages/logs
- Screenshots (if applicable)

**Template**:
```markdown
**Description**
Brief description of the bug

**Steps to Reproduce**
1. Step one
2. Step two
3. Step three

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- OS: Windows 11
- Python: 3.10.5
- Version: 5.0.0

**Logs**
```
Error logs here
```

**Screenshots**
[If applicable]
```

### Feature Requests

**Include**:
- Clear description of feature
- Use case / motivation
- Proposed solution
- Alternative solutions considered
- Additional context

---

## Development Workflow

### Daily Workflow

```bash
# 1. Start day - update main
git checkout main
git pull upstream main

# 2. Create/switch to feature branch
git checkout -b feature/my-feature

# 3. Make changes
# ... edit files ...

# 4. Run tests
pytest

# 5. Format code
black backend/
isort backend/

# 6. Commit changes
git add .
git commit -m "feat: add new feature"

# 7. Push to fork
git push origin feature/my-feature

# 8. Create PR when ready
```

### Before Submitting PR

**Checklist**:
- [ ] Code follows style guide
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Code formatted (black, isort)
- [ ] No merge conflicts with main
- [ ] Commit messages follow guidelines
- [ ] PR description is complete

---

## Project Structure

```
antigravity-v5/
├── backend/              # Backend Python code
│   ├── agents/          # Security testing agents
│   ├── ai/              # AI integrations
│   ├── api/             # API endpoints
│   ├── core/            # Core functionality
│   ├── integrations/    # External integrations
│   └── main.py          # Entry point
├── src/                 # Frontend React code
│   ├── components/      # React components
│   ├── hooks/           # Custom hooks
│   └── lib/             # Utilities
├── tests/               # Test suites
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   └── e2e/            # End-to-end tests
├── docs/                # Documentation
└── scripts/             # Utility scripts
```

---

## Getting Help

### Resources

- **Documentation**: `docs/` directory
- **API Reference**: `docs/API_REFERENCE.md`
- **Examples**: `docs/USAGE_EXAMPLES.md`
- **Troubleshooting**: `docs/TROUBLESHOOTING.md`

### Communication

- **Issues**: GitHub Issues for bugs and features
- **Discussions**: GitHub Discussions for questions
- **Security**: Email security@example.com for security issues

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

## Recognition

Contributors will be recognized in:
- `CONTRIBUTORS.md` file
- Release notes
- Project documentation

Thank you for contributing to Antigravity V5! 🚀

---

**Last Updated**: May 25, 2026  
**Maintainer**: Antigravity V5 Team
