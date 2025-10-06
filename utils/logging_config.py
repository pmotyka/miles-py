"""
Logging configuration with Google Cloud Logging integration.
"""
import logging
import sys
import atexit
from typing import Optional
from google.cloud import logging as cloud_logging
from config import get_config

# Global reference to cloud logging client for cleanup
_cloud_logging_client = None

def setup_logging(use_cloud_logging: bool = True) -> logging.Logger:
    """
    Set up application logging with Google Cloud Logging integration.
    
    Args:
        use_cloud_logging: Whether to use Google Cloud Logging (default: True)
    
    Returns:
        Configured logger instance
    """
    # Get log level from configuration
    config = get_config()
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger('miles_aggregator')
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Set up console handler for local development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Set up Google Cloud Logging if enabled and credentials are available
    if use_cloud_logging and config.gcs_credentials_path:
        try:
            # Initialize Google Cloud Logging client
            global _cloud_logging_client
            _cloud_logging_client = cloud_logging.Client.from_service_account_json(
                config.gcs_credentials_path
            )
            
            # Set up cloud logging handler
            cloud_handler = _cloud_logging_client.get_default_handler()
            cloud_handler.setLevel(log_level)
            logger.addHandler(cloud_handler)
            
            # Register cleanup function to properly close the handler
            atexit.register(_cleanup_cloud_logging)
            
            logger.info("Google Cloud Logging initialized successfully")
            
        except Exception as e:
            logger.warning(f"Failed to initialize Google Cloud Logging: {e}")
            logger.info("Continuing with console logging only")
    elif use_cloud_logging:
        logger.info("Google Cloud Logging disabled - no credentials file specified")
    
    # Prevent duplicate logs from root logger
    logger.propagate = False
    
    return logger

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (defaults to 'miles_aggregator')
    
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f'miles_aggregator.{name}')
    return logging.getLogger('miles_aggregator')

def _cleanup_cloud_logging():
    """
    Clean up Google Cloud Logging resources.
    This function is called automatically at program exit.
    """
    global _cloud_logging_client
    if _cloud_logging_client:
        try:
            # Flush any pending log entries
            for handler in logging.getLogger('miles_aggregator').handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
            
            # Close the cloud logging client
            _cloud_logging_client.close()
            _cloud_logging_client = None
        except Exception:
            # Ignore errors during cleanup to avoid shutdown issues
            pass

def flush_logs():
    """
    Manually flush all log handlers.
    Call this before application shutdown for clean exit.
    """
    try:
        logger = logging.getLogger('miles_aggregator')
        for handler in logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
    except Exception:
        # Ignore errors during flush
        pass