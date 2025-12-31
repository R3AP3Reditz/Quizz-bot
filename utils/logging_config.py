"""
Logging Configuration Module
Sets up comprehensive logging for the quiz bot
"""

import logging
import logging.handlers
import os
from pathlib import Path
import sys

# Ensure logs directory exists
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def setup_logging(
    log_level: str = "INFO",
    log_file: str = "quiz_bot.log",
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
    log_to_console: bool = True
):
    """
    Setup comprehensive logging configuration

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Name of the log file
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        log_to_console: Whether to also log to console
    """
    log_file_path = LOGS_DIR / log_file

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Create separate loggers for different components
    setup_component_loggers(formatter)

    logging.info("Logging system initialized")


def setup_component_loggers(formatter):
    """Setup separate loggers for different components"""

    components = {
        'database': 'database.log',
        'memory': 'memory.log',
        'cache': 'cache.log',
        'backup': 'backup.log',
        'bot': 'bot.log'
    }

    for component, log_file in components.items():
        logger = logging.getLogger(component)
        log_file_path = LOGS_DIR / log_file

        # File handler for component
        handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=5242880,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)


class PerformanceLogger:
    """Logger for tracking performance metrics"""

    def __init__(self, logger_name: str = "performance"):
        self.logger = logging.getLogger(logger_name)
        self.log_file = LOGS_DIR / "performance.log"

        # Setup handler
        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_query_time(self, query_name: str, duration: float):
        """Log database query execution time"""
        self.logger.info(f"Query: {query_name} | Duration: {duration:.4f}s")

    def log_cache_hit(self, cache_type: str):
        """Log cache hit"""
        self.logger.info(f"Cache Hit: {cache_type}")

    def log_cache_miss(self, cache_type: str):
        """Log cache miss"""
        self.logger.info(f"Cache Miss: {cache_type}")

    def log_operation(self, operation: str, duration: float, success: bool):
        """Log general operation"""
        status = "SUCCESS" if success else "FAILURE"
        self.logger.info(f"Operation: {operation} | Duration: {duration:.4f}s | Status: {status}")


class ErrorLogger:
    """Logger for tracking errors and exceptions"""

    def __init__(self, logger_name: str = "errors"):
        self.logger = logging.getLogger(logger_name)
        self.log_file = LOGS_DIR / "errors.log"

        # Setup handler
        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s\n%(exc_info)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.ERROR)

    def log_error(self, error_type: str, message: str, exception: Exception = None):
        """Log an error with optional exception"""
        error_msg = f"[{error_type}] {message}"
        if exception:
            self.logger.error(error_msg, exc_info=exception)
        else:
            self.logger.error(error_msg)

    def log_critical(self, message: str, exception: Exception = None):
        """Log a critical error"""
        if exception:
            self.logger.critical(message, exc_info=exception)
        else:
            self.logger.critical(message)


class AuditLogger:
    """Logger for tracking user actions and changes"""

    def __init__(self, logger_name: str = "audit"):
        self.logger = logging.getLogger(logger_name)
        self.log_file = LOGS_DIR / "audit.log"

        # Setup handler
        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_user_action(self, user_id: int, action: str, details: str = ""):
        """Log a user action"""
        self.logger.info(f"User {user_id} | Action: {action} | {details}")

    def log_data_change(self, change_type: str, details: str):
        """Log a data change"""
        self.logger.info(f"Data Change: {change_type} | {details}")

    def log_admin_action(self, admin_id: int, action: str, target: str = ""):
        """Log an administrative action"""
        self.logger.info(f"Admin {admin_id} | Action: {action} | Target: {target}")


# Global logger instances
performance_logger = PerformanceLogger()
error_logger = ErrorLogger()
audit_logger = AuditLogger()


# Context manager for timing operations
class TimedOperation:
    """Context manager for timing and logging operations"""

    def __init__(self, operation_name: str, logger=None):
        self.operation_name = operation_name
        self.logger = logger or performance_logger
        self.start_time = None
        self.success = False

    def __enter__(self):
        import time
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time
        self.success = exc_type is None
        self.logger.log_operation(self.operation_name, duration, self.success)
        return False  # Don't suppress exceptions
