/**
 * MQTT Client for Pico W WiFi Sensor
 * 
 * This module provides MQTT connectivity for publishing sensor data
 * to a Mosquitto broker using lwIP's MQTT client library.
 */

#include "mqtt_client.h"
#include "lwip/apps/mqtt.h"
#include "lwip/dns.h"
#include "lwip/icmp.h"
#include "lwip/inet_chksum.h"
#include "lwip/ip.h"
#include "lwip/netif.h"
#include "lwip/raw.h"
#include "lwip/timeouts.h"
#include "lwip/tcp.h"
#include "lwip/pbuf.h"
#include "pico/stdlib.h"
#include <stdio.h>
#include <string.h>

// MQTT client instance
static mqtt_client_t *mqtt_client = NULL;
static mqtt_config_t current_config = {0};
static mqtt_state_t current_state = MQTT_STATE_DISCONNECTED;

// TCP port test variables
static bool tcp_test_connected = false;
static bool tcp_test_failed = false;

// Forward declarations
static void mqtt_connection_cb(mqtt_client_t *client, void *arg, mqtt_connection_status_t status);
static void mqtt_publish_cb(void *arg, err_t err);
static err_t tcp_test_connected_cb(void *arg, struct tcp_pcb *tpcb, err_t err);
static void tcp_test_error_cb(void *arg, err_t err);
static err_t tcp_test_connected_cb(void *arg, struct tcp_pcb *tpcb, err_t err);
static void tcp_test_error_cb(void *arg, err_t err);

/**
 * MQTT connection callback
 */
static void mqtt_connection_cb(mqtt_client_t *client, void *arg, mqtt_connection_status_t status)
{
    printf("MQTT connection callback received, status: %d\n", status);
    if (status == MQTT_CONNECT_ACCEPTED) {
        printf("MQTT connected to broker successfully\n");
        current_state = MQTT_STATE_CONNECTED;
    } else {
        printf("MQTT connection failed, status: %d\n", status);
        // More detailed error reporting
        switch(status) {
            case MQTT_CONNECT_REFUSED_PROTOCOL_VERSION:
                printf("  Error: Protocol version refused\n");
                break;
            case MQTT_CONNECT_REFUSED_IDENTIFIER:
                printf("  Error: Client identifier refused\n");
                break;
            case MQTT_CONNECT_REFUSED_SERVER:
                printf("  Error: Server unavailable\n");
                break;
            case MQTT_CONNECT_REFUSED_USERNAME_PASS:
                printf("  Error: Username/password refused\n");
                break;
            case MQTT_CONNECT_REFUSED_NOT_AUTHORIZED_:
                printf("  Error: Not authorized\n");
                break;
            case 256:
                printf("  Error: TCP connection failed or timeout\n");
                printf("  Note: This can happen after successful connection due to keep-alive timeout\n");
                printf("  Check: Is broker configured for keep-alive timeout?\n");
                printf("  Check: Network stability to %s:%d\n", 
                       ip4addr_ntoa(&current_config.broker_ip), MQTT_BROKER_PORT);
                break;
            default:
                printf("  Error: Unknown error code %d\n", status);
                if (status > 255) {
                    printf("  This appears to be a network/TCP error\n");
                    printf("  Possible causes: Connection timeout, keep-alive timeout, network unstable\n");
                }
                break;
        }
        current_state = MQTT_STATE_ERROR;
    }
}

/**
 * TCP port test connected callback
 */
static err_t tcp_test_connected_cb(void *arg, struct tcp_pcb *tpcb, err_t err)
{
    printf("TCP test: Connection established to port 1883\n");
    tcp_test_connected = true;
    
    // Close the test connection immediately with proper cleanup
    tcp_arg(tpcb, NULL);
    tcp_recv(tpcb, NULL);
    tcp_err(tpcb, NULL);
    tcp_poll(tpcb, NULL, 0);
    tcp_sent(tpcb, NULL);
    
    err_t close_err = tcp_close(tpcb);
    if (close_err != ERR_OK) {
        printf("TCP test: Force close connection\n");
        tcp_abort(tpcb);
    }
    
    return ERR_OK;
}

/**
 * TCP port test error callback
 */
static void tcp_test_error_cb(void *arg, err_t err)
{
    printf("TCP test: Connection failed to port 1883, error: %d\n", err);
    tcp_test_failed = true;
    // No need to cleanup PCB here, lwIP handles it in error cases
}

/**
 * MQTT publish callback
 */
static void mqtt_publish_cb(void *arg, err_t err)
{
    if (err == ERR_OK) {
        printf("MQTT message published successfully\n");
    } else {
        printf("MQTT publish error: %d\n", err);
    }
}

/**
 * Test if TCP port is open and accepting connections
 */
