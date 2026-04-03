from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
import asyncio

from backend.core.state import stats_db_manager
from backend.core.reporting import ReportGenerator
from backend.core.config import settings
from backend.core.database import db_manager # [NEW] Distributed Intelligence Backbone

router = APIRouter()
REPORTS_DIR = settings.REPORTS_DIR

@router.get("/download/{filename}")
async def download_report_file(filename: str):
    file_path = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=filename, media_type='application/pdf')

@router.get("/")
async def list_reports():
    """
    Lists all generated PDF reports.
    """
    if not os.path.exists(REPORTS_DIR):
        return []
    
    files = [f for f in os.listdir(REPORTS_DIR) if f.endswith(".pdf")]
    return [{"name": f, "path": f"/api/reports/pdf/{f.replace('Scan_Report_', '').replace('.pdf', '')}"} for f in files]

@router.get("/pdf/{scan_id}")
async def generate_pdf_report(scan_id: str):
    """
    Serves or Generates a PDF security report.
    V6 OMEGA Stabilization: strictly awaits generation and validates paths.
    """
    filename = f"Scan_Report_{scan_id}.pdf"
    report_path = os.path.join(str(REPORTS_DIR), filename) # Force string conversion to fix TypeError
    
    try:
        # 1. Check for Cached Report
        if os.path.exists(report_path):
            return FileResponse(
                path=report_path,
                media_type='application/pdf',
                filename=filename
            )
        
        # 2. On-Demand Generation if missing
        scan_data = next((s for s in stats_db_manager.get_stats().get("scans", []) if s["id"] == scan_id), None)
        if not scan_data:
            raise HTTPException(status_code=404, detail="Scan record not found.")

        # Trigger Real-Time Report Generation (V6 HARDENED)
        try:
            reporter = ReportGenerator()
            # Fetch events from the local scan record first
            scan_events = scan_data.get("events", [])
            
            # [NEW] Sync findings from Supabase for high-fidelity reports
            try:
                await db_manager.initialize()
                supabase_vulns = await db_manager.get_vulnerabilities(scan_id)
                for v in supabase_vulns:
                    # Map Supabase Row to HiveEvent format for the generator
                    scan_events.append({
                        "type": "VULN_CONFIRMED",
                        "source": v.get("validated_by", "EliteDB"),
                        "payload": {
                            "type": v.get("vuln_type"),
                            "url": v.get("endpoint"),
                            "severity": v.get("severity"),
                            "evidence": v.get("evidence"),
                            "description": v.get("description")
                        }
                    })
            except Exception as db_err:
                print(f"[REPORTER] Supabase fetch failed, falling back to local events: {db_err}")

            telemetry = scan_data.get("telemetry", {})
            target_url = scan_data.get("target", scan_data.get("name", "Unknown"))

            # CRITICAL FIX: Strictly await the report generation coroutine
            print(f"[REPORTER] Triggering On-Demand Generation for {scan_id}...")
            await reporter.generate_report(
                scan_id=scan_id,
                events=scan_events,
                target_url=target_url,
                telemetry=telemetry
            )
            
            # Verify the file was actually written after await
            if os.path.exists(report_path):
                return FileResponse(path=report_path, media_type='application/pdf', filename=filename)
            else:
                raise HTTPException(status_code=500, detail="Report generation failed to materialize.")

        except Exception as gen_err:
             print(f"âŒ ON-DEMAND GEN FAILED: {gen_err}")
             raise HTTPException(status_code=500, detail=f"Generation Failure: {str(gen_err)}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Atomic Serve Failure: {str(e)}")

