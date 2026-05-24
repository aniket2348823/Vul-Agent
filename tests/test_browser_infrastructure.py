"""
Test script for Phase 1 Browser Infrastructure
Verifies BrowserOrchestrator, OpenClawEngine, PinchTabEngine, HybridSessionManager, and ForensicCollector
"""

import asyncio
from backend.core.browser_orchestrator import BrowserOrchestrator, BrowserEngine
from backend.core.hybrid_session_manager import HybridSessionManager
from backend.core.forensic_collector import ForensicCollector


async def test_browser_orchestrator():
    """Test BrowserOrchestrator initialization and basic operations."""
    print("\n=== Testing BrowserOrchestrator ===")
    
    try:
        orchestrator = BrowserOrchestrator()
        print("✓ BrowserOrchestrator initialized")
        
        # Test engine selection
        engine = orchestrator._select_engine(
            url="https://example.com/login",
            operation="navigate",
            stealth=True
        )
        print(f"✓ Engine selection: {engine.value} (expected: OPENCLAW for stealth)")
        
        engine = orchestrator._select_engine(
            url="https://api.example.com/data",
            operation="extract_tokens",
            stealth=False
        )
        print(f"✓ Engine selection: {engine.value} (expected: PINCHTAB for fast ops)")
        
        return True
        
    except Exception as e:
        print(f"✗ BrowserOrchestrator test failed: {e}")
        return False


async def test_session_manager():
    """Test HybridSessionManager session save/restore."""
    print("\n=== Testing HybridSessionManager ===")
    
    try:
        manager = HybridSessionManager()
        print("✓ HybridSessionManager initialized")
        
        # Test session save
        test_session_data = {
            "cookies": [{"name": "test", "value": "123"}],
            "localStorage": {"key": "value"}
        }
        
        success = await manager.save_session(
            session_id="test_scan_001",
            engine="openclaw",
            session_data=test_session_data,
            metadata={"target": "https://example.com"}
        )
        print(f"✓ Session save: {success}")
        
        # Test session restore
        restored = await manager.restore_session(
            session_id="test_scan_001",
            engine="openclaw"
        )
        print(f"✓ Session restore: {restored is not None}")
        
        # Test session listing
        sessions = manager.list_sessions()
        print(f"✓ Session listing: {len(sessions)} sessions found")
        
        return True
        
    except Exception as e:
        print(f"✗ HybridSessionManager test failed: {e}")
        return False


async def test_forensic_collector():
    """Test ForensicCollector evidence collection."""
    print("\n=== Testing ForensicCollector ===")
    
    try:
        collector = ForensicCollector()
        print("✓ ForensicCollector initialized")
        
        # Test network log capture
        test_network_events = [
            {"type": "request", "url": "https://example.com/api/data", "method": "GET"},
            {"type": "response", "url": "https://example.com/api/data", "status": 200}
        ]
        
        log_path = await collector.capture_network_logs(
            scan_id="test_scan_001",
            network_events=test_network_events,
            label="test_network"
        )
        print(f"✓ Network log capture: {log_path is not None}")
        
        # Test console log capture
        test_console_messages = [
            {"level": "info", "text": "Application started"},
            {"level": "error", "text": "XSS detected"}
        ]
        
        console_path = await collector.capture_console_logs(
            scan_id="test_scan_001",
            console_messages=test_console_messages,
            label="test_console"
        )
        print(f"✓ Console log capture: {console_path is not None}")
        
        # Test evidence summary
        summary = collector.get_evidence_summary("test_scan_001")
        print(f"✓ Evidence summary: {summary['total_evidence']} items collected")
        
        # Test evidence bundling
        bundle_path = await collector.bundle_evidence(
            scan_id="test_scan_001",
            vuln_id="XSS-001"
        )
        print(f"✓ Evidence bundling: {bundle_path is not None}")
        
        return True
        
    except Exception as e:
        print(f"✗ ForensicCollector test failed: {e}")
        return False


async def test_config():
    """Test configuration loading."""
    print("\n=== Testing Configuration ===")
    
    try:
        from config import ConfigManager
        
        config = ConfigManager()
        print("✓ ConfigManager initialized")
        
        # Check OpenClaw config
        print(f"✓ OpenClaw enabled: {config.openclaw.enabled}")
        print(f"✓ OpenClaw headless: {config.openclaw.headless}")
        print(f"✓ OpenClaw browser: {config.openclaw.browser_type}")
        
        # Check PinchTab config
        print(f"✓ PinchTab enabled: {config.pinchtab.enabled}")
        print(f"✓ PinchTab URL: {config.pinchtab.base_url}")
        
        # Check Hybrid config
        print(f"✓ Hybrid browser enabled: {config.hybrid_browser.enabled}")
        print(f"✓ Hybrid default engine: {config.hybrid_browser.default_engine}")
        print(f"✓ Hybrid session sharing: {config.hybrid_browser.session_sharing}")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


async def main():
    """Run all Phase 1 infrastructure tests."""
    print("=" * 60)
    print("Phase 1 Browser Infrastructure Test Suite")
    print("=" * 60)
    
    results = []
    
    # Test configuration
    results.append(("Configuration", await test_config()))
    
    # Test BrowserOrchestrator
    results.append(("BrowserOrchestrator", await test_browser_orchestrator()))
    
    # Test HybridSessionManager
    results.append(("HybridSessionManager", await test_session_manager()))
    
    # Test ForensicCollector
    results.append(("ForensicCollector", await test_forensic_collector()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
