"""
Logging Configuration

Centralized logging setup for the application.
- Local environment: Logs to console with colored output
- Cloud environment: Integrates with Google Cloud Logging

Usage:
    from maxiagent.core.logging import get_logger

    logger = get_logger(__name__)
    logger.info("Application started")
    logger.debug("Debug information")
    logger.error("An error occurred")
"""
import logging
import sys

from maxiagent.core.config import settings

# Try to import Google Cloud Logging (may not be available locally)
try:
    from google.cloud import logging as cloud_logging
    CLOUD_LOGGING_AVAILABLE = True
except ImportError:
    CLOUD_LOGGING_AVAILABLE = False


class ColoredFormatter(logging.Formatter):
    """
    Colored log formatter for better readability in local development.

    Colors:
    - DEBUG: Cyan
    - INFO: Green
    - WARNING: Yellow
    - ERROR: Red
    - CRITICAL: Red + Bold
    """

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[1;31m', # Red + Bold
    }
    RESET = '\033[0m'

    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"

        # Format the message
        return super().format(record)


def setup_logging() -> None:
    """
    Configure logging for the application.

    Local Environment:
    - Logs to console with colored output
    - Shows: timestamp, level, logger name, message
    - Default level: DEBUG (or from LOG_LEVEL env var)

    Cloud Environment (Google Cloud Run):
    - Integrates with Google Cloud Logging
    - Logs are sent to Cloud Logging Explorer
    - Default level: INFO
    """

    # Determine log level from settings (uses EFFECTIVE_LOG_LEVEL which auto-configures based on ENV)
    log_level_str = settings.EFFECTIVE_LOG_LEVEL.upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    if settings.IS_LOCAL:
        # ==================== Local Environment ====================
        # Console handler with colored output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        # Colored formatter for better readability
        formatter = ColoredFormatter(
            fmt='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # Log initial message
        root_logger.info(f"🖥️  Local logging configured (level: {log_level_str})")

    else:
        # ==================== Cloud Environment ====================
        if CLOUD_LOGGING_AVAILABLE:
            try:
                # Setup Google Cloud Logging
                client = cloud_logging.Client(project=settings.GOOGLE_CLOUD_PROJECT)
                client.setup_logging(log_level=log_level)

                # Also add console handler for Cloud Run logs
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(log_level)

                formatter = logging.Formatter(
                    fmt='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                console_handler.setFormatter(formatter)
                root_logger.addHandler(console_handler)

                root_logger.info(f"☁️  Cloud logging configured (project: {settings.GOOGLE_CLOUD_PROJECT}, level: {log_level_str})")

            except Exception as e:
                # Fallback to console logging if Cloud Logging fails
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(log_level)

                formatter = logging.Formatter(
                    fmt='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                console_handler.setFormatter(formatter)
                root_logger.addHandler(console_handler)

                root_logger.warning(f"⚠️  Failed to setup Cloud Logging: {e}. Using console logging.")
        else:
            # Fallback if google-cloud-logging is not installed
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)

            formatter = logging.Formatter(
                fmt='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

            root_logger.warning("⚠️  google-cloud-logging not available. Using console logging.")

    # Suppress noisy third-party loggers
    _suppress_noisy_loggers()


def _suppress_noisy_loggers() -> None:
    """
    Reduce log noise from third-party libraries.

    Sets higher log levels for commonly verbose loggers.
    """
    noisy_loggers = [
        'urllib3',
        'google.auth',
        'google.api_core',
        'google.genai.types',  # Suppress Google Gen AI SDK warnings
        'werkzeug',  # Flask's built-in server
        'google_genai.types',  # Supressing the 'there are non-text parts' message
        'google_adk.google.adk.models.google_llm',  # Suppress verbose LLM request/response logs
        'google.adk.models.google_llm',  # Alternative path for ADK LLM logs
    ]

    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified module.

    Args:
        name: Name of the logger (typically __name__ from the calling module)

    Returns:
        Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Application started")
        logger.debug("Debug information")
        logger.error("An error occurred", exc_info=True)
    """
    return logging.getLogger(name)


# Initialize logging when this module is imported
setup_logging()