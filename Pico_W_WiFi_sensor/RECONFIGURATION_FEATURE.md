# Reconfiguration Feature

This project intentionally splits configuration into two paths:

- **WiFi provisioning** (SSID/password) is only done in **setup/AP mode** (physical access required).
- **MQTT configuration** is adjustable in **run mode** from the dashboard (network access).

This keeps WiFi credentials off remote endpoints (no auth/TLS) while still allowing routine MQTT changes.

## Setup Mode (WiFi)

Use when: first-time setup, WiFi password change, or recovery.

- Trigger: hold GPIO22 to GND for ~3 seconds during boot
- Connect to AP: `picow_config`
- Open: `http://192.168.0.1/` (served at `/index.shtml`)
- Action: enter SSID + password → save → device restarts and joins your WiFi

## Run Mode (MQTT)

Use when: changing broker IP/topic or enabling/disabling MQTT.

- Open dashboard: `http://<device-ip>/`
- Edit MQTT settings → save
- Device writes the new MQTT config to flash and **reboots to apply changes**

### API behavior

Run mode also exposes a small JSON API on port 8080:

- `GET /api/config` (current MQTT settings)
- `POST /api/config` (update MQTT settings + reboot)

## Notes

- WiFi credentials are not changed via run-mode APIs.
- If you need to change WiFi, use setup mode (GPIO22).
