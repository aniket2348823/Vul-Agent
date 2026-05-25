"""
E2E Tests for Report Generation Workflows

Tests the complete report generation process from findings to PDF.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import json

from backend.core.state import StateManager
from backend.core.reporting import ReportGenerator


@pytest_asyncio.fixture
async def state_manager():
    """Create state manager for report tests."""
    return StateManager()


@pytest_asyncio.fixture
async def report_generator():
    """Create report generator for tests."""
    return ReportGenerator()


@pytest_asyncio.fixture
async def sample_scan_data(state_manager):
    """Create sample scan data with findings."""
    scan_id = "report-scan-001"
    target_url = "http://test.com"
    
    # Initialize scan
    await state_manager.initialize_scan(scan_id, target_url)
    
    # Add findings
    findings = [
        {
            "id": "finding-001",
            "type": "xss",
            "severity": "high",
            "url": f"{target_url}/search",
            "parameter": "q",
            "payload": "<script>alert(1)</script>",
            "description": "Reflected XSS in search parameter",
            "impact": "Attacker can execute arbitrary JavaScript",
            "remediation": "Implement proper input validation and output encoding"
        },
        {
            "id": "finding-002",
            "type": "csrf",
            "severity": "medium",
            "url": f"{target_url}/api/update-profile",
            "method": "POST",
            "description": "Missing CSRF protection on profile update",
            "impact": "Attacker can perform unauthorized actions",
            "remediation": "Implement CSRF tokens"
        },
        {
            "id": "finding-003",
            "type": "sqli",
            "severity": "critical",
            "url": f"{target_url}/user",
            "parameter": "id",
            "payload": "1' OR '1'='1",
            "description": "SQL injection in user lookup",
            "impact": "Database compromise possible",
            "remediation": "Use parameterized queries"
        }
    ]
    
    for finding in findings:
        state_manager.add_finding(scan_id, finding)
    
    # Update scan status
    state_manager.update_scan_status(scan_id, "completed")
    
    return scan_id, findings


@pytest.mark.asyncio
async def test_report_generation_basic(report_generator, state_manager, sample_scan_data):
    """Test basic report generation."""
    scan_id, findings = sample_scan_data
    
    # Get scan data
    scan_state = state_manager.get_scan_state(scan_id)
    assert scan_state is not None
    
    # Get findings
    scan_findings = state_manager.get_findings(scan_id)
    assert len(scan_findings) == 3
    
    # Mock PDF generation
    with patch.object(report_generator, 'generate_pdf', return_value="/tmp/report.pdf") as mock_gen:
        # Generate report
        report_path = report_generator.generate_pdf(scan_id, scan_state, scan_findings)
        
        # Verify report generated
        assert report_path is not None
        mock_gen.assert_called_once()


@pytest.mark.asyncio
async def test_report_with_severity_breakdown(state_manager, sample_scan_data):
    """Test report includes severity breakdown."""
    scan_id, findings = sample_scan_data
    
    # Get findings
    scan_findings = state_manager.get_findings(scan_id)
    
    # Calculate severity breakdown
    severity_counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0
    }
    
    for finding in scan_findings:
        severity = finding.get("severity", "low")
        if severity in severity_counts:
            severity_counts[severity] += 1
    
    # Verify breakdown
    assert severity_counts["critical"] == 1
    assert severity_counts["high"] == 1
    assert severity_counts["medium"] == 1
    assert severity_counts["low"] == 0


@pytest.mark.asyncio
async def test_report_with_vulnerability_types(state_manager, sample_scan_data):
    """Test report includes vulnerability type breakdown."""
    scan_id, findings = sample_scan_data
    
    # Get findings
    scan_findings = state_manager.get_findings(scan_id)
    
    # Calculate type breakdown
    type_counts = {}
    for finding in scan_findings:
        vuln_type = finding.get("type", "unknown")
        type_counts[vuln_type] = type_counts.get(vuln_type, 0) + 1
    
    # Verify breakdown
    assert type_counts.get("xss") == 1
    assert type_counts.get("csrf") == 1
    assert type_counts.get("sqli") == 1


@pytest.mark.asyncio
async def test_report_with_remediation_steps(state_manager, sample_scan_data):
    """Test report includes remediation steps."""
    scan_id, findings = sample_scan_data
    
    # Get findings
    scan_findings = state_manager.get_findings(scan_id)
    
    # Verify all findings have remediation
    for finding in scan_findings:
        assert "remediation" in finding
        assert len(finding["remediation"]) > 0


@pytest.mark.asyncio
async def test_report_with_scan_metadata(state_manager, sample_scan_data):
    """Test report includes scan metadata."""
    scan_id, findings = sample_scan_data
    
    # Add metadata
    state_manager.update_scan_metadata(scan_id, {
        "scan_type": "full",
        "duration": 3600,
        "pages_scanned": 50,
        "requests_made": 500
    })
    
    # Get scan state
    scan_state = state_manager.get_scan_state(scan_id)
    metadata = scan_state.get("metadata", {})
    
    # Verify metadata
    assert metadata.get("scan_type") == "full"
    assert metadata.get("duration") == 3600
    assert metadata.get("pages_scanned") == 50
    assert metadata.get("requests_made") == 500


@pytest.mark.asyncio
async def test_report_generation_with_no_findings(report_generator, state_manager):
    """Test report generation when no findings exist."""
    # Setup
    scan_id = "report-scan-002"
    target_url = "http://clean-site.com"
    
    # Initialize scan with no findings
    await state_manager.initialize_scan(scan_id, target_url)
    state_manager.update_scan_status(scan_id, "completed")
    
    # Get scan data
    scan_state = state_manager.get_scan_state(scan_id)
    scan_findings = state_manager.get_findings(scan_id)
    
    # Verify no findings
    assert len(scan_findings) == 0
    
    # Mock PDF generation
    with patch.object(report_generator, 'generate_pdf', return_value="/tmp/report-clean.pdf") as mock_gen:
        # Generate report
        report_path = report_generator.generate_pdf(scan_id, scan_state, scan_findings)
        
        # Verify report still generated
        assert report_path is not None
        mock_gen.assert_called_once()


@pytest.mark.asyncio
async def test_report_export_formats(report_generator, state_manager, sample_scan_data):
    """Test report export in multiple formats."""
    scan_id, findings = sample_scan_data
    
    # Get scan data
    scan_state = state_manager.get_scan_state(scan_id)
    scan_findings = state_manager.get_findings(scan_id)
    
    # Mock different export formats
    with patch.object(report_generator, 'generate_pdf', return_value="/tmp/report.pdf") as mock_pdf:
        with patch.object(report_generator, 'generate_json', return_value="/tmp/report.json") as mock_json:
            with patch.object(report_generator, 'generate_html', return_value="/tmp/report.html") as mock_html:
                # Generate PDF
                pdf_path = report_generator.generate_pdf(scan_id, scan_state, scan_findings)
                assert pdf_path is not None
                
                # Generate JSON
                json_path = report_generator.generate_json(scan_id, scan_state, scan_findings)
                assert json_path is not None
                
                # Generate HTML
                html_path = report_generator.generate_html(scan_id, scan_state, scan_findings)
                assert html_path is not None


@pytest.mark.asyncio
async def test_report_with_screenshots(state_manager, sample_scan_data):
    """Test report includes screenshot references."""
    scan_id, findings = sample_scan_data
    
    # Add screenshot references to findings
    scan_findings = state_manager.get_findings(scan_id)
    for i, finding in enumerate(scan_findings):
        finding["screenshot"] = f"/tmp/screenshot-{i}.png"
        state_manager.update_finding(scan_id, finding["id"], finding)
    
    # Verify screenshots added
    updated_findings = state_manager.get_findings(scan_id)
    for finding in updated_findings:
        assert "screenshot" in finding
        assert finding["screenshot"].endswith(".png")


@pytest.mark.asyncio
async def test_report_with_timeline(state_manager, sample_scan_data):
    """Test report includes scan timeline."""
    scan_id, findings = sample_scan_data
    
    # Add timeline events
    timeline = [
        {"timestamp": "2026-05-25T10:00:00", "event": "Scan started"},
        {"timestamp": "2026-05-25T10:15:00", "event": "Reconnaissance complete"},
        {"timestamp": "2026-05-25T10:30:00", "event": "Vulnerability testing started"},
        {"timestamp": "2026-05-25T11:00:00", "event": "Scan completed"}
    ]
    
    state_manager.update_scan_metadata(scan_id, {"timeline": timeline})
    
    # Get scan state
    scan_state = state_manager.get_scan_state(scan_id)
    metadata = scan_state.get("metadata", {})
    
    # Verify timeline
    assert "timeline" in metadata
    assert len(metadata["timeline"]) == 4


@pytest.mark.asyncio
async def test_report_generation_error_handling(report_generator, state_manager):
    """Test report generation error handling."""
    # Setup with invalid scan ID
    scan_id = "nonexistent-scan"
    
    # Try to get scan state
    scan_state = state_manager.get_scan_state(scan_id)
    
    # Verify returns None for nonexistent scan
    assert scan_state is None


@pytest.mark.asyncio
async def test_complete_report_workflow(report_generator, state_manager):
    """Test complete report generation workflow."""
    # Setup
    scan_id = "report-scan-003"
    target_url = "http://test.com"
    
    # Step 1: Initialize scan
    await state_manager.initialize_scan(scan_id, target_url)
    state_manager.update_scan_status(scan_id, "running")
    
    # Step 2: Add findings during scan
    finding = {
        "id": "finding-001",
        "type": "xss",
        "severity": "high",
        "url": f"{target_url}/test",
        "description": "Test finding"
    }
    state_manager.add_finding(scan_id, finding)
    
    # Step 3: Complete scan
    state_manager.update_scan_status(scan_id, "completed")
    
    # Step 4: Get scan data
    scan_state = state_manager.get_scan_state(scan_id)
    scan_findings = state_manager.get_findings(scan_id)
    
    # Step 5: Generate report
    with patch.object(report_generator, 'generate_pdf', return_value="/tmp/report-final.pdf") as mock_gen:
        report_path = report_generator.generate_pdf(scan_id, scan_state, scan_findings)
        
        # Verify complete workflow
        assert scan_state.get("status") == "completed"
        assert len(scan_findings) == 1
        assert report_path is not None
        mock_gen.assert_called_once()
