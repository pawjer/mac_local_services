"""Custom exceptions for BLE presence detection system."""


class BLEPresenceError(Exception):
    """Base exception for all BLE presence detection errors."""
    pass


class ConfigurationError(BLEPresenceError):
    """Raised when configuration is invalid or missing."""
    pass


class ScannerError(BLEPresenceError):
    """Raised when BLE scanning operations fail."""
    pass


class IdentificationError(BLEPresenceError):
    """Raised when device identification fails."""
    pass


class PublishingError(BLEPresenceError):
    """Raised when MQTT publishing fails."""
    pass


class RepositoryError(BLEPresenceError):
    """Raised when state persistence operations fail."""
    pass
