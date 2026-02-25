/**
 * DHT22 Temperature and Humidity Sensor Driver Implementation
 * For Raspberry Pi Pico
 */

#include "dht22.h"
#include "hardware/gpio.h"
#include <stdio.h>
#include <string.h>

// Last valid reading
static dht22_data_t last_reading = {0.0, 0.0, false};

// Wait for pin state change with timeout
static bool wait_for_pin_state(uint gpio, bool state, uint32_t timeout_us) {
    absolute_time_t timeout_time = make_timeout_time_us(timeout_us);
    
    while (gpio_get(gpio) != state) {
        if (absolute_time_diff_us(get_absolute_time(), timeout_time) <= 0) {
            return false;  // Timeout
        }
    }
    return true;
}

// Measure pulse width in microseconds
static uint32_t measure_pulse_us(uint gpio, bool state, uint32_t timeout_us) {
    absolute_time_t start_time = get_absolute_time();
    absolute_time_t timeout_time = make_timeout_time_us(timeout_us);
    
    while (gpio_get(gpio) == state) {
        if (absolute_time_diff_us(get_absolute_time(), timeout_time) <= 0) {
            return 0;  // Timeout
        }
    }
    
    return absolute_time_diff_us(start_time, get_absolute_time());
}

/**
 * Initialize DHT22 sensor
 */
void dht22_init(uint gpio) {
    gpio_init(gpio);
    gpio_set_dir(gpio, GPIO_OUT);
    gpio_put(gpio, 1);
    sleep_ms(2000);  // Wait 2 seconds for sensor to stabilize
    
    printf("DHT22 initialized on GPIO %d\n", gpio);
}

/**
 * Read data from DHT22 sensor
 * Returns true if reading is successful
 */
bool dht22_read(uint gpio, dht22_data_t *data) {
    uint8_t bytes[5] = {0};
    uint32_t pulse_width;
    
    // Send start signal
    gpio_set_dir(gpio, GPIO_OUT);
    gpio_put(gpio, 0);
    sleep_ms(1);  // Pull low for at least 1ms
    gpio_put(gpio, 1);
    sleep_us(30);  // Wait 30us
    
    // Switch to input mode
    gpio_set_dir(gpio, GPIO_IN);
    
    // Wait for DHT22 response (pull low then high)
    if (!wait_for_pin_state(gpio, 0, 100)) {
        printf("DHT22: No response (timeout waiting for LOW)\n");
        return false;
    }
    
    if (!wait_for_pin_state(gpio, 1, 100)) {
        printf("DHT22: No response (timeout waiting for HIGH)\n");
        return false;
    }
    
    if (!wait_for_pin_state(gpio, 0, 100)) {
        printf("DHT22: No response (timeout waiting for data start)\n");
        return false;
    }
    
    // Read 40 bits of data (5 bytes)
    for (int i = 0; i < 40; i++) {
        // Wait for start of bit transmission (pin goes high)
        if (!wait_for_pin_state(gpio, 1, 100)) {
            printf("DHT22: Timeout waiting for bit %d start\n", i);
            return false;
        }
        
        // Measure pulse width to determine if it's 0 or 1
        pulse_width = measure_pulse_us(gpio, 1, 100);
        
        if (pulse_width == 0) {
            printf("DHT22: Timeout measuring bit %d\n", i);
            return false;
        }
        
        // If pulse is longer than 40us, it's a '1', otherwise '0'
        if (pulse_width > 40) {
            bytes[i / 8] |= (1 << (7 - (i % 8)));
        }
    }
    
    // Verify checksum
    uint8_t checksum = bytes[0] + bytes[1] + bytes[2] + bytes[3];
    if (checksum != bytes[4]) {
        printf("DHT22: Checksum error (calculated: 0x%02X, received: 0x%02X)\n", 
               checksum, bytes[4]);
        return false;
    }
    
    // Calculate humidity (bytes 0-1)
    uint16_t humidity_raw = (bytes[0] << 8) | bytes[1];
    data->humidity = humidity_raw / 10.0f;
    
    // Calculate temperature (bytes 2-3)
    uint16_t temperature_raw = ((bytes[2] & 0x7F) << 8) | bytes[3];
    data->temperature = temperature_raw / 10.0f;
    
    // Check for negative temperature
    if (bytes[2] & 0x80) {
        data->temperature = -data->temperature;
    }
    
    data->valid = true;
    
    // Store as last valid reading
    memcpy(&last_reading, data, sizeof(dht22_data_t));
    
    printf("DHT22: Temp=%.1f°C, Humidity=%.1f%%\n", 
           data->temperature, data->humidity);
    
    return true;
}

/**
 * Get last valid reading
 */
void dht22_get_last_reading(dht22_data_t *data) {
    memcpy(data, &last_reading, sizeof(dht22_data_t));
}
