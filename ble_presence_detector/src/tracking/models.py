"""Data models for presence tracking."""

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class DetectionEvent:
    """Record of a single BLE detection.

    Attributes:
        timestamp: When the device was detected
        rssi: Received Signal Strength Indicator in dBm
        distance_estimate: Estimated distance in meters (if calculable)
    """
    timestamp: datetime
    rssi: int
    distance_estimate: Optional[float] = None

    @staticmethod
    def estimate_distance(rssi: int, tx_power: int = -59) -> float:
        """Estimate distance from RSSI using the log-distance path loss model.

        This is an approximation and can vary significantly based on:
        - Environmental interference
        - Device orientation
        - Obstacles between devices
        - Antenna characteristics

        Formula: distance = 10 ^ ((tx_power - rssi) / (10 * n))
        where n is the path loss exponent (typically 2-4, we use 2)

        Args:
            rssi: Received signal strength in dBm
            tx_power: Transmit power at 1 meter in dBm (default -59 for typical BLE)

        Returns:
            Estimated distance in meters
        """
        if rssi >= 0:
            return 0.0

        path_loss_exponent = 2.0
        ratio = (tx_power - rssi) / (10.0 * path_loss_exponent)
        return math.pow(10, ratio)


@dataclass
class DevicePresenceState:
    """Current presence state of a tracked device.

    This is the core data model for tracking. It maintains both current
    state and historical data for confidence calculations.

    Attributes:
        device_id: Unique device identifier
        device_name: Human-readable device name
        present: Current presence status (based on confidence threshold)
        confidence: Current confidence level (0.0 - 1.0)
        last_seen: When device was last detected
        last_detection: Most recent detection event details
        detection_history: Recent detection events (bounded)
        state_changes: Count of presence state transitions
    """
    device_id: str
    device_name: str
    present: bool = False
    confidence: float = 0.0
    last_seen: datetime = field(default_factory=datetime.now)
    last_detection: Optional[DetectionEvent] = None
    detection_history: List[DetectionEvent] = field(default_factory=list)
    state_changes: int = 0

    def add_detection(self, rssi: int, tx_power: Optional[int] = None,
                     max_history: int = 10) -> None:
        """Add a new detection event.

        Updates last_seen, creates detection event with distance estimate,
        and maintains bounded history.

        Args:
            rssi: Received signal strength
            tx_power: Advertised TX power (if available)
            max_history: Maximum detection events to keep
        """
        now = datetime.now()
        self.last_seen = now

        tx_power_value = tx_power if tx_power is not None else -59
        distance = DetectionEvent.estimate_distance(rssi, tx_power_value)

        event = DetectionEvent(
            timestamp=now,
            rssi=rssi,
            distance_estimate=distance
        )

        self.last_detection = event
        self.detection_history.append(event)

        if len(self.detection_history) > max_history:
            self.detection_history = self.detection_history[-max_history:]

    def get_average_rssi(self, count: int = 5) -> Optional[float]:
        """Calculate average RSSI from recent detections.

        Useful for smoothing RSSI values which can be noisy.

        Args:
            count: Number of recent detections to average

        Returns:
            Average RSSI or None if no history
        """
        if not self.detection_history:
            return None

        recent = self.detection_history[-count:]
        return sum(event.rssi for event in recent) / len(recent)

    def get_average_distance(self, count: int = 5) -> Optional[float]:
        """Calculate average distance from recent detections.

        Args:
            count: Number of recent detections to average

        Returns:
            Average distance in meters or None if no history
        """
        if not self.detection_history:
            return None

        recent = self.detection_history[-count:]
        distances = [event.distance_estimate for event in recent
                    if event.distance_estimate is not None]

        if not distances:
            return None

        return sum(distances) / len(distances)

    def increment_state_changes(self) -> None:
        """Increment the state change counter."""
        self.state_changes += 1
