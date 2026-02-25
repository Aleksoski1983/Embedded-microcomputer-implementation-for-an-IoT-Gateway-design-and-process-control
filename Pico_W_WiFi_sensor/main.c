/**
 * This file is part of "Wi-Fi Configure.
 *
 * This software eliminates the need to know the network name, password and,
 * if required, IP address, network mask and default gateway at compile time.
 * These can be set directly on the Pico-W and also changed afterwards.
 *
 */

#include <string.h>
#include <stdlib.h>

#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"
#include "hardware/i2c.h"
#include "hardware/watchdog.h"
#include "lwipopts.h"
#include "lwip/apps/httpd.h"

#include "access_point.h"
#include "tcp_test_server.h"
#include "ssd1306.h"
#include "dht22.h"
#include "mqtt_client.h"
#include "http_server.h"
#include "api_server.h"

// Global sensor data for web display
float g_temperature = 0.0;
float g_humidity = 0.0;
bool g_sensor_valid = false;

// Make config accessible for SSI handler in http_server.c
extern config *_c;

// OLED pins - GPIO 0 (SDA) and GPIO 1 (SCL)
#define OLED_SDA_PIN 0
#define OLED_SCL_PIN 1

// Global sensor data
static dht22_data_t sensor_data = {0.0, 0.0, false};
static config g_config; // Global config used by API server (and optional SSI)

void print_config(config *c) {
    if(c->magic != MAGIC) {
        printf("No configuration found.\n");
        return;
    }

    printf("Stored configuration data:\n");
    printf("\tMagic:        %04X\n",  c->magic);
    printf("\tSSID:        \"%s\"\n", c->ssid);
    printf("\tPassword:    \"%s\"\n", c->passwd);
    printf("\tIP:           %s\n",    ip4addr_ntoa(&(c->ip)));
    printf("\tNetmask:      %s\n",    ip4addr_ntoa(&(c->mask)));
    printf("\tDef. Gateway: %s\n",    ip4addr_ntoa(&(c->gw)));
    printf("\tMQTT Enabled: %d\n",    c->mqtt_enabled);
    printf("\tMQTT Broker:  %s\n",    ip4addr_ntoa(&(c->mqtt_broker_ip)));
    printf("\tMQTT Topic:   \"%s\"\n", c->mqtt_topic);
}

void clear_flash(void)
{
    config config;

    printf("Client has requested the erasure of the configuration\n");
    flash_erase_page(WIFI_CONFIG_PAGE, 1);
    flash_read((uint8_t *)&config, sizeof(config), WIFI_CONFIG_PAGE);
    print_config(&config);

}

// SSI handler for the run mode web server
u16_t run_ssi_handler(int iIndex, char *pcInsert, int iInsertLen)
{
    size_t printed;
    dht22_data_t data;
    
    switch (iIndex) {
    case 0: // Device status / SSID
        printed = snprintf(pcInsert, iInsertLen, "%s", g_config.ssid);
        break;
    case 1: // IP Address
        printed = snprintf(pcInsert, iInsertLen, "%s", ip4addr_ntoa(netif_ip4_addr(netif_default)));
        break;
    case 2: // Temperature
        dht22_get_last_reading(&data);
        if (data.valid) {
            printed = snprintf(pcInsert, iInsertLen, "%.1f", data.temperature);
        } else {
            printed = snprintf(pcInsert, iInsertLen, "--");
        }
        break;
    case 3: // Humidity
        dht22_get_last_reading(&data);
        if (data.valid) {
            printed = snprintf(pcInsert, iInsertLen, "%.1f", data.humidity);
        } else {
            printed = snprintf(pcInsert, iInsertLen, "--");
        }
        break;
    case 4: // MQTT Enabled
        printed = snprintf(pcInsert, iInsertLen, "%s", g_config.mqtt_enabled ? "Yes" : "No");
        break;
    case 5: // MQTT Broker IP
        if (g_config.mqtt_broker_ip.addr != IPADDR_NONE) {
            printed = snprintf(pcInsert, iInsertLen, "%s", ip4addr_ntoa(&g_config.mqtt_broker_ip));
        } else {
            printed = snprintf(pcInsert, iInsertLen, "Not configured");
        }
        break;
    case 6: // MQTT Topic
        if (g_config.mqtt_topic[0] != '\0') {
            printed = snprintf(pcInsert, iInsertLen, "%s", g_config.mqtt_topic);
        } else {
            printed = snprintf(pcInsert, iInsertLen, "Not configured");
        }
        break;
    case 7: // MQTT Status
        if (!g_config.mqtt_enabled) {
            printed = snprintf(pcInsert, iInsertLen, "<span class=\"status-badge status-offline\">Disabled</span>");
        } else if (mqtt_is_connected()) {
            printed = snprintf(pcInsert, iInsertLen, "<span class=\"status-badge status-online\">Connected</span>");
        } else {
            printed = snprintf(pcInsert, iInsertLen, "<span class=\"status-badge status-offline\">Disconnected</span>");
        }
        break;
    default:
        printed = 0;
        break;
    }
    return (u16_t)printed;
}

