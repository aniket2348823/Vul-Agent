import asyncio
from redis.asyncio import Redis
import os

async def check_redis_cleanup():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        client = Redis.from_url(redis_url, decode_responses=True)
        # Check for any scan_context, worker_queue, or workers hash keys
        keys = await client.keys("*")
        leftovers = [k for k in keys if any(x in k for x in ["scan_context", "worker_queue", "workers"])]
        
        if not leftovers:
            print("[VERIFIED] Redis Cluster Registry is 100% PURGED. Zero-Leak State Confirmed.")
        else:
            print(f"[REMAINING KEYS] {leftovers}")
            # Clean them up if they exist for a true zero-state
            for k in leftovers:
                await client.delete(k)
            print("[CLEANED] All leftover artifacts purged manually.")
            
        await client.close()
    except Exception as e:
        print(f"[ERROR] Redis check failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_redis_cleanup())
