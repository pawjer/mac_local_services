"""Configuration loader for YAML files."""

import yaml
from pathlib import Path
from typing import Any, Dict
from pydantic import ValidationError

from .models import AppConfig
from ..core.exceptions import ConfigurationError


class ConfigLoader:
    """Loads and validates configuration from YAML files."""

    @staticmethod
    def load(config_path: Path) -> AppConfig:
        """Load configuration from YAML file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            Validated AppConfig instance

        Raises:
            ConfigurationError: If file not found, invalid YAML, or validation fails
        """
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {config_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to read {config_path}: {e}")

        if not isinstance(data, dict):
            raise ConfigurationError(f"Configuration must be a dictionary, got {type(data)}")

        try:
            return AppConfig(**data)
        except ValidationError as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")

    @staticmethod
    def load_from_dict(data: Dict[str, Any]) -> AppConfig:
        """Load configuration from dictionary (useful for testing).

        Args:
            data: Configuration dictionary

        Returns:
            Validated AppConfig instance

        Raises:
            ConfigurationError: If validation fails
        """
        try:
            return AppConfig(**data)
        except ValidationError as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")
