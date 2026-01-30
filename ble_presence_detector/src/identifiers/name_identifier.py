"""Name-based device identifier."""

import re
from .base import BaseIdentifier
from ..core.protocols import BLEAdvertisement


class NameBasedIdentifier(BaseIdentifier):
    """Identifies devices by their advertised name.

    Supports both exact string matching and regex patterns.
    """

    def __init__(self, device_id: str, device_name: str, pattern: str, use_regex: bool = False):
        """Initialize name-based identifier.

        Args:
            device_id: Unique device identifier
            device_name: Human-readable device name
            pattern: Name pattern to match (exact string or regex)
            use_regex: Whether to treat pattern as regex

        Raises:
            ValueError: If regex pattern is invalid
        """
        super().__init__(device_id, device_name)
        self._pattern = pattern
        self._use_regex = use_regex

        if use_regex:
            try:
                self._compiled_pattern = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}")
        else:
            self._compiled_pattern = None

    def matches(self, advertisement: BLEAdvertisement) -> bool:
        """Check if advertisement name matches the pattern.

        Args:
            advertisement: BLE advertisement data

        Returns:
            True if name matches (case-insensitive)
        """
        if advertisement.name is None:
            return False

        if self._use_regex:
            return self._compiled_pattern.search(advertisement.name) is not None
        else:
            return advertisement.name.lower() == self._pattern.lower()

    def __repr__(self) -> str:
        """String representation for debugging."""
        mode = "regex" if self._use_regex else "exact"
        return f"NameBasedIdentifier(device_id='{self._device_id}', pattern='{self._pattern}', mode={mode})"
