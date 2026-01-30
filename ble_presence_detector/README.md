# BLE Presence Detector

A modular, SOLID-principled Bluetooth Low Energy (BLE) presence detection system that tracks devices and reports their presence via MQTT.

## Features

- **Multiple Identification Strategies**: Identify devices by name, MAC address, manufacturer data, or service UUIDs
- **Confidence-Based Tracking**: Exponential decay confidence system for accurate presence detection
- **MQTT Integration**: Real-time presence updates published to MQTT broker
- **State Persistence**: Survives restarts by saving state to disk
- **Extensible Architecture**: Easy to add new identification methods or storage backends
- **SOLID Design**: Clean separation of concerns, dependency injection, and protocol-based abstractions

## Architecture

The system follows SOLID principles with a clean separation of concerns:

```
BLE Device → Scanner → Tracker → [Observer Pattern] → MQTT Publisher
                          ↓
                     Repository (State Persistence)
```

### Core Components

1. **Scanner** (`src/scanner/ble_scanner.py`): Continuously scans for BLE advertisements using the bleak library
2. **Identifiers** (`src/identifiers/`): Strategy pattern for device identification (name, MAC, manufacturer, service UUID)
3. **Tracker** (`src/tracking/presence_tracker.py`): Core business logic for presence detection and confidence calculation
4. **Publisher** (`src/publishing/mqtt_publisher.py`): Observer that publishes state changes to MQTT
5. **Repository** (`src/repository/json_repository.py`): Persists state to JSON file

### Design Patterns

- **Strategy Pattern**: Pluggable device identifiers
- **Factory Pattern**: Creates identifiers from configuration
- **Observer Pattern**: MQTT publisher observes state changes
- **Repository Pattern**: Abstract state persistence

## Installation

### Prerequisites

- Python 3.9+
- MQTT broker (e.g., Mosquitto)
- Bluetooth adapter with BLE support

### Install Dependencies

```bash
cd /Users/proboszcz/Devel/mac_local_services/ble_presence_detector
pip3 install -r requirements.txt
```

## Configuration

Edit `config/devices.yaml` to configure your devices:

```yaml
mqtt:
  host: localhost
  port: 1883
  topic_prefix: home/presence
  qos: 1

scanner:
  scan_interval: 5.0  # seconds between scans
  scan_duration: 3.0  # duration of each scan

state_file: state.json
log_level: INFO

devices:
  # Identify by name (exact match)
  - id: john_iphone
    name: "John's iPhone"
    identifiers:
      - type: name
        pattern: "John's iPhone"
        regex: false
    confidence_threshold: 0.5
    decay_rate: 0.1

  # Identify by name (regex)
  - id: laptop
    name: "MacBook Pro"
    identifiers:
      - type: name
        pattern: "MacBook.*Pro"
        regex: true
    confidence_threshold: 0.5
    decay_rate: 0.1

  # Identify by MAC address
  - id: smart_watch
    name: "Smart Watch"
    identifiers:
      - type: mac
        address: "AA:BB:CC:DD:EE:FF"
    confidence_threshold: 0.5
    decay_rate: 0.1

  # Identify by manufacturer data (e.g., AirPods)
  - id: john_airpods
    name: "John's AirPods"
    identifiers:
      - type: manufacturer
        company_id: 76  # Apple
        data_pattern: "0719"  # AirPods pattern
    confidence_threshold: 0.6
    decay_rate: 0.15

  # Identify by service UUID (e.g., fitness equipment)
  - id: wahoo_kickr
    name: "Wahoo KICKR"
    identifiers:
      - type: service_uuid
        uuids:
          - "00001818-0000-1000-8000-00805f9b34fb"  # Cycling Power
        require_all: false
    confidence_threshold: 0.5
    decay_rate: 0.1

  # Multiple identifiers (any match = detection)
  - id: multi_device
    name: "Multi Device"
    identifiers:
      - type: name
        pattern: "Device Name"
        regex: false
      - type: mac
        address: "11:22:33:44:55:66"
    confidence_threshold: 0.5
    decay_rate: 0.1
```

### Configuration Parameters

#### Device Configuration

- **id**: Unique identifier for the device
- **name**: Human-readable device name
- **identifiers**: List of identification strategies (any match = detection)
- **confidence_threshold**: Minimum confidence for "present" state (0.0-1.0)
- **decay_rate**: How fast confidence decays per second (higher = faster)

#### Identifier Types

**Name-based** (`type: name`):
- `pattern`: Name to match
- `regex`: Whether pattern is a regex (default: false)

**MAC address** (`type: mac`):
- `address`: MAC address in any format (normalized automatically)

**Manufacturer data** (`type: manufacturer`):
- `company_id`: Bluetooth company ID (e.g., 76 for Apple)
- `data_pattern`: Optional hex pattern to match in manufacturer data

**Service UUID** (`type: service_uuid`):
- `uuids`: List of service UUIDs
- `require_all`: If true, all UUIDs must be present (AND). If false, any UUID (OR).

## Usage

### Manual Execution

```bash
cd /Users/proboszcz/Devel/mac_local_services/ble_presence_detector
python3 src/main.py config/devices.yaml
```

### Service Integration

The system integrates with the existing `ha-services-run.sh` service manager:

```bash
# Start the service
cd /Users/proboszcz/Devel/mac_local_services
./ha-services-run.sh start ble-presence

# Check status
./ha-services-run.sh status ble-presence

# View logs
./ha-services-run.sh logs ble-presence

# Stop the service
./ha-services-run.sh stop ble-presence
```

