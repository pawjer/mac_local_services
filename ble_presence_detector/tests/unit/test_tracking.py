"""Unit tests for tracking components."""

import pytest
from datetime import datetime, timedelta
import math

from src.tracking.models import DetectionEvent, DevicePresenceState
from src.tracking.confidence_calculator import ConfidenceCalculator


class TestDetectionEvent:
    """Test detection event model."""

    def test_distance_estimation(self):
        """Test distance estimation from RSSI."""
        distance = DetectionEvent.estimate_distance(rssi=-65, tx_power=-59)
        assert distance > 0

    def test_distance_at_1m(self):
        """Test distance at 1 meter (rssi = tx_power)."""
        distance = DetectionEvent.estimate_distance(rssi=-59, tx_power=-59)
        assert 0.9 <= distance <= 1.1

    def test_distance_very_close(self):
        """Test distance when very close (high RSSI)."""
        distance = DetectionEvent.estimate_distance(rssi=-40, tx_power=-59)
        assert distance < 1.0


class TestDevicePresenceState:
    """Test device presence state model."""

    def test_add_detection(self):
        """Test adding a detection event."""
        state = DevicePresenceState(device_id="test", device_name="Test")

        old_last_seen = state.last_seen
        state.add_detection(rssi=-65)

        assert state.last_seen >= old_last_seen
        assert state.last_detection is not None
        assert state.last_detection.rssi == -65
        assert len(state.detection_history) == 1

    def test_detection_history_limit(self):
        """Test detection history is bounded."""
        state = DevicePresenceState(device_id="test", device_name="Test")

        for i in range(20):
            state.add_detection(rssi=-65)

        assert len(state.detection_history) == 10

    def test_average_rssi(self):
        """Test average RSSI calculation."""
        state = DevicePresenceState(device_id="test", device_name="Test")

        state.add_detection(rssi=-60)
        state.add_detection(rssi=-70)

        avg = state.get_average_rssi()
        assert avg == -65.0

    def test_average_rssi_no_history(self):
        """Test average RSSI with no history."""
        state = DevicePresenceState(device_id="test", device_name="Test")
        assert state.get_average_rssi() is None

    def test_increment_state_changes(self):
        """Test state change counter."""
        state = DevicePresenceState(device_id="test", device_name="Test")

        assert state.state_changes == 0
        state.increment_state_changes()
        assert state.state_changes == 1


class TestConfidenceCalculator:
    """Test confidence calculator."""

    def test_immediate_confidence(self):
        """Test confidence immediately after detection."""
        calc = ConfidenceCalculator(decay_rate=0.1)
        now = datetime.now()

        confidence = calc.calculate(last_seen=now, current_time=now)
        assert confidence == 1.0

    def test_decay_over_time(self):
        """Test confidence decays over time."""
        calc = ConfidenceCalculator(decay_rate=0.1)
        now = datetime.now()
        later = now + timedelta(seconds=10)

        confidence = calc.calculate(last_seen=now, current_time=later)
        assert 0 < confidence < 1.0

    def test_exponential_decay_formula(self):
        """Test exponential decay formula."""
        decay_rate = 0.1
        calc = ConfidenceCalculator(decay_rate=decay_rate)
        now = datetime.now()
        later = now + timedelta(seconds=10)

        confidence = calc.calculate(last_seen=now, current_time=later)
        expected = math.exp(-decay_rate * 10)

        assert abs(confidence - expected) < 0.001

    def test_is_present(self):
        """Test presence determination."""
        calc = ConfidenceCalculator(decay_rate=0.1)

        assert calc.is_present(0.6, threshold=0.5)
        assert not calc.is_present(0.4, threshold=0.5)

    def test_time_to_threshold(self):
        """Test time to threshold calculation."""
        decay_rate = 0.1
        calc = ConfidenceCalculator(decay_rate=decay_rate)

        time = calc.time_to_threshold(threshold=0.5)
        expected = -math.log(0.5) / decay_rate

        assert abs(time - expected) < 0.001

    def test_half_life(self):
        """Test half-life calculation."""
        decay_rate = 0.1
        calc = ConfidenceCalculator(decay_rate=decay_rate)

        half_life = calc.half_life
        expected = math.log(2) / decay_rate

        assert abs(half_life - expected) < 0.001
