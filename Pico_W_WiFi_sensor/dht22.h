/**
 * DHT22 Temperature and Humidity Sensor Driver
 * For Raspberry Pi Pico
 * 
 * GPIO 15 - DHT22 Data Pin
 */

#ifndef DHT22_H
#define DHT22_H

#include "pico/stdlib.h"
#include <stdbool.h>

#define DHT22_PIN 15

// DHT22 data structure
typedef struct {
    float temperature;  // Temperature in Celsius
    float humidity;     // Relative humidity in %
    bool valid;         // Data validity flag
} dht22_data_t;

// Function prototypes
void dht22_init(uint gpio);
bool dht22_read(uint gpio, dht22_data_t *data);
void dht22_get_last_reading(dht22_data_t *data);

#endif // DHT22_H
