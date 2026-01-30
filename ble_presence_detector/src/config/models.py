"""Configuration models using Pydantic for validation."""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Union
from pathlib import Path


class NameIdentifierConfig(BaseModel):
    """Configuration for name-based device identification."""
    type: str = Field(default="name", frozen=True)
    pattern: str = Field(..., description="Device name pattern to match")
    regex: bool = Field(default=False, description="Whether pattern is a regex")


class MACIdentifierConfig(BaseModel):
    """Configuration for MAC address-based identification."""
    type: str = Field(default="mac", frozen=True)
    address: str = Field(..., description="MAC address (any format)")

    @field_validator('address')
    @classmethod
    def normalize_mac(cls, v: str) -> str:
        """Normalize MAC address to lowercase with colons."""
        cleaned = v.replace(':', '').replace('-', '').replace('.', '').lower()
        if len(cleaned) != 12:
            raise ValueError(f"Invalid MAC address: {v}")
        return ':'.join(cleaned[i:i+2] for i in range(0, 12, 2))


class ManufacturerIdentifierConfig(BaseModel):
    """Configuration for manufacturer data-based identification."""
    type: str = Field(default="manufacturer", frozen=True)
    company_id: int = Field(..., description="Bluetooth company identifier")
    data_pattern: Optional[str] = Field(None, description="Hex pattern to match in manufacturer data")


class ServiceUUIDIdentifierConfig(BaseModel):
    """Configuration for service UUID-based identification."""
    type: str = Field(default="service_uuid", frozen=True)
    uuids: List[str] = Field(..., description="Service UUIDs to match")
    require_all: bool = Field(default=False, description="Whether all UUIDs must be present")

    @field_validator('uuids')
    @classmethod
    def normalize_uuids(cls, v: List[str]) -> List[str]:
        """Normalize UUIDs to lowercase."""
        return [uuid.lower() for uuid in v]


IdentifierConfig = Union[
    NameIdentifierConfig,
    MACIdentifierConfig,
    ManufacturerIdentifierConfig,
    ServiceUUIDIdentifierConfig
]


class DeviceConfig(BaseModel):
    """Configuration for a tracked device."""
    id: str = Field(..., description="Unique device identifier")
    name: str = Field(..., description="Human-readable device name")
    identifiers: List[IdentifierConfig] = Field(..., description="Identification strategies")
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0,
                                       description="Confidence threshold for presence")
    decay_rate: float = Field(default=0.1, ge=0.0, le=1.0,
                              description="Confidence decay rate per second")

    @field_validator('identifiers')
    @classmethod
    def validate_identifiers(cls, v: List[IdentifierConfig]) -> List[IdentifierConfig]:
        """Ensure at least one identifier is configured."""
        if not v:
            raise ValueError("At least one identifier must be configured")
        return v


class MQTTConfig(BaseModel):
    """Configuration for MQTT connection."""
    host: str = Field(default="localhost", description="MQTT broker host")
    port: int = Field(default=1883, ge=1, le=65535, description="MQTT broker port")
    username: Optional[str] = Field(None, description="MQTT username")
    password: Optional[str] = Field(None, description="MQTT password")
    topic_prefix: str = Field(default="home/presence", description="MQTT topic prefix")
    qos: int = Field(default=1, ge=0, le=2, description="MQTT QoS level")
    client_id: str = Field(default="ble_presence_detector", description="MQTT client ID")


class ScannerConfig(BaseModel):
    """Configuration for BLE scanner."""
    scan_interval: float = Field(default=5.0, gt=0, description="Interval between scans in seconds")
    scan_duration: float = Field(default=3.0, gt=0, description="Duration of each scan in seconds")

    @field_validator('scan_duration')
    @classmethod
    def validate_duration(cls, v: float, info) -> float:
        """Ensure scan duration is less than interval."""
        if 'scan_interval' in info.data and v >= info.data['scan_interval']:
            raise ValueError("scan_duration must be less than scan_interval")
        return v


class AppConfig(BaseModel):
    """Main application configuration."""
    mqtt: MQTTConfig = Field(default_factory=MQTTConfig)
    scanner: ScannerConfig = Field(default_factory=ScannerConfig)
    devices: List[DeviceConfig] = Field(..., description="Devices to track")
    state_file: str = Field(default="state.json", description="Path to state persistence file")
    log_level: str = Field(default="INFO", description="Logging level")

    @field_validator('devices')
    @classmethod
    def validate_devices(cls, v: List[DeviceConfig]) -> List[DeviceConfig]:
        """Ensure at least one device is configured and IDs are unique."""
        if not v:
            raise ValueError("At least one device must be configured")

        device_ids = [device.id for device in v]
        if len(device_ids) != len(set(device_ids)):
            raise ValueError("Device IDs must be unique")

        return v

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()
