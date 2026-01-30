# BLE Presence Detector - Configuration Guide

## Configuration Overview

The BLE Presence Detector uses a **three-tier configuration system**:

1. **YAML Config File** (`config/devices.yaml`) - Base configuration
2. **Environment Variables** - Override YAML settings
3. **Service File** (`50-ble-presence.service`) - Service management

```
Priority: Environment Variables > YAML Config
```

## Configuration Files

### 1. Device Configuration (YAML)

**Location**: `config/devices.yaml`

**Purpose**: Define which BLE devices to track and how to identify them

**Example**:
```yaml
devices:
  - id: my_iphone
    name: "My iPhone"
    identifiers:
      - type: name
        pattern: "iPhone"
        regex: false
    confidence_threshold: 0.5
    decay_rate: 0.1
```

This file contains:
- ✅ Device definitions (what to track)
- ✅ Identifier strategies (how to detect)
- ✅ Default MQTT/scanner settings
- ❌ **Do not hardcode sensitive info here** (use env vars instead)

### 2. Environment Configuration (.env)

**Location**: `/Users/proboszcz/Devel/mac_local_services/env/ble-presence.env`

**Purpose**: Override YAML settings, configure deployment-specific values

**Example**:
```bash
# MQTT broker
MQTT_HOST=10.9.0.3
MQTT_PORT=1883
MQTT_USERNAME=mqtt_user
MQTT_PASSWORD=secret123

# Scanner tuning
SCAN_INTERVAL=5.0
SCAN_DURATION=3.0

# Logging
LOG_LEVEL=INFO
```

This file:
- ✅ Overrides YAML settings
- ✅ Stores environment-specific config
- ✅ Can contain secrets (not in git)
- ✅ Easy to edit without changing code

### 3. Service File

**Location**: `50-ble-presence.service`

**Purpose**: Service management, startup configuration

**Example**:
```bash
NAME=ble-presence
TYPE=simple
CMD=python3 .../src/main.py .../config/devices.yaml --env-file .../env/ble-presence.env
WAIT_FOR=tcp:10.9.0.3:1883
ENV_FILE=env/ble-presence.env
RESTART=always
RESTART_DELAY=5
```

## Supported Environment Variables

All settings can be overridden via environment variables:

### MQTT Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MQTT_HOST` | MQTT broker hostname/IP | `localhost` | `10.9.0.3` |
| `MQTT_PORT` | MQTT broker port | `1883` | `1883` |
| `MQTT_USERNAME` | MQTT username (optional) | None | `mqtt_user` |
| `MQTT_PASSWORD` | MQTT password (optional) | None | `secret123` |
| `MQTT_TOPIC_PREFIX` | Topic prefix for messages | `home/presence` | `ble/presence` |
| `MQTT_QOS` | MQTT Quality of Service | `1` | `0`, `1`, or `2` |
| `MQTT_CLIENT_ID` | MQTT client identifier | `ble_presence_detector` | `mac_mini_ble` |

### Scanner Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `SCAN_INTERVAL` | Seconds between scans | `5.0` | `10.0` |
| `SCAN_DURATION` | Duration of each scan | `3.0` | `5.0` |

### Application Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `STATE_FILE` | State persistence file | `state.json` | `/var/lib/ble-state.json` |
| `LOG_LEVEL` | Logging verbosity | `INFO` | `DEBUG`, `WARNING` |

## Configuration Workflow

### Initial Setup

1. **Copy example env file**:
   ```bash
   cp .env.example /Users/proboszcz/Devel/mac_local_services/env/ble-presence.env
   ```

2. **Edit MQTT settings**:
   ```bash
   nano /Users/proboszcz/Devel/mac_local_services/env/ble-presence.env
   ```
   Set `MQTT_HOST` to your broker's IP

3. **Configure devices**:
   ```bash
   nano config/devices.yaml
   ```
   Add your BLE devices

4. **Start service**:
   ```bash
   cd /Users/proboszcz/Devel/mac_local_services
   ./ha-services-run.sh start ble-presence
   ```

### Making Changes

#### Change MQTT Broker

**Option 1: Edit env file** (recommended):
```bash
nano env/ble-presence.env
# Change MQTT_HOST=...
./ha-services-run.sh restart ble-presence
```

