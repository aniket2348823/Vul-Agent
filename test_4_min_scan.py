import requests
import time
import sys

TARGET = "http://testphp.vulnweb.com/"

payload = {
    "target_url": TARGET,
    "method": "GET",
    "headers": {"User-Agent": "Antigravity/6.0"},
    "body": "",
    "modules": [
        "tech_sqli", "logic_idor"
    ],
    "filters": [],
    "velocity": 10,
    "duration": 240  # 4 minutes
}

print(f"Starting 4-MINUTE (240s) scan against {TARGET}...")
try:
    resp = requests.post("http://127.0.0.1:8000/api/attack/fire", json=payload)
    if resp.status_code == 200:
        scan_id = resp.json().get("scan_id")
        print(f"Scan launched! ID: {scan_id}")
    else:
        print(f"Failed to launch: {resp.text}")
        sys.exit(1)
        
    print("Polling scan status...")
    
    while True:
        time.sleep(10)
        try:
            stats = requests.get("http://127.0.0.1:8000/api/state/stats").json()
            scan = next((s for s in stats.get("scans", []) if s["id"] == scan_id), None)
            if scan:
                print(f"[{scan.get('duration', '?')}] Status: {scan['status']} | Results: {len(scan.get('results', []))}")
                if scan['status'] in ['Completed', 'Interrupted', 'Vulnerable']:
                    break
            else:
                print("Checking...")
        except BaseException as e:
            print(f"Backend offline?: {e}")
            
    # Check PDF
    print("Testing PDF Generation Endpoint...")
    pdf_resp = requests.get(f"http://127.0.0.1:8000/api/reports/pdf/{scan_id}")
    print(f"PDF Endpoint Status: {pdf_resp.status_code}")
    if pdf_resp.status_code == 200:
        print("PDF SUCCESS!")
    else:
        print("PDF FAILED!")

except Exception as e:
    print(f"Error: {e}")
