# OpenClaw + PinchTab Deep Integration Specification

## Overview

This specification defines the **deepest possible integration** of OpenClaw browser automation into the Antigravity V5 penetration testing system, working in **hybrid mode with PinchTab**.

## What's Included

### 📋 Specification Documents

1. **STATUS.md** - Current implementation status and completion summary
2. **requirements.md** - 15 detailed requirements with acceptance criteria
3. **design.md** - Complete technical architecture and implementation design
4. **tasks.md** - 23 implementation tasks with 300+ subtasks
5. **DEEP_INTEGRATION_SUMMARY.md** - Executive summary with agent-specific details
6. **README.md** (this file) - Quick start guide

## Architecture Summary

### Hybrid Browser Stack

```
┌─────────────────────────────────────────┐
│         BrowserOrchestrator             │
│  (Unified API - Intelligent Routing)    │
├──────────────────┬──────────────────────┤
│   OpenClaw       │      PinchTab        │
│   (Deep Auto)    │   (Fast Scrape)      │
└──────────────────┴──────────────────────┘
```

### Integration Depth

**All 10 agents enhanced with browser capabilities:**

| Agent | Role | Browser Enhancement |
|-------|------|---------------------|
| **Omega** | Strategist | Browser campaign planning, SPA detection |
| **Alpha** | Scout | Hybrid HTTP + Browser recon, JS route extraction |
| **Beta** | Breaker | Real browser XSS testing, CSRF validation |
| **Sigma** | Orchestrator | DOM-aware payload generation, pre-testing |
| **Gamma** | Auditor | Visual exploit verification, DOM mutation detection |
| **Delta** | Hybrid Controller | Unified PinchTab + OpenClaw management |
| **Prism** | Sentinel | Deep DOM analysis, shadow DOM inspection |
| **Chi** | Inspector | Real-time event interception, dark patterns |
| **Zeta** | Cortex | Browser resource monitoring, context lifecycle |
| **Kappa** | Librarian | Session persistence, browser state archival |

## Key Features

### Hybrid Mode
- **OpenClaw**: Deep automation, multi-step workflows, stealth mode
- **PinchTab**: Fast DOM scraping, token extraction, lightweight ops
- **Auto-Selection**: Intelligent routing based on task requirements

### Deep Integration
- Every agent gets browser capabilities via `BrowserOrchestrator`
- Backward compatible - HTTP functionality unchanged
- Unified API - single interface for both engines
- Session sharing between engines
- Forensic evidence for all browser operations

## Quick Start

### Prerequisites

```bash
# Ensure PinchTab is running
# Ensure Python 3.9+ installed
# Ensure Node.js installed (for Playwright)
```

### Installation

```bash
# 1. Install Python dependencies
pip install -r backend/requirements.txt

# 2. Install Playwright browsers
playwright install chromium

# 3. Install OpenClaw (if local development)
pip install -e d:/projects/openclaw

# 4. Configure environment
cp .env.example .env
# Edit .env and set:
# OPENCLAW_ENABLED=true
# PINCHTAB_ENABLED=true
```

### Configuration

Add to `.env`:

```bash
# OpenClaw
OPENCLAW_ENABLED=true
OPENCLAW_DEBUG=false
OPENCLAW_HEADLESS=true
OPENCLAW_BROWSER=chromium
OPENCLAW_STEALTH_MODE=true
OPENCLAW_MAX_CONTEXTS=5

# PinchTab
PINCHTAB_ENABLED=true
PINCHTAB_URL=http://localhost:3000

# Hybrid Mode
BROWSER_AUTO_SELECT=true
BROWSER_PREFER_SPEED=false
```

## Implementation Timeline

### Phase 1: Core Infrastructure (Week 1-2)
- BrowserOrchestrator (unified API)
- OpenClawEngine (deep automation)
- PinchTabEngine (fast operations)
- HybridSessionManager
- ForensicCollector

### Phase 2: Primary Agents (Week 3-4)
- Alpha (hybrid recon)
- Beta (browser exploitation)
- Sigma (browser-aware payloads)

### Phase 3: Secondary Agents (Week 5-6)
- Gamma (browser verification)
- Delta (unified controller)
- Omega (browser campaigns)

### Phase 4: Advanced Agents (Week 7-8)
- Prism (deep DOM analysis)
- Chi (event interception)
- Zeta (resource monitoring)
- Kappa (session persistence)

### Phase 5: Testing & Validation (Week 9-10)
- Unit tests
- Integration tests
- Performance testing
- Acceptance criteria validation

### Phase 6: Documentation & Deployment (Week 11-12)
- Documentation
- Deployment preparation
- Post-deployment monitoring

**Total Timeline**: 12 weeks (3 months)

## Success Criteria

