"""Factory for creating device identifiers from configuration."""

from typing import List
from ..config.models import (
    DeviceConfig, IdentifierConfig,
    NameIdentifierConfig, MACIdentifierConfig,
    ManufacturerIdentifierConfig, ServiceUUIDIdentifierConfig
)
from ..core.exceptions import ConfigurationError
from .base import BaseIdentifier
from .name_identifier import NameBasedIdentifier
from .mac_identifier import MACAddressIdentifier
from .manufacturer_identifier import ManufacturerDataIdentifier
from .service_uuid_identifier import ServiceUUIDIdentifier


class IdentifierFactory:
    """Factory for creating device identifiers.

    This implements the Factory pattern, creating appropriate identifier
    instances based on configuration type. Adding a new identifier type
    requires only:
    1. Creating the identifier class
    2. Adding a new config model
    3. Adding a case to _create_single()
    """

    @staticmethod
    def create_identifiers(device_config: DeviceConfig) -> List[BaseIdentifier]:
        """Create all identifiers for a device.

        A device matches if ANY of its identifiers match (OR logic).

        Args:
            device_config: Device configuration

        Returns:
            List of identifier instances

        Raises:
            ConfigurationError: If identifier config is invalid
        """
        identifiers = []

        for identifier_config in device_config.identifiers:
            identifier = IdentifierFactory._create_single(
                device_config.id,
                device_config.name,
                identifier_config
            )
            identifiers.append(identifier)

        return identifiers

    @staticmethod
    def _create_single(device_id: str, device_name: str,
                      config: IdentifierConfig) -> BaseIdentifier:
        """Create a single identifier from configuration.

        Args:
            device_id: Device ID
            device_name: Device name
            config: Identifier configuration

        Returns:
            Identifier instance

        Raises:
            ConfigurationError: If identifier type is unknown or config is invalid
        """
        try:
            if isinstance(config, NameIdentifierConfig):
                return NameBasedIdentifier(
                    device_id=device_id,
                    device_name=device_name,
                    pattern=config.pattern,
                    use_regex=config.regex
                )

            elif isinstance(config, MACIdentifierConfig):
                return MACAddressIdentifier(
                    device_id=device_id,
                    device_name=device_name,
                    mac_address=config.address
                )

            elif isinstance(config, ManufacturerIdentifierConfig):
                return ManufacturerDataIdentifier(
                    device_id=device_id,
                    device_name=device_name,
                    company_id=config.company_id,
                    data_pattern=config.data_pattern
                )

            elif isinstance(config, ServiceUUIDIdentifierConfig):
                return ServiceUUIDIdentifier(
                    device_id=device_id,
                    device_name=device_name,
                    uuids=config.uuids,
                    require_all=config.require_all
                )

            else:
                raise ConfigurationError(
                    f"Unknown identifier type: {type(config).__name__}"
                )

        except ValueError as e:
            raise ConfigurationError(
                f"Invalid identifier configuration for device '{device_id}': {e}"
            )
