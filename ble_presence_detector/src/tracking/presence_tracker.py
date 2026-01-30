"""Core presence tracking logic."""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from ..core.protocols import BLEAdvertisement, StateObserver
from ..config.models import DeviceConfig
from .models import DevicePresenceState
from .confidence_calculator import ConfidenceCalculator
from ..identifiers.base import BaseIdentifier


logger = logging.getLogger(__name__)


class PresenceTracker:
    """Tracks device presence based on BLE advertisements.

    This is the core business logic component that:
    1. Receives BLE advertisements from the scanner
    2. Matches them against device identifiers
    3. Updates confidence levels
    4. Determines presence state transitions
    5. Notifies observers of changes

    Uses the Observer pattern to notify components (like MQTT publisher)
    when device presence states change.
    """

    def __init__(self, device_configs: List[DeviceConfig],
                 identifiers_map: Dict[str, List[BaseIdentifier]]):
        """Initialize presence tracker.

        Args:
            device_configs: Device configurations
            identifiers_map: Map of device_id -> list of identifiers
        """
        self._device_configs = {config.id: config for config in device_configs}
        self._identifiers_map = identifiers_map
        self._states: Dict[str, DevicePresenceState] = {}
        self._observers: List[StateObserver] = []
        self._calculators: Dict[str, ConfidenceCalculator] = {}

        for device_id, config in self._device_configs.items():
            self._states[device_id] = DevicePresenceState(
                device_id=device_id,
                device_name=config.name
            )

            self._calculators[device_id] = ConfidenceCalculator(
                decay_rate=config.decay_rate
            )

        logger.info(f"Presence tracker initialized for {len(device_configs)} devices")

    def register_observer(self, observer: StateObserver) -> None:
        """Register an observer for state change notifications.

        Args:
            observer: Observer to register
        """
        self._observers.append(observer)
        logger.debug(f"Registered observer: {observer.__class__.__name__}")

    async def process_advertisement(self, advertisement: BLEAdvertisement) -> None:
        """Process a BLE advertisement.

        This is the main entry point called by the scanner for each
        detected advertisement.

        Args:
            advertisement: BLE advertisement data
        """
        matched_devices = self._identify_devices(advertisement)

        for device_id in matched_devices:
            await self._update_device_state(device_id, advertisement)

    async def update_all_confidences(self) -> None:
        """Update confidence for all devices based on time decay.

        Should be called periodically to apply exponential decay and
        detect when devices transition to absent state.
        """
        current_time = datetime.now()

        for device_id, state in self._states.items():
            old_confidence = state.confidence
            calculator = self._calculators[device_id]
            config = self._device_configs[device_id]

            new_confidence = calculator.calculate(
                last_seen=state.last_seen,
                initial_confidence=1.0,
                current_time=current_time
            )

            old_present = state.present
            new_present = calculator.is_present(
                new_confidence,
                config.confidence_threshold
            )

            state.confidence = new_confidence
            state.present = new_present

            if old_present != new_present:
                logger.info(
                    f"Device '{state.device_name}' ({device_id}) "
                    f"{'appeared' if new_present else 'disappeared'} "
                    f"(confidence: {new_confidence:.3f})"
                )

                old_state_copy = DevicePresenceState(
                    device_id=state.device_id,
                    device_name=state.device_name,
                    present=old_present,
                    confidence=old_confidence,
                    last_seen=state.last_seen,
                    last_detection=state.last_detection,
                    detection_history=state.detection_history.copy(),
                    state_changes=state.state_changes
                )

                state.increment_state_changes()
                await self._notify_observers(device_id, old_state_copy, state)

    def _identify_devices(self, advertisement: BLEAdvertisement) -> List[str]:
        """Identify which devices match this advertisement.

        Args:
            advertisement: BLE advertisement data

        Returns:
            List of device IDs that match
        """
        matched = []

        for device_id, identifiers in self._identifiers_map.items():
            for identifier in identifiers:
                if identifier.matches(advertisement):
                    matched.append(device_id)
                    logger.debug(
                        f"Advertisement from {advertisement.address} matched "
                        f"device '{self._states[device_id].device_name}' ({device_id}) "
                        f"via {identifier.__class__.__name__}"
                    )
                    break

        return matched

    async def _update_device_state(self, device_id: str,
                                  advertisement: BLEAdvertisement) -> None:
        """Update state for a detected device.

        Args:
            device_id: Device that was detected
            advertisement: Advertisement data
        """
        state = self._states[device_id]
        config = self._device_configs[device_id]
        calculator = self._calculators[device_id]

        old_state_copy = DevicePresenceState(
            device_id=state.device_id,
            device_name=state.device_name,
            present=state.present,
            confidence=state.confidence,
            last_seen=state.last_seen,
            last_detection=state.last_detection,
            detection_history=state.detection_history.copy(),
            state_changes=state.state_changes
        )

        state.add_detection(
            rssi=advertisement.rssi,
            tx_power=advertisement.tx_power
        )

        state.confidence = 1.0

        new_present = calculator.is_present(
            state.confidence,
            config.confidence_threshold
        )

        if state.present != new_present:
            logger.info(
                f"Device '{state.device_name}' ({device_id}) "
                f"{'appeared' if new_present else 'disappeared'} "
                f"(rssi={advertisement.rssi}, confidence={state.confidence:.3f})"
            )

            state.present = new_present
            state.increment_state_changes()
            await self._notify_observers(device_id, old_state_copy, state)

        else:
            logger.debug(
                f"Device '{state.device_name}' ({device_id}) detected "
                f"(rssi={advertisement.rssi}, confidence={state.confidence:.3f}, "
                f"distance≈{state.last_detection.distance_estimate:.1f}m)"
            )

    async def _notify_observers(self, device_id: str,
                               old_state: DevicePresenceState,
                               new_state: DevicePresenceState) -> None:
        """Notify all observers of a state change.

        Args:
            device_id: Device ID
            old_state: Previous state
            new_state: New state
        """
        for observer in self._observers:
            try:
                await observer.on_state_change(device_id, old_state, new_state)
            except Exception as e:
                logger.error(
                    f"Error notifying observer {observer.__class__.__name__}: {e}",
                    exc_info=True
                )

    def get_state(self, device_id: str) -> Optional[DevicePresenceState]:
        """Get current state for a device.

        Args:
            device_id: Device ID

        Returns:
            Current state or None if device not tracked
        """
        return self._states.get(device_id)

    def get_all_states(self) -> Dict[str, DevicePresenceState]:
        """Get all device states.

        Returns:
            Dictionary of device_id -> state
        """
        return self._states.copy()