**Option 2: Temporary override**:
```bash
MQTT_HOST=192.168.1.100 python3 src/main.py config/devices.yaml
```

#### Change Scan Timing

```bash
# Edit env file
nano env/ble-presence.env
# Set SCAN_INTERVAL=10.0
# Set SCAN_DURATION=5.0
./ha-services-run.sh restart ble-presence
```

#### Add/Remove Devices

```bash
# Edit device config
nano config/devices.yaml
# Add new device entry
./ha-services-run.sh restart ble-presence
```

#### Change Log Level

```bash
# Quick debug without editing files
./ha-services-run.sh stop ble-presence
LOG_LEVEL=DEBUG ./ha-services-run.sh start ble-presence
```

## Configuration Best Practices

### ✅ DO

- **Store secrets in env file**: MQTT passwords, credentials
- **Use env vars for deployment differences**: Different MQTT hosts per environment
- **Keep device configs in YAML**: Device definitions, identifiers, thresholds
- **Version control YAML**: Check in `config/devices.yaml`
- **Ignore env file in git**: Keep `env/ble-presence.env` out of version control

### ❌ DON'T

- **Don't hardcode IPs in YAML**: Use `MQTT_HOST` env var instead
- **Don't commit passwords**: Keep sensitive data in env files
- **Don't edit service file frequently**: Use env vars for changes
- **Don't use absolute paths**: Let config be relative when possible

## Examples

### Multi-Environment Setup

**Production** (`env/ble-presence.env`):
```bash
MQTT_HOST=10.9.0.3
MQTT_USERNAME=prod_user
MQTT_PASSWORD=prod_pass
LOG_LEVEL=INFO
```

**Development** (`env/ble-presence-dev.env`):
```bash
MQTT_HOST=localhost
LOG_LEVEL=DEBUG
SCAN_INTERVAL=10.0  # Less aggressive scanning
```

Run with different env:
```bash
python3 src/main.py config/devices.yaml --env-file env/ble-presence-dev.env
```

### Sensitive Credentials

**YAML** (`config/devices.yaml`):
```yaml
mqtt:
  host: localhost  # Will be overridden
  port: 1883
  # No username/password here!
```

**ENV** (`env/ble-presence.env`):
```bash
MQTT_HOST=secure-broker.local
MQTT_USERNAME=secure_user
MQTT_PASSWORD=super_secret_password
```

### Performance Tuning

For busy environments with many devices:
```bash
# env/ble-presence.env
SCAN_INTERVAL=10.0    # Scan every 10s instead of 5s
SCAN_DURATION=5.0     # Longer scan window
LOG_LEVEL=WARNING     # Less verbose
```

## Verification

Check which settings are active:

```bash
# View env file
cat env/ble-presence.env

# Test configuration loading
python3 -c "
from src.config.loader import ConfigLoader
from pathlib import Path
config = ConfigLoader.load(Path('config/devices.yaml'))
print(f'MQTT: {config.mqtt.host}:{config.mqtt.port}')
print(f'Scanner: {config.scanner.scan_interval}s / {config.scanner.scan_duration}s')
"

# Watch startup logs
./ha-services-run.sh logs ble-presence | head -20
```

Look for override messages:
```
2026-01-30 17:30:00 - INFO - Override: MQTT host = 10.9.0.3
2026-01-30 17:30:00 - INFO - MQTT broker: 10.9.0.3:1883
```

## Troubleshooting

### Configuration not loading?

1. Check env file exists:
   ```bash
   ls -la env/ble-presence.env
   ```

2. Check service file references it:
   ```bash
   grep ENV_FILE 50-ble-presence.service
   ```

3. Check for syntax errors:
   ```bash
   python3 -c "from src.config.loader import ConfigLoader; ConfigLoader.load(Path('config/devices.yaml'))"
   ```

### Which value is being used?

```bash
# Start with DEBUG logging
LOG_LEVEL=DEBUG ./ha-services-run.sh start ble-presence

# Check logs for "Override:" messages
./ha-services-run.sh logs ble-presence | grep Override
```

### Environment variable not working?

```bash
# Test directly
MQTT_HOST=test.local python3 src/main.py config/devices.yaml

# Check if python-dotenv is installed
pip3 list | grep dotenv
```
