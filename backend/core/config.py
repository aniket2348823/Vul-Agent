import os
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

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
    ALPHA_RECON_VIA_PLANNER: bool = os.getenv("ALPHA_RECON_VIA_PLANNER", "true").lower() == "true"
    ALPHA_RECON_TIMEOUT_SECONDS: int = int(os.getenv("ALPHA_RECON_TIMEOUT_SECONDS", "180"))
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
    """Central configuration management using the Singleton pattern with validation."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_all()
            cls._instance._validate_all()
        return cls._instance
    
    def _load_all(self):
        self.redis = RedisConfig()
        self.supabase = SupabaseConfig()
        self.worker = WorkerConfig()
        self.pinchtab = PinchTabConfig()
        self.openclaw = OpenClawConfig()
        self.hybrid_browser = HybridBrowserConfig()
        self.master = MasterConfig()
        self.validation_errors: List[str] = []
    
    def _validate_all(self):
        """Validate all configuration settings."""
        self.validation_errors = []
        
        # Validate Redis configuration
        self._validate_redis()
        
        # Validate Supabase configuration
        self._validate_supabase()
        
        # Validate Worker configuration
        self._validate_worker()
        
        # Validate Browser configurations
        self._validate_browser_configs()
        
        # Validate paths
        self._validate_paths()
        
        # Log validation results
        if self.validation_errors:
            logger.warning(f"[ConfigManager] Configuration validation found {len(self.validation_errors)} issues:")
            for error in self.validation_errors:
                logger.warning(f"  - {error}")
        else:
            logger.info("[ConfigManager] Configuration validation passed")
    
    def _validate_redis(self):
        """Validate Redis configuration."""
        if not self.redis.url:
            self.validation_errors.append("Redis URL is not configured")
        
        if self.redis.max_connections < 1:
            self.validation_errors.append("Redis max_connections must be at least 1")
        
        if self.redis.socket_timeout < 1:
            self.validation_errors.append("Redis socket_timeout must be at least 1 second")
    
    def _validate_supabase(self):
        """Validate Supabase configuration."""
        if self.supabase.url and not self.supabase.url.startswith(('http://', 'https://')):
            self.validation_errors.append("Supabase URL must start with http:// or https://")
        
        if self.supabase.url and not self.supabase.key:
            self.validation_errors.append("Supabase key is required when URL is configured")
    
    def _validate_worker(self):
        """Validate Worker configuration."""
        valid_specialties = ['hybrid', 'recon', 'attack', 'analysis']
        if self.worker.specialty not in valid_specialties:
            self.validation_errors.append(f"Worker specialty must be one of {valid_specialties}")
        
        if self.worker.max_concurrent_tasks < 1:
            self.validation_errors.append("Worker max_concurrent_tasks must be at least 1")
        
        if self.worker.heartbeat_interval < 5:
            self.validation_errors.append("Worker heartbeat_interval must be at least 5 seconds")
    
    def _validate_browser_configs(self):
        """Validate browser configurations."""
        # Validate PinchTab
        if self.pinchtab.enabled:
            if not self.pinchtab.base_url.startswith(('http://', 'https://')):
                self.validation_errors.append("PinchTab base_url must start with http:// or https://")
            
            if self.pinchtab.timeout < 1000:
                self.validation_errors.append("PinchTab timeout must be at least 1000ms")
            
            valid_browsers = ['chromium', 'firefox', 'webkit']
            if self.pinchtab.browser_type not in valid_browsers:
                self.validation_errors.append(f"PinchTab browser_type must be one of {valid_browsers}")
        
        # Validate OpenClaw
        if self.openclaw.enabled:
            if self.openclaw.timeout < 1000:
                self.validation_errors.append("OpenClaw timeout must be at least 1000ms")
            
            valid_browsers = ['chromium', 'firefox', 'webkit']
            if self.openclaw.browser_type not in valid_browsers:
                self.validation_errors.append(f"OpenClaw browser_type must be one of {valid_browsers}")
            
            if self.openclaw.viewport_width < 100 or self.openclaw.viewport_height < 100:
                self.validation_errors.append("OpenClaw viewport dimensions must be at least 100x100")
            
            if self.openclaw.max_contexts < 1:
                self.validation_errors.append("OpenClaw max_contexts must be at least 1")
        
        # Validate Hybrid Browser
        if self.hybrid_browser.enabled:
            valid_engines = ['auto', 'openclaw', 'pinchtab']
            if self.hybrid_browser.default_engine not in valid_engines:
                self.validation_errors.append(f"Hybrid default_engine must be one of {valid_engines}")
            
            if not self.openclaw.enabled and not self.pinchtab.enabled:
                self.validation_errors.append("Hybrid browser requires at least one engine (OpenClaw or PinchTab) to be enabled")
    
    def _validate_paths(self):
        """Validate critical paths exist and are writable."""
        critical_paths = [
            (REPORTS_DIR, "Reports directory"),
            (STATIC_DIR, "Static directory"),
        ]
        
        for path, name in critical_paths:
            path_obj = Path(path)
            if not path_obj.exists():
                try:
                    path_obj.mkdir(parents=True, exist_ok=True)
                    logger.info(f"[ConfigManager] Created {name}: {path}")
                except Exception as e:
                    self.validation_errors.append(f"{name} could not be created: {e}")
            elif not os.access(path, os.W_OK):
                self.validation_errors.append(f"{name} is not writable: {path}")
    
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validation_errors) == 0
    
    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors."""
        return self.validation_errors.copy()

    def get_all(self) -> Dict[str, Any]:
        """Serializes current configuration for logging or UI sync."""
        return {
            "redis": self.redis.__dict__,
            "supabase": {"url": self.supabase.url, "key": "MASKED", "openrouter_key": "MASKED"},
            "worker": self.worker.__dict__,
            "pinchtab": self.pinchtab.__dict__,
            "openclaw": self.openclaw.__dict__,
            "hybrid_browser": self.hybrid_browser.__dict__,
            "master": self.master.__dict__,
            "validation": {
                "is_valid": self.is_valid(),
                "error_count": len(self.validation_errors),
                "errors": self.validation_errors
            }
        }

if __name__ == "__main__":
    # Test Config Mapping
    config = ConfigManager()
    print("Xytherion Config Matrix Loaded.")
    print(json.dumps(config.get_all(), indent=2))
