import sys
import os
# Ensure the backend is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from backend.core.reporting import ReportGenerator
from datetime import datetime, timedelta

import asyncio

async def run_test():
    print(">>> Initiating Report Generation Test Sequence...")
    
    # Mock Start Time
    start_time = datetime.now()
    
    # Mock Event Stream matching the Kill Chain
    events = [
        # ... (same events)
    ]
    
    # Re-using events from the file content
    events = [
        {
            "timestamp": start_time + timedelta(seconds=3.12),
            "type": "TARGET_ACQUIRED",
            "source": "agent_alpha",
            "payload": {"url": "http://api.nexus-commerce.io/api/v1/cart/update", "method": "POST"}
        },
        {
            "timestamp": start_time + timedelta(seconds=15.004),
            "type": "JOB_COMPLETED", # Mapped to PAYLOAD_GEN for Sigma
            "source": "agent_sigma",
            "payload": {"status": "SUCCESS"}
        },
        {
            "timestamp": start_time + timedelta(seconds=22.45),
            "type": "LOG", # Mapped to INJECTION for Beta
            "source": "agent_beta",
            "payload": "Payload -9223372036854775808..."
        },
        {
            "timestamp": start_time + timedelta(seconds=23.15),
            "type": "VULN_CONFIRMED", # Mapped to VERIFICATION
            "source": "agent_gamma",
            "payload": {
                "type": "EXPLOIT",
                "id": "AG-TEST-01",
                "payload": {"type": "logic_arithmetic_overflow", "payload": "-9223372036854775808"}
            }
        },
        {
            "timestamp": start_time + timedelta(seconds=42.0),
            "type": "LOG", # Mapped to ARCHIVE for Kappa
            "source": "agent_kappa",
            "payload": "Vector logic_overflow_v2 stored in Hive Memory."
        }
    ]
    
    target_url = "api.nexus-commerce.io"
    scan_id = "VERIFICATION_TEST_001"
    
    generator = ReportGenerator()
    try:
        output_path = await generator.generate_report(scan_id, events, target_url)
        print(f"[SUCCESS] Report generated at: {output_path}")
    except Exception as e:
        print(f"[FAILURE] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())