## MQTT Topics

### State Topic

`{prefix}/{device_id}/state`

Payload: `"present"` or `"absent"`

Published with QoS 1 and retained.

### Attributes Topic

`{prefix}/{device_id}/attributes`

JSON payload with detailed information:

```json
{
  "device_id": "john_iphone",
  "device_name": "John's iPhone",
  "present": true,
  "confidence": 0.987,
  "last_seen": "2026-01-30T10:30:45.123456",
  "state_changes": 5,
  "rssi": -65,
  "timestamp": "2026-01-30T10:30:45.123456",
  "distance_m": 2.15,
  "average_rssi": -67.2,
  "average_distance_m": 2.34
}
```

## Confidence System

The system uses exponential decay to model uncertainty about device presence:

```
confidence(t) = e^(-λt)
```

Where:
- `t` = time since last detection (seconds)
- `λ` = decay_rate (from configuration)

### Understanding Decay Rate

The decay rate determines how quickly confidence drops:

- **decay_rate = 0.1**: Half-life ≈ 6.9 seconds (fast decay)
- **decay_rate = 0.05**: Half-life ≈ 13.9 seconds (moderate)
- **decay_rate = 0.02**: Half-life ≈ 34.7 seconds (slow)

**Half-life** is the time for confidence to drop from 1.0 to 0.5.

### Example

With `decay_rate = 0.1` and `confidence_threshold = 0.5`:
- Device detected → confidence = 1.0 → present
- After 6.9 seconds → confidence = 0.5 → still present (at threshold)
- After 7 seconds → confidence < 0.5 → absent

## Testing

### Run Unit Tests

```bash
cd /Users/proboszcz/Devel/mac_local_services/ble_presence_detector
pytest tests/unit/ -v
```

### Run Integration Tests

```bash
pytest tests/integration/ -v
```

### Run All Tests

```bash
pytest tests/ -v
```

## Extending the System

### Adding a New Identifier Type

The system is designed for easy extension. To add a new identifier type (e.g., RSSI-based):

1. **Create identifier class** (`src/identifiers/rssi_identifier.py`):
```python
from .base import BaseIdentifier
from ..core.protocols import BLEAdvertisement

class RSSIIdentifier(BaseIdentifier):
    def __init__(self, device_id: str, device_name: str, min_rssi: int):
        super().__init__(device_id, device_name)
        self._min_rssi = min_rssi

    def matches(self, advertisement: BLEAdvertisement) -> bool:
        return advertisement.rssi >= self._min_rssi
```

2. **Add config model** (`src/config/models.py`):
```python
class RSSIIdentifierConfig(BaseModel):
    type: str = Field(default="rssi", frozen=True)
    min_rssi: int = Field(..., description="Minimum RSSI threshold")
```

3. **Update factory** (`src/identifiers/factory.py`):
```python
elif isinstance(config, RSSIIdentifierConfig):
    return RSSIIdentifier(
        device_id=device_id,
        device_name=device_name,
        min_rssi=config.min_rssi
    )
```

4. **Use in configuration**:
```yaml
identifiers:
  - type: rssi
    min_rssi: -70
```

### Adding a New Repository Backend

To use Redis instead of JSON:

1. **Create repository** (`src/repository/redis_repository.py`):
```python
from ..core.protocols import StateRepository

class RedisStateRepository(StateRepository):
    async def save(self, device_id: str, state: Any) -> None:
        # Redis implementation
        pass

    async def load(self, device_id: str) -> Optional[Any]:
        # Redis implementation
        pass

    async def load_all(self) -> Dict[str, Any]:
        # Redis implementation
        pass
```

2. **Inject in main.py**:
```python
# Instead of:
self._repository = JSONStateRepository(state_file_path)

# Use:
self._repository = RedisStateRepository(redis_config)
```

No changes needed to tracker or other components!

## Troubleshooting

### No devices detected

1. Check Bluetooth is enabled: `system_profiler SPBluetoothDataType`
2. Verify device is advertising (check with LightBlue or nRF Connect app)
3. Increase `scan_duration` in config
4. Set `log_level: DEBUG` to see all advertisements

### Device randomly appears/disappears

1. Increase `confidence_threshold` (more tolerant to missed scans)
2. Decrease `decay_rate` (slower confidence decay)
3. Check for Bluetooth interference

### High CPU usage

1. Increase `scan_interval` (scan less frequently)
2. Reduce number of tracked devices
3. Use more specific identifiers (MAC instead of name)

## Common Service UUIDs

- Heart Rate: `0000180d-0000-1000-8000-00805f9b34fb`
- Battery: `0000180f-0000-1000-8000-00805f9b34fb`
- Device Information: `0000180a-0000-1000-8000-00805f9b34fb`
- Cycling Speed/Cadence: `00001816-0000-1000-8000-00805f9b34fb`
- Cycling Power: `00001818-0000-1000-8000-00805f9b34fb`
- Fitness Machine: `00001826-0000-1000-8000-00805f9b34fb`

## Bluetooth Company IDs

- Apple: 76 (0x004C)
- Microsoft: 6 (0x0006)
- Google: 224 (0x00E0)
- Samsung: 117 (0x0075)
- Garmin: 2454 (0x0996)

Full list: https://www.bluetooth.com/specifications/assigned-numbers/

## License

This project is part of the mac_local_services home automation system.
