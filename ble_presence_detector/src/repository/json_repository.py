"""JSON-based state repository."""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

from ..core.protocols import StateRepository
from ..tracking.models import DevicePresenceState, DetectionEvent
from ..core.exceptions import RepositoryError


logger = logging.getLogger(__name__)


class JSONStateRepository(StateRepository):
    """Persists device states to a JSON file.

    Implements the Repository pattern, abstracting state persistence.
    This implementation uses a simple JSON file, but could be replaced
    with Redis, SQLite, etc. without changing other components.
    """

    def __init__(self, file_path: Path):
        """Initialize JSON repository.

        Args:
            file_path: Path to JSON file for persistence
        """
        self._file_path = Path(file_path)
        logger.info(f"JSON repository initialized at {self._file_path}")

    async def save(self, device_id: str, state: DevicePresenceState) -> None:
        """Save a device's presence state.

        Args:
            device_id: Device ID
            state: State to save

        Raises:
            RepositoryError: If save fails
        """
        try:
            all_states = await self.load_all()
            all_states[device_id] = state
            await self._save_all(all_states)

            logger.debug(f"Saved state for device {device_id}")

        except Exception as e:
            raise RepositoryError(f"Failed to save state for {device_id}: {e}")

    async def load(self, device_id: str) -> Optional[DevicePresenceState]:
        """Load a device's presence state.

        Args:
            device_id: Device ID

        Returns:
            State if found, None otherwise

        Raises:
            RepositoryError: If load fails
        """
        try:
            all_states = await self.load_all()
            return all_states.get(device_id)

        except Exception as e:
            raise RepositoryError(f"Failed to load state for {device_id}: {e}")

    async def load_all(self) -> Dict[str, DevicePresenceState]:
        """Load all persisted device states.

        Returns:
            Dictionary of device_id -> state

        Raises:
            RepositoryError: If load fails critically
        """
        if not self._file_path.exists():
            logger.debug(f"State file {self._file_path} does not exist, returning empty dict")
            return {}

        try:
            with open(self._file_path, 'r') as f:
                data = json.load(f)

            states = {}
            for device_id, state_data in data.items():
                try:
                    state = self._deserialize_state(state_data)
                    states[device_id] = state
                except Exception as e:
                    logger.warning(f"Failed to deserialize state for {device_id}: {e}")

            logger.info(f"Loaded {len(states)} device states from {self._file_path}")
            return states

        except json.JSONDecodeError as e:
            logger.error(f"Corrupted JSON in {self._file_path}: {e}")
            return {}

        except Exception as e:
            raise RepositoryError(f"Failed to load states: {e}")

    async def _save_all(self, states: Dict[str, DevicePresenceState]) -> None:
        """Save all states to file.

        Args:
            states: All states to save

        Raises:
            RepositoryError: If save fails
        """
        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)

            data = {}
            for device_id, state in states.items():
                data[device_id] = self._serialize_state(state)

            with open(self._file_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(states)} device states to {self._file_path}")

        except Exception as e:
            raise RepositoryError(f"Failed to save states: {e}")

    @staticmethod
    def _serialize_state(state: DevicePresenceState) -> Dict[str, Any]:
        """Serialize state to JSON-compatible dict.

        Args:
            state: State to serialize

        Returns:
            Serialized state
        """
        data = {
            "device_id": state.device_id,
            "device_name": state.device_name,
            "present": state.present,
            "confidence": state.confidence,
            "last_seen": state.last_seen.isoformat(),
            "state_changes": state.state_changes
        }

        if state.last_detection:
            data["last_detection"] = {
                "timestamp": state.last_detection.timestamp.isoformat(),
                "rssi": state.last_detection.rssi,
                "distance_estimate": state.last_detection.distance_estimate
            }

        data["detection_history"] = [
            {
                "timestamp": event.timestamp.isoformat(),
                "rssi": event.rssi,
                "distance_estimate": event.distance_estimate
            }
            for event in state.detection_history[-5:]
        ]

        return data

    @staticmethod
    def _deserialize_state(data: Dict[str, Any]) -> DevicePresenceState:
        """Deserialize state from JSON dict.

        Args:
            data: Serialized state

        Returns:
            DevicePresenceState instance
        """
        last_detection = None
        if "last_detection" in data and data["last_detection"]:
            last_detection = DetectionEvent(
                timestamp=datetime.fromisoformat(data["last_detection"]["timestamp"]),
                rssi=data["last_detection"]["rssi"],
                distance_estimate=data["last_detection"].get("distance_estimate")
            )

        detection_history = []
        if "detection_history" in data:
            for event_data in data["detection_history"]:
                event = DetectionEvent(
                    timestamp=datetime.fromisoformat(event_data["timestamp"]),
                    rssi=event_data["rssi"],
                    distance_estimate=event_data.get("distance_estimate")
                )
                detection_history.append(event)

        return DevicePresenceState(
            device_id=data["device_id"],
            device_name=data["device_name"],
            present=data["present"],
            confidence=data["confidence"],
            last_seen=datetime.fromisoformat(data["last_seen"]),
            last_detection=last_detection,
            detection_history=detection_history,
            state_changes=data.get("state_changes", 0)
        )
