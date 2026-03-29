import os
import json
from typing import Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

# XYTHERION CONFIGURATION MATRIX
# Role: Dynamic environment-based settings for the distributed swarm.

@dataclass
class RedisConfig:
    url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    max_connections: int = 10
    socket_timeout: int = 5

@dataclass
class SupabaseConfig:
    url: str = os.getenv("SUPABASE_URL", "")
    key: str = os.getenv("SUPABASE_KEY", "")

@dataclass
class WorkerConfig:
    worker_id: str = os.getenv("WORKER_ID", "")
    specialty: str = os.getenv("WORKER_SPECIALTY", "hybrid")
    max_concurrent_tasks: int = 5
    heartbeat_interval: int = 30

@dataclass
class PinchTabConfig:
    headless: bool = os.getenv("PINCHTAB_HEADLESS", "true").lower() == "true"
    browser_type: str = "chromium"
    timeout: int = 30000
    user_agent: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

@dataclass
class MasterConfig:
    max_workers: int = 50
    distribution_interval: int = 10
    worker_timeout: int = 180

class ConfigManager:
    """Central configuration management using the Singleton pattern."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_all()
        return cls._instance
    
    def _load_all(self):
        self.redis = RedisConfig()
        self.supabase = SupabaseConfig()
        self.worker = WorkerConfig()
        self.pinchtab = PinchTabConfig()
        self.master = MasterConfig()

    def get_all(self) -> Dict[str, Any]:
        """Serializes current configuration for logging or UI sync."""
        return {
            "redis": self.redis.__dict__,
            "supabase": {"url": self.supabase.url, "key": "MASKED"},
            "worker": self.worker.__dict__,
            "pinchtab": self.pinchtab.__dict__,
            "master": self.master.__dict__
        }

if __name__ == "__main__":
    # Test Config Mapping
    config = ConfigManager()
    print("Xytherion Config Matrix Loaded.")
    print(json.dumps(config.get_all(), indent=2))