// Update OLED display with device information and sensor data (full redraw)
void update_oled_display(const char *mode, const char *network, const char *ip_addr, const char *device_name) {
    char buffer[32];
    dht22_data_t data;
    
    ssd1306_clear();
    
    // Draw compact header
    ssd1306_draw_string(0, 0, "Pico W Sensor", 1);
    ssd1306_draw_line(0, 10, 127, 10, 1);
    
    // Display Network with SSID label
    ssd1306_draw_string(0, 12, "SSID:", 1);
    if (strlen(network) > 16) {
        strncpy(buffer, network, 16);
        buffer[16] = '\0';
    } else {
        strcpy(buffer, network);
    }
    ssd1306_draw_string(35, 12, buffer, 1);
    
    // Display IP Address with IP label
    ssd1306_draw_string(0, 22, "IP:", 1);
    ssd1306_draw_string(20, 22, ip_addr, 1);
    
    ssd1306_draw_line(0, 32, 127, 32, 1);
    
    // Display Temperature and Humidity
    dht22_get_last_reading(&data);
    if (data.valid) {
        snprintf(buffer, sizeof(buffer), "Temperature: %.1fC", data.temperature);
        ssd1306_draw_string(0, 35, buffer, 1);
        snprintf(buffer, sizeof(buffer), "Humidity:  %.1f%%", data.humidity);
        ssd1306_draw_string(0, 45, buffer, 1);
    } else {
        ssd1306_draw_string(0, 35, "Temperature: --", 1);
        ssd1306_draw_string(0, 45, "Humidity:  --", 1);
    }
    
    // Draw footer with WiFi and MQTT status
    ssd1306_draw_line(0, 55, 127, 55, 1);
    
    // Check WiFi connection status
    bool wifi_connected = (cyw43_tcpip_link_status(&cyw43_state, CYW43_ITF_STA) == CYW43_LINK_UP);
    
    // Build status line: "WiFi:√ MQTT:√" or "WiFi:X MQTT:X"
    snprintf(buffer, sizeof(buffer), "WiFi:%c MQTT:%c", 
             wifi_connected ? '+' : 'X',  // + for connected, X for disconnected
             (_c->mqtt_enabled && mqtt_is_connected()) ? '+' : 'X');
    
    ssd1306_draw_string(0, 57, buffer, 1);
    
    ssd1306_show();
}

// Update only sensor values (no blinking)
void update_sensor_display() {
    char buffer[32];
    dht22_data_t data;
    
    dht22_get_last_reading(&data);
    
    // Clear only the sensor area
    ssd1306_draw_rect(0, 36, 128, 20, 0, true);
    
    if (data.valid) {
        snprintf(buffer, sizeof(buffer), "Temperature: %.1fC", data.temperature);
        ssd1306_draw_string(0, 36, buffer, 1);
        snprintf(buffer, sizeof(buffer), "Humidity:  %.1f%%", data.humidity);
        ssd1306_draw_string(0, 46, buffer, 1);
    } else {
        ssd1306_draw_string(0, 36, "Temperature: --", 1);
        ssd1306_draw_string(0, 46, "Humidity:  --", 1);
    }
    
    ssd1306_show();
}

