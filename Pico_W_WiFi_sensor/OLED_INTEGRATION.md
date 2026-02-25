# OLED Display Integration Guide

## Overview
This project has been upgraded with an SSD1306 128x64 OLED display (I2C) to show device status, IP address, mode, network, and device information.

## Hardware Connection

### OLED Display Pinout
Connect your SSD1306 OLED display to the Pico W as follows:

| OLED Pin | Pico W Pin | GPIO |
|----------|------------|------|
| VCC      | 3.3V (Pin 36) | - |
| GND      | GND (any ground pin) | - |
| SDA      | GP0 (Pin 1) | GPIO 0 |
| SCL      | GP1 (Pin 2) | GPIO 1 |

**Important Notes:**
- Use 3.3V power (NOT 5V) for the OLED display
- GPIO 0 and GPIO 1 are now dedicated to the OLED display
- The display uses I2C0 interface at 400kHz

## Files Added

### 1. ssd1306.h
Header file containing:
- Display dimensions and I2C address definitions
- SSD1306 command constants
- Function prototypes for display control

### 2. ssd1306.c
Implementation file containing:
- I2C communication functions
- Display initialization
- Graphics primitives (pixels, lines, rectangles)
- Text rendering with 5x8 font
- Display buffer management

## Files Modified

### 1. CMakeLists.txt
**Changes:**
- Added `ssd1306.c` to executable sources
- Added `hardware_i2c` to target link libraries

### 2. main.c
**Changes:**
- Added include for `hardware/i2c.h` and `ssd1306.h`
- Added OLED pin definitions (GPIO 0 and 1)
- Added `update_oled_display()` function to refresh display
- Modified `main()` to initialize OLED before WiFi
- Added display updates for different modes:
  - Starting/Initialization
  - Config Mode (shows "192.168.0.1")
  - Connecting to WiFi
  - Connected (shows SSID and IP address)
  - Error states

## Display Information

The OLED shows the following information:

### Header Section
- Device name: "Pico W WiFi Sensor"
- Inverted (black text on white background)

### Main Content
1. **Line 1:** Status/Mode information
2. **Line 2:** Network SSID or connection status  
3. **Line 3:** IP address information
4. **Line 4:** Device identifier
5. **Line 5:** Additional status information
6. **Line 6:** Footer or secondary information

### Footer
- Decorative elements or status indicators

## Display States

### 1. Startup
```
Pico W WiFi Sensor
Mode: Starting
Net:  Initializing...
IP:   ---
Dev:  Pico W
Status: Ready
```

### 2. Configuration Mode
```
Pico W WiFi Sensor
Mode: Config Mode
Net:  Setup AP
IP:   192.168.0.1
Dev:  Pico W
Status: Waiting
```

### 3. Connecting
```
Pico W WiFi Sensor
Mode: Run Mode
Net:  Connecting...
IP:   ---
Dev:  Pico W
Status: Scanning
```

### 4. Connected
```
Pico W WiFi Sensor
Mode: Connected
Net:  YourWiFiName
IP:   192.168.1.100
Dev:  Pico W
Status: Online
```

### 5. Error State
```
Pico W WiFi Sensor
Mode: ERROR
Net:  WiFi Failed
IP:   Check Config
Dev:  Pico W
Status: Failed
```

## Building the Project

1. **Clean previous build** (if needed):
```powershell
Remove-Item -Recurse -Force build
mkdir build
cd build
```

2. **Configure CMake:**
```powershell
cmake -G Ninja ..
```

3. **Compile:**
```powershell
ninja
```

Or use VS Code task: **Terminal → Run Task → Compile Project**

## Troubleshooting

### OLED Display Not Working

**Problem:** Display remains blank or shows garbage
**Solutions:**
- Verify I2C address (0x3C is default, some use 0x3D)
  - If using 0x3D, change `SSD1306_I2C_ADDR` in `ssd1306.h`
- Check wiring:
  - SDA to GPIO 0 (Pin 1)
  - SCL to GPIO 1 (Pin 2)
  - VCC to 3.3V (NOT 5V)
  - GND to any ground pin
- Ensure OLED is powered correctly (3.3V)
- Try adding small delays after initialization

### I2C Communication Errors

**Problem:** I2C timeout or communication failure
**Solutions:**
- Check for loose connections
- Verify pull-up resistors (built-in enabled in code)
- Try reducing I2C speed (change 400kHz to 100kHz in `ssd1306_init`)
- Use a multimeter to check voltage levels

### Compilation Errors

**Problem:** Missing includes or undefined references
**Solutions:**
- Ensure all files are saved
- Clean and rebuild the project
- Verify CMakeLists.txt changes were applied
- Check that Pico SDK is properly installed

### Display Shows Partial Information

**Problem:** Text is cut off or overlapping
**Solutions:**
- Network names longer than 18 characters are automatically truncated
- Adjust text positions in `update_oled_display()` function
- Use smaller font size (size 1 instead of 2)

## API Reference

### Display Initialization
```c
bool ssd1306_init(void *i2c, uint8_t sda_pin, uint8_t scl_pin);
```
Initialize the display with specified I2C instance and pins.

### Basic Operations
```c
void ssd1306_clear(void);                    // Clear display buffer
void ssd1306_show(void);                     // Update display with buffer
void ssd1306_power(bool on);                 // Power on/off
void ssd1306_invert(bool invert);            // Invert colors
void ssd1306_set_contrast(uint8_t contrast); // Set contrast (0-255)
```

### Graphics Functions
```c
void ssd1306_draw_pixel(int x, int y, uint8_t color);
void ssd1306_draw_line(int x0, int y0, int x1, int y1, uint8_t color);
void ssd1306_draw_rect(int x, int y, int width, int height, uint8_t color, bool filled);
void ssd1306_draw_char(int x, int y, char c, uint8_t size);
void ssd1306_draw_string(int x, int y, const char *str, uint8_t size);
```

### Custom Display Updates
To create custom display layouts, modify the `update_oled_display()` function in `main.c`:

```c
void update_oled_display(const char *mode, const char *network, 
                        const char *ip_addr, const char *device_name) {
    ssd1306_clear();
    
    // Your custom layout here
    ssd1306_draw_string(0, 0, "Custom Text", 1);
    
    ssd1306_show();
}
```

## Future Enhancements

Possible improvements:
- Add signal strength indicator
- Display connection uptime
- Show sensor data (if sensors added)
- Add scrolling text for long network names
- Display QR code for easy WiFi configuration
- Add graphical indicators (WiFi icon, battery level, etc.)
- Implement screen saver mode

## Notes

- The display refresh is only called at key state changes to minimize CPU usage
- Display buffer uses ~1KB of RAM (128x64/8 = 1024 bytes)
- I2C operates at 400kHz for faster updates
- Font is 5x8 pixels per character with 1 pixel spacing
- Display supports two font sizes: 1x (5x8) and 2x (10x16)

## License
Same license as the main project (BSD-3-Clause)
