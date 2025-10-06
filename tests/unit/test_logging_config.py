"""
Unit tests for logging configuration.
"""
import logging
import pytest
from unittest.mock import patch, MagicMock

from utils.logging_config import setup_logging, get_logger


class TestLoggingConfig:
    """Test logging configuration and setup."""
    
    @patch('utils.logging_config.get_config')
    def test_setup_logging_console_only(self, mock_get_config):
        """Test logging setup with console handler only."""
        mock_config = MagicMock()
        mock_config.log_level = 'INFO'
        mock_config.gcs_credentials_path = '/tmp/test_credentials.json'
        mock_get_config.return_value = mock_config
        
        logger = setup_logging(use_cloud_logging=False)
        
        assert logger.name == 'miles_aggregator'
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)
    
    @patch('utils.logging_config.cloud_logging')
    @patch('utils.logging_config.get_config')
    def test_setup_logging_with_cloud_logging_success(self, mock_get_config, mock_cloud_logging):
        """Test successful logging setup with Google Cloud Logging."""
        mock_config = MagicMock()
        mock_config.log_level = 'DEBUG'
        mock_config.gcs_credentials_path = '/tmp/test_credentials.json'
        mock_get_config.return_value = mock_config
        
        # Mock cloud logging client
        mock_client = MagicMock()
        mock_handler = MagicMock()
        mock_handler.level = logging.DEBUG
        mock_client.get_default_handler.return_value = mock_handler
        mock_cloud_logging.Client.from_service_account_json.return_value = mock_client
        
        logger = setup_logging(use_cloud_logging=True)
        
        assert logger.name == 'miles_aggregator'
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) == 2  # Console + Cloud
        
        # Verify cloud logging client was called
        mock_cloud_logging.Client.from_service_account_json.assert_called_once_with(
            '/tmp/test_credentials.json'
        )
    
    @patch('utils.logging_config.cloud_logging')
    @patch('utils.logging_config.get_config')
    def test_setup_logging_cloud_logging_failure(self, mock_get_config, mock_cloud_logging):
        """Test logging setup falls back to console when cloud logging fails."""
        mock_config = MagicMock()
        mock_config.log_level = 'INFO'
        mock_config.gcs_credentials_path = '/tmp/test_credentials.json'
        mock_get_config.return_value = mock_config
        
        # Mock cloud logging to raise exception
        mock_cloud_logging.Client.from_service_account_json.side_effect = Exception("Cloud logging failed")
        
        logger = setup_logging(use_cloud_logging=True)
        
        assert logger.name == 'miles_aggregator'
        assert len(logger.handlers) == 1  # Only console handler
        assert isinstance(logger.handlers[0], logging.StreamHandler)
    
    def test_get_logger_default(self):
        """Test getting default logger."""
        logger = get_logger()
        assert logger.name == 'miles_aggregator'
    
    def test_get_logger_with_name(self):
        """Test getting logger with specific name."""
        logger = get_logger('test_module')
        assert logger.name == 'miles_aggregator.test_module'
    
    @patch('utils.logging_config.get_config')
    def test_logging_levels(self, mock_get_config):
        """Test different logging levels are set correctly."""
        test_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        
        for level_name in test_levels:
            mock_config = MagicMock()
            mock_config.log_level = level_name
            mock_config.gcs_credentials_path = '/tmp/test_credentials.json'
            mock_get_config.return_value = mock_config
            
            logger = setup_logging(use_cloud_logging=False)
            
            expected_level = getattr(logging, level_name)
            assert logger.level == expected_level
            assert logger.handlers[0].level == expected_level