import asyncio
import websockets
import aiohttp
import json
import random
import time

WS_URL = "ws://127.0.0.1:8000/stream?client_type=spy"
API_URL = "http://127.0.0.1:8000/api/recon/ingest"

endpoints = [
    "/api/v1/users/login",
    "/api/v1/payments/checkout",
    "/admin/config.php",
    "/graphql",
    "/index.html",
    "/assets/main.js"
]

method = ["GET", "POST", "PUT", "DELETE"]

async def send_traffic():
    async with aiohttp.ClientSession() as session:
        while True:
            # Simulate intercepting a packet
            payload = {
                "url": f"https://target-app.internal{random.choice(endpoints)}",
                "method": random.choice(method),
                "headers": {"User-Agent": "Mozilla/5.0", "x-scanner": "v12-engine"},
                "body": '{"test": "data"}' if random.random() > 0.5 else "",
                "timestamp": time.time(),
                "payload": {}
            }
            
            try:
                async with session.post(API_URL, json=payload) as resp:
                    pass
            except Exception as e:
                print(f"Failed to push traffic: {e}")
                
            await asyncio.sleep(random.uniform(0.1, 0.4)) # High speed traffic simulation

async def main():
    print("[SPY SIMULATOR] Connecting to WebSocket...")
    try:
        async with websockets.connect(WS_URL) as ws:
            print("[SPY SIMULATOR] WebSocket Connected. Interception Active.")
            
            # Start pushing traffic while WS stays open
            asyncio.create_task(send_traffic())
            
            # Keep connection alive
            while True:
                await ws.recv()
    except Exception as e:
        print(f"[SPY SIMULATOR] Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
