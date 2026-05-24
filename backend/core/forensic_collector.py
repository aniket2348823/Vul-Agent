"""
Forensic Evidence Collector for Browser-Based Testing
Captures screenshots, DOM snapshots, network logs, and console output.
"""

import json
import gzip
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import base64
import asyncio


class ForensicCollector:
    """
    Collects and stores forensic evidence from browser-based security testing.
    Supports both OpenClaw and PinchTab engines.
    """
    
    def __init__(self, storage_dir: str = "scan_states/forensics"):
        """
        Initialize the forensic collector.
        
        Args:
            storage_dir: Directory to store forensic evidence
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_cache: Dict[str, List[Dict[str, Any]]] = {}
        
    async def capture_screenshot(
        self,
        scan_id: str,
        context,
        engine: str,
        label: str = "screenshot",
        full_page: bool = True
    ) -> Optional[str]:
        """
        Capture a screenshot from the browser.
        
        Args:
            scan_id: Scan identifier
            context: Browser context (OpenClaw page or PinchTab client)
            engine: Engine type ("openclaw" or "pinchtab")
            label: Label for the screenshot
            full_page: Whether to capture full page or viewport only
            
        Returns:
            Path to saved screenshot, or None if failed
        """
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{scan_id}_{label}_{timestamp}.png"
            filepath = self.storage_dir / scan_id / "screenshots" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            if engine == "openclaw":
                # OpenClaw/Playwright screenshot
                await context.screenshot(path=str(filepath), full_page=full_page)
            elif engine == "pinchtab":
                # PinchTab screenshot (placeholder - depends on PinchTab API)
                # screenshot_data = await context.screenshot()
                # with open(filepath, 'wb') as f:
                #     f.write(screenshot_data)
                pass
            
            # Store metadata
            self._add_evidence(scan_id, {
                "type": "screenshot",
                "label": label,
                "filepath": str(filepath),
                "timestamp": timestamp,
                "engine": engine,
                "full_page": full_page
            })
            
            return str(filepath)
            
        except Exception as e:
            print(f"[ForensicCollector] Screenshot capture failed: {e}")
            return None
    
    async def capture_dom_snapshot(
        self,
        scan_id: str,
        context,
        engine: str,
        label: str = "dom",
        compress: bool = True
    ) -> Optional[str]:
        """
        Capture a DOM snapshot (HTML source).
        
        Args:
            scan_id: Scan identifier
            context: Browser context
            engine: Engine type
            label: Label for the snapshot
            compress: Whether to gzip compress the snapshot
            
        Returns:
            Path to saved snapshot, or None if failed
        """
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
            ext = ".html.gz" if compress else ".html"
            filename = f"{scan_id}_{label}_{timestamp}{ext}"
            filepath = self.storage_dir / scan_id / "dom" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Get HTML content
            if engine == "openclaw":
                html_content = await context.content()
            elif engine == "pinchtab":
                # PinchTab DOM extraction (placeholder)
                html_content = ""  # await context.get_html()
            else:
                return None
            
            # Save with optional compression
            if compress:
                with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                    f.write(html_content)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            
            # Store metadata
            self._add_evidence(scan_id, {
                "type": "dom_snapshot",
                "label": label,
                "filepath": str(filepath),
                "timestamp": timestamp,
                "engine": engine,
                "compressed": compress,
                "size_bytes": len(html_content)
            })
            
            return str(filepath)
            
        except Exception as e:
            print(f"[ForensicCollector] DOM snapshot failed: {e}")
            return None
    
    async def capture_network_logs(
        self,
        scan_id: str,
        network_events: List[Dict[str, Any]],
        label: str = "network",
        compress: bool = True
    ) -> Optional[str]:
        """
        Save network traffic logs.
        
        Args:
            scan_id: Scan identifier
            network_events: List of network events (requests/responses)
            label: Label for the logs
            compress: Whether to gzip compress the logs
            
        Returns:
            Path to saved logs, or None if failed
        """
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
            ext = ".json.gz" if compress else ".json"
            filename = f"{scan_id}_{label}_{timestamp}{ext}"
            filepath = self.storage_dir / scan_id / "network" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Serialize network events
            json_data = json.dumps(network_events, indent=2)
            
            # Save with optional compression
            if compress:
                with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                    f.write(json_data)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(json_data)
            
            # Store metadata
            self._add_evidence(scan_id, {
                "type": "network_logs",
                "label": label,
                "filepath": str(filepath),
                "timestamp": timestamp,
                "compressed": compress,
                "event_count": len(network_events)
            })
            
            return str(filepath)
            
        except Exception as e:
            print(f"[ForensicCollector] Network log capture failed: {e}")
            return None
    
    async def capture_console_logs(
        self,
        scan_id: str,
        console_messages: List[Dict[str, Any]],
        label: str = "console",
        compress: bool = False
    ) -> Optional[str]:
        """
        Save console output logs.
        
        Args:
            scan_id: Scan identifier
            console_messages: List of console messages
            label: Label for the logs
            compress: Whether to gzip compress the logs
            
        Returns:
            Path to saved logs, or None if failed
        """
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
            ext = ".json.gz" if compress else ".json"
            filename = f"{scan_id}_{label}_{timestamp}{ext}"
            filepath = self.storage_dir / scan_id / "console" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Serialize console messages
            json_data = json.dumps(console_messages, indent=2)
            
            # Save with optional compression
            if compress:
                with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                    f.write(json_data)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(json_data)
            
            # Store metadata
            self._add_evidence(scan_id, {
                "type": "console_logs",
                "label": label,
                "filepath": str(filepath),
                "timestamp": timestamp,
                "compressed": compress,
                "message_count": len(console_messages)
            })
            
            return str(filepath)
            
        except Exception as e:
            print(f"[ForensicCollector] Console log capture failed: {e}")
            return None
    
    async def bundle_evidence(
        self,
        scan_id: str,
        vuln_id: Optional[str] = None,
        include_types: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Bundle all evidence for a scan into a single archive.
        
        Args:
            scan_id: Scan identifier
            vuln_id: Optional vulnerability identifier
            include_types: Optional list of evidence types to include
            
        Returns:
            Path to evidence bundle, or None if failed
        """
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            bundle_name = f"{scan_id}_evidence_{timestamp}.json.gz"
            
            if vuln_id:
                bundle_name = f"{scan_id}_{vuln_id}_evidence_{timestamp}.json.gz"
            
            bundle_path = self.storage_dir / scan_id / bundle_name
            bundle_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Collect evidence metadata
            evidence_list = self.evidence_cache.get(scan_id, [])
            
            if include_types:
                evidence_list = [e for e in evidence_list if e["type"] in include_types]
            
            bundle_data = {
                "scan_id": scan_id,
                "vuln_id": vuln_id,
                "timestamp": timestamp,
                "evidence_count": len(evidence_list),
                "evidence": evidence_list
            }
            
            # Save bundle
            with gzip.open(bundle_path, 'wt', encoding='utf-8') as f:
                json.dump(bundle_data, f, indent=2)
            
            return str(bundle_path)
            
        except Exception as e:
            print(f"[ForensicCollector] Evidence bundling failed: {e}")
            return None
    
    def _add_evidence(self, scan_id: str, evidence: Dict[str, Any]):
        """
        Add evidence metadata to cache.
        
        Args:
            scan_id: Scan identifier
            evidence: Evidence metadata
        """
        if scan_id not in self.evidence_cache:
            self.evidence_cache[scan_id] = []
        
        self.evidence_cache[scan_id].append(evidence)
    
    def get_evidence_summary(self, scan_id: str) -> Dict[str, Any]:
        """
        Get summary of collected evidence for a scan.
        
        Args:
            scan_id: Scan identifier
            
        Returns:
            Evidence summary
        """
        evidence_list = self.evidence_cache.get(scan_id, [])
        
        summary = {
            "scan_id": scan_id,
            "total_evidence": len(evidence_list),
            "by_type": {},
            "by_engine": {},
            "storage_path": str(self.storage_dir / scan_id)
        }
        
        for evidence in evidence_list:
            # Count by type
            ev_type = evidence["type"]
            summary["by_type"][ev_type] = summary["by_type"].get(ev_type, 0) + 1
            
            # Count by engine
            engine = evidence.get("engine", "unknown")
            summary["by_engine"][engine] = summary["by_engine"].get(engine, 0) + 1
        
        return summary
    
    async def cleanup_old_evidence(self, max_age_days: int = 7) -> int:
        """
        Remove old forensic evidence files.
        
        Args:
            max_age_days: Maximum age of evidence in days
            
        Returns:
            Number of files cleaned up
        """
        try:
            from datetime import timedelta
            
            cleaned = 0
            cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)
            
            for scan_dir in self.storage_dir.iterdir():
                if not scan_dir.is_dir():
                    continue
                
                for evidence_file in scan_dir.rglob("*"):
                    if not evidence_file.is_file():
                        continue
                    
                    # Check file modification time
                    mtime = datetime.fromtimestamp(evidence_file.stat().st_mtime)
                    
                    if mtime < cutoff_time:
                        evidence_file.unlink()
                        cleaned += 1
            
            return cleaned
            
        except Exception as e:
            print(f"[ForensicCollector] Cleanup failed: {e}")
            return 0
