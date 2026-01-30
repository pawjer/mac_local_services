"""BLE scanner using bleak library."""

import asyncio
import logging
from datetime import datetime
from typing import List, Callable, Optional
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from ..core.protocols import BLEAdvertisement, AdvertisementCallback
from ..core.exceptions import ScannerError


logger = logging.getLogger(__name__)


class BLEScanner:
    """Continuous BLE scanner with callback-based architecture.

    Uses the bleak library for cross-platform BLE scanning. Scans continuously
    with configurable intervals and durations, invoking callbacks for each
    detected advertisement.

    This follows the Observer pattern - callbacks are registered and notified
    of advertisements without the scanner knowing what they do with the data.
    """

    def __init__(self, scan_interval: float = 5.0, scan_duration: float = 3.0):
        """Initialize BLE scanner.

        Args:
            scan_interval: Seconds between scan starts
            scan_duration: Duration of each scan in seconds

        Raises:
            ValueError: If scan_duration >= scan_interval
        """
        if scan_duration >= scan_interval:
            raise ValueError("scan_duration must be less than scan_interval")

        self._scan_interval = scan_interval
        self._scan_duration = scan_duration
        self._callbacks: List[AdvertisementCallback] = []
        self._running = False
        self._scan_task: Optional[asyncio.Task] = None

        logger.info(f"BLE scanner initialized: interval={scan_interval}s, duration={scan_duration}s")

    def register_callback(self, callback: AdvertisementCallback) -> None:
        """Register a callback for advertisement notifications.

        Args:
            callback: Async function to call with each advertisement
        """
        self._callbacks.append(callback)
        logger.debug(f"Registered callback: {callback.__name__}")

    async def start(self) -> None:
        """Start continuous scanning.

        Raises:
            ScannerError: If scanner is already running or fails to start
        """
        if self._running:
            raise ScannerError("Scanner is already running")

        self._running = True
        self._scan_task = asyncio.create_task(self._scan_loop())
        logger.info("BLE scanner started")

    async def stop(self) -> None:
        """Stop scanning gracefully."""
        if not self._running:
            return

        self._running = False

        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass

        logger.info("BLE scanner stopped")

    async def _scan_loop(self) -> None:
        """Main scanning loop.

        Continuously scans for BLE devices, with pauses between scans.
        Each scan invokes callbacks for detected advertisements.
        """
        logger.debug("Starting scan loop")

        while self._running:
            try:
                scan_start = datetime.now()
                logger.debug(f"Starting BLE scan (duration={self._scan_duration}s)")

                async with BleakScanner(detection_callback=self._on_detection) as scanner:
                    await asyncio.sleep(self._scan_duration)

                scan_elapsed = (datetime.now() - scan_start).total_seconds()
                logger.debug(f"Scan completed in {scan_elapsed:.2f}s")

                sleep_time = max(0, self._scan_interval - scan_elapsed)
                if sleep_time > 0:
                    logger.debug(f"Sleeping for {sleep_time:.2f}s before next scan")
                    await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                logger.debug("Scan loop cancelled")
                break

            except Exception as e:
                logger.error(f"Error in scan loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    def _on_detection(self, device: BLEDevice, advertisement_data: AdvertisementData) -> None:
        """Called by bleak when a device is detected.

        Converts bleak's data structures to our protocol and notifies callbacks.

        Args:
            device: Detected BLE device
            advertisement_data: Advertisement data from device
        """
        try:
            advertisement = self._convert_advertisement(device, advertisement_data)

            logger.debug(
                f"Detected: {advertisement.address} "
                f"(name='{advertisement.name}', rssi={advertisement.rssi})"
            )

            for callback in self._callbacks:
                try:
                    asyncio.create_task(callback(advertisement))
                except Exception as e:
                    logger.error(f"Error in callback {callback.__name__}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error processing advertisement: {e}", exc_info=True)

    @staticmethod
    def _convert_advertisement(device: BLEDevice,
                               advertisement_data: AdvertisementData) -> BLEAdvertisement:
        """Convert bleak advertisement to our protocol.

        Args:
            device: BLE device from bleak
            advertisement_data: Advertisement data from bleak

        Returns:
            BLEAdvertisement instance
        """
        return BLEAdvertisement(
            address=device.address.lower(),
            name=advertisement_data.local_name or device.name,
            rssi=advertisement_data.rssi,
            manufacturer_data=dict(advertisement_data.manufacturer_data) if advertisement_data.manufacturer_data else {},
            service_uuids=[uuid.lower() for uuid in advertisement_data.service_uuids] if advertisement_data.service_uuids else [],
            service_data={k.lower(): v for k, v in advertisement_data.service_data.items()} if advertisement_data.service_data else {},
            tx_power=advertisement_data.tx_power,
            timestamp=datetime.now()
        )
