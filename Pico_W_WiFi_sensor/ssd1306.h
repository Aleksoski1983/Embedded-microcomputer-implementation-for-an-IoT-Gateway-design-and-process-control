/**
 * SSD1306 OLED Display Driver for Raspberry Pi Pico
 * 128x64 I2C OLED Display
 */

#ifndef SSD1306_H
#define SSD1306_H

#include <stdint.h>
#include <stdbool.h>

// Display dimensions
#define SSD1306_WIDTH  128
#define SSD1306_HEIGHT 64

// I2C address (default is 0x3C, some displays use 0x3D)
#define SSD1306_I2C_ADDR 0x3C

// SSD1306 Commands
#define SSD1306_SET_CONTRAST        0x81
#define SSD1306_DISPLAY_ALL_ON_RESUME 0xA4
#define SSD1306_DISPLAY_ALL_ON      0xA5
#define SSD1306_NORMAL_DISPLAY      0xA6
#define SSD1306_INVERT_DISPLAY      0xA7
#define SSD1306_DISPLAY_OFF         0xAE
#define SSD1306_DISPLAY_ON          0xAF
#define SSD1306_SET_DISPLAY_OFFSET  0xD3
#define SSD1306_SET_COM_PINS        0xDA
#define SSD1306_SET_VCOM_DETECT     0xDB
#define SSD1306_SET_DISPLAY_CLOCK_DIV 0xD5
#define SSD1306_SET_PRECHARGE       0xD9
#define SSD1306_SET_MULTIPLEX       0xA8
#define SSD1306_SET_LOW_COLUMN      0x00
#define SSD1306_SET_HIGH_COLUMN     0x10
#define SSD1306_SET_START_LINE      0x40
#define SSD1306_MEMORY_MODE         0x20
#define SSD1306_COLUMN_ADDR         0x21
#define SSD1306_PAGE_ADDR           0x22
#define SSD1306_COM_SCAN_INC        0xC0
#define SSD1306_COM_SCAN_DEC        0xC8
#define SSD1306_SEG_REMAP           0xA0
#define SSD1306_CHARGE_PUMP         0x8D
#define SSD1306_EXTERNAL_VCC        0x01
#define SSD1306_SWITCH_CAP_VCC      0x02

// Scrolling commands
#define SSD1306_ACTIVATE_SCROLL                      0x2F
#define SSD1306_DEACTIVATE_SCROLL                    0x2E
#define SSD1306_SET_VERTICAL_SCROLL_AREA             0xA3
#define SSD1306_RIGHT_HORIZONTAL_SCROLL              0x26
#define SSD1306_LEFT_HORIZONTAL_SCROLL               0x27
#define SSD1306_VERTICAL_AND_RIGHT_HORIZONTAL_SCROLL 0x29
#define SSD1306_VERTICAL_AND_LEFT_HORIZONTAL_SCROLL  0x2A

/**
 * Initialize the SSD1306 display
 * @param i2c I2C instance (i2c0 or i2c1)
 * @param sda_pin GPIO pin for SDA
 * @param scl_pin GPIO pin for SCL
 * @return true if initialization successful
 */
bool ssd1306_init(void *i2c, uint8_t sda_pin, uint8_t scl_pin);

/**
 * Clear the display
 */
void ssd1306_clear(void);

/**
 * Update the display with current buffer content
 */
void ssd1306_show(void);

/**
 * Draw a pixel at the specified coordinates
 * @param x X coordinate (0-127)
 * @param y Y coordinate (0-63)
 * @param color 1 for white, 0 for black
 */
void ssd1306_draw_pixel(int x, int y, uint8_t color);

/**
 * Draw a line
 * @param x0, y0 Start coordinates
 * @param x1, y1 End coordinates
 * @param color 1 for white, 0 for black
 */
void ssd1306_draw_line(int x0, int y0, int x1, int y1, uint8_t color);

/**
 * Draw a rectangle
 * @param x, y Top-left corner
 * @param width, height Rectangle dimensions
 * @param color 1 for white, 0 for black
 * @param filled true for filled rectangle
 */
void ssd1306_draw_rect(int x, int y, int width, int height, uint8_t color, bool filled);

/**
 * Draw a character at the specified position
 * @param x X coordinate (0-127)
 * @param y Y coordinate (0-63, must be multiple of 8)
 * @param c Character to draw
 * @param size Font size (1 or 2)
 */
void ssd1306_draw_char(int x, int y, char c, uint8_t size);

/**
 * Draw a string at the specified position
 * @param x X coordinate (0-127)
 * @param y Y coordinate (0-63, must be multiple of 8)
 * @param str String to draw
 * @param size Font size (1 or 2)
 */
void ssd1306_draw_string(int x, int y, const char *str, uint8_t size);

/**
 * Set display contrast
 * @param contrast Contrast value (0-255)
 */
void ssd1306_set_contrast(uint8_t contrast);

/**
 * Invert display colors
 * @param invert true to invert, false for normal
 */
void ssd1306_invert(bool invert);

/**
 * Power on/off the display
 * @param on true to turn on, false to turn off
 */
void ssd1306_power(bool on);

#endif // SSD1306_H
