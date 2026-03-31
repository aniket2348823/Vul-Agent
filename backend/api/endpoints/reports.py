from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from io import BytesIO
import uuid
import random
import os

from backend.core.state import stats_db_manager
from backend.core.reporting import ReportGenerator
from backend.core.config import settings

router = APIRouter()
REPORTS_DIR = settings.REPORTS_DIR

# Ensure directory exists is now handled by config.py

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
    # Extract scan_id from Scan_Report_{id}.pdf
    def extract_id(fname):
        if fname.startswith("Scan_Report_") and fname.endswith(".pdf"):
            return fname.replace("Scan_Report_", "").replace(".pdf", "")
        return fname

    return [{"name": f, "path": f"/api/reports/pdf/{extract_id(f)}"} for f in files]
@router.get("/pdf/{scan_id}")
async def generate_pdf_report(scan_id: str):
    """
    Serves a generated PDF security report.
    Unified Cache-Only Dispatch (V6).
    """
    filename = f"Scan_Report_{scan_id}.pdf"
    report_path = os.path.join(REPORTS_DIR, filename)
    
    try:
        if os.path.exists(report_path):
            return FileResponse(
                path=report_path,
                media_type='application/pdf',
                filename=f"Scan_Report_{scan_id}.pdf"
            )
        else:
            # Check if scan exists but report isn't ready
            scan_data = next((s for s in stats_db_manager.get_stats().get("scans", []) if s["id"] == scan_id), None)
            if not scan_data:
                raise HTTPException(status_code=404, detail="Scan record not found.")
            
            raise HTTPException(status_code=404, detail="AI Report is still being finalized. Please wait for the 'Ready' signal.")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Atomic Serve Failure: {str(e)}")

@router.get("/consolidated")
async def generate_consolidated_report():
    """
    Placeholder for consolidated report generation.
    """
    raise HTTPException(status_code=501, detail="Consolidated reports not yet implemented in Visual Architect mode.")

