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
    SCAN_TIMEOUT: int = int(os.getenv("SCAN_TIMEOUT", "600"))  # Default 10 minutes
    ALPHA_ENABLE_V6: bool = os.getenv("ALPHA_ENABLE_V6", "true").lower() == "true"
    ALPHA_TOOL_ROOT: str = os.getenv("ALPHA_TOOL_ROOT", r"D:\projects")
    ALPHA_ARTIFACT_ROOT: str = os.getenv("ALPHA_ARTIFACT_ROOT", "data/scans")
    ALPHA_DEFAULT_MODE: str = os.getenv("ALPHA_DEFAULT_MODE", "STANDARD")
    ALPHA_DEFAULT_RPS: int = int(os.getenv("ALPHA_DEFAULT_RPS", "50"))
    ALPHA_MAX_HTTPX_THREADS: int = int(os.getenv("ALPHA_MAX_HTTPX_THREADS", "50"))
    ALPHA_MAX_CRAWL_DEPTH: int = int(os.getenv("ALPHA_MAX_CRAWL_DEPTH", "3"))
    ALPHA_ENABLE_EXTERNAL_TOOLS: bool = os.getenv("ALPHA_ENABLE_EXTERNAL_TOOLS", "false").lower() == "true"
    ALPHA_TOOL_TIMEOUT_SECONDS: int = int(os.getenv("ALPHA_TOOL_TIMEOUT_SECONDS", "180"))
    ALPHA_ENABLE_PINCHTAB: bool = os.getenv("ALPHA_ENABLE_PINCHTAB", "true").lower() == "true"
    ALPHA_EXPLICIT_AUTHORIZATION: bool = os.getenv("ALPHA_EXPLICIT_AUTHORIZATION", "false").lower() == "true"
    PINCHTAB_BASE_URL: str = os.getenv("PINCHTAB_BASE_URL", "http://127.0.0.1:9867")
    ALPHA_ENABLE_NEO4J: bool = os.getenv("ALPHA_ENABLE_NEO4J", "false").lower() == "true"
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")
    ALPHA_ENABLE_OPENCTI_EXPORT: bool = os.getenv("ALPHA_ENABLE_OPENCTI_EXPORT", "false").lower() == "true"
    OPENCTI_URL: str = os.getenv("OPENCTI_URL", "")
    OPENCTI_TOKEN: str = os.getenv("OPENCTI_TOKEN", "")

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
    base_url: str = os.getenv("PINCHTAB_BASE_URL", "http://127.0.0.1:9867")
    enabled: bool = os.getenv("ALPHA_ENABLE_PINCHTAB", "true").lower() == "true"
    headless: bool = os.getenv("PINCHTAB_HEADLESS", "true").lower() == "true"
    browser_type: str = "chromium"
    timeout: int = 30000
    user_agent: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

@dataclass
class OpenClawConfig:
    enabled: bool = os.getenv("OPENCLAW_ENABLED", "true").lower() == "true"
    headless: bool = os.getenv("OPENCLAW_HEADLESS", "true").lower() == "true"
    browser_type: str = os.getenv("OPENCLAW_BROWSER", "chromium")
    timeout: int = int(os.getenv("OPENCLAW_TIMEOUT", "30000"))
    stealth_mode: bool = os.getenv("OPENCLAW_STEALTH", "true").lower() == "true"
    user_agent: str = os.getenv("OPENCLAW_USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    viewport_width: int = int(os.getenv("OPENCLAW_VIEWPORT_WIDTH", "1920"))
    viewport_height: int = int(os.getenv("OPENCLAW_VIEWPORT_HEIGHT", "1080"))
    max_contexts: int = int(os.getenv("OPENCLAW_MAX_CONTEXTS", "5"))

@dataclass
class HybridBrowserConfig:
    """Configuration for hybrid OpenClaw + PinchTab browser orchestration."""
    enabled: bool = os.getenv("HYBRID_BROWSER_ENABLED", "true").lower() == "true"
    default_engine: str = os.getenv("HYBRID_DEFAULT_ENGINE", "auto")  # auto, openclaw, pinchtab
    auto_fallback: bool = os.getenv("HYBRID_AUTO_FALLBACK", "true").lower() == "true"
    session_sharing: bool = os.getenv("HYBRID_SESSION_SHARING", "true").lower() == "true"
    forensics_enabled: bool = os.getenv("HYBRID_FORENSICS_ENABLED", "true").lower() == "true"
    forensics_dir: str = os.getenv("HYBRID_FORENSICS_DIR", "scan_states/forensics")
    session_dir: str = os.getenv("HYBRID_SESSION_DIR", "scan_states/sessions")

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
        self.openclaw = OpenClawConfig()
        self.hybrid_browser = HybridBrowserConfig()
        self.master = MasterConfig()

    def get_all(self) -> Dict[str, Any]:
        """Serializes current configuration for logging or UI sync."""
        return {
            "redis": self.redis.__dict__,
            "supabase": {"url": self.supabase.url, "key": "MASKED", "openrouter_key": "MASKED"},
            "worker": self.worker.__dict__,
            "pinchtab": self.pinchtab.__dict__,
            "openclaw": self.openclaw.__dict__,
            "hybrid_browser": self.hybrid_browser.__dict__,
            "master": self.master.__dict__
        }

if __name__ == "__main__":
    # Test Config Mapping
    config = ConfigManager()
    print("Xytherion Config Matrix Loaded.")
    print(json.dumps(config.get_all(), indent=2))
