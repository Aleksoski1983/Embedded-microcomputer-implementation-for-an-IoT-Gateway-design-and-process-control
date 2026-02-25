/**
 * MQTT Client for Pico W WiFi Sensor
 * 
 * This module provides MQTT connectivity for publishing sensor data
 * to a Mosquitto broker.
 */

#ifndef MQTT_CLIENT_H
#define MQTT_CLIENT_H

#include "lwip/ip4_addr.h"
#include <stdbool.h>

// MQTT configuration
#define MQTT_BROKER_PORT 1883
#define MQTT_CLIENT_ID "picow_sensor"
#define MQTT_TOPIC_MAX_LEN 64

// MQTT client states
typedef enum {
    MQTT_STATE_DISCONNECTED,
    MQTT_STATE_CONNECTING,
    MQTT_STATE_CONNECTED,
    MQTT_STATE_ERROR
} mqtt_state_t;

// MQTT configuration structure
typedef struct {
    ip4_addr_t broker_ip;
    char topic[MQTT_TOPIC_MAX_LEN + 1];
    bool enabled;
} mqtt_config_t;

/**
 * Initialize the MQTT client
 * @return true on success, false on failure
 */
bool mqtt_client_init(void);

/**
 * Configure and connect to MQTT broker
 * @param config Pointer to MQTT configuration
 * @return true if connection initiated, false on error
 */
bool mqtt_sensor_connect(const mqtt_config_t *config);

/**
 * Disconnect from MQTT broker
 */
void mqtt_sensor_disconnect(void);

/**
 * Publish temperature and humidity data to MQTT broker
 * @param temperature Temperature value in Celsius
 * @param humidity Humidity value in percent
 * @return true on success, false on failure
 */
bool mqtt_publish_sensor_data(float temperature, float humidity);

/**
 * Get current MQTT connection state
 * @return Current MQTT state
 */
mqtt_state_t mqtt_get_state(void);

/**
 * Check if MQTT client is connected
 * @return true if connected, false otherwise
 */
bool mqtt_is_connected(void);

/**
 * Update MQTT configuration (reconnect if needed)
 * @param config Pointer to new MQTT configuration
 * @return true on success, false on failure
 */
bool mqtt_update_config(const mqtt_config_t *config);

/**
 * Test basic network connectivity to MQTT broker
 * @param broker_ip IP address of the broker to test
 * @return true if network appears reachable, false otherwise
 */
bool mqtt_test_connectivity(const ip4_addr_t *broker_ip);

#endif // MQTT_CLIENT_H
