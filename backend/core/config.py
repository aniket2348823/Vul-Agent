import os
import json
from typing import Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Initialize Environment
load_dotenv()

# --- VUL AGENT: UNIFIED PATH RESOLUTION (V6-OMEGA) ---
# Ensure absolute roots regardless of where the app is launched
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__)) # .../backend/core
BACKEND_DIR = os.path.abspath(os.path.join(CONFIG_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")

# Ensure critical directories exist
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# XYTHERION CONFIGURATION MATRIX
# Role: Dynamic environment-based settings for the distributed swarm.

@dataclass
class GlobalSettings:
    """Consolidated project-level settings."""
    PROJECT_ROOT: str = PROJECT_ROOT
    REPORTS_DIR: str = REPORTS_DIR
    STATIC_DIR: str = STATIC_DIR
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

settings = GlobalSettings()

@dataclass
class RedisConfig:
    url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    max_connections: int = 10
    socket_timeout: int = 5

@dataclass
class SupabaseConfig:
    url: str = os.getenv("SUPABASE_URL", "")
    key: str = os.getenv("SUPABASE_KEY", "")
    openrouter_key: str = os.getenv("OPENROUTER_API_KEY", "")

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
            "supabase": {"url": self.supabase.url, "key": "MASKED", "openrouter_key": "MASKED"},
            "worker": self.worker.__dict__,
            "pinchtab": self.pinchtab.__dict__,
            "master": self.master.__dict__
        }

if __name__ == "__main__":
    # Test Config Mapping
    config = ConfigManager()
    print("Xytherion Config Matrix Loaded.")
    print(json.dumps(config.get_all(), indent=2))
