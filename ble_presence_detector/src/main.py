"""Main application orchestrator for BLE presence detection."""

import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from .config.loader import ConfigLoader
from .config.models import AppConfig, MQTTConfig, ScannerConfig
from .core.exceptions import BLEPresenceError, ConfigurationError
from .scanner.ble_scanner import BLEScanner
from .identifiers.factory import IdentifierFactory
from .tracking.presence_tracker import PresenceTracker
from .publishing.mqtt_publisher import MQTTPublisher
from .repository.json_repository import JSONStateRepository


logger = logging.getLogger(__name__)


class BLEPresenceDetector:
    """Main application orchestrator.

    Coordinates all components:
    1. Scanner detects BLE advertisements
    2. Tracker matches them to devices and updates presence
    3. Publisher sends state changes to MQTT
    4. Repository persists state to disk

    Uses dependency injection throughout for testability and flexibility.
    """

    def __init__(self, config: AppConfig, state_file_path: Path):
        """Initialize BLE presence detector.

        Args:
            config: Application configuration
            state_file_path: Path to state file
        """
        self._config = config
        self._state_file_path = state_file_path

        self._scanner: Optional[BLEScanner] = None
        self._tracker: Optional[PresenceTracker] = None
        self._publisher: Optional[MQTTPublisher] = None
        self._repository: Optional[JSONStateRepository] = None

        self._running = False
        self._update_task: Optional[asyncio.Task] = None

    async def setup(self) -> None:
        """Initialize all components with dependency injection.

        Raises:
            BLEPresenceError: If setup fails
        """
        logger.info("Setting up BLE presence detector")

        try:
            identifiers_map = {}
            for device_config in self._config.devices:
                identifiers = IdentifierFactory.create_identifiers(device_config)
                identifiers_map[device_config.id] = identifiers
                logger.info(
                    f"Created {len(identifiers)} identifier(s) for "
                    f"'{device_config.name}' ({device_config.id})"
                )

            self._tracker = PresenceTracker(
                device_configs=self._config.devices,
                identifiers_map=identifiers_map
            )

            self._scanner = BLEScanner(
                scan_interval=self._config.scanner.scan_interval,
                scan_duration=self._config.scanner.scan_duration
            )

            self._scanner.register_callback(self._tracker.process_advertisement)

            self._publisher = MQTTPublisher(self._config.mqtt)
            self._tracker.register_observer(self._publisher)

            await self._publisher.connect()

            self._repository = JSONStateRepository(self._state_file_path)

            await self._restore_state()

            logger.info("Setup complete")

        except Exception as e:
            logger.error(f"Setup failed: {e}", exc_info=True)
            raise BLEPresenceError(f"Setup failed: {e}")

    async def run(self) -> None:
        """Run the main application loop.

        Raises:
            BLEPresenceError: If run fails
        """
        if self._running:
            raise BLEPresenceError("Already running")

        self._running = True
        logger.info("Starting BLE presence detector")

        try:
            await self._scanner.start()

            self._update_task = asyncio.create_task(self._update_loop())

            while self._running:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Run cancelled")

        except Exception as e:
            logger.error(f"Run failed: {e}", exc_info=True)
            raise BLEPresenceError(f"Run failed: {e}")

    async def shutdown(self) -> None:
        """Clean shutdown of all components."""
        logger.info("Shutting down")

        self._running = False

        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

        if self._scanner:
            await self._scanner.stop()

        await self._save_state()

        if self._publisher:
            await self._publisher.disconnect()

        logger.info("Shutdown complete")

    async def _update_loop(self) -> None:
        """Periodically update confidence and save state.

        This loop applies exponential decay to confidence levels and
        persists state to disk.
        """
        while self._running:
            try:
                await asyncio.sleep(1)

                if self._tracker:
                    await self._tracker.update_all_confidences()

                if self._running and self._tracker:
                    await self._save_state()

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error(f"Error in update loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _restore_state(self) -> None:
        """Restore device states from repository."""
        if not self._repository or not self._tracker:
            return

        try:
            logger.info("Restoring device states")
            saved_states = await self._repository.load_all()

            for device_id, saved_state in saved_states.items():
                current_state = self._tracker.get_state(device_id)
                if current_state:
                    current_state.present = saved_state.present
                    current_state.confidence = saved_state.confidence
                    current_state.last_seen = saved_state.last_seen
                    current_state.last_detection = saved_state.last_detection
                    current_state.detection_history = saved_state.detection_history
                    current_state.state_changes = saved_state.state_changes

                    logger.info(
                        f"Restored state for '{current_state.device_name}' ({device_id}): "
                        f"{'present' if current_state.present else 'absent'} "
                        f"(confidence={current_state.confidence:.3f})"
                    )

        except Exception as e:
            logger.warning(f"Failed to restore state: {e}")

    async def _save_state(self) -> None:
        """Save all device states to repository."""
        if not self._repository or not self._tracker:
            return

        try:
            states = self._tracker.get_all_states()
            for device_id, state in states.items():
                await self._repository.save(device_id, state)

        except Exception as e:
            logger.error(f"Failed to save state: {e}", exc_info=True)


def apply_env_overrides(config: AppConfig) -> AppConfig:
    """Apply environment variable overrides to configuration.

    Environment variables take precedence over YAML configuration.

    Supported variables:
    - MQTT_HOST: MQTT broker host
    - MQTT_PORT: MQTT broker port
    - MQTT_USERNAME: MQTT username
    - MQTT_PASSWORD: MQTT password
    - MQTT_TOPIC_PREFIX: MQTT topic prefix
    - MQTT_QOS: MQTT QoS level
    - MQTT_CLIENT_ID: MQTT client ID
    - SCAN_INTERVAL: BLE scan interval in seconds
    - SCAN_DURATION: BLE scan duration in seconds
    - STATE_FILE: Path to state file
    - LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)

    Args:
        config: Loaded configuration from YAML

    Returns:
        Configuration with environment overrides applied
    """
    # MQTT overrides
    if mqtt_host := os.getenv('MQTT_HOST'):
        config.mqtt.host = mqtt_host
        logger.info(f"Override: MQTT host = {mqtt_host}")

    if mqtt_port := os.getenv('MQTT_PORT'):
        config.mqtt.port = int(mqtt_port)
        logger.info(f"Override: MQTT port = {mqtt_port}")

    if mqtt_username := os.getenv('MQTT_USERNAME'):
        config.mqtt.username = mqtt_username
        logger.info("Override: MQTT username set")

    if mqtt_password := os.getenv('MQTT_PASSWORD'):
        config.mqtt.password = mqtt_password
        logger.info("Override: MQTT password set")

    if mqtt_topic_prefix := os.getenv('MQTT_TOPIC_PREFIX'):
        config.mqtt.topic_prefix = mqtt_topic_prefix
        logger.info(f"Override: MQTT topic prefix = {mqtt_topic_prefix}")

    if mqtt_qos := os.getenv('MQTT_QOS'):
        config.mqtt.qos = int(mqtt_qos)
        logger.info(f"Override: MQTT QoS = {mqtt_qos}")

    if mqtt_client_id := os.getenv('MQTT_CLIENT_ID'):
        config.mqtt.client_id = mqtt_client_id
        logger.info(f"Override: MQTT client ID = {mqtt_client_id}")

    # Scanner overrides
    if scan_interval := os.getenv('SCAN_INTERVAL'):
        config.scanner.scan_interval = float(scan_interval)
        logger.info(f"Override: Scan interval = {scan_interval}s")

    if scan_duration := os.getenv('SCAN_DURATION'):
        config.scanner.scan_duration = float(scan_duration)
        logger.info(f"Override: Scan duration = {scan_duration}s")

    # State file override
    if state_file := os.getenv('STATE_FILE'):
        config.state_file = state_file
        logger.info(f"Override: State file = {state_file}")

    # Log level override
    if log_level := os.getenv('LOG_LEVEL'):
        config.log_level = log_level.upper()
        logger.info(f"Override: Log level = {log_level}")

    return config


async def main(config_path: Optional[Path] = None, env_file: Optional[Path] = None) -> None:
    """Main entry point.

    Args:
        config_path: Path to configuration file
        env_file: Path to .env file (optional)
    """
    parser = argparse.ArgumentParser(description='BLE Presence Detector')
    parser.add_argument('config_file', help='Path to YAML configuration file')
    parser.add_argument('--env-file', help='Path to .env file for overrides', default=None)

    args = parser.parse_args()

    config_path = Path(args.config_file)
    env_file = Path(args.env_file) if args.env_file else None

    # Load .env file if specified
    if env_file and env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print(f"Loaded environment from {env_file}")
        except ImportError:
            print("Warning: python-dotenv not installed, skipping .env file", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Failed to load .env file: {e}", file=sys.stderr)

    # Load base configuration from YAML
    try:
        config = ConfigLoader.load(config_path)
    except ConfigurationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Setup basic logging first
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Apply environment variable overrides
    config = apply_env_overrides(config)

    logger.info(f"Starting BLE presence detector with config: {config_path}")
    logger.info(f"MQTT broker: {config.mqtt.host}:{config.mqtt.port}")
    logger.info(f"MQTT topic prefix: {config.mqtt.topic_prefix}")
    logger.info(f"Scan interval: {config.scanner.scan_interval}s, duration: {config.scanner.scan_duration}s")

    state_file_path = config_path.parent / config.state_file

    detector = BLEPresenceDetector(config, state_file_path)

    loop = asyncio.get_event_loop()

    def signal_handler(sig):
        """Handle shutdown signals."""
        logger.info(f"Received signal {sig}, initiating shutdown")
        asyncio.create_task(detector.shutdown())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    try:
        await detector.setup()
        await detector.run()

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt")

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await detector.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
