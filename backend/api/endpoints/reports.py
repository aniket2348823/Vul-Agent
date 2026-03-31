from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
import asyncio

from backend.core.state import stats_db_manager
from backend.core.reporting import ReportGenerator
from backend.core.config import settings

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
            # Fetch events and telemetry for this specific scan
            all_events = stats_db_manager.get_stats().get("events", [])
            scan_events = [e for e in all_events if e.get("scan_id") == scan_id]
            telemetry = scan_data.get("telemetry", {})
            target_url = scan_data.get("target", "Unknown")

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
    raise HTTPException(status_code=501, detail="Consolidated reports not yet implemented in V6 OMEGA.")
