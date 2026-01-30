# Environment-Based Configuration - Summary

## What Changed

The BLE Presence Detector now supports **environment variable overrides** following the same pattern as other services in the `mac_local_services` project.

## File Structure

```
mac_local_services/
├── env/
│   └── ble-presence.env          ← NEW: Environment overrides
├── 50-ble-presence.service       ← UPDATED: References env file
└── ble_presence_detector/
    ├── .env.example              ← NEW: Example env file
    ├── CONFIGURATION.md          ← NEW: Configuration guide
    ├── config/
    │   └── devices.yaml          ← Base config (MQTT host updated)
    └── src/
        └── main.py               ← UPDATED: Loads env, applies overrides
```

## Key Files

### 1. Environment File: `env/ble-presence.env`

**All configurable settings:**
```bash
# MQTT
MQTT_HOST=10.9.0.3              # ← Your MQTT broker
MQTT_PORT=1883
MQTT_USERNAME=                   # Optional
MQTT_PASSWORD=                   # Optional
MQTT_TOPIC_PREFIX=home/presence
MQTT_QOS=1
MQTT_CLIENT_ID=ble_presence_detector

# Scanner
SCAN_INTERVAL=5.0
SCAN_DURATION=3.0

# Application
STATE_FILE=state.json
LOG_LEVEL=INFO
```

### 2. Service File: `50-ble-presence.service`

```bash
NAME=ble-presence
TYPE=simple
CMD=python3 .../src/main.py .../config/devices.yaml --env-file .../env/ble-presence.env
WAIT_FOR=tcp:10.9.0.3:1883
ENV_FILE=env/ble-presence.env    # ← ha-services-run.sh loads this
RESTART=always
RESTART_DELAY=5
```

### 3. Updated: `src/main.py`

Added:
- Environment variable loading via `python-dotenv`
- `apply_env_overrides()` function
- Command-line argument: `--env-file`
- Logging of all overrides

### 4. Updated: `requirements.txt`

Added:
```
python-dotenv>=1.0.0
```

## How It Works

### Configuration Priority (Highest to Lowest)

1. **Environment Variables** (from `env/ble-presence.env`)
2. **YAML Config** (from `config/devices.yaml`)

### Service Startup Flow

```
./ha-services-run.sh start ble-presence
    ↓
Loads ENV_FILE=env/ble-presence.env
    ↓
Runs CMD with --env-file flag
    ↓
main.py loads devices.yaml
    ↓
main.py loads .env file
    ↓
main.py applies env var overrides
    ↓
Service starts with merged config
```

## Usage Examples

### Quick Configuration Changes

**Change MQTT broker:**
```bash
nano env/ble-presence.env
# Edit: MQTT_HOST=192.168.1.100
./ha-services-run.sh restart ble-presence
```

**Enable debug logging:**
```bash
nano env/ble-presence.env
# Edit: LOG_LEVEL=DEBUG
./ha-services-run.sh restart ble-presence
```

**Add MQTT authentication:**
```bash
nano env/ble-presence.env
# Uncomment and set:
# MQTT_USERNAME=your_user
# MQTT_PASSWORD=your_pass
./ha-services-run.sh restart ble-presence
```

### Temporary Override (Testing)

```bash
# Override for single run
MQTT_HOST=test-broker.local LOG_LEVEL=DEBUG \
  python3 src/main.py config/devices.yaml
```

### Multiple Environments

**Production:**
```bash
python3 src/main.py config/devices.yaml --env-file env/ble-presence.env
```

**Development:**
```bash
python3 src/main.py config/devices.yaml --env-file env/ble-presence-dev.env
```

## What to Configure Where

### In `env/ble-presence.env` (Environment-Specific):
✅ MQTT broker IP/hostname
✅ MQTT credentials
✅ Log levels
✅ Scanner timing (if different per environment)
✅ State file location

### In `config/devices.yaml` (Device-Specific):
✅ Device definitions
✅ Identifier strategies
✅ Confidence thresholds
✅ Decay rates
✅ Default settings

## Verification

### Check Configuration Loading

```bash
./ha-services-run.sh logs ble-presence | grep -E "Override|MQTT broker|Scan interval"
```

You should see:
```
Override: MQTT host = 10.9.0.3
MQTT broker: 10.9.0.3:1883
Scan interval: 5.0s, duration: 3.0s
```

### Test Without Service

```bash
cd /Users/proboszcz/Devel/mac_local_services/ble_presence_detector
python3 src/main.py config/devices.yaml --env-file ../env/ble-presence.env
```

## Benefits

1. **No code changes needed** - Edit env file only
2. **Follows project patterns** - Same as theengs and other services
3. **Secure** - Passwords in env file, not in YAML
4. **Flexible** - Different configs per environment
5. **Easy rollback** - Just revert env file changes

## Migration Notes

If you had custom settings in `config/devices.yaml`:
1. Move MQTT host/port to `env/ble-presence.env`
2. Move any credentials to `env/ble-presence.env`
3. Keep device definitions in YAML

## Current Configuration

**MQTT Broker**: 10.9.0.3:1883 (from env file)
**Topic Prefix**: home/presence
**Scan Interval**: 5.0 seconds
**Scan Duration**: 3.0 seconds

All ready to go! Just:
1. Update device definitions in `config/devices.yaml`
2. Adjust settings in `env/ble-presence.env` if needed
3. Start service: `./ha-services-run.sh start ble-presence`
