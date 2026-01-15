# HA Services Runner

Automatyczny manager serwisów dla Home Assistant na macOS.

## Struktura

```
ha-services-run.sh              # Główny runner
local_services/
├── 00-ble-proxy.service        # Serwisy ładowane alfabetycznie
├── 10-reolink-proxy.service
├── 20-theengs.service
├── scripts/                    # Skrypty dla TYPE=script
│   ├── reolink-socat.sh
│   └── theengs-start.sh
└── env/                        # Pliki środowiskowe
    └── theengs.env
logs/                           # Auto-tworzone logi
.pids/                          # Auto-tworzone PID files
```

## Użycie

```bash
./ha-services-run.sh              # Start + monitor (Ctrl+C stop)
./ha-services-run.sh start        # Start all
./ha-services-run.sh stop         # Stop all
./ha-services-run.sh restart      # Restart all
./ha-services-run.sh reload       # Start new, stop removed, keep running
./ha-services-run.sh status       # Show status table
./ha-services-run.sh logs         # Tail all logs

# Single service
./ha-services-run.sh start theengs
./ha-services-run.sh stop ble-proxy
./ha-services-run.sh logs theengs
```

## Format pliku .service

```bash
NAME="service-name"              # Nazwa (default: z nazwy pliku)
TYPE="simple"                    # simple | script
CMD="command --args"             # Komenda do uruchomienia
WAIT_FOR="tcp:localhost:1883"    # tcp:host:port | service:name
RESTART="always"                 # always | no
RESTART_DELAY=5                  # Sekundy między restartami
ENV="VAR=value"                  # Zmienna środowiskowa
ENV_FILE="env/name.env"          # Plik ze zmiennymi
STOP_PATTERN="pattern"           # Pattern dla pkill
```

## Dodawanie nowego serwisu

1. Utwórz plik `local_services/XX-nazwa.service`
2. Uruchom `./ha-services-run.sh reload`

## Reload

`reload` inteligentnie aktualizuje serwisy:
- Nowe pliki .service → uruchamia
- Usunięte pliki → zatrzymuje serwis  
- Istniejące działające → nie dotyka