static bool test_tcp_port(const ip4_addr_t *ip, u16_t port, uint32_t timeout_ms)
{
    struct tcp_pcb *test_pcb = NULL;
    
    // Reset test flags
    tcp_test_connected = false;
    tcp_test_failed = false;
    
    printf("Testing TCP connection to %s:%d...\n", ip4addr_ntoa(ip), port);
    
    // Create TCP PCB
    test_pcb = tcp_new();
    if (test_pcb == NULL) {
        printf("TCP test: Failed to create PCB\n");
        return false;
    }
    
    // Set callbacks
    tcp_arg(test_pcb, NULL);
    tcp_err(test_pcb, tcp_test_error_cb);
    
    // Attempt connection
    err_t err = tcp_connect(test_pcb, ip, port, tcp_test_connected_cb);
    if (err != ERR_OK) {
        printf("TCP test: Connect initiation failed, error: %d\n", err);
        tcp_close(test_pcb);
        return false;
    }
    
    // Wait for connection or timeout with shorter polling interval
    uint32_t start_time = to_ms_since_boot(get_absolute_time());
    uint32_t elapsed_time = 0;
    
    while (!tcp_test_connected && !tcp_test_failed && elapsed_time < timeout_ms) {
        sleep_ms(50);  // Longer sleep to reduce CPU usage
        elapsed_time = to_ms_since_boot(get_absolute_time()) - start_time;
    }
    
    // Cleanup if connection didn't complete properly
    if (!tcp_test_connected && !tcp_test_failed) {
        printf("TCP test: Connection timeout after %lu ms\n", timeout_ms);
        tcp_abort(test_pcb);  // Force abort on timeout
        return false;
    }
    
    if (tcp_test_connected) {
        printf("TCP test: Port %d is open and accepting connections\n", port);
        return true;
    } else {
        printf("TCP test: Port %d connection failed\n", port);
        return false;
    }
}

/**
 * Initialize the MQTT client
 */
bool mqtt_client_init(void)
{
    if (mqtt_client != NULL) {
        printf("MQTT client already initialized\n");
        return true;
    }

    mqtt_client = mqtt_client_new();
    if (mqtt_client == NULL) {
        printf("Failed to create MQTT client\n");
        return false;
    }

    printf("MQTT client initialized\n");
    return true;
}

/**
 * Configure and connect to MQTT broker
 */
bool mqtt_sensor_connect(const mqtt_config_t *config)
{
    if (mqtt_client == NULL) {
        printf("MQTT client not initialized\n");
        return false;
    }

    if (!config->enabled) {
        printf("MQTT is disabled in configuration\n");
        return false;
    }

    if (config->broker_ip.addr == IPADDR_NONE || config->broker_ip.addr == 0) {
        printf("Invalid MQTT broker IP address\n");
        return false;
    }

    if (strlen(config->topic) == 0) {
        printf("MQTT topic is empty\n");
        return false;
    }

    // Store current configuration
    memcpy(&current_config, config, sizeof(mqtt_config_t));

    // Set up MQTT client info
    struct mqtt_connect_client_info_t ci;
    memset(&ci, 0, sizeof(ci));
    ci.client_id = MQTT_CLIENT_ID;
    ci.keep_alive = 30;  // Reduced from 60 to 30 seconds for more frequent heartbeats
    ci.will_topic = NULL;  // No last will
    ci.will_msg = NULL;
    ci.will_retain = 0;
    ci.will_qos = 0;
    
    printf("MQTT client info:\n");
    printf("  Client ID: %s\n", ci.client_id);
    printf("  Keep alive: %d seconds\n", ci.keep_alive);

    printf("Connecting to MQTT broker at %s:%d\n", 
           ip4addr_ntoa(&config->broker_ip), MQTT_BROKER_PORT);
    printf("MQTT client ID: %s\n", MQTT_CLIENT_ID);
        printf("MQTT topic: %s\n", config->topic);

    // Verify network interface is up and has IP
    if (!netif_is_up(netif_default)) {
        printf("ERROR: Network interface is down\n");
        current_state = MQTT_STATE_ERROR;
        return false;
    }
    
    if (ip4_addr_isany(netif_ip4_addr(netif_default))) {
        printf("ERROR: No IP address assigned to network interface\n");
        current_state = MQTT_STATE_ERROR;
        return false;
    }
    
    printf("Network status: Interface UP, Local IP: %s\n", 
           ip4addr_ntoa(netif_ip4_addr(netif_default)));
    
    // Test basic connectivity to broker
    printf("Testing connectivity to broker...\n");
    if (!mqtt_test_connectivity(&config->broker_ip)) {
        printf("ERROR: Basic network connectivity test failed\n");
        current_state = MQTT_STATE_ERROR;
        return false;
    }
    printf("Network connectivity test passed\n");
    
    // Test if MQTT port is actually open
    printf("Testing MQTT port accessibility...\n");
    if (!test_tcp_port(&config->broker_ip, MQTT_BROKER_PORT, 3000)) {  // Reduced timeout to 3 seconds
        printf("ERROR: MQTT port %d is not accessible on broker %s\n", 
               MQTT_BROKER_PORT, ip4addr_ntoa(&config->broker_ip));
        printf("Possible causes:\n");
        printf("  - Mosquitto broker not running\n");
        printf("  - Broker not listening on port %d\n", MQTT_BROKER_PORT);
        printf("  - Firewall blocking port %d\n", MQTT_BROKER_PORT);
        printf("  - Broker configured for different port\n");
        current_state = MQTT_STATE_ERROR;
        return false;
    }
    printf("MQTT port test passed - broker is listening\n");
    
    // Give lwIP time to clean up test connection before starting MQTT
    printf("Allowing TCP test cleanup...\n");
    sleep_ms(500);
    
    current_state = MQTT_STATE_CONNECTING;

    // Allow network stack to settle
    printf("Waiting for network stack to stabilize...\n");
    sleep_ms(1000);
    
    // Connect to MQTT broker using lwIP's mqtt_client_connect function
    printf("Initiating TCP connection to %s:%d...\n", 
           ip4addr_ntoa(&config->broker_ip), MQTT_BROKER_PORT);
    err_t err = mqtt_client_connect(mqtt_client,
                                     &config->broker_ip,
                                     MQTT_BROKER_PORT,
                                     mqtt_connection_cb,
                                     NULL,
                                     &ci);

    if (err != ERR_OK) {
        printf("MQTT connection initiation failed: %d\n", err);
        current_state = MQTT_STATE_ERROR;
        return false;
    }

    return true;
}

