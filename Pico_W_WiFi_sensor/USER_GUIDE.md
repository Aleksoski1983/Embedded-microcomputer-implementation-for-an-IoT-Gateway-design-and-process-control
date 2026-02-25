# Pico W WiFi Sensor - User Guide

This guide documents the current firmware behavior (setup portal, dashboard, JSON API, MQTT) as of January 2026.

## Overview

The device has two modes:

- **Setup mode (AP)**: used to provision WiFi credentials (SSID + password)
- **Run mode (STA)**: normal operation (DHT22 + OLED + dashboard + MQTT)

WiFi credentials and MQTT settings are stored in flash and persist across reboots.

## Quick Start

1. Flash `build/wifi_configure.uf2` to the Pico W (BOOTSEL).
2. Enter setup mode (first boot with empty config, or hold GPIO22→GND for ~3 seconds during boot).
3. Connect to the AP `picow_config` and open `http://192.168.0.1/`.
4. Enter WiFi SSID/password → **Save & Restart**.
5. Reconnect your PC/phone to your normal WiFi and open `http://<device-ip>/`.

## Setup Mode (Access Point)

### How to enter

- Hold **GPIO22 to GND** during boot and keep it there until ~3 seconds have passed.

### Network details

- SSID: `picow_config`
- Password: none (open)
- Device IP: `192.168.0.1`

### Setup portal

- URL: `http://192.168.0.1/` (redirects to `/index.shtml`)
- The portal is **WiFi-only** (SSID + password).

Security note: the AP is open and HTTP is unencrypted. Keep setup mode short and use it in a trusted environment.

## Run Mode (Normal Operation)

### Dashboard (port 80)

- URL: `http://<device-ip>/`
- Shows uptime, IP, temperature, humidity, and MQTT connection status.
- Allows editing MQTT configuration (and reboots to apply changes).

### JSON API (port 8080)

The UI fetches live data from a dedicated mini HTTP server on port 8080:

- `GET http://<device-ip>:8080/api/data`
- `GET http://<device-ip>:8080/api/config`
- `POST http://<device-ip>:8080/api/config` (updates MQTT settings and triggers reboot)

This split keeps the port-80 server simple (static files) and uses JSON for dynamic state.

#### Schema

Base URL: `http://<device-ip>:8080`

**GET `/api/data`** (live status + sensor)

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
    "connected": true,
    "state": "connected"
  }
}
```

**GET `/api/config`** (current MQTT config)

```json
{
  "mqtt": {
    "enabled": true,
    "broker_ip": "192.168.1.100",
    "topic": "sensor/picow"
  }
}
```

**POST `/api/config`** (update MQTT config and reboot)

Request:

```json
{
  "enabled": true,
  "broker_ip": "192.168.1.100",
  "topic": "sensor/picow"
}
```

Response:

```json
{"ok":true,"rebooting":true}
```

## MQTT

### Configure

- In run mode, open the dashboard and update:
  - Enabled/disabled
  - Broker IP
  - Topic

Saving triggers a reboot (expected behavior).

### Payload

Sensor values are published in JSON:

```json
{"temperature":25.5,"humidity":60.2}
```

## OLED

See `OLED_INTEGRATION.md` for wiring and display behavior.

## Building

Prereqs: Pico SDK, ARM GCC toolchain, CMake, Ninja, Python 3.

```powershell
cmake -G Ninja -S . -B build
cmake --build build
```

Output: `build/wifi_configure.uf2`

## Modifying Web Pages

Web assets live in `wifi_setup/fs/`.

After editing files, regenerate the embedded filesystem and rebuild:

```powershell
cd wifi_setup
python .\generate_fsdata.py
cd ..
cmake --build build
```

## Troubleshooting

- Can’t see `picow_config`: verify GPIO22 is held low during boot for ~3 seconds.
- Setup page doesn’t load: ensure you’re on `http://` (not `https://`) and connected to the AP.
- Can’t find run-mode IP: check serial output (115200) or your router DHCP lease list.
- MQTT not connecting: confirm broker IP/port 1883 reachable and topic is valid.
- Test with: `telnet <device_ip> 4711`
- Useful for custom protocols or testing

### Serial Debug Levels

To add verbose debugging:
1. Edit `main.c`
2. Add debug prints:
   ```c
   printf("Debug: WiFi status = %d\n", status);
   ```
3. Rebuild and flash

### Watchdog Timer

**Add automatic reset on hang**:
```c
#include "hardware/watchdog.h"

// In main():
watchdog_enable(8000, 1); // 8 second timeout

// In main loop:
watchdog_update(); // Reset timer
```

### Multiple Network Profiles

To support multiple WiFi networks:
1. Modify `flash_program.h` to include array of configs
2. Extend web interface for profile selection
3. Add fallback logic in connection code
4. Increase flash allocation

### Static IP Without Web Config

To hardcode static IP in firmware:
```c
// In main.c, replace DHCP with:
ip4_addr_t ip, netmask, gateway;
IP4_ADDR(&ip, 192, 168, 1, 100);
IP4_ADDR(&netmask, 255, 255, 255, 0);
IP4_ADDR(&gateway, 192, 168, 1, 1);
netif_set_addr(netif, &ip, &netmask, &gateway);
```

---

## Technical Specifications

- **Microcontroller**: RP2040 (Dual ARM Cortex-M0+ @ 133MHz)
- **WiFi Chip**: CYW43439 (2.4GHz 802.11n)
- **Flash Memory**: 2MB
- **RAM**: 264KB
- **TCP/IP Stack**: lwIP (Lightweight IP)
- **HTTP Server**: lwIP httpd module
- **WiFi Standards**: 802.11b/g/n (2.4GHz only)
- **Security**: WPA2-PSK, WPA/WPA2 mixed (no WPA3)
- **Power Consumption**: 
  - Active (WiFi TX): ~180mA @ 3.3V
  - Active (WiFi RX): ~100mA @ 3.3V
  - Idle: ~30mA @ 3.3V

---

## License

Refer to `LICENSE.TXT` for project licensing information.

DHCP server component uses code from lwIP and has separate licensing - see `wifi_setup/LICENSE-dhcpserver`.

---

## Additional Resources

- **Pico W Documentation**: https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html
- **Pico SDK**: https://github.com/raspberrypi/pico-sdk
- **lwIP Documentation**: https://www.nongnu.org/lwip/
- **Getting Started Guide**: https://datasheets.raspberrypi.com/pico/getting-started-with-pico.pdf

---

## Quick Reference Card

### Boot Modes
| Mode | Trigger | Network | IP Address | Purpose |
|------|---------|---------|------------|---------|
| **Configuration** | GPIO22→GND 3s | picow_config (AP) | 192.168.0.1 | WiFi setup |
| **Run** | Normal boot | Configured WiFi | DHCP assigned | Normal operation |

### Key Pins
| Pin | GPIO | Function |
|-----|------|----------|
| 29 | GPIO22 | Setup button input |
| 3, 8, 13... | GND | Ground reference |

### Serial Settings
| Parameter | Value |
|-----------|-------|
| Baud Rate | 115200 |
| Data Bits | 8 |
| Parity | None |
| Stop Bits | 1 |

### Web Interfaces
| Mode | URL | Function |
|------|-----|----------|
| Configuration | http://192.168.0.1 | WiFi setup form |
| Run | http://[device-ip] | Status dashboard |

### Build Commands
```powershell
# Configure
cmake -G Ninja ..

# Build
ninja

# Or use VS Code task
Terminal → Run Task → Compile Project
```

---

**Last Updated**: January 2026  
**Firmware Version**: 1.0  
**Pico SDK Version**: 2.2.0
