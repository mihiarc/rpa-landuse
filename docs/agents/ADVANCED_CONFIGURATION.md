# Advanced Configuration for Production Deployment

This guide provides comprehensive configuration patterns for deploying RPA Land Use Analytics agents in production environments with proper security, performance optimization, and monitoring.

## Table of Contents

- [Configuration Architecture](#configuration-architecture)
- [Environment-Based Configuration](#environment-based-configuration)
- [Production Deployment Configurations](#production-deployment-configurations)
- [Multi-Environment Configuration Management](#multi-environment-configuration-management)
- [Security Configuration](#security-configuration)
- [Performance Tuning](#performance-tuning)
- [Monitoring and Observability](#monitoring-and-observability)
- [Configuration Validation](#configuration-validation)
- [Production Deployment Checklist](#production-deployment-checklist)
- [Troubleshooting](#troubleshooting)

## Configuration Architecture

The RPA Land Use Analytics system uses a unified configuration architecture with multiple layers:

```mermaid
graph TD
    A[Environment Variables] --> B[LanduseConfig Class]
    C[.env Files] --> B
    D[Command Line Args] --> B
    B --> E[Agent Factory]
    E --> F[Basic Agent]
    E --> G[Map-Enabled Agent]
    E --> H[Streamlit Agent]
    
    I[SecurityConfig] --> J[Input Validation]
    I --> K[Rate Limiting]
    I --> L[SQL Query Validation]
    
    B --> M[Database Config]
    B --> N[LLM Config]
    B --> O[Memory Config]
    B --> P[Tool Config]
    
    style B fill:#e1f5fe
    style I fill:#fff3e0
    style E fill:#f3e5f5
```

### Configuration Hierarchy

1. **Environment Variables** (highest priority)
2. **Configuration files** (.env, config files)
3. **Command line arguments**
4. **Default values** (lowest priority)

## Environment-Based Configuration

### Development Environment

```bash
# config/dev.env
# Development environment configuration

# API Keys
OPENAI_API_KEY=sk-dev-your-development-key
ANTHROPIC_API_KEY=sk-ant-dev-your-development-key

# Model Configuration (faster models for development)
LANDUSE_MODEL=gpt-4o-mini
TEMPERATURE=0.2
MAX_TOKENS=2000

# Database Configuration
LANDUSE_DB_PATH=data/processed/landuse_analytics.duckdb
LANDUSE_MAX_QUERY_ROWS=500
LANDUSE_DEFAULT_DISPLAY_LIMIT=25

# Development Features
DEBUG=true
VERBOSE=true
ENABLE_LOGGING=true
LOG_LEVEL=DEBUG

# Relaxed Limits for Development
LANDUSE_MAX_ITERATIONS=10
LANDUSE_MAX_EXECUTION_TIME=300
LANDUSE_RATE_LIMIT_CALLS=100
LANDUSE_RATE_LIMIT_WINDOW=60

# Knowledge Base (optional for dev)
LANDUSE_ENABLE_KNOWLEDGE_BASE=false
LANDUSE_ENABLE_MAPS=true

# Streamlit Configuration
STREAMLIT_CACHE_TTL=60
```

### Staging Environment

```bash
# config/staging.env
# Staging environment configuration

# API Keys (separate staging keys)
OPENAI_API_KEY=sk-staging-your-staging-key
ANTHROPIC_API_KEY=sk-ant-staging-your-staging-key

# Model Configuration (production-like)
LANDUSE_MODEL=gpt-4o
TEMPERATURE=0.1
MAX_TOKENS=4000

# Database Configuration
LANDUSE_DB_PATH=/data/staging/landuse_analytics.duckdb
LANDUSE_MAX_QUERY_ROWS=1000
LANDUSE_DEFAULT_DISPLAY_LIMIT=50

# Staging Features
DEBUG=false
VERBOSE=false
ENABLE_LOGGING=true
LOG_LEVEL=INFO

# Production-like Limits
LANDUSE_MAX_ITERATIONS=8
LANDUSE_MAX_EXECUTION_TIME=120
LANDUSE_RATE_LIMIT_CALLS=60
LANDUSE_RATE_LIMIT_WINDOW=60

# Full Feature Set
LANDUSE_ENABLE_KNOWLEDGE_BASE=true
LANDUSE_ENABLE_MAPS=true
LANDUSE_KNOWLEDGE_BASE_PATH=/data/staging/docs
LANDUSE_CHROMA_PERSIST_DIR=/data/staging/chroma_db

# Streamlit Configuration
STREAMLIT_CACHE_TTL=300
```

### Production Environment

```bash
# config/prod.env
# Production environment configuration

# API Keys (production keys with rate limits)
OPENAI_API_KEY=sk-prod-your-production-key
ANTHROPIC_API_KEY=sk-ant-prod-your-production-key

# Model Configuration (optimized for production)
LANDUSE_MODEL=claude-3-5-sonnet-20241022
TEMPERATURE=0.1
MAX_TOKENS=4000

# Database Configuration
LANDUSE_DB_PATH=/data/prod/landuse_analytics.duckdb
LANDUSE_MAX_QUERY_ROWS=1000
LANDUSE_DEFAULT_DISPLAY_LIMIT=50

# Production Security
DEBUG=false
VERBOSE=false
ENABLE_LOGGING=true
LOG_LEVEL=WARNING

# Production Limits
LANDUSE_MAX_ITERATIONS=5
LANDUSE_MAX_EXECUTION_TIME=60
LANDUSE_RATE_LIMIT_CALLS=30
LANDUSE_RATE_LIMIT_WINDOW=60

# Production Features
LANDUSE_ENABLE_KNOWLEDGE_BASE=true
LANDUSE_ENABLE_MAPS=true
LANDUSE_KNOWLEDGE_BASE_PATH=/data/prod/docs
LANDUSE_CHROMA_PERSIST_DIR=/data/prod/chroma_db

# Streamlit Configuration
STREAMLIT_CACHE_TTL=3600

# Security Settings
ENABLE_RATE_LIMITING=true
LANDUSE_SECURITY_LOG_PATH=/var/log/landuse/security.log

# Performance Monitoring
LANDUSE_METRICS_ENABLED=true
LANDUSE_METRICS_ENDPOINT=http://prometheus:9090/metrics
```

## Production Deployment Configurations

### Docker Compose Configuration

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  landuse-agent:
    image: rpa-landuse:latest
    environment:
      - ENV=production
      - LANDUSE_DB_PATH=/data/landuse_analytics.duckdb
      - LANDUSE_MODEL=${LANDUSE_MODEL:-claude-3-5-sonnet-20241022}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LOG_LEVEL=WARNING
      - ENABLE_RATE_LIMITING=true
      - LANDUSE_RATE_LIMIT_CALLS=30
      - LANDUSE_RATE_LIMIT_WINDOW=60
    volumes:
      - /opt/landuse/data:/data:ro
      - /opt/landuse/logs:/logs
    ports:
      - "8501:8501"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
    
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana-storage:/var/lib/grafana
    
volumes:
  grafana-storage:
```

### Kubernetes Configuration

```yaml
# k8s/landuse-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: landuse-agent
  namespace: landuse
spec:
  replicas: 3
  selector:
    matchLabels:
      app: landuse-agent
  template:
    metadata:
      labels:
        app: landuse-agent
    spec:
      containers:
      - name: landuse-agent
        image: rpa-landuse:latest
        ports:
        - containerPort: 8501
        env:
        - name: ENV
          value: "production"
        - name: LANDUSE_DB_PATH
          value: "/data/landuse_analytics.duckdb"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: openai-key
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: anthropic-key
        - name: LOG_LEVEL
          value: "WARNING"
        - name: LANDUSE_RATE_LIMIT_CALLS
          value: "30"
        - name: LANDUSE_RATE_LIMIT_WINDOW
          value: "60"
        volumeMounts:
        - name: data-volume
          mountPath: /data
          readOnly: true
        - name: logs-volume
          mountPath: /logs
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /_stcore/health
            port: 8501
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /_stcore/health
            port: 8501
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 65534
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: landuse-data-pvc
      - name: logs-volume
        persistentVolumeClaim:
          claimName: landuse-logs-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: landuse-service
  namespace: landuse
spec:
  selector:
    app: landuse-agent
  ports:
  - port: 80
    targetPort: 8501
  type: LoadBalancer
```

## Multi-Environment Configuration Management

### Configuration Factory Pattern

```python
# config/environment_config.py
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from pathlib import Path

from landuse.config.landuse_config import LanduseConfig

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

@dataclass
class EnvironmentConfig:
    """Environment-specific configuration settings"""
    
    # Security Settings
    enable_debug: bool
    enable_verbose: bool
    log_level: str
    
    # Performance Settings
    max_iterations: int
    max_execution_time: int
    rate_limit_calls: int
    rate_limit_window: int
    
    # Feature Flags
    enable_knowledge_base: bool
    enable_maps: bool
    enable_rate_limiting: bool
    
    # Database Settings
    db_path: str
    max_query_rows: int
    cache_ttl: int

class ConfigurationFactory:
    """Factory for creating environment-specific configurations"""
    
    ENVIRONMENT_CONFIGS = {
        Environment.DEVELOPMENT: EnvironmentConfig(
            enable_debug=True,
            enable_verbose=True,
            log_level="DEBUG",
            max_iterations=10,
            max_execution_time=300,
            rate_limit_calls=100,
            rate_limit_window=60,
            enable_knowledge_base=False,
            enable_maps=True,
            enable_rate_limiting=False,
            db_path="data/processed/landuse_analytics.duckdb",
            max_query_rows=500,
            cache_ttl=60
        ),
        Environment.STAGING: EnvironmentConfig(
            enable_debug=False,
            enable_verbose=False,
            log_level="INFO",
            max_iterations=8,
            max_execution_time=120,
            rate_limit_calls=60,
            rate_limit_window=60,
            enable_knowledge_base=True,
            enable_maps=True,
            enable_rate_limiting=True,
            db_path="/data/staging/landuse_analytics.duckdb",
            max_query_rows=1000,
            cache_ttl=300
        ),
        Environment.PRODUCTION: EnvironmentConfig(
            enable_debug=False,
            enable_verbose=False,
            log_level="WARNING",
            max_iterations=5,
            max_execution_time=60,
            rate_limit_calls=30,
            rate_limit_window=60,
            enable_knowledge_base=True,
            enable_maps=True,
            enable_rate_limiting=True,
            db_path="/data/prod/landuse_analytics.duckdb",
            max_query_rows=1000,
            cache_ttl=3600
        )
    }
    
    @classmethod
    def create_config(cls, environment: Environment, **overrides) -> LanduseConfig:
        """Create configuration for specific environment"""
        env_config = cls.ENVIRONMENT_CONFIGS[environment]
        
        # Convert environment config to LanduseConfig parameters
        config_params = {
            'debug': env_config.enable_debug,
            'verbose': env_config.enable_verbose,
            'max_iterations': env_config.max_iterations,
            'max_execution_time': env_config.max_execution_time,
            'rate_limit_calls': env_config.rate_limit_calls,
            'rate_limit_window': env_config.rate_limit_window,
            'enable_knowledge_base': env_config.enable_knowledge_base,
            'enable_map_generation': env_config.enable_maps,
            'db_path': env_config.db_path,
            'max_query_rows': env_config.max_query_rows,
            'streamlit_cache_ttl': env_config.cache_ttl,
            **overrides
        }
        
        return LanduseConfig.from_env(**config_params)

# Usage example
def get_config_for_environment(env_name: str) -> LanduseConfig:
    """Get configuration for environment name"""
    environment = Environment(env_name.lower())
    return ConfigurationFactory.create_config(environment)
```

### Environment Detection

```python
# config/env_detection.py
import os
from typing import Optional

def detect_environment() -> str:
    """Detect current environment from various sources"""
    
    # Check explicit environment variable
    if env := os.getenv('ENV'):
        return env.lower()
    
    # Check Kubernetes environment
    if os.getenv('KUBERNETES_SERVICE_HOST'):
        if os.getenv('KUBE_NAMESPACE') == 'production':
            return 'production'
        elif os.getenv('KUBE_NAMESPACE') == 'staging':
            return 'staging'
        else:
            return 'development'
    
    # Check Docker environment
    if os.path.exists('/.dockerenv'):
        return 'production' if os.getenv('PROD') else 'staging'
    
    # Check for CI environment
    if any(os.getenv(var) for var in ['CI', 'GITHUB_ACTIONS', 'GITLAB_CI']):
        return 'testing'
    
    # Default to development
    return 'development'

def load_environment_config(env_name: Optional[str] = None) -> LanduseConfig:
    """Load configuration for detected or specified environment"""
    if env_name is None:
        env_name = detect_environment()
    
    # Load environment-specific .env file
    env_file = f"config/{env_name}.env"
    if os.path.exists(env_file):
        from dotenv import load_dotenv
        load_dotenv(env_file)
    
    return get_config_for_environment(env_name)
```

## Security Configuration

### API Key Management

```python
# config/secrets_manager.py
import os
import boto3
from typing import Dict, Optional
from botocore.exceptions import ClientError

class SecretsManager:
    """Manage API keys and secrets securely"""
    
    def __init__(self, region_name: str = 'us-east-1'):
        self.region_name = region_name
        
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from AWS Secrets Manager"""
        try:
            session = boto3.session.Session()
            client = session.client(
                service_name='secretsmanager',
                region_name=self.region_name
            )
            
            response = client.get_secret_value(SecretId=secret_name)
            return response['SecretString']
            
        except ClientError as e:
            print(f"Error retrieving secret {secret_name}: {e}")
            return None
    
    def get_api_keys(self) -> Dict[str, str]:
        """Get all required API keys"""
        secrets = {}
        
        # Try AWS Secrets Manager first
        if openai_key := self.get_secret('landuse/openai-api-key'):
            secrets['OPENAI_API_KEY'] = openai_key
        elif openai_key := os.getenv('OPENAI_API_KEY'):
            secrets['OPENAI_API_KEY'] = openai_key
            
        if anthropic_key := self.get_secret('landuse/anthropic-api-key'):
            secrets['ANTHROPIC_API_KEY'] = anthropic_key
        elif anthropic_key := os.getenv('ANTHROPIC_API_KEY'):
            secrets['ANTHROPIC_API_KEY'] = anthropic_key
            
        return secrets

# Set up secrets in environment
def setup_production_secrets():
    """Set up secrets for production environment"""
    secrets_manager = SecretsManager()
    secrets = secrets_manager.get_api_keys()
    
    for key, value in secrets.items():
        os.environ[key] = value
```

### SQL Query Security

```python
# config/security_config.py
from landuse.utils.security import SQLQueryValidator, RateLimiter
from landuse.config.landuse_config import LanduseConfig

class SecurityConfig:
    """Security configuration for production"""
    
    def __init__(self, config: LanduseConfig):
        self.config = config
        self.query_validator = SQLQueryValidator()
        self.rate_limiter = RateLimiter(
            max_calls=config.rate_limit_calls,
            time_window=config.rate_limit_window
        )
    
    def validate_query(self, query: str, user_id: str) -> tuple[bool, Optional[str]]:
        """Validate query with rate limiting"""
        # Check rate limit first
        allowed, error = self.rate_limiter.check_rate_limit(user_id)
        if not allowed:
            return False, error
            
        # Validate SQL query
        return self.query_validator.validate_query(query)
    
    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers for web applications"""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'"
        }
```

## Performance Tuning

### Database Connection Optimization

```python
# config/performance_config.py
from landuse.config.landuse_config import LanduseConfig

class PerformanceConfig:
    """Performance optimization configurations"""
    
    @staticmethod
    def get_production_db_config() -> Dict[str, Any]:
        """Get optimized database configuration for production"""
        return {
            'read_only': True,
            'memory_limit': '2GB',
            'threads': 4,
            'max_memory': '80%',
            'enable_object_cache': True,
            'enable_query_profiling': False  # Disable in production
        }
    
    @staticmethod
    def get_streamlit_cache_config(config: LanduseConfig) -> Dict[str, Any]:
        """Get optimized Streamlit cache configuration"""
        return {
            'ttl': config.streamlit_cache_ttl,
            'max_entries': 1000,
            'allow_output_mutation': False,
            'show_spinner': True
        }
    
    @staticmethod
    def get_llm_optimization_config() -> Dict[str, Any]:
        """Get LLM optimization configuration"""
        return {
            'max_retries': 3,
            'timeout': 30.0,
            'streaming': True,
            'temperature': 0.1,  # Lower temperature for consistency
            'request_timeout': 60.0,
            'max_tokens': 4000
        }
```

### Memory Management

```python
# config/memory_config.py
import resource
import psutil
from typing import Dict, Any

class MemoryConfig:
    """Memory management and monitoring"""
    
    @staticmethod
    def set_memory_limits():
        """Set memory limits for the process"""
        # Set maximum memory usage (2GB)
        max_memory = 2 * 1024 * 1024 * 1024  # 2GB in bytes
        resource.setrlimit(resource.RLIMIT_AS, (max_memory, max_memory))
    
    @staticmethod
    def get_memory_status() -> Dict[str, Any]:
        """Get current memory usage"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': process.memory_percent(),
            'available_mb': psutil.virtual_memory().available / 1024 / 1024
        }
    
    @staticmethod
    def check_memory_threshold(threshold_percent: float = 80.0) -> bool:
        """Check if memory usage is below threshold"""
        memory_status = MemoryConfig.get_memory_status()
        return memory_status['percent'] < threshold_percent
```

## Monitoring and Observability

### Metrics Configuration

```python
# config/monitoring_config.py
import time
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, start_http_server

class MetricsConfig:
    """Prometheus metrics configuration"""
    
    def __init__(self):
        # Define metrics
        self.query_counter = Counter(
            'landuse_queries_total',
            'Total number of queries processed',
            ['agent_type', 'status']
        )
        
        self.query_duration = Histogram(
            'landuse_query_duration_seconds',
            'Time spent processing queries',
            ['agent_type']
        )
        
        self.active_sessions = Gauge(
            'landuse_active_sessions',
            'Number of active user sessions'
        )
        
        self.memory_usage = Gauge(
            'landuse_memory_usage_bytes',
            'Current memory usage in bytes'
        )
        
        self.api_calls = Counter(
            'landuse_api_calls_total',
            'Total API calls made',
            ['provider', 'model']
        )
    
    def start_metrics_server(self, port: int = 8000):
        """Start Prometheus metrics server"""
        start_http_server(port)
    
    def record_query(self, agent_type: str, duration: float, status: str):
        """Record query metrics"""
        self.query_counter.labels(agent_type=agent_type, status=status).inc()
        self.query_duration.labels(agent_type=agent_type).observe(duration)
    
    def update_memory_usage(self, memory_bytes: int):
        """Update memory usage metric"""
        self.memory_usage.set(memory_bytes)
    
    def record_api_call(self, provider: str, model: str):
        """Record API call metric"""
        self.api_calls.labels(provider=provider, model=model).inc()

# Global metrics instance
metrics = MetricsConfig()
```

### Logging Configuration

```python
# config/logging_config.py
import logging
import logging.handlers
from pathlib import Path
from typing import Optional

def setup_production_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """Set up production logging configuration"""
    
    logger = logging.getLogger('landuse')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler for production
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def setup_security_logging(log_file: str = "/var/log/landuse/security.log"):
    """Set up security-specific logging"""
    security_logger = logging.getLogger('landuse.security')
    security_logger.setLevel(logging.WARNING)
    
    # Security log should always go to file
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - SECURITY - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    security_logger.addHandler(handler)
    
    return security_logger
```

## Configuration Validation

### Automated Configuration Testing

```python
# tests/test_configuration.py
import pytest
import os
import tempfile
from pathlib import Path

from landuse.config.landuse_config import LanduseConfig
from landuse.utils.security import SecureConfig

class TestConfigurationValidation:
    """Test configuration validation across environments"""
    
    def test_development_config(self):
        """Test development configuration is valid"""
        config = ConfigurationFactory.create_config(Environment.DEVELOPMENT)
        
        assert config.debug is True
        assert config.verbose is True
        assert config.max_iterations >= 5
        assert config.enable_map_generation is True
    
    def test_production_config(self):
        """Test production configuration is secure"""
        config = ConfigurationFactory.create_config(Environment.PRODUCTION)
        
        assert config.debug is False
        assert config.verbose is False
        assert config.max_iterations <= 8
        assert config.max_execution_time <= 120
        assert config.rate_limit_calls <= 60
    
    def test_api_key_validation(self):
        """Test API key validation"""
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY required"):
            config = LanduseConfig(model_name="claude-3-sonnet-20240229")
    
    def test_database_path_validation(self):
        """Test database path validation"""
        with pytest.raises(FileNotFoundError):
            config = LanduseConfig(db_path="/nonexistent/path.duckdb")
    
    def test_secure_config_validation(self):
        """Test secure configuration validation"""
        with pytest.raises(ValueError):
            SecureConfig(temperature=2.5)  # Invalid temperature
        
        with pytest.raises(ValueError):
            SecureConfig(max_tokens=0)  # Invalid max_tokens

def test_environment_detection():
    """Test environment detection logic"""
    # Test explicit environment variable
    os.environ['ENV'] = 'staging'
    assert detect_environment() == 'staging'
    
    # Test Kubernetes detection
    del os.environ['ENV']
    os.environ['KUBERNETES_SERVICE_HOST'] = 'kubernetes.default.svc'
    os.environ['KUBE_NAMESPACE'] = 'production'
    assert detect_environment() == 'production'
    
    # Cleanup
    for key in ['KUBERNETES_SERVICE_HOST', 'KUBE_NAMESPACE']:
        if key in os.environ:
            del os.environ[key]

@pytest.mark.parametrize("env_name", ["development", "staging", "production"])
def test_all_environments_valid(env_name):
    """Test that all environment configurations are valid"""
    config = get_config_for_environment(env_name)
    
    # Basic validation
    assert isinstance(config, LanduseConfig)
    assert config.max_iterations > 0
    assert config.max_execution_time > 0
    assert 0.0 <= config.temperature <= 2.0
    assert config.max_tokens > 0
```

### Configuration Health Checks

```python
# config/health_checks.py
from typing import Dict, Any, List
from pathlib import Path
import duckdb
import requests

class ConfigurationHealthCheck:
    """Health checks for configuration validation"""
    
    def __init__(self, config: LanduseConfig):
        self.config = config
    
    def check_database_connection(self) -> Dict[str, Any]:
        """Check database connectivity and schema"""
        try:
            conn = duckdb.connect(self.config.db_path, read_only=True)
            
            # Check basic connectivity
            result = conn.execute("SELECT 1").fetchone()
            if result[0] != 1:
                return {"status": "error", "message": "Database connection failed"}
            
            # Check required tables exist
            required_tables = [
                'fact_landuse_transitions',
                'dim_scenario',
                'dim_geography',
                'dim_landuse',
                'dim_time'
            ]
            
            for table in required_tables:
                try:
                    conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                except Exception as e:
                    return {
                        "status": "error", 
                        "message": f"Required table {table} not found: {e}"
                    }
            
            conn.close()
            return {"status": "healthy", "message": "Database connection successful"}
            
        except Exception as e:
            return {"status": "error", "message": f"Database error: {e}"}
    
    def check_api_keys(self) -> Dict[str, Any]:
        """Check API key validity"""
        issues = []
        
        # Check OpenAI API key
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            if not openai_key.startswith('sk-'):
                issues.append("OpenAI API key format invalid")
        elif 'gpt' in self.config.model_name.lower():
            issues.append("OpenAI API key required for GPT models")
        
        # Check Anthropic API key
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key:
            if not anthropic_key.startswith('sk-ant-'):
                issues.append("Anthropic API key format invalid")
        elif 'claude' in self.config.model_name.lower():
            issues.append("Anthropic API key required for Claude models")
        
        if issues:
            return {"status": "error", "message": "; ".join(issues)}
        else:
            return {"status": "healthy", "message": "API keys configured correctly"}
    
    def check_file_permissions(self) -> Dict[str, Any]:
        """Check file and directory permissions"""
        issues = []
        
        # Check database file permissions
        db_path = Path(self.config.db_path)
        if not db_path.exists():
            issues.append(f"Database file does not exist: {db_path}")
        elif not db_path.is_file():
            issues.append(f"Database path is not a file: {db_path}")
        elif not os.access(db_path, os.R_OK):
            issues.append(f"Cannot read database file: {db_path}")
        
        # Check map output directory
        if self.config.enable_map_generation:
            map_dir = Path(self.config.map_output_dir)
            if not map_dir.exists():
                try:
                    map_dir.mkdir(parents=True, exist_ok=True)
                except PermissionError:
                    issues.append(f"Cannot create map output directory: {map_dir}")
            elif not os.access(map_dir, os.W_OK):
                issues.append(f"Cannot write to map output directory: {map_dir}")
        
        if issues:
            return {"status": "error", "message": "; ".join(issues)}
        else:
            return {"status": "healthy", "message": "File permissions correct"}
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        checks = {
            'database': self.check_database_connection(),
            'api_keys': self.check_api_keys(),
            'file_permissions': self.check_file_permissions()
        }
        
        # Overall status
        all_healthy = all(check['status'] == 'healthy' for check in checks.values())
        overall_status = 'healthy' if all_healthy else 'error'
        
        return {
            'overall_status': overall_status,
            'checks': checks,
            'timestamp': time.time()
        }
```

## Production Deployment Checklist

### Pre-Deployment Checklist

- [ ] **Security Configuration**
  - [ ] API keys stored in secure secrets manager
  - [ ] Database in read-only mode
  - [ ] Rate limiting enabled
  - [ ] SQL query validation enabled
  - [ ] Security logging configured
  - [ ] No debug/verbose logging in production

- [ ] **Performance Configuration**
  - [ ] Memory limits set appropriately
  - [ ] Cache TTL optimized for usage patterns
  - [ ] Database connection pool configured
  - [ ] Query execution timeouts set
  - [ ] Max iterations limited

- [ ] **Monitoring Configuration**
  - [ ] Prometheus metrics enabled
  - [ ] Health check endpoints configured
  - [ ] Log aggregation set up
  - [ ] Alerting rules configured
  - [ ] Performance monitoring enabled

- [ ] **Infrastructure Configuration**
  - [ ] Container security context configured
  - [ ] Resource limits and requests set
  - [ ] Persistent volumes configured
  - [ ] Network policies applied
  - [ ] Load balancer health checks configured

### Post-Deployment Validation

```bash
#!/bin/bash
# scripts/validate_deployment.sh

set -e

echo "Running post-deployment validation..."

# Check health endpoints
echo "Checking health endpoints..."
curl -f http://localhost:8501/_stcore/health || exit 1

# Check metrics endpoint
echo "Checking metrics endpoint..."
curl -f http://localhost:8000/metrics || exit 1

# Test basic query functionality
echo "Testing basic query functionality..."
python -c "
from landuse.agents.landuse_agent import LanduseAgent
agent = LanduseAgent()
result = agent.query('SELECT COUNT(*) FROM dim_scenario LIMIT 1')
assert 'rows returned' in result.lower() or 'scenario' in result.lower()
print('Basic query test passed')
"

# Check database connectivity
echo "Checking database connectivity..."
python -c "
import duckdb
conn = duckdb.connect('data/processed/landuse_analytics.duckdb', read_only=True)
result = conn.execute('SELECT COUNT(*) FROM fact_landuse_transitions').fetchone()
assert result[0] > 0
print(f'Database contains {result[0]} transition records')
conn.close()
"

# Check configuration
echo "Checking configuration..."
python -c "
from landuse.config.landuse_config import LanduseConfig
config = LanduseConfig()
assert config.debug is False
assert config.max_iterations <= 8
print('Configuration validation passed')
"

echo "All deployment validation checks passed!"
```

## Troubleshooting

### Common Configuration Issues

1. **API Key Issues**
   ```bash
   # Check API key format
   echo $OPENAI_API_KEY | grep -E '^sk-[a-zA-Z0-9]{48}$'
   echo $ANTHROPIC_API_KEY | grep -E '^sk-ant-[a-zA-Z0-9]{98}$'
   ```

2. **Database Connection Issues**
   ```bash
   # Test database connection
   duckdb data/processed/landuse_analytics.duckdb -c "SELECT COUNT(*) FROM fact_landuse_transitions;"
   ```

3. **Memory Issues**
   ```bash
   # Check memory usage
   python -c "
   import psutil
   memory = psutil.virtual_memory()
   print(f'Total: {memory.total / 1024**3:.1f}GB')
   print(f'Available: {memory.available / 1024**3:.1f}GB')
   print(f'Used: {memory.percent}%')
   "
   ```

4. **Permission Issues**
   ```bash
   # Check file permissions
   ls -la data/processed/landuse_analytics.duckdb
   ls -la maps/agent_generated/
   ```

### Configuration Debugging

```python
# debug/config_debug.py
from landuse.config.landuse_config import LanduseConfig
from landuse.config.health_checks import ConfigurationHealthCheck

def debug_configuration():
    """Debug configuration issues"""
    try:
        config = LanduseConfig()
        print(f"Configuration loaded successfully:")
        print(f"Model: {config.model_name}")
        print(f"Database: {config.db_path}")
        print(f"Debug mode: {config.debug}")
        print(f"Max iterations: {config.max_iterations}")
        
        # Run health checks
        health_checker = ConfigurationHealthCheck(config)
        results = health_checker.run_all_checks()
        
        print("\nHealth Check Results:")
        for check_name, result in results['checks'].items():
            status = result['status']
            message = result['message']
            print(f"{check_name}: {status} - {message}")
        
    except Exception as e:
        print(f"Configuration error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_configuration()
```

### Performance Monitoring

```python
# monitoring/performance_monitor.py
import time
import psutil
from typing import Dict, Any

class PerformanceMonitor:
    """Monitor system performance metrics"""
    
    def __init__(self):
        self.start_time = time.time()
        self.initial_memory = psutil.virtual_memory().used
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        process = psutil.Process()
        memory = psutil.virtual_memory()
        
        return {
            'uptime_seconds': time.time() - self.start_time,
            'cpu_percent': process.cpu_percent(),
            'memory_percent': process.memory_percent(),
            'memory_used_mb': process.memory_info().rss / 1024 / 1024,
            'system_memory_percent': memory.percent,
            'system_memory_available_gb': memory.available / 1024**3,
            'open_files': len(process.open_files()),
            'num_threads': process.num_threads()
        }
    
    def check_thresholds(self) -> Dict[str, bool]:
        """Check if metrics exceed thresholds"""
        metrics = self.get_metrics()
        
        return {
            'cpu_ok': metrics['cpu_percent'] < 80,
            'memory_ok': metrics['memory_percent'] < 80,
            'system_memory_ok': metrics['system_memory_percent'] < 90,
            'files_ok': metrics['open_files'] < 1000,
            'threads_ok': metrics['num_threads'] < 100
        }
```

This comprehensive configuration guide provides the foundation for deploying RPA Land Use Analytics agents in production environments with proper security, performance optimization, and monitoring capabilities. The configuration patterns are designed to be maintainable, secure, and scalable across different deployment environments.