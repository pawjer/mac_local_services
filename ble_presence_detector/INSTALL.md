# Installation Guide

## Installation Method

### Option 1: Using pipx (Recommended)

Install as a standalone application, isolated from other Python packages:

```bash
# Install pipx if not already installed
brew install pipx
pipx ensurepath

# Install BLE presence detector
cd /Users/proboszcz/Devel/mac_local_services
pipx install ./ble_presence_detector
```

Verify installation:
```bash
ble-presence-detector --help
```

### Option 2: Using venv

Create a virtual environment (if you prefer not to use pipx):

```bash
cd /Users/proboszcz/Devel/mac_local_services/ble_presence_detector
python3 -m venv venv
./venv/bin/pip install -e .
```

## Quick Start

### 1. Install Python Dependencies

**If using pipx:** Already done during `pipx install`

**If using venv:**
```bash
cd /Users/proboszcz/Devel/mac_local_services/ble_presence_detector
./venv/bin/pip install -r requirements.txt
```

### 2. Configure Devices

Edit `config/devices.yaml` with your device information:

```bash
# Find your device MAC address and name using:
# - LightBlue app (iOS)
# - nRF Connect app (iOS/Android)
# - Or temporarily run with DEBUG logging to see all detected devices

# Temporary scan to see all devices:
python3 -c "
import asyncio
from bleak import BleakScanner

async def scan():
    devices = await BleakScanner.discover()
    for d in devices:
        print(f'{d.address}: {d.name}')

asyncio.run(scan())
"
```

Update `config/devices.yaml` with your actual devices.

### 3. Test Manually

```bash
# Ensure MQTT broker is running
# If using Mosquitto:
brew services start mosquitto
# Or manually:
mosquitto -v

# Run the detector
python3 src/main.py config/devices.yaml
```

In another terminal, subscribe to MQTT messages:

```bash
mosquitto_sub -t 'home/presence/#' -v
```

### 4. Install as Service

```bash
cd /Users/proboszcz/Devel/mac_local_services

# Start the service
./ha-services-run.sh start ble-presence

# Check logs
./ha-services-run.sh logs ble-presence

# Check status
./ha-services-run.sh status ble-presence
```

## Verification Checklist

- [ ] Dependencies installed (`pip3 install -r requirements.txt`)
- [ ] Configuration updated (`config/devices.yaml`)
- [ ] MQTT broker running (default: localhost:1883)
- [ ] Bluetooth enabled
- [ ] Manual test successful (device detected)
- [ ] MQTT messages received
- [ ] Service starts successfully

## Troubleshooting

### "No module named 'bleak'"

```bash
pip3 install -r requirements.txt
```

### "Failed to connect to MQTT broker"

```bash
# Check if Mosquitto is running
brew services list | grep mosquitto

# Start if needed
brew services start mosquitto

# Or run manually for debugging
mosquitto -v
```

### "No devices detected"

1. Verify Bluetooth is enabled
2. Check device is advertising (use LightBlue/nRF Connect app)
3. Try increasing `scan_duration` in config
4. Set `log_level: DEBUG` to see all advertisements

### Permission issues on macOS

On macOS, you may need to grant Python access to Bluetooth:

1. Go to System Preferences → Security & Privacy → Privacy → Bluetooth
2. Add Python or Terminal to the list
3. Restart the application

## Next Steps

After successful installation:

1. Monitor MQTT topics in Home Assistant or Node-RED
2. Create automations based on presence
3. Adjust `confidence_threshold` and `decay_rate` for your needs
4. Add more devices to track

## Advanced Configuration

### Custom Decay Rates

Different devices may need different decay rates:

- **Phones**: Often sleep and stop advertising → slower decay (0.05-0.1)
- **AirPods**: Sporadic advertising → faster decay (0.15-0.2)
- **Fitness devices**: Consistent advertising → moderate decay (0.1)

### Testing Decay Behavior

```python
from src.tracking.confidence_calculator import ConfidenceCalculator

calc = ConfidenceCalculator(decay_rate=0.1)
print(f"Half-life: {calc.half_life:.1f} seconds")
print(f"Time to 50% confidence: {calc.time_to_threshold(0.5):.1f} seconds")
```

Adjust `decay_rate` until the half-life matches your expected device behavior.
