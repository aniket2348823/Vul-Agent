# Configuration Reference - Antigravity V5

Complete reference for all configuration options in Antigravity V5.

---

## Table of Contents

1. [Environment Variables](#environment-variables)
2. [Configuration Files](#configuration-files)
3. [Database Configuration](#database-configuration)
4. [Security Configuration](#security-configuration)
5. [Browser Configuration](#browser-configuration)
6. [API Configuration](#api-configuration)
7. [Logging Configuration](#logging-configuration)
8. [Performance Tuning](#performance-tuning)

---

## Environment Variables

### Application Settings

#### `APP_ENV`
- **Type**: String
- **Default**: `development`
- **Options**: `development`, `staging`, `production`
- **Description**: Application environment mode
- **Example**: `APP_ENV=production`

#### `APP_DEBUG`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable debug mode (disable in production)
- **Example**: `APP_DEBUG=false`

#### `APP_SECRET_KEY`
- **Type**: String (32+ characters)
- **Required**: Yes
- **Description**: Secret key for session encryption
- **Example**: `APP_SECRET_KEY=your-secure-random-key-here`
- **Generate**: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`

---

### Database Configuration

#### `DATABASE_URL`
- **Type**: String (PostgreSQL URL)
- **Required**: Yes
- **Format**: `postgresql://user:password@host:port/database`
- **Example**: `DATABASE_URL=postgresql://antigravity:pass@localhost:5432/antigravity`

#### `DATABASE_POOL_SIZE`
- **Type**: Integer
- **Default**: `10`
- **Range**: `5-50`
- **Description**: Connection pool size
- **Example**: `DATABASE_POOL_SIZE=20`

#### `DATABASE_MAX_OVERFLOW`
- **Type**: Integer
- **Default**: `5`
- **Range**: `0-20`
- **Description**: Maximum overflow connections
- **Example**: `DATABASE_MAX_OVERFLOW=10`

#### `DATABASE_POOL_TIMEOUT`
- **Type**: Integer (seconds)
- **Default**: `30`
- **Description**: Connection timeout
- **Example**: `DATABASE_POOL_TIMEOUT=60`

#### `DATABASE_ECHO`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Log all SQL queries (debug only)
- **Example**: `DATABASE_ECHO=true`

---

### Redis Configuration

#### `REDIS_URL`
- **Type**: String (Redis URL)
- **Required**: Yes
- **Format**: `redis://host:port/db`
- **Example**: `REDIS_URL=redis://localhost:6379/0`

#### `REDIS_PASSWORD`
- **Type**: String
- **Required**: No (recommended for production)
- **Description**: Redis authentication password
- **Example**: `REDIS_PASSWORD=secure-redis-password`

#### `REDIS_MAX_CONNECTIONS`
- **Type**: Integer
- **Default**: `50`
- **Description**: Maximum Redis connections
- **Example**: `REDIS_MAX_CONNECTIONS=100`

#### `REDIS_SOCKET_TIMEOUT`
- **Type**: Integer (seconds)
- **Default**: `5`
- **Description**: Socket timeout for Redis operations
- **Example**: `REDIS_SOCKET_TIMEOUT=10`

---

### Security Configuration

#### `FORENSIC_ENCRYPTION_KEY`
- **Type**: String (Fernet key)
- **Required**: Yes (production)
- **Description**: Encryption key for forensic data
- **Example**: `FORENSIC_ENCRYPTION_KEY=your-fernet-key-here`
- **Generate**: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

#### `CSRF_SECRET_KEY`
- **Type**: String (32+ characters)
- **Required**: Yes
- **Description**: Secret key for CSRF token generation
- **Example**: `CSRF_SECRET_KEY=your-csrf-secret-key`

#### `JWT_SECRET_KEY`
- **Type**: String (32+ characters)
- **Required**: Yes
- **Description**: Secret key for JWT token signing
- **Example**: `JWT_SECRET_KEY=your-jwt-secret-key`

#### `CSRF_TOKEN_EXPIRY`
- **Type**: Integer (seconds)
- **Default**: `3600`
- **Description**: CSRF token expiration time
- **Example**: `CSRF_TOKEN_EXPIRY=7200`

#### `RATE_LIMIT_ENABLED`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable rate limiting
- **Example**: `RATE_LIMIT_ENABLED=true`

#### `RATE_LIMIT_REQUESTS`
- **Type**: Integer
- **Default**: `100`
- **Description**: Maximum requests per window
- **Example**: `RATE_LIMIT_REQUESTS=200`

#### `RATE_LIMIT_WINDOW`
- **Type**: Integer (seconds)
- **Default**: `60`
- **Description**: Rate limit time window
- **Example**: `RATE_LIMIT_WINDOW=60`

#### `URL_VALIDATOR_ALLOWLIST`
- **Type**: String (comma-separated)
- **Default**: Empty
- **Description**: Allowed internal URLs for SSRF protection
- **Example**: `URL_VALIDATOR_ALLOWLIST=192.168.1.0/24,10.0.0.0/8`

---

### Browser Configuration

#### `BROWSER_HEADLESS`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Run browsers in headless mode
- **Example**: `BROWSER_HEADLESS=false`

#### `BROWSER_MAX_CONTEXTS`
- **Type**: Integer
- **Default**: `5`
- **Range**: `1-20`
- **Description**: Maximum concurrent browser contexts
- **Example**: `BROWSER_MAX_CONTEXTS=10`

#### `BROWSER_CONTEXT_TIMEOUT`
- **Type**: Integer (seconds)
- **Default**: `300`
- **Description**: Browser context idle timeout
- **Example**: `BROWSER_CONTEXT_TIMEOUT=600`

#### `BROWSER_MEMORY_THRESHOLD_MB`
- **Type**: Integer (megabytes)
- **Default**: `500`
- **Description**: Memory threshold for cleanup
- **Example**: `BROWSER_MEMORY_THRESHOLD_MB=1000`

#### `BROWSER_POOL_SIZE`
- **Type**: Integer
- **Default**: `3`
- **Range**: `1-10`
- **Description**: Browser context pool size
- **Example**: `BROWSER_POOL_SIZE=5`

#### `BROWSER_LAZY_INIT`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable lazy browser initialization
- **Example**: `BROWSER_LAZY_INIT=false`

#### `BROWSER_VIEWPORT_WIDTH`
- **Type**: Integer (pixels)
- **Default**: `1920`
- **Description**: Browser viewport width
- **Example**: `BROWSER_VIEWPORT_WIDTH=1280`

#### `BROWSER_VIEWPORT_HEIGHT`
- **Type**: Integer (pixels)
- **Default**: `1080`
- **Description**: Browser viewport height
- **Example**: `BROWSER_VIEWPORT_HEIGHT=720`

#### `BROWSER_USER_AGENT`
- **Type**: String
- **Default**: Playwright default
- **Description**: Custom user agent string
- **Example**: `BROWSER_USER_AGENT=Mozilla/5.0...`

---

### API Configuration

#### `API_HOST`
- **Type**: String (IP address)
- **Default**: `127.0.0.1`
- **Description**: API server bind address
- **Example**: `API_HOST=0.0.0.0`

#### `API_PORT`
- **Type**: Integer
- **Default**: `8000`
- **Range**: `1024-65535`
- **Description**: API server port
- **Example**: `API_PORT=8080`

#### `API_WORKERS`
- **Type**: Integer
- **Default**: `4`
- **Description**: Number of API worker processes
- **Example**: `API_WORKERS=8`
- **Recommendation**: `(2 * CPU_CORES) + 1`

#### `API_TIMEOUT`
- **Type**: Integer (seconds)
- **Default**: `60`
- **Description**: API request timeout
- **Example**: `API_TIMEOUT=120`

#### `API_MAX_REQUEST_SIZE`
- **Type**: Integer (bytes)
- **Default**: `10485760` (10MB)
- **Description**: Maximum request body size
- **Example**: `API_MAX_REQUEST_SIZE=20971520`

#### `API_CORS_ORIGINS`
- **Type**: String (comma-separated)
- **Default**: `*`
- **Description**: Allowed CORS origins
- **Example**: `API_CORS_ORIGINS=https://app.example.com,https://admin.example.com`

#### `API_CORS_CREDENTIALS`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Allow credentials in CORS requests
- **Example**: `API_CORS_CREDENTIALS=false`

---

### Logging Configuration

#### `LOG_LEVEL`
- **Type**: String
- **Default**: `INFO`
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description**: Logging level
- **Example**: `LOG_LEVEL=WARNING`

#### `LOG_FILE`
- **Type**: String (file path)
- **Default**: `logs/app.log`
- **Description**: Log file path
- **Example**: `LOG_FILE=/var/log/antigravity/app.log`

#### `LOG_FORMAT`
- **Type**: String
- **Default**: `json`
- **Options**: `json`, `text`
- **Description**: Log output format
- **Example**: `LOG_FORMAT=text`

#### `LOG_MAX_SIZE`
- **Type**: Integer (bytes)
- **Default**: `10485760` (10MB)
- **Description**: Maximum log file size before rotation
- **Example**: `LOG_MAX_SIZE=52428800`

#### `LOG_BACKUP_COUNT`
- **Type**: Integer
- **Default**: `5`
- **Description**: Number of rotated log files to keep
- **Example**: `LOG_BACKUP_COUNT=10`

#### `LOG_SQL_QUERIES`
- **Type**: Boolean
- **Default**: `false`
- **Description**: Log all SQL queries (debug only)
- **Example**: `LOG_SQL_QUERIES=true`

---

### Monitoring Configuration

#### `SENTRY_DSN`
- **Type**: String (Sentry DSN URL)
- **Required**: No (recommended for production)
- **Description**: Sentry error tracking DSN
- **Example**: `SENTRY_DSN=https://key@sentry.io/project`

#### `SENTRY_ENVIRONMENT`
- **Type**: String
- **Default**: Value of `APP_ENV`
- **Description**: Sentry environment name
- **Example**: `SENTRY_ENVIRONMENT=production`

#### `SENTRY_TRACES_SAMPLE_RATE`
- **Type**: Float
- **Default**: `0.1`
- **Range**: `0.0-1.0`
- **Description**: Percentage of transactions to trace
- **Example**: `SENTRY_TRACES_SAMPLE_RATE=0.5`

#### `PROMETHEUS_ENABLED`
- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable Prometheus metrics
- **Example**: `PROMETHEUS_ENABLED=false`

#### `PROMETHEUS_PORT`
- **Type**: Integer
- **Default**: `9090`
- **Description**: Prometheus metrics port
- **Example**: `PROMETHEUS_PORT=9091`

---

### Agent Configuration

#### `AGENT_TIMEOUT`
- **Type**: Integer (seconds)
- **Default**: `300`
- **Description**: Agent execution timeout
- **Example**: `AGENT_TIMEOUT=600`

#### `AGENT_MAX_RETRIES`
- **Type**: Integer
- **Default**: `3`
- **Description**: Maximum agent retry attempts
- **Example**: `AGENT_MAX_RETRIES=5`

#### `AGENT_PARALLEL_LIMIT`
- **Type**: Integer
- **Default**: `5`
- **Description**: Maximum parallel agent executions
- **Example**: `AGENT_PARALLEL_LIMIT=10`

---

## Configuration Files

### User Configuration

**Location**: `data/config/user_config.json`

```json
{
  "scan_defaults": {
    "depth": 3,
    "timeout": 300,
    "parallel_requests": 10
  },
  "browser_preferences": {
    "headless": true,
    "viewport": {
      "width": 1920,
      "height": 1080
    }
  },
  "reporting": {
    "format": "pdf",
    "include_screenshots": true,
    "include_payloads": true
  }
}
```

### PRD Configuration

**Location**: `data/config/prd.json`

```json
{
  "project_name": "Security Scan",
  "target_url": "https://example.com",
  "scope": {
    "include": ["https://example.com/*"],
    "exclude": ["/logout", "/admin"]
  },
  "agents": {
    "alpha": {"enabled": true},
    "beta": {"enabled": true},
    "gamma": {"enabled": true}
  }
}
```

### Keyring Configuration

**Location**: `data/config/keyring.json`

```json
{
  "api_keys": {
    "openai": "sk-...",
    "anthropic": "sk-ant-..."
  },
  "credentials": {
    "test_user": {
      "username": "testuser",
      "password": "testpass"
    }
  }
}
```

---

## Performance Tuning

### High-Traffic Configuration

```bash
# Increase workers
API_WORKERS=16

# Increase database pool
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=20

# Increase browser contexts
BROWSER_MAX_CONTEXTS=20
BROWSER_POOL_SIZE=10

# Increase Redis connections
REDIS_MAX_CONNECTIONS=200
```

### Low-Memory Configuration

```bash
# Reduce workers
API_WORKERS=2

# Reduce database pool
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=2

# Reduce browser contexts
BROWSER_MAX_CONTEXTS=3
BROWSER_POOL_SIZE=1
BROWSER_MEMORY_THRESHOLD_MB=250
```

### Development Configuration

```bash
# Enable debug mode
APP_ENV=development
APP_DEBUG=true
LOG_LEVEL=DEBUG

# Disable security features
RATE_LIMIT_ENABLED=false

# Enable SQL logging
DATABASE_ECHO=true
LOG_SQL_QUERIES=true

# Visible browser
BROWSER_HEADLESS=false
```

---

## Security Best Practices

### Production Security Checklist

- [ ] Set `APP_DEBUG=false`
- [ ] Generate unique `APP_SECRET_KEY`
- [ ] Generate unique `FORENSIC_ENCRYPTION_KEY`
- [ ] Generate unique `CSRF_SECRET_KEY`
- [ ] Generate unique `JWT_SECRET_KEY`
- [ ] Set strong `REDIS_PASSWORD`
- [ ] Enable `RATE_LIMIT_ENABLED=true`
- [ ] Configure `URL_VALIDATOR_ALLOWLIST`
- [ ] Set `API_CORS_ORIGINS` to specific domains
- [ ] Enable `SENTRY_DSN` for error tracking
- [ ] Set `LOG_LEVEL=WARNING` or `ERROR`
- [ ] Use HTTPS for all external connections

---

## Validation

### Configuration Validation Script

```python
#!/usr/bin/env python3
"""Validate Antigravity V5 configuration."""

import os
import sys

def validate_config():
    """Validate required configuration."""
    required = [
        'APP_SECRET_KEY',
        'DATABASE_URL',
        'REDIS_URL',
        'FORENSIC_ENCRYPTION_KEY',
        'CSRF_SECRET_KEY',
        'JWT_SECRET_KEY',
    ]
    
    missing = []
    for var in required:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing required variables: {', '.join(missing)}")
        return False
    
    # Validate key lengths
    if len(os.getenv('APP_SECRET_KEY', '')) < 32:
        print("❌ APP_SECRET_KEY must be at least 32 characters")
        return False
    
    print("✅ Configuration valid")
    return True

if __name__ == '__main__':
    sys.exit(0 if validate_config() else 1)
```

---

## Troubleshooting

### Common Configuration Issues

#### Database Connection Failed
```bash
# Check DATABASE_URL format
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1;"
```

#### Redis Connection Failed
```bash
# Check REDIS_URL
echo $REDIS_URL

# Test connection
redis-cli -u $REDIS_URL PING
```

#### Browser Launch Failed
```bash
# Install browsers
playwright install chromium

# Check headless mode
export BROWSER_HEADLESS=true
```

---

## Environment-Specific Configurations

### Development

```bash
APP_ENV=development
APP_DEBUG=true
LOG_LEVEL=DEBUG
BROWSER_HEADLESS=false
RATE_LIMIT_ENABLED=false
```

### Staging

```bash
APP_ENV=staging
APP_DEBUG=false
LOG_LEVEL=INFO
BROWSER_HEADLESS=true
RATE_LIMIT_ENABLED=true
```

### Production

```bash
APP_ENV=production
APP_DEBUG=false
LOG_LEVEL=WARNING
BROWSER_HEADLESS=true
RATE_LIMIT_ENABLED=true
SENTRY_DSN=https://...
```

---

## References

- [Deployment Guide](DEPLOYMENT.md)
- [Security Best Practices](SECURITY_BEST_PRACTICES.md)
- [Performance Tuning](PERFORMANCE.md)
- [Troubleshooting](TROUBLESHOOTING.md)

---

**Last Updated**: May 26, 2026  
**Version**: 5.0  
**Status**: Complete
