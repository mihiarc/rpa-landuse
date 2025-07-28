"""Structured logging implementation."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console
from rich.logging import RichHandler

from landuse.core.app_config import LoggingConfig
from landuse.core.interfaces import LoggerInterface


class StructuredLogger(LoggerInterface):
    """
    Structured logger with rich console output and optional file logging.
    
    Features:
    - Structured JSON logging to files
    - Rich console output for development
    - Performance timing support
    - Security event logging
    - Component-specific loggers
    """
    
    def __init__(self, config: LoggingConfig):
        """Initialize structured logger."""
        self.config = config
        self.console = Console()
        
        # Create main logger
        self.logger = self._setup_logger()
        
        # Create specialized loggers
        self.security_logger = self._setup_security_logger()
        self.performance_logger = self._setup_performance_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Set up main application logger."""
        logger = logging.getLogger('landuse')
        logger.setLevel(getattr(logging, self.config.level))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Add console handler with Rich
        if not self.config.log_file:
            rich_handler = RichHandler(
                console=self.console,
                show_time=True,
                show_path=True,
                rich_tracebacks=True
            )
            rich_handler.setFormatter(logging.Formatter(
                fmt='[%(name)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            logger.addHandler(rich_handler)
        
        # Add file handler if configured
        if self.config.log_file:
            # Ensure log directory exists
            log_path = Path(self.config.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(self.config.log_file)
            file_handler.setFormatter(StructuredFormatter())
            logger.addHandler(file_handler)
        
        return logger
    
    def _setup_security_logger(self) -> logging.Logger:
        """Set up security event logger."""
        security_logger = logging.getLogger('landuse.security')
        security_logger.setLevel(logging.INFO)
        
        if self.config.log_file:
            # Create separate security log file
            security_log_path = Path(self.config.log_file).parent / 'security.log'
            
            security_handler = logging.FileHandler(security_log_path)
            security_handler.setFormatter(StructuredFormatter())
            security_logger.addHandler(security_handler)
        
        return security_logger
    
    def _setup_performance_logger(self) -> logging.Logger:
        """Set up performance metrics logger."""
        perf_logger = logging.getLogger('landuse.performance')
        perf_logger.setLevel(logging.INFO)
        
        if self.config.enable_performance_logging and self.config.log_file:
            # Create separate performance log file
            perf_log_path = Path(self.config.log_file).parent / 'performance.log'
            
            perf_handler = logging.FileHandler(perf_log_path)
            perf_handler.setFormatter(StructuredFormatter())
            perf_logger.addHandler(perf_handler)
        
        return perf_logger
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self.logger.error(message, extra=kwargs)
    
    def security_event(self, event_type: str, message: str, **context) -> None:
        """Log security event."""
        self.security_logger.info(
            f"[SECURITY] {event_type}: {message}",
            extra={
                'event_type': event_type,
                'security_event': True,
                **context
            }
        )
    
    def performance_event(self, operation: str, duration: float, **context) -> None:
        """Log performance event."""
        if self.config.enable_performance_logging:
            self.performance_logger.info(
                f"[PERFORMANCE] {operation}: {duration:.3f}s",
                extra={
                    'operation': operation,
                    'duration': duration,
                    'performance_event': True,
                    **context
                }
            )
    
    def log_query_execution(self, query: str, duration: float, row_count: int) -> None:
        """Log database query execution."""
        self.performance_event(
            'database_query',
            duration,
            query_length=len(query),
            row_count=row_count
        )
    
    def log_llm_call(self, model: str, duration: float, token_count: int) -> None:
        """Log LLM API call."""
        self.performance_event(
            'llm_call',
            duration,
            model=model,
            token_count=token_count
        )


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                              'filename', 'module', 'lineno', 'funcName', 'created', 
                              'msecs', 'relativeCreated', 'thread', 'threadName', 
                              'processName', 'process', 'message']:
                    log_data[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)