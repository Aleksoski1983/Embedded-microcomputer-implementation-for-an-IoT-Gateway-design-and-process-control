# LwIP (Lightweight IP) Integration Guide

## Overview
LwIP (Lightweight IP) is an open-source TCP/IP stack designed for embedded systems with limited resources. In this project, LwIP provides the networking foundation for WiFi connectivity, HTTP server, DHCP, and MQTT communication on the Raspberry Pi Pico W.

## What is LwIP?
- **LwIP** stands for Lightweight IP.
- It is a small, efficient TCP/IP stack for embedded systems.
- Supports IPv4, IPv6, TCP, UDP, ICMP, DHCP, DNS, and more.
- Designed for low memory usage and high performance on microcontrollers.

## LwIP in This Application
This project uses LwIP to enable:
- WiFi network connectivity (via the Pico W's WiFi chip)
- Running an HTTP server for configuration and status
- DHCP server for AP mode
- MQTT client for IoT messaging
- TCP/UDP communication for custom protocols

## How LwIP Works in the Project

### 1. Initialization
- LwIP is initialized early in the application (see `main.c`).
- The Pico SDK provides LwIP integration and hardware abstraction.
- Network interfaces (netif) are configured for either Station (STA) or Access Point (AP) mode.

### 2. Network Interfaces
- **STA Mode:** Connects to an existing WiFi network as a client.
- **AP Mode:** Creates a WiFi access point for configuration.
- Each mode sets up a separate LwIP network interface.

### 3. DHCP
- **STA Mode:** Uses DHCP client to obtain an IP address from the router.
- **AP Mode:** Runs a DHCP server to assign IP addresses to connected clients.

### 4. HTTP Server
- Uses LwIP's raw API to serve web pages for configuration and status.
- Handles HTTP GET/POST requests and serves static files from flash.

### 5. MQTT Client
- Uses LwIP sockets for MQTT protocol communication with a broker.
- Handles publish/subscribe for IoT messaging.

### 6. TCP/UDP Communication
- LwIP provides raw TCP/UDP sockets for custom protocols (e.g., test server).

## Key Files
- `lwipopts.h`: LwIP configuration options (buffer sizes, features, etc.)
- `main.c`: LwIP initialization, network interface setup
- `api_server.c/h`, `tcp_test_server.c/h`: HTTP and TCP server implementations
- `mqtt_client.c/h`: MQTT client implementation

## Typical LwIP Workflow
1. **Initialize LwIP stack**
2. **Configure network interface** (STA or AP)
3. **Start DHCP client/server** as needed
4. **Start application servers** (HTTP, MQTT, etc.)
5. **Handle network events** (connections, data, errors)

## Example: LwIP Initialization (main.c)
```c
#include "lwip/init.h"
#include "lwip/netif.h"
#include "lwip/dhcp.h"
// ...
lwip_init();
// Configure netif, set up DHCP, start servers
```

## LwIP Configuration (lwipopts.h)
- Buffer sizes, memory pools, and enabled features are set in `lwipopts.h`.
- Adjust these settings to optimize for RAM/ROM usage and performance.

## Troubleshooting LwIP
- **No network:** Check WiFi credentials, ensure LwIP is initialized before use.
- **DHCP issues:** Verify correct mode (client/server), check IP address ranges.
- **HTTP/MQTT not working:** Ensure servers are started after network is up.
- **Memory errors:** Tune buffer sizes in `lwipopts.h`.

## References
- [LwIP Wiki](https://savannah.nongnu.org/projects/lwip/)
- [Pico SDK Networking Docs](https://raspberrypi.github.io/pico-sdk-doxygen/group__lwip.html)
- [LwIP User Manual (PDF)](https://www.nongnu.org/lwip/2_1_x/group__lwip__opts.html)

## License
LwIP is licensed under a BSD-style license. See the main project license for details.