void main(void) {
    config *cfg = &g_config;

    stdio_init_all();
    
    // Wait for USB and continuously print to help diagnose
    for(int i = 0; i < 10; i++) {
        printf("=== PICO STARTING %d ===\n", i);
        fflush(stdout);
        sleep_ms(500);
    }
    
    printf("\n=== PICO READY ===\n");
    printf("Serial port initialized\n");
    fflush(stdout);

    // Initialize OLED display
    printf("Initializing OLED display...\n");
    fflush(stdout);
    if (ssd1306_init(i2c0, OLED_SDA_PIN, OLED_SCL_PIN)) {
        printf("OLED display initialized successfully\n");
        update_oled_display("Starting", "Initializing...", "---", "Pico W");
        fflush(stdout);
    } else {
        printf("Warning: OLED display initialization failed\n");
        fflush(stdout);
    }

    // Initialize DHT22 sensor
    printf("Initializing DHT22 sensor on GPIO %d...\n", DHT22_PIN);
    fflush(stdout);
    dht22_init(DHT22_PIN);

    printf("Initializing CYW43...\n");
    fflush(stdout);
    if (cyw43_arch_init()) {
        printf("failed to initialise CYW43\n");
        fflush(stdout);
        update_oled_display("ERROR", "CYW43 Init Failed", "---", "Pico W");
        while(1) {
            sleep_ms(1000);
            printf("ERROR: CYW43 init failed\n");
            fflush(stdout);
        }
    }
    printf("CYW43 initialized successfully\n");
    fflush(stdout);

    printf("Starting Wifi Configure\n");
    show_stats();

/* Configuration loading starts here */
    printf("\n=== LOADING CONFIGURATION FROM FLASH ===\n");
    flash_read((uint8_t *)cfg, sizeof(*cfg), WIFI_CONFIG_PAGE);

    // Make config available to setup SSI/CGI code
    _c = cfg;

    bool setup_requested = forceSetup();
    bool config_missing = (cfg->magic != MAGIC);
    if (setup_requested || config_missing) {
        printf("\n=== ENTERING CONFIG MODE ===\n");
        if (setup_requested) {
            printf("Setup requested via GPIO %d held low\n", SETUP_GPIO);
        }
        if (config_missing) {
            printf("No valid configuration in flash\n");
        }

        update_oled_display("Config Mode", "AP: picow_config", "192.168.0.1", "Pico W");

        // Run captive portal/AP setup. User must provide WiFi credentials.
        // Static IP and gateway are optional (DHCP allowed).
        run_access_point(cfg, false, false);

        // Ensure required fields exist.
        cfg->magic = MAGIC;
        if (cfg->mqtt_broker_ip.addr == IPADDR_NONE || cfg->mqtt_broker_ip.addr == 0) {
            IP4_ADDR(&cfg->mqtt_broker_ip, 192, 168, 100, 52);
        }
        if (cfg->mqtt_topic[0] == '\0') {
            strcpy(cfg->mqtt_topic, "DHT22");
        }

        flash_write_page((uint8_t *)cfg, sizeof(*cfg), WIFI_CONFIG_PAGE);
        printf("Configuration saved to flash from config mode\n");
        print_config(cfg);
    } else {
        // Patch up missing MQTT fields (backwards compatible with older flash layouts).
        bool changed = false;
        if (cfg->mqtt_broker_ip.addr == IPADDR_NONE || cfg->mqtt_broker_ip.addr == 0) {
            IP4_ADDR(&cfg->mqtt_broker_ip, 192, 168, 100, 52);
            changed = true;
        }
        if (cfg->mqtt_topic[0] == '\0') {
            strcpy(cfg->mqtt_topic, "DHT22");
            changed = true;
        }
        if (changed) {
            flash_write_page((uint8_t *)cfg, sizeof(*cfg), WIFI_CONFIG_PAGE);
            printf("Config had missing MQTT fields; updated and saved.\n");
        }

        print_config(cfg);
    }
/* Configuration loading ends here */


/* Code for your device starts here */
    printf("\nPico is in run mode!\n");
    cyw43_arch_gpio_put(CYW43_WL_GPIO_LED_PIN, 0);


/* Typical connection sequence ends here */
    cyw43_arch_enable_sta_mode();
        if(cfg->ip.addr != IPADDR_NONE){
#if LWIP_DHCP == 1
        dhcp_release_and_stop(netif_default);
#endif
        netif_set_addr(netif_default, &(cfg->ip), &(cfg->mask), &(cfg->gw));
        netif_set_up(netif_default);
#if LWIP_DHCP == 1
        dhcp_inform(netif_default);
#endif
        printf("Using static IP: %s\n", ip4addr_ntoa(netif_ip4_addr(netif_default)));
    }
    else{
        printf("Using DHCP: ");
    }

    printf("Connecting to WiFi...\n");
    update_oled_display("Run Mode", "Connecting...", "---", "Pico W");
    
    if (cyw43_arch_wifi_connect_timeout_ms(cfg->ssid, cfg->passwd, CYW43_AUTH_WPA2_AES_PSK, 30000)) {
        printf("failed to connect.\n");
        update_oled_display("ERROR", "WiFi Failed", "Check Config", "Pico W");
        return;
    }
    else {
        printf("connected.\n");
        cyw43_arch_gpio_put(CYW43_WL_GPIO_LED_PIN, 1);
        
        // Update OLED with connection info
        const char *ip_str = ip4addr_ntoa(netif_ip4_addr(netif_default));
        update_oled_display("Connected", cfg->ssid, ip_str, "Pico W");
    }
    /* Typical connection sequence ends here */

    // Initialize HTTP server for run mode
    printf("Starting HTTP server at http://%s\n", ip4addr_ntoa(netif_ip4_addr(netif_default)));

    // Start the HTTP daemon
    httpd_init();

    printf("HTTP server running. Open http://%s in your browser.\n", ip4addr_ntoa(netif_ip4_addr(netif_default)));

    // Start dedicated JSON API server on port 8080
    api_server_start(cfg);

    // Initialize and connect MQTT client if enabled
    printf("\n=== MQTT Configuration ===\n");
    printf("MQTT Enabled: %s\n", cfg->mqtt_enabled ? "YES" : "NO");
    if (cfg->mqtt_enabled) {
        printf("MQTT Broker IP: %s\n", ip4addr_ntoa(&cfg->mqtt_broker_ip));
        printf("MQTT Topic: %s\n", cfg->mqtt_topic);
        printf("Initializing MQTT client...\n");
        
        if (mqtt_client_init()) {
            mqtt_config_t mqtt_cfg;
            mqtt_cfg.broker_ip = cfg->mqtt_broker_ip;
            strncpy(mqtt_cfg.topic, cfg->mqtt_topic, MQTT_TOPIC_MAX_LEN);
            mqtt_cfg.topic[MQTT_TOPIC_MAX_LEN] = '\0';
            mqtt_cfg.enabled = cfg->mqtt_enabled;
            
            printf("Attempting to connect to MQTT broker...\n");
            if (mqtt_sensor_connect(&mqtt_cfg)) {
                printf("MQTT connection initiated successfully\n");
            } else {
                printf("ERROR: Failed to initiate MQTT connection\n");
            }
        } else {
            printf("ERROR: Failed to initialize MQTT client\n");
        }
    } else {
        printf("MQTT is disabled in configuration\n");
    }
    printf("=========================\n\n");

    // Just to show you what can be done...
    // run_tcp_server(clear_flash);

    // Keep the device running
    uint32_t last_sensor_read = 0;
    uint32_t mqtt_connection_check = 0;
    const uint32_t SENSOR_READ_INTERVAL_MS = 5000; // Read sensor every 5 seconds
    const uint32_t MQTT_CHECK_INTERVAL_MS = 10000; // Check MQTT connection every 10 seconds
    
    while (true) {
        // Check if restart was requested from web interface
        if (restart_requested) {
            printf("Restart requested from web interface - waiting 3 seconds to allow HTTP response...\n");
            sleep_ms(3000); // Give time for HTTP response to be sent
            printf("Restarting device...\n");
            watchdog_enable(100, 1); // Quick restart
            while(1); // Wait for watchdog reset
        }
        
        uint32_t now = to_ms_since_boot(get_absolute_time());
        
        // Check MQTT connection status periodically
        if (cfg->mqtt_enabled && (now - mqtt_connection_check >= MQTT_CHECK_INTERVAL_MS)) {
            mqtt_state_t mqtt_state = mqtt_get_state();
            printf("[%lu] MQTT Status Check: %s\n", now, 
                   mqtt_state == MQTT_STATE_CONNECTED ? "Connected" :
                   mqtt_state == MQTT_STATE_CONNECTING ? "Connecting" :
                   mqtt_state == MQTT_STATE_ERROR ? "Error" : "Disconnected");
            
            // Attempt reconnection if in error state or disconnected
            // But only if we've been in error state for more than 30 seconds
            static uint32_t error_start_time = 0;
            if (mqtt_state == MQTT_STATE_ERROR || mqtt_state == MQTT_STATE_DISCONNECTED) {
                if (error_start_time == 0) {
                    error_start_time = now;
                    printf("[%lu] MQTT error detected, waiting 30s before reconnection attempt\n", now);
                } else if ((now - error_start_time) >= 30000) { // 30 second delay
                    printf("[%lu] Attempting MQTT reconnection after error timeout...\n", now);
                    mqtt_config_t mqtt_cfg;
                    mqtt_cfg.broker_ip = cfg->mqtt_broker_ip;
                    strncpy(mqtt_cfg.topic, cfg->mqtt_topic, MQTT_TOPIC_MAX_LEN);
                    mqtt_cfg.topic[MQTT_TOPIC_MAX_LEN] = '\0';
                    mqtt_cfg.enabled = cfg->mqtt_enabled ? true : false;
                    
                    if (mqtt_sensor_connect(&mqtt_cfg)) {
                        printf("[%lu] MQTT reconnection initiated\n", now);
                        error_start_time = 0; // Reset error timer
                    } else {
                        printf("[%lu] MQTT reconnection failed\n", now);
                        error_start_time = now; // Reset timer for next attempt
                    }
                }
            } else {
                error_start_time = 0; // Reset error timer if not in error state
            }
            mqtt_connection_check = now;
        }
        
        // Read DHT22 sensor periodically
        if (now - last_sensor_read >= SENSOR_READ_INTERVAL_MS) {
            if (dht22_read(DHT22_PIN, &sensor_data)) {
                // Update global variables for web display
                g_temperature = sensor_data.temperature;
                g_humidity = sensor_data.humidity;
                g_sensor_valid = true;
                
                printf("\n[%lu] Sensor reading: %.1f°C, %.1f%%\n", 
                       now, sensor_data.temperature, sensor_data.humidity);
                
                // Update only sensor values on OLED (no full redraw - prevents blinking)
                update_sensor_display();
                
                // Publish to MQTT if enabled and connected
                if (cfg->mqtt_enabled) {
                    if (mqtt_is_connected()) {
                        printf("[%lu] MQTT Status: Connected - Publishing data...\n", now);
                        if (mqtt_publish_sensor_data(sensor_data.temperature, sensor_data.humidity)) {
                            printf("[%lu] SUCCESS: Sensor data published to MQTT topic '%s'\n", now, cfg->mqtt_topic);
                        } else {
                            printf("[%lu] ERROR: Failed to publish sensor data to MQTT\n", now);
                        }
                    } else {
                        printf("[%lu] MQTT Status: Not connected - Skipping publish\n", now);
                    }
                } else {
                    printf("[%lu] MQTT is disabled\n", now);
                }
            } else {
                printf("[%lu] ERROR: Failed to read DHT22 sensor\n", now);
            }
            last_sensor_read = now;
        }
        
        sleep_ms(1000);
        cyw43_arch_gpio_put(CYW43_WL_GPIO_LED_PIN, !cyw43_arch_gpio_get(CYW43_WL_GPIO_LED_PIN));
    }

    // NOT_REACHED
    return;
}
