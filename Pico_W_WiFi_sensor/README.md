# Pico W WiFi Sensor (DHT22 + OLED + MQTT + Web Dashboard)

Firmware for Raspberry Pi Pico W that:

- Reads a DHT22 temperature/humidity sensor
- Shows status on an SSD1306 128×64 OLED (I2C)
- Serves a modern web dashboard (static HTML + JS)
- Publishes sensor data over MQTT (lwIP MQTT)
- Stores configuration in flash (persists across reboots)

## Web Interfaces

### Run Mode (normal operation)

- Dashboard: `http://<device-ip>/` (port 80)
- JSON API: `http://<device-ip>:8080/api/*` (port 8080)
- MQTT configuration is changed from the dashboard and applied after reboot.

### Setup Mode (WiFi recovery / first-time provisioning)

- Hold **GPIO22 to GND for ~3 seconds during boot**.
- Device starts an AP: `picow_config` (open network)
- Open: `http://192.168.0.1/` (auto-redirects to `/index.shtml`)
- Setup portal is intentionally **WiFi-only** (SSID + password). This is a safety decision because there is no auth/TLS.

## JSON API (port 8080)

- `GET /api/data` → runtime status and latest sensor values
- `GET /api/config` → current MQTT config (enabled/broker_ip/topic)
- `POST /api/config` → update MQTT config, write to flash, respond `{ ok:true, rebooting:true }`

### API Schema (examples)

Base URL: `http://<device-ip>:8080`

#### `GET /api/data`

Response (200):

```json
{
	"uptime_ms": 123456,
	"sensor": {
		"temperature_c": 24.8,
		"humidity_percent": 55.1,
		"valid": true
	},
	"wifi": { "ip": "192.168.1.50" },
	"mqtt": {
		"enabled": true,
		"connected": false,
		"state": "connecting"
	}
}
```

Notes:
- When the sensor is not valid: `temperature_c` and `humidity_percent` are `null`, and `valid` is `false`.
- `mqtt.state` is one of: `"connected" | "connecting" | "disconnected" | "error"`.

#### `GET /api/config`

Response (200):

```json
{
	"mqtt": {
		"enabled": true,
		"broker_ip": "192.168.1.100",
		"topic": "sensor/picow"
	}
}
```

#### `POST /api/config`

Request body (application/json):

```json
{
	"enabled": true,
	"broker_ip": "192.168.1.100",
	"topic": "sensor/picow"
}
```

Response (200):

```json
{"ok":true,"rebooting":true}
```

Validation:
- `broker_ip` must be a valid IPv4 string (not `0.0.0.0`).
- `topic` must be 1..64 characters.

CORS:
- `OPTIONS` is supported and responses include `Access-Control-Allow-Origin: *`.

## Build & Flash

Prereqs: Pico SDK, ARM GCC, CMake, Ninja, and Python 3.

Build:

1. Configure: `cmake -G Ninja -S . -B build`
2. Build: `cmake --build build`
3. Flash: copy `build/wifi_configure.uf2` to the Pico W in BOOTSEL mode.

## Editing the Web UI

Static files are in `wifi_setup/fs/`.

After editing any file in that folder, regenerate the embedded filesystem:

1. `cd wifi_setup`
2. `python generate_fsdata.py`
3. Rebuild firmware (`cmake --build build`)

## Docs

- Setup/run behavior: `USER_GUIDE.md`
- MQTT usage: `MQTT_GUIDE.md` and `MQTT_QUICKSTART.md`
- OLED wiring: `OLED_INTEGRATION.md`

## License

See `LICENSE.TXT`.

