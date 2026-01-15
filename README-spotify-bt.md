# Spotify BT Service

REST API do zdalnej kontroli połączeń Bluetooth i Spotify na macOS.

## Instalacja Dependencies

```bash
# Zainstaluj blueutil
brew install blueutil

# Zainstaluj sinatra gem
gem install sinatra webrick
```

## Uruchomienie

```bash
# Z katalogu głównego HomeAssistant
./ha-services-run.sh start spotify-bt

# Sprawdź status
./ha-services-run.sh status

# Zobacz logi
./ha-services-run.sh logs spotify-bt
```

## API Endpoints

### Bluetooth

**GET /speakers** - Lista sparowanych urządzeń audio
```bash
curl http://localhost:8766/speakers
```

**POST /connect** - Połącz z urządzeniem
```bash
curl -X POST http://localhost:8766/connect \
  -H "Content-Type: application/json" \
  -d '{"address": "aa-bb-cc-dd-ee-ff"}'
```

**POST /disconnect** - Rozłącz urządzenie
```bash
curl -X POST http://localhost:8766/disconnect \
  -H "Content-Type: application/json" \
  -d '{"address": "aa-bb-cc-dd-ee-ff"}'
```

**GET /status** - Status połączeń Bluetooth
```bash
curl http://localhost:8766/status
```

### Spotify

**POST /spotify/play** - Uruchom/wznów Spotify
```bash
curl -X POST http://localhost:8766/spotify/play
```

**POST /spotify/pause** - Zatrzymaj Spotify
```bash
curl -X POST http://localhost:8766/spotify/pause
```

**GET /spotify/status** - Status Spotify
```bash
curl http://localhost:8766/spotify/status
```

**GET /health** - Health check
```bash
curl http://localhost:8766/health
```

## Integracja z Home Assistant

### configuration.yaml

```yaml
rest_command:
  bt_connect:
    url: "http://macbook.local:8766/connect"
    method: POST
    content_type: "application/json"
    payload: '{"address": "{{ address }}"}'
  
  bt_disconnect:
    url: "http://macbook.local:8766/disconnect"
    method: POST
    content_type: "application/json"
    payload: '{"address": "{{ address }}"}'
  
  spotify_play:
    url: "http://macbook.local:8766/spotify/play"
    method: POST
  
  spotify_pause:
    url: "http://macbook.local:8766/spotify/pause"
    method: POST

sensor:
  - platform: rest
    name: MacBook BT Status
    resource: "http://macbook.local:8766/status"
    scan_interval: 30
    json_attributes:
      - connected_devices
    value_template: "{{ value_json.connected_devices | length }}"
  
  - platform: rest
    name: MacBook Spotify Status
    resource: "http://macbook.local:8766/spotify/status"
    scan_interval: 10
    json_attributes:
      - state
      - track
    value_template: >
      {% if value_json.running %}
        {{ value_json.state }}
      {% else %}
        not_running
      {% endif %}
```

### Przykładowy skrypt

```yaml
script:
  play_music_on_speaker:
    alias: "Włącz muzykę na głośniku"
    sequence:
      - service: rest_command.bt_connect
        data:
          address: "aa-bb-cc-dd-ee-ff"
      - delay:
          seconds: 3
      - service: rest_command.spotify_play

  stop_music:
    alias: "Zatrzymaj muzykę"
    sequence:
      - service: rest_command.spotify_pause
```

## Test

```bash
# Lista głośników
curl http://localhost:8766/speakers | jq

# Status Spotify
curl http://localhost:8766/spotify/status | jq

# Logi serwisu
tail -f logs/spotify-bt.log
```

## Port

Domyślny port: **8766**

## Konfiguracja

Wszystkie ustawienia są w pliku `env/spotify-bt.env`:

```bash
# Server settings
PORT=8766                    # API port
BIND_HOST=0.0.0.0           # Bind address (0.0.0.0 = all interfaces)
LOG_LEVEL=info              # Log level: debug, info, warn, error

# Bluetooth settings
BLUEUTIL_USE_SYSTEM_PROFILER=1  # Use system_profiler (required for SSH)
BT_CONNECT_TIMEOUT=5        # Timeout for connect operation (seconds)
BT_CONNECT_WAIT=2           # Wait time after connect before verification (seconds)
BT_DISCONNECT_TIMEOUT=3     # Timeout for disconnect operation (seconds)

# Audio device detection
AUDIO_DEVICE_KEYWORDS=speaker,headphone,wh-,soundcore  # Keywords for filtering (comma-separated)

# Spotify settings
SPOTIFY_LAUNCH_DELAY=2      # Wait time after launching Spotify (seconds)
```

### Dostosowanie filtra audio devices

Jeśli Twoje urządzenie nie jest wykrywane, dodaj jego nazwę lub część nazwy do `AUDIO_DEVICE_KEYWORDS`:

```bash
# Przykład: Dodaj "ue boom" dla głośnika UE Boom
AUDIO_DEVICE_KEYWORDS=speaker,headphone,wh-,soundcore,ue,boom

# Przykład: Tylko konkretne urządzenia
AUDIO_DEVICE_KEYWORDS=wh-1000xm3,soundcore,liberty
```

Keywords są case-insensitive i sprawdzane jako substring w nazwie urządzenia.

Po zmianie konfiguracji restart serwisu:
```bash
~/Devel/HomeAssistant/ha-services-run.sh restart spotify-bt
```
