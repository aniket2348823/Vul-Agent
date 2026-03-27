class Config:
    # System Constants
    DEFAULT_CONCURRENCY = 50
    MAX_CONCURRENCY = 100
    SOCKET_TIMEOUT = 5.0
    PRIME_SLEEP = 0.05
    
    # Scan Configuration
    SCAN_TIMEOUT = 600  # Max scan duration in seconds (10 minutes)
    DEPTH_SCAN_TIMEOUT = 600  # 10 minutes for depth scans
    
    # Recon Constants
    IGNORED_EXTENSIONS = ['.jpg', '.png', '.gif', '.css', '.js', '.woff2', '.svg']

settings = Config()

