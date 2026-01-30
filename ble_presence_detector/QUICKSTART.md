# Quick Start Guide

Get the BLE Presence Detector running in 5 minutes!

## Step 1: Verify Installation

```bash
cd /Users/proboszcz/Devel/mac_local_services/ble_presence_detector
python3 verify_install.py
```

You should see all checks pass.

## Step 2: Install Dependencies

```bash
pip3 install -r requirements.txt
```

This installs:
- `bleak` - BLE scanning
- `paho-mqtt` - MQTT communication
- `pyyaml` - YAML configuration
- `pydantic` - Configuration validation

## Step 3: Find Your Devices

Quick scan to discover BLE devices:

```bash
python3 -c "
import asyncio
from bleak import BleakScanner

async def scan():
    print('Scanning for BLE devices...')
    devices = await BleakScanner.discover(timeout=5.0)
    print(f'\nFound {len(devices)} devices:\n')
    for d in devices:
        print(f'  MAC: {d.address}')
        print(f'  Name: {d.name or \"Unknown\"}')
        print()

asyncio.run(scan())
"
```

## Step 4: Configure Your Devices

Edit `config/devices.yaml` with your actual devices:

```bash
# Example: Track your iPhone
devices:
  - id: my_iphone
    name: "My iPhone"
    identifiers:
      - type: name
        pattern: "iPhone"  # Use the exact name from Step 3
        regex: false
    confidence_threshold: 0.5
    decay_rate: 0.1
```

Or use MAC address if name changes:

```yaml
  - id: my_iphone
    name: "My iPhone"
    identifiers:
      - type: mac
        address: "AA:BB:CC:DD:EE:FF"  # From Step 3
    confidence_threshold: 0.5
    decay_rate: 0.1
```

## Step 5: Test It!

### Terminal 1: Start MQTT Broker

```bash
# If you have Homebrew Mosquitto:
brew services start mosquitto

# Or run manually:
mosquitto -v
```

### Terminal 2: Subscribe to MQTT Messages

```bash
mosquitto_sub -t 'home/presence/#' -v
```

### Terminal 3: Run the Detector

```bash
python3 src/main.py config/devices.yaml
```

You should see:
- Terminal 3: Log messages showing BLE scanning
- Terminal 2: MQTT messages when devices appear/disappear

Example MQTT message:
```
home/presence/my_iphone/state present
home/presence/my_iphone/attributes {"device_id":"my_iphone","device_name":"My iPhone","present":true,"confidence":1.0,...}
```

## Step 6: Install as Service

Once testing works:

```bash
cd /Users/proboszcz/Devel/mac_local_services
./ha-services-run.sh start ble-presence
./ha-services-run.sh status ble-presence
./ha-services-run.sh logs ble-presence
```

## Troubleshooting

### No devices detected?

1. Make sure Bluetooth is enabled
2. Check device is actually advertising (use LightBlue app)
3. Try `log_level: DEBUG` in config to see all advertisements

### MQTT connection failed?

```bash
# Check if Mosquitto is running
brew services list | grep mosquitto

# Check the port
lsof -i :1883
```

### Permission denied on macOS?

Go to: System Preferences → Security & Privacy → Privacy → Bluetooth
Add Python or Terminal to the allowed list.

## Next Steps

1. **Tune confidence parameters**: Adjust `decay_rate` and `confidence_threshold` for your devices
2. **Add more devices**: Add family members' phones, AirPods, etc.
3. **Create automations**: Use MQTT messages in Home Assistant or Node-RED
4. **Monitor logs**: `./ha-services-run.sh logs ble-presence` to see what's happening

## Common Device Patterns

### AirPods (don't always advertise name)

```yaml
  - id: my_airpods
    name: "My AirPods"
    identifiers:
      - type: manufacturer
        company_id: 76  # Apple
        data_pattern: "0719"  # AirPods pattern
    confidence_threshold: 0.6
    decay_rate: 0.15  # Faster decay since they advertise sporadically
```

### Fitness Equipment (advertises service UUIDs)

```yaml
  - id: wahoo_kickr
    name: "Wahoo KICKR"
    identifiers:
      - type: service_uuid
        uuids:
          - "00001818-0000-1000-8000-00805f9b34fb"  # Cycling Power
        require_all: false
    confidence_threshold: 0.5
    decay_rate: 0.1
```

### Smart Watch (consistent name and MAC)

```yaml
  - id: apple_watch
    name: "Apple Watch"
    identifiers:
      - type: name
        pattern: "Apple Watch"
        regex: false
      - type: mac
        address: "AA:BB:CC:DD:EE:FF"
    confidence_threshold: 0.5
    decay_rate: 0.1
```

## Understanding Confidence

Confidence starts at 1.0 when detected and decays exponentially:

- **decay_rate = 0.1**: Device considered "absent" after ~7 seconds of no detection (with default 0.5 threshold)
- **decay_rate = 0.05**: ~14 seconds
- **decay_rate = 0.02**: ~35 seconds

Choose based on your device:
- **Phones**: Usually 0.05-0.1 (they sleep sometimes)
- **AirPods**: 0.15-0.2 (sporadic advertising)
- **Fitness gear**: 0.1 (consistent advertising)

## Success!

If you see MQTT messages appearing when you move devices around, you're all set! 🎉

For more details, see:
- **README.md**: Full documentation
- **INSTALL.md**: Detailed installation guide
- **IMPLEMENTATION_SUMMARY.md**: Technical details