The integration is successful when:

1. ✅ All 10 agents have browser capabilities
2. ✅ Hybrid mode intelligently routes between engines
3. ✅ Alpha discovers 90%+ endpoints on SPAs
4. ✅ Beta verifies XSS in real browser context
5. ✅ Sigma generates DOM-aware payloads
6. ✅ Gamma verifies exploits visually
7. ✅ Delta coordinates both engines seamlessly
8. ✅ Sessions persist across scans
9. ✅ Zero memory leaks after 100 scans
10. ✅ Forensic evidence captured for all operations

## Usage Examples

### Example 1: Hybrid Reconnaissance (Alpha)

```python
# Alpha automatically uses hybrid mode
target_url = "https://example.com"

# HTTP recon (existing)
http_endpoints = await alpha._http_recon(target_url)

# Browser recon (NEW)
browser_endpoints = await alpha._browser_recon(target_url)

# Merged results
all_endpoints = alpha._merge_endpoints(http_endpoints, browser_endpoints)
```

### Example 2: Browser XSS Testing (Beta)

```python
# Beta tests XSS in real browser
payload = "<script>alert(1)</script>"
url = "https://example.com/search?q="

# Test in browser (NEW)
result = await beta.browser.test_payload(url, payload)

if result.get("exploited"):
    # Capture forensic evidence
    screenshot = await beta.browser.capture_screenshot()
    # Publish VULN_CONFIRMED with visual proof
```

### Example 3: DOM-Aware Payloads (Sigma)

```python
# Sigma generates payloads based on actual DOM
dom_structure = await sigma.browser.analyze_dom(target_url)

# Generate form-specific payloads
for form in dom_structure.get("forms", []):
    for field in form.get("fields", []):
        payload = sigma._generate_field_payload(field)
        # Test in browser before HTTP execution
        if await sigma.browser.test_payload(url, payload):
            validated_payloads.append(payload)
```

## Architecture Diagrams

### Request Flow

```
User Request
    ↓
HiveOrchestrator
    ↓
Agent (e.g., Alpha)
    ↓
BrowserOrchestrator
    ↓
    ├─→ OpenClaw (if deep analysis needed)
    │   ├─→ Navigate with stealth
    │   ├─→ Extract JS routes
    │   ├─→ Intercept network
    │   └─→ Return deep results
    │
    └─→ PinchTab (if fast scraping needed)
        ├─→ Quick navigate
        ├─→ Extract tokens
        ├─→ Fast DOM scrape
        └─→ Return fast results
```

### Session Flow

```
Scan Start
    ↓
Alpha Recon (Browser)
    ↓
Session Created
    ↓
HybridSessionManager.save_session()
    ↓
Beta Exploitation (Browser)
    ↓
HybridSessionManager.restore_session()
    ↓
Session Reused
    ↓
Kappa Archives Session
    ↓
Session Available for Replay
```

## Testing Strategy

### Unit Tests
- Test each component in isolation
- Mock browser engines for speed
- Test intelligent routing logic
- Test session management

### Integration Tests
- Test full agent workflows
- Test hybrid mode coordination
- Test session persistence
- Test forensic evidence collection

### Performance Tests
- Memory leak detection (100 scans)
- Concurrent context limits
- Engine selection overhead
- Session restoration speed

### Acceptance Tests
- Validate all 15 requirements
- Test on real SPAs (React/Vue/Angular)
- Verify endpoint discovery rates
- Verify exploit verification accuracy

## Troubleshooting

### OpenClaw Not Found
```bash
# Install from local path
pip install -e d:/projects/openclaw

# Or install from PyPI (if available)
pip install openclaw
```

### Playwright Browser Not Installed
```bash
playwright install chromium
```

### PinchTab Connection Failed
```bash
# Ensure PinchTab is running
# Check PINCHTAB_URL in .env
# Default: http://localhost:3000
```

### Memory Leaks
```bash
# Check Zeta monitoring
# Verify context cleanup
# Check OPENCLAW_MAX_CONTEXTS setting
```

## Contributing

When implementing tasks:

1. Follow the task order in `tasks.md`
2. Complete all subtasks before moving to next task
3. Write tests for each component
4. Update documentation as you go
5. Verify backward compatibility
6. Test with both OpenClaw and PinchTab

## Support

For questions or issues:

1. Check `STATUS.md` for current implementation status
2. Check `DEEP_INTEGRATION_SUMMARY.md` for agent-specific details
3. Review `design.md` for architecture details
4. Check `tasks.md` for implementation guidance
5. Review test files for usage examples

## License

[Your License Here]

---

**Status**: ✅ **IMPLEMENTATION COMPLETE** - See STATUS.md for details

**Last Updated**: 2026-05-24

**Version**: 1.0.0
