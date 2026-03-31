import requests
import json
import time

payload = {
    "target_url": "http://testphp.vulnweb.com/",
    "method": "GET",
    "headers": {"User-Agent": "Antigravity/1.0"},
    "velocity": 10,
    "modules": ["tech_sqli"],
    "duration": 10
}

try:
    print("Initiating scan...")
    response = requests.post("http://127.0.0.1:8000/api/attack/fire", json=payload)
    print("Status:", response.status_code)
    print("Response:", response.text)
    
    if response.status_code == 200:
        data = response.json()
        scan_id = data.get("scan_id")
        print(f"Scan ID: {scan_id}")
        
        # Poll for completion
        for _ in range(20): # At most 40 seconds
            time.sleep(2)
            r = requests.get("http://127.0.0.1:8000/api/dashboard/stats")
            stats = r.json()
            # print(stats)
            scans = stats.get("metrics", {}).get("recent_scans", [])
            active = stats.get("metrics", {}).get("active_scans", 0)
            
            for s in scans:
                if s["id"] == scan_id:
                    print(f"Status in DB: {s['status']}")
                    if s["status"] == "Completed":
                        print("SCAN COMPLETED SUCCESSFULLY!")
                        exit(0)
            print(f"Polling... active scans: {active}")
        
        print("Test failed: Scan did not complete within 40 seconds.")
except Exception as e:
    print(f"Test script error: {e}")
