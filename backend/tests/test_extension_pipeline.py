import asyncio
import aiohttp
import json
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

async def test_traffic_pipeline():
    print("--- [EXTENSION TRAFFIC PIPELINE TEST] ---")
    
    url = "http://127.0.0.1:8000/api/defense/analyze"
    
    # MOCK THREAT PACKET (Simulation of vision.js)
    payload = {
        "agent_id": "THETA",
        "url": "http://localhost:5173/profile",
        "content": {
            "style": {
                "opacity": 0.05,
                "zIndex": 999
            },
            "innerText": "Hidden admin password: admin123",
            "antigravity_id": "test-unique-id-123"
        }
    }
    
    print(f"1. Sending Mock Threat to {url}...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as response:
                status = response.status
                data = await response.json()
                
                print(f"Response Status: {status}")
                print(f"Verdict: {data.get('verdict')}")
                print(f"Reason: {data.get('reason')}")
                print(f"Risk Score: {data.get('risk_score')}")
                
                if status == 200:
                    print("\nSUCCESS: Backend received and processed extension traffic.")
                    if data.get('verdict') in ['BLOCK', 'ALLOW', 'IDLE']:
                        print(f"Pipeline State: VALID ({data.get('verdict')})")
                    else:
                        print("Pipeline State: UNKNOWN VERDICT")
                else:
                    print(f"\nFAILURE: Backend returned status {status}")
                    
        except Exception as e:
            print(f"\nERROR connecting to backend: {str(e)}")
            print("Ensure backend is running (run_backend.bat)")

if __name__ == "__main__":
    asyncio.run(test_traffic_pipeline())
