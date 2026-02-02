# MQTT-Based Runtime Configuration Design

## Overview

Allow runtime configuration changes via MQTT without restarting the service.

## MQTT Topics

### Configuration Topics (Subscribe)

```
home/presence/config/{device_id}/threshold    → Set confidence_threshold (0.0-1.0)
home/presence/config/{device_id}/decay_rate   → Set decay_rate (0.0-1.0)
home/presence/config/global/scan_interval     → Set scan interval (seconds)
home/presence/config/global/scan_duration     → Set scan duration (seconds)
home/presence/config/global/log_level         → Set log level (DEBUG/INFO/WARNING/ERROR)
```

### Response Topics (Publish)

```
home/presence/config/{device_id}/status       → "ok" or error message
home/presence/config/global/status            → "ok" or error message
```

### Current Config Query

```
home/presence/config/{device_id}/get          → Publish current config
home/presence/config/global/get               → Publish global config
```

## Message Format

### Set Threshold
```bash
mosquitto_pub -h 10.9.0.3 -t 'home/presence/config/probophone/threshold' -m '0.3'
```

Response:
```json
{
  "status": "ok",
  "device_id": "probophone",
  "setting": "threshold",
  "old_value": 0.5,
  "new_value": 0.3,
  "timestamp": "2026-01-30T17:30:00.000000"
}
```

### Set Decay Rate
```bash
mosquitto_pub -h 10.9.0.3 -t 'home/presence/config/probophone/decay_rate' -m '0.05'
```

### Query Current Config
```bash
mosquitto_pub -h 10.9.0.3 -t 'home/presence/config/probophone/get' -m ''
```

Response:
```json
{
  "device_id": "probophone",
  "name": "Probophone",
  "confidence_threshold": 0.3,
  "decay_rate": 0.05,
  "identifiers": [...],
  "current_state": {
    "present": true,
    "confidence": 0.87
  }
}
```

## Implementation

### 1. Add ConfigManager Class

```python
# src/config/runtime_manager.py
class RuntimeConfigManager:
    """Manages runtime configuration updates via MQTT."""

    def __init__(self, tracker, device_configs, mqtt_client):
        self._tracker = tracker
        self._device_configs = device_configs
        self._mqtt_client = mqtt_client

    async def update_threshold(self, device_id: str, threshold: float):
        """Update confidence threshold for a device."""
        if device_id not in self._device_configs:
            raise ValueError(f"Unknown device: {device_id}")

        old_value = self._device_configs[device_id].confidence_threshold
        self._device_configs[device_id].confidence_threshold = threshold

        return {"old_value": old_value, "new_value": threshold}

    async def update_decay_rate(self, device_id: str, decay_rate: float):
        """Update decay rate for a device."""
        # Update config
        # Recreate calculator with new rate
        # Return status
```

### 2. Extend MQTT Publisher

```python
# src/publishing/mqtt_publisher.py

class MQTTPublisher(StateObserver):

    def __init__(self, config, runtime_config_manager=None):
        # ... existing code ...
        self._config_manager = runtime_config_manager

    async def connect(self):
        # ... existing code ...

        # Subscribe to config topics
        if self._config_manager:
            self._client.subscribe("home/presence/config/+/threshold")
            self._client.subscribe("home/presence/config/+/decay_rate")
            self._client.subscribe("home/presence/config/+/get")
            self._client.message_callback_add(
                "home/presence/config/+/threshold",
                self._on_config_threshold
            )
            self._client.message_callback_add(
                "home/presence/config/+/decay_rate",
                self._on_config_decay
            )
            self._client.message_callback_add(
                "home/presence/config/+/get",
                self._on_config_get
            )

    def _on_config_threshold(self, client, userdata, message):
        """Handle threshold update."""
        topic_parts = message.topic.split('/')
        device_id = topic_parts[3]
        new_value = float(message.payload.decode())

        try:
            result = await self._config_manager.update_threshold(device_id, new_value)
            self._publish_config_status(device_id, "threshold", "ok", result)
        except Exception as e:
            self._publish_config_status(device_id, "threshold", "error", str(e))
```

### 3. Wire in main.py

```python
# src/main.py

async def setup(self):
    # ... existing setup ...

    # Create runtime config manager
    self._config_manager = RuntimeConfigManager(
        tracker=self._tracker,
        device_configs=self._config.devices,
        mqtt_client=self._publisher._client
    )

    # Pass to publisher
    self._publisher.set_config_manager(self._config_manager)
```

## Complexity Estimate

### Simple Implementation (2-3 hours)
- Basic threshold and decay_rate updates
- No persistence (resets on restart)
- Manual testing

### Full Implementation (4-5 hours)
- All config parameters
- Persist changes to YAML file
- Validation and error handling
- Unit tests
- Documentation

### Production Implementation (6-8 hours)
- Full implementation above
- Config history/audit log
- Rollback capability
- Integration tests
- Home Assistant discovery/integration

## Benefits

✅ **Zero downtime**: Change settings without restart
✅ **Quick tuning**: Adjust thresholds while testing
✅ **Remote control**: Change from Home Assistant dashboard
✅ **Device-specific**: Different settings per device
✅ **Debugging**: Change log level on the fly

## Example Use Cases

### 1. Quick Threshold Adjustment
```bash
# Phone disappearing too quickly? Lower threshold
mosquitto_pub -h 10.9.0.3 -t 'home/presence/config/probophone/threshold' -m '0.3'

# Still there? Make decay slower
mosquitto_pub -h 10.9.0.3 -t 'home/presence/config/probophone/decay_rate' -m '0.05'
```

### 2. Debug a Specific Device
```bash
# Get current config
mosquitto_pub -h 10.9.0.3 -t 'home/presence/config/kickr_core/get' -m ''

# Subscribe to see the response
mosquitto_sub -h 10.9.0.3 -t 'home/presence/config/kickr_core/status' -v
```

### 3. Home Assistant Integration
```yaml
# In Home Assistant configuration.yaml
input_number:
  probophone_threshold:
    name: "Probophone Detection Threshold"
    min: 0.1
    max: 1.0
    step: 0.05
    initial: 0.5

automation:
  - alias: "Update Probophone Threshold"
    trigger:
      - platform: state
        entity_id: input_number.probophone_threshold
    action:
      - service: mqtt.publish
        data:
          topic: "home/presence/config/probophone/threshold"
          payload: "{{ states('input_number.probophone_threshold') }}"
```

Then adjust with a slider in Home Assistant UI!

## Alternative: Simpler Approach

If you want something **even simpler** (30 minutes):

### Option 1: MQTT Commands
Just add command topics:

```bash
# Reload config from YAML
mosquitto_pub -h 10.9.0.3 -t 'home/presence/command/reload' -m ''

# Adjust one device temporarily (in memory only)
mosquitto_pub -h 10.9.0.3 -t 'home/presence/command/tune' \
  -m '{"device":"probophone","threshold":0.3,"decay":0.05}'
```

### Option 2: Web UI
Simple web interface on localhost:8080:
- View all devices and their settings
- Sliders to adjust threshold/decay
- Apply button saves to YAML and reloads

## Recommendation

**Start with Option 1 (Simple Commands)**:
1. Add reload command (5 minutes)
2. Add temporary tune command (15 minutes)
3. Test with your phone
4. If you like it, expand to full MQTT config later

This gives you 80% of the benefit with 20% of the effort.

Would you like me to implement the simple version first?