/**
 * Disconnect from MQTT broker
 */
void mqtt_sensor_disconnect(void)
{
    if (mqtt_client != NULL && current_state == MQTT_STATE_CONNECTED) {
        mqtt_disconnect(mqtt_client);
        current_state = MQTT_STATE_DISCONNECTED;
        printf("MQTT disconnected\n");
    }
}

/**
 * Publish temperature and humidity data to MQTT broker
 */
bool mqtt_publish_sensor_data(float temperature, float humidity)
{
    if (mqtt_client == NULL) {
        printf("MQTT client not initialized\n");
        return false;
    }

    if (current_state != MQTT_STATE_CONNECTED) {
        printf("MQTT not connected (state: %d)\n", current_state);
        return false;
    }

    if (!current_config.enabled) {
        return false;
    }

    // Create JSON payload
    char payload[128];
    int len = snprintf(payload, sizeof(payload),
                       "{\"temperature\":%.1f,\"humidity\":%.1f}",
                       temperature, humidity);

    if (len < 0 || len >= sizeof(payload)) {
        printf("Failed to create MQTT payload\n");
        return false;
    }

    // Publish message
    err_t err = mqtt_publish(mqtt_client,
                             current_config.topic,
                             payload,
                             len,
                             0,  // QoS 0
                             0,  // retain = false
                             mqtt_publish_cb,
                             NULL);

    if (err != ERR_OK) {
        printf("MQTT publish failed: %d\n", err);
        return false;
    }

    printf("Publishing to %s: %s\n", current_config.topic, payload);
    return true;
}

/**
 * Get current MQTT connection state
 */
mqtt_state_t mqtt_get_state(void)
{
    return current_state;
}

/**
 * Check if MQTT client is connected
 */
bool mqtt_is_connected(void)
{
    return (current_state == MQTT_STATE_CONNECTED);
}

/**
 * Update MQTT configuration (reconnect if needed)
 */
bool mqtt_update_config(const mqtt_config_t *config)
{
    // Disconnect if currently connected
    if (current_state == MQTT_STATE_CONNECTED) {
        mqtt_sensor_disconnect();
        sleep_ms(100); // Brief delay to ensure clean disconnect
    }

    // Connect with new configuration if enabled
    if (config->enabled) {
        return mqtt_sensor_connect(config);
    }

    return true;
}

/**
 * Test basic network connectivity to MQTT broker
 */
bool mqtt_test_connectivity(const ip4_addr_t *broker_ip)
{
    // Basic checks
    if (!netif_is_up(netif_default)) {
        printf("Network interface is down\n");
        return false;
    }
    
    if (ip4_addr_isany(netif_ip4_addr(netif_default))) {
        printf("No IP address assigned\n");
        return false;
    }
    
    // Check if broker IP is in same subnet for basic routing
    ip4_addr_t local_ip = *netif_ip4_addr(netif_default);
    ip4_addr_t netmask = *netif_ip4_netmask(netif_default);
    
    printf("Network diagnostics:\n");
    printf("  Local IP: %s\n", ip4addr_ntoa(&local_ip));
    printf("  Netmask:  %s\n", ip4addr_ntoa(&netmask));
    printf("  Gateway:  %s\n", ip4addr_ntoa(netif_ip4_gw(netif_default)));
    printf("  Target:   %s\n", ip4addr_ntoa(broker_ip));
    
    // Check if broker is in same subnet
    if ((local_ip.addr & netmask.addr) == (broker_ip->addr & netmask.addr)) {
        printf("  Broker is in same subnet (direct routing)\n");
    } else {
        printf("  Broker is in different subnet (via gateway)\n");
        if (ip4_addr_isany(netif_ip4_gw(netif_default))) {
            printf("  WARNING: No gateway configured for external routing\n");
            return false;
        }
    }
    
    return true;
}