@router.get("/consolidated")
async def generate_consolidated_report():
    """
    Generates a high-fidelity intelligence report aggregating ALL scans.
    Performs cross-scan deduplication and strategic multi-vector analysis.
    """
    scan_id = "Consolidated_Intelligence"
    filename = f"Scan_Report_{scan_id}.pdf"
    report_path = os.path.join(str(REPORTS_DIR), filename)
    
    try:
        # Aggregation Logic
        stats = stats_db_manager.get_stats()
        all_scans = stats.get("scans", [])
        all_events = stats.get("events", [])
        
        if not all_scans:
            raise HTTPException(status_code=404, detail="No scan data available for consolidation.")

        consolidated_events = []
        total_requests = 0
        total_duration_secs = 0
        
        # Deduplication Map: (type, url, payload_hash) -> event
        dedup_map = {}
        
        for scan in all_scans:
            s_id = scan["id"]
            s_events = [e for e in all_events if e.get("scan_id") == s_id]
            
            # Aggregate Telemetry
            telemetry = scan.get("telemetry", {})
            total_requests += telemetry.get("total_requests", 0)
            # Duration parsing (approximate)
            try:
                dur_str = str(telemetry.get("duration", "0"))
                if "h" in dur_str:
                    # Logic for complex strings if needed
                    pass
                else:
                    total_duration_secs += int(dur_str.split()[0].replace('s', ''))
            except: pass
            
            # Deduplicate Vulnerabilities across scans
            for e in s_events:
                if any(t in str(e.get('type', '')).upper() for t in ["VULN_CONFIRMED", "HIDDEN_TEXT", "PROMPT_INJECTION"]):
                    payload = e.get('payload', {})
                    v_type = str(payload.get('type', '')).upper()
                    v_url = str(payload.get('url', '')).lower()
                    v_data = str(payload.get('payload', payload.get('data', ''))).strip().lower()[:100]
                    
                    sig = f"{v_type}|{v_url}|{v_data}"
                    if sig not in dedup_map:
                        dedup_map[sig] = e
                        consolidated_events.append(e)
                else:
                    # Non-vuln event? Maybe include some logs for timeline
                    if len(consolidated_events) < 500: # Cap timeline size
                        consolidated_events.append(e)

        # Build Consolidated Telemetry
        consolidated_telemetry = {
            "start_time": all_scans[0].get("start_time"),
            "end_time": all_scans[-1].get("end_time"),
            "duration": f"{total_duration_secs}s",
            "total_requests": total_requests,
            "avg_latency_ms": sum(s.get("telemetry", {}).get("avg_latency_ms", 0) for s in all_scans) / len(all_scans),
            "peak_concurrency": max(s.get("telemetry", {}).get("peak_concurrency", 0) for s in all_scans),
            "ai_calls": sum(s.get("telemetry", {}).get("ai_calls", 0) for s in all_scans)
        }

        # Generate the Report
        reporter = ReportGenerator()
        await reporter.generate_report(
            scan_id=scan_id,
            events=consolidated_events,
            target_url="MULTI-TARGET CONSOLIDATED ASSET",
            telemetry=consolidated_telemetry
        )

        if os.path.exists(report_path):
            return FileResponse(path=report_path, media_type='application/pdf', filename=filename)
        else:
            raise HTTPException(status_code=500, detail="Consolidated report generation failed.")

    except Exception as e:
        print(f"❌ CONSOLIDATED GEN FAILED: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- PROBLEM 12 FIX: Scan Diff Engine ---

@router.get("/diff/{scan_id_1}/{scan_id_2}")
async def diff_scans(scan_id_1: str, scan_id_2: str):
    """
    Compare two scans to identify new, fixed, worsened, and improved vulnerabilities.
    Essential for iterative security validation.
    """
    # Try sharded state first, fallback to stats.json
    scan1_data = await stats_db_manager.read_scan_state(scan_id_1)
    scan2_data = await stats_db_manager.read_scan_state(scan_id_2)

    # Fallback to stats.json scans
    if not scan1_data:
        scan1_data = next((s for s in stats_db_manager.get_stats().get("scans", []) if s["id"] == scan_id_1), None)
    if not scan2_data:
        scan2_data = next((s for s in stats_db_manager.get_stats().get("scans", []) if s["id"] == scan_id_2), None)

    if not scan1_data or not scan2_data:
        raise HTTPException(status_code=404, detail="One or both scan IDs not found.")

    # Extract vulnerabilities from results
    def extract_vulns(scan_data):
        vulns = {}
        for r in scan_data.get("results", scan_data.get("vulnerabilities", [])):
            payload = r.get("payload", r) if isinstance(r, dict) else {}
            vid = payload.get("vuln_id", payload.get("id", payload.get("url", "") + "|" + payload.get("type", "")))
            vulns[vid] = payload
        return vulns

    vulns1 = extract_vulns(scan1_data)
    vulns2 = extract_vulns(scan2_data)

    new_vulns = [v for vid, v in vulns2.items() if vid not in vulns1]
    fixed_vulns = [v for vid, v in vulns1.items() if vid not in vulns2]
    worsened = []
    improved = []

    for vid in set(vulns1) & set(vulns2):
        old_score = vulns1[vid].get("final_risk_score", vulns1[vid].get("confidence", 0))
        new_score = vulns2[vid].get("final_risk_score", vulns2[vid].get("confidence", 0))
        if isinstance(old_score, (int, float)) and isinstance(new_score, (int, float)):
            if new_score > old_score + 0.1:
                worsened.append({"vuln_id": vid, "old_score": old_score, "new_score": new_score})
            elif new_score < old_score - 0.1:
                improved.append({"vuln_id": vid, "old_score": old_score, "new_score": new_score})

    return {
        "scan_1": scan_id_1,
        "scan_2": scan_id_2,
        "new_vulnerabilities": new_vulns,
        "fixed_vulnerabilities": fixed_vulns,
        "worsened": worsened,
        "improved": improved,
        "summary": {
            "new": len(new_vulns),
            "fixed": len(fixed_vulns),
            "worsened": len(worsened),
            "improved": len(improved)
        }
    }


# --- PROBLEM 15 FIX: Incremental Live Reports ---

@router.get("/live/{scan_id}")
async def get_live_report(scan_id: str):
    """
    Get the current live report state for an active or completed scan.
    Allows viewing findings mid-scan without waiting for completion.
    """
    # Try sharded state first
    data = await stats_db_manager.read_scan_state(scan_id)

    # Fallback to stats.json
    if not data:
        scan = next((s for s in stats_db_manager.get_stats().get("scans", []) if s["id"] == scan_id), None)
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found.")
        data = scan

    events = data.get("events", [])
    vuln_events = [e for e in events if e.get("type") in ["VULN_CONFIRMED", "VULN_CANDIDATE"]]

    return {
        "scan_id": scan_id,
        "status": data.get("status", "unknown"),
        "vulnerability_count": len(vuln_events),
        "vulnerabilities": vuln_events[:100],  # Cap for performance
        "total_events": len(events),
        "started_at": data.get("timestamp", data.get("started_at")),
        "last_updated": data.get("last_updated", data.get("timestamp")),
        "results": data.get("results", [])
    }

