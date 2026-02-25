/**
 * This file is part of "Wi-Fi Configure.
 *
 * This software eliminates the need to know the network name, password and,
 * if required, IP address, network mask and default gateway at compile time.
 * These can be set directly on the Pico-W and also changed afterwards.
 *
 * Copyright (c) 2024 Gerhard Schiller gerhard.schiller@pm.me
 *
 * SPDX-License-Identifier: BSD-3-Clause
 */


#include "lwip/apps/httpd.h"
#include "http_server.h"
#include "pico/cyw43_arch.h"
#include "access_point.h"
#include "flash_program.h"
#include "hardware/watchdog.h"
#include "mqtt_client.h"

/*
 * This file contains the code for SSI and CGI handling.
 *
 * Server Side Includes (SSI):
 * The tags (enclosed in "<!--" and "-->") embedded in web pages are
 * replaced by the server with dynamic text before the document is
 * delivered to the client. See ssi_handler().
 *
 * The Common Gateway Interface (CGI) allows a web server to delegate the
 * execution of a request.
 * This is exploited here by redirecting a call for a non-existent page to a
 * routine. See cgi_handler()
 */

extern config *_c;

// External sensor data from main.c
extern float g_temperature;
extern float g_humidity;
extern bool g_sensor_valid;

const char * __not_in_flash("httpd") ssi_tags[] = {
    "SSID",    // 0
    "PASSWD",  // 1
    "B0",      // 2
    "B1",      // 3
    "B2",      // 4
    "B3",      // 5
    "B4",      // 6
    "B5",      // 7
    "B6",      // 8
    "B7",      // 9
    "B8",      // 10
    "B9",      // 11
    "B10",     // 12
    "B11",     // 13
    "MQTTEN",  // 14
    "M0",      // 15
    "M1",      // 16
    "M2",      // 17
    "M3",      // 18
    "MQTTTOPIC", // 19
    "ssid",      // 20 - Display SSID value
    "ipaddr",    // 21 - Display IP address
    "temp",      // 22 - Display temperature
    "humidity",  // 23 - Display humidity
    "mqtten",    // 24 - Display MQTT enabled status
    "mqttbroker",// 25 - Display MQTT broker IP
    "mqtttopic", // 26 - Display MQTT topic
    "mqttstatus",// 27 - Display MQTT connection status
};

// Restart control
bool restart_requested = false;

#define HIGHLIGHT "STYLE=\"background-color: #72A4D2;\""
static uint8_t  lan[3][4];
bool _need_ip;
bool _need_gw;

static bool ip_err = false;
static bool mask_err = false;
static bool gw_err = false;

/*
 * ssi_init()
 *
 * Check ssi-tags for length and inizialize the ssi handler
 */

void ssi_init()
{
    size_t i;
    for (i = 0; i < LWIP_ARRAYSIZE(ssi_tags); i++) {
        LWIP_ASSERT("tag too long for LWIP_HTTPD_MAX_TAG_NAME_LEN",
                    strlen(ssi_tags[i]) <= LWIP_HTTPD_MAX_TAG_NAME_LEN);
    }

    http_set_ssi_handler(ssi_handler, ssi_tags, LWIP_ARRAYSIZE(ssi_tags));
}

/*
 * ssi_handler()
 *
 * SSI is triggered by the file extension ".shtml"
 */

u16_t __time_critical_func(ssi_handler)(int iIndex, char *pcInsert, int iInsertLen)
{
    // SSID and password may contain quotation marks which must be
    // converted to "&quote;" for the web site.
    // So we make the buffer twice the maximum size.
    // (and hope a full-length password doesn't contain
    // more than nine quotation marks)
    // static char webStr[PASSWD_MAX_LEN * 2];
    char webStr[PASSWD_MAX_LEN * 2];

    size_t printed = 0;
    switch (iIndex) {
        case 0: /* "SSID" */
            if(*(_c->ssid) != '\0'){
                encode_value(_c->ssid, webStr);
                printed = snprintf(pcInsert, iInsertLen, "%s", webStr);
            }
            break;
        case 1: /* "password" */
            if(*(_c->passwd) != '\0'){
                encode_value(_c->passwd, webStr);
                printed = snprintf(pcInsert, iInsertLen, "%s", webStr);
            }
        break;

        case 2: /* "static ip address a */
        case 3: /* "static ip address b */
        case 4: /* "static ip address c */
        case 5: /* "static ip address d */
            if(_c->ip.addr != IPADDR_NONE){
                printed = snprintf(pcInsert, iInsertLen, "%d",
                                   ip4_addr_get_byte(&(_c->ip), iIndex - 2));
            }
        break;

        case 6: /* "net mask address a */
        case 7: /* "net mask address b */
        case 8: /* "net mask address c */
        case 9: /* "net mask address d */
            if(_c->mask.addr != IPADDR_NONE){
                printed = snprintf(pcInsert, iInsertLen, "%d",
                                   ip4_addr_get_byte(&(_c->mask), iIndex - 6));
            }
            break;

        case 10: /* "def gateway address a */
        case 11: /* "def gateway address b */
        case 12: /* "def gateway address c */
        case 13: /* "def gateway address d */
            if(_c->gw.addr != IPADDR_NONE){
                printed = snprintf(pcInsert, iInsertLen, "%d",
                                   ip4_addr_get_byte(&(_c->gw), iIndex - 10));
            }
            break;

        case 14: /* "mqtt_enabled" */
            if(_c->mqtt_enabled){
                printed = snprintf(pcInsert, iInsertLen, "checked");
            }
            break;

        case 15: /* "MQTT broker IP address a */
        case 16: /* "MQTT broker IP address b */
        case 17: /* "MQTT broker IP address c */
        case 18: /* "MQTT broker IP address d */
            if(_c->mqtt_broker_ip.addr != IPADDR_NONE){
                printed = snprintf(pcInsert, iInsertLen, "%d",
                                   ip4_addr_get_byte(&(_c->mqtt_broker_ip), iIndex - 15));
            }
            break;

        case 19: /* "mqtt_topic" */
            if(*(_c->mqtt_topic) != '\0'){
                encode_value(_c->mqtt_topic, webStr);
                printed = snprintf(pcInsert, iInsertLen, "%s", webStr);
            }
            break;

        case 20: /* "ssid" - Display SSID value */
            printed = snprintf(pcInsert, iInsertLen, "%s", _c->ssid);
            break;

        case 21: /* "ipaddr" - Display IP address */
            printed = snprintf(pcInsert, iInsertLen, "%s", ip4addr_ntoa(netif_ip4_addr(netif_default)));
            break;

        case 22: /* "temp" - Display temperature */
            if (g_sensor_valid) {
                printed = snprintf(pcInsert, iInsertLen, "%.1f°C", g_temperature);
            } else {
                printed = snprintf(pcInsert, iInsertLen, "--");
            }
            break;

        case 23: /* "humidity" - Display humidity */
            if (g_sensor_valid) {
                printed = snprintf(pcInsert, iInsertLen, "%.1f%%", g_humidity);
            } else {
                printed = snprintf(pcInsert, iInsertLen, "--");
            }
            break;

        case 24: /* "mqtten" - Display MQTT enabled status */
            printed = snprintf(pcInsert, iInsertLen, "%s", _c->mqtt_enabled ? "Yes" : "No");
            break;

        case 25: /* "mqttbroker" - Display MQTT broker IP */
            if (_c->mqtt_broker_ip.addr != IPADDR_NONE) {
                printed = snprintf(pcInsert, iInsertLen, "%s", ip4addr_ntoa(&(_c->mqtt_broker_ip)));
            } else {
                printed = snprintf(pcInsert, iInsertLen, "Not configured");
            }
            break;

        case 26: /* "mqtttopic" - Display MQTT topic */
            if(*(_c->mqtt_topic) != '\0'){
                printed = snprintf(pcInsert, iInsertLen, "%s", _c->mqtt_topic);
            } else {
                printed = snprintf(pcInsert, iInsertLen, "Not configured");
            }
            break;

        case 27: /* "mqttstatus" - Display MQTT connection status */
            if (!_c->mqtt_enabled) {
                printed = snprintf(pcInsert, iInsertLen, "<span class=\"status-badge status-offline\">Disabled</span>");
            } else {
                printed = snprintf(pcInsert, iInsertLen,
                                   mqtt_is_connected()
                                       ? "<span class=\"status-badge status-online\">Connected</span>"
                                       : "<span class=\"status-badge status-offline\">Disconnected</span>");
            }
            break;
    }
    LWIP_ASSERT("sane length", printed <= 0xFFFF);
    return (u16_t)printed;
}

/*
 * encode_value()
 *
 * SSID and password may contain quotation marks which must be
 * converted to "&quote;" for the web site.
 */

void encode_value(char *src, char *dest)
{
    while(*src){
        if(*src == '"'){
            *dest++ = '&';
            *dest++ = 'q';
            *dest++ = 'u';
            *dest++ = 'o';
            *dest++ = 't';
            *dest++ = ';';
            src++;
        }
        else{
            *dest++ = *src++;
        }
    }
    *dest = '\0';
}

/* Html request for "/setup.cgi" will start cgi_handler_setup */
static const tCGI cgi_handlers[] = {
    {"/setup.cgi", cgi_handler},
};

/* CGI handler for run mode reconfiguration */
static const tCGI reconfig_cgi_handlers[] = {
    {"/reconfig.cgi", cgi_handler},
};

/*
 * cgi_init()
 *
 * initialize the CGI handler
 */

void
cgi_init(void)
{
    http_set_cgi_handlers(cgi_handlers, 1);
}

/*
 * reconfig_cgi_init()
 *
 * Initialize the CGI handler for run mode reconfiguration
 */

void
reconfig_cgi_init(void)
{
    http_set_cgi_handlers(reconfig_cgi_handlers, 1);
}

/*
 * cgi_handler()
 *
 * This cgi handler triggered by a request for "/setup.cgi"
 */

const char *
cgi_handler(int iIndex, int iNumParams, char *pcParam[], char *pcValue[])
{
    memset(lan, 0, sizeof(lan));
    ip_err   = false;
    mask_err = false;
    gw_err   = false;
    
    // MQTT variables
    uint8_t mqtt_ip[4] = {0};
    bool mqtt_enabled = false;
    bool mqtt_ip_found[4] = {false}; // Track which IP bytes were found

    bool any_lan_param = false;
    bool any_mqtt_param = false;

    DEBUG_printf("\n=== CGI Handler Called ===\n");
    DEBUG_printf("Number of parameters: %d\n", iNumParams);
    
    for (int i = 0; i < iNumParams; i++){
        DEBUG_printf("Param[%d]: %s = %s\n", i, pcParam[i], pcValue[i]);
        
        if(strcmp(pcParam[i], "ssid") == 0){
            url_decode(pcValue[i], _c->ssid);
            DEBUG_printf("  -> Decoded SSID: %s\n", _c->ssid);
        }
        else if(strcmp(pcParam[i], "passwd") == 0){
            url_decode(pcValue[i], _c->passwd);
            DEBUG_printf("  -> Decoded password: %s\n", _c->passwd);
        }
        else if(strcmp(pcParam[i], "mqtt_enabled") == 0){
            mqtt_enabled = true;
            any_mqtt_param = true;
            DEBUG_printf("  -> MQTT enabled checkbox checked\n");
        }
        else if(strcmp(pcParam[i], "mqtt_topic") == 0){
            any_mqtt_param = true;
            // Clear topic only if a topic was provided/attempted.
            memset(_c->mqtt_topic, 0, sizeof(_c->mqtt_topic));
            url_decode(pcValue[i], _c->mqtt_topic);
            DEBUG_printf("  -> Decoded MQTT topic: %s\n", _c->mqtt_topic);
        }
        else if(pcParam[i][0] == 'M'){
            // MQTT broker IP address (M0, M1, M2, M3)
            any_mqtt_param = true;
            uint8_t index = atoi(&(pcParam[i][1]));
            int val = atoi(pcValue[i]);
            DEBUG_printf("  -> MQTT IP byte M%d = %d\n", index, val);
            if(index >= 0 && index <= 3){
                if(val >= 0 && val <= 255){
                    mqtt_ip[index] = val;
                    mqtt_ip_found[index] = true;
                } else {
                    DEBUG_printf("  -> Invalid IP byte value: %d\n", val);
                }
            } else {
                DEBUG_printf("  -> Invalid IP byte index: %d\n", index);
            }
        }
        else if(pcParam[i][0] == 'B'){
            any_lan_param = true;
            uint8_t index = atoi(&(pcParam[i][1]));
            int val = atoi(pcValue[i]);
            switch(index){
                case 0:
                case 1:
                case 2:
                case 3: // IP address
                    if(pcValue[i][0] == '\0' && _need_ip)
                        ip_err = true;
                    else if(val < 0 || val > 255)
                        ip_err = true;
                    else
                        lan[index/4][index%4] = val;
                    break;

                case 4:
                case 5:
                case 6:
                case 7: // net mask
                    if(pcValue[i][0] == '\0' && _need_ip)
                        mask_err = true;
                    else if(val < 0 || val > 255)
                        mask_err = true;
                    else
                        lan[index/4][index%4] = val;
                    break;

                case 8:
                case 9:
                case 10:
                case 11: // default gateway
                    if(pcValue[i][0] == '\0' && _need_gw)
                        gw_err = true;
                    else if(val < 0 || val > 255)
                        gw_err = true;
                    else
                        lan[index/4][index%4] = val;
                    break;

            }
        }
    }

    // Only update LAN fields if any LAN parameters were present.
    // This allows a WiFi-only setup page to avoid clobbering static IP settings.
    if (any_lan_param) {
        IP4_ADDR(&(_c->ip),   lan[0][0], lan[0][1], lan[0][2], lan[0][3]);
        if(!_c->ip.addr)
            _c->ip.addr = IPADDR_NONE;

        IP4_ADDR(&(_c->mask), lan[1][0], lan[1][1], lan[1][2], lan[1][3]);
        if(!_c->mask.addr)
            _c->mask.addr = IPADDR_NONE;

        IP4_ADDR(&(_c->gw),   lan[2][0], lan[2][1], lan[2][2], lan[2][3]);
        if(!_c->gw.addr)
            _c->gw.addr = IPADDR_NONE;
    }

    // Only update MQTT config if any MQTT parameters were present.
    // This allows a WiFi-only setup page to avoid disabling MQTT.
    if (any_mqtt_param) {
        _c->mqtt_enabled = mqtt_enabled ? 1 : 0;
    }
    
    // Check if we have all MQTT IP bytes - if not, preserve existing IP
    bool mqtt_ip_complete = mqtt_ip_found[0] && mqtt_ip_found[1] && mqtt_ip_found[2] && mqtt_ip_found[3];
    if (any_mqtt_param && mqtt_ip_complete) {
        IP4_ADDR(&(_c->mqtt_broker_ip), mqtt_ip[0], mqtt_ip[1], mqtt_ip[2], mqtt_ip[3]);
        DEBUG_printf("MQTT IP set from form: %d.%d.%d.%d\n", mqtt_ip[0], mqtt_ip[1], mqtt_ip[2], mqtt_ip[3]);
    } else if (any_mqtt_param) {
        DEBUG_printf("MQTT IP incomplete - preserving existing: %s\n", ip4addr_ntoa(&(_c->mqtt_broker_ip)));
        DEBUG_printf("  Found: M0=%s, M1=%s, M2=%s, M3=%s\n",
                     mqtt_ip_found[0] ? "yes" : "no",
                     mqtt_ip_found[1] ? "yes" : "no", 
                     mqtt_ip_found[2] ? "yes" : "no",
                     mqtt_ip_found[3] ? "yes" : "no");
    }
    
    // If MQTT topic is empty, preserve existing topic
    if (any_mqtt_param && strlen(_c->mqtt_topic) == 0) {
        // Read current config from flash to get existing topic
        config temp_config;
        flash_read((uint8_t *)&temp_config, sizeof(temp_config), WIFI_CONFIG_PAGE);
        if (temp_config.magic == MAGIC && strlen(temp_config.mqtt_topic) > 0) {
            strncpy(_c->mqtt_topic, temp_config.mqtt_topic, MQTT_TOPIC_MAX_LEN);
            _c->mqtt_topic[MQTT_TOPIC_MAX_LEN] = '\0';
            DEBUG_printf("MQTT topic preserved from flash: '%s'\n", _c->mqtt_topic);
        } else {
            strcpy(_c->mqtt_topic, "DHT22");  // Default topic
            DEBUG_printf("MQTT topic set to default: 'DHT22'\n");
        }
    }

    DEBUG_printf("\n=== Processed Configuration ===\n");
    DEBUG_printf("IP %s\n", ip4addr_ntoa(&(_c->ip)));
    DEBUG_printf("NM %s\n", ip4addr_ntoa(&(_c->mask)));
    DEBUG_printf("GW %s\n", ip4addr_ntoa(&(_c->gw)));
    DEBUG_printf("MQTT Enabled: %d\n", _c->mqtt_enabled);
    DEBUG_printf("MQTT Broker: %s\n", ip4addr_ntoa(&(_c->mqtt_broker_ip)));
    DEBUG_printf("MQTT Topic: '%s' (length: %d)\n", _c->mqtt_topic, strlen(_c->mqtt_topic));
    
    if(!(ip_err || mask_err || gw_err))
        DEBUG_printf("Configure OK\n");
    else
        DEBUG_printf("Configure ERROR\n");

    if(!(ip_err || mask_err || gw_err)){
        _c->magic = MAGIC;
        isConfigured = true;
        
        DEBUG_printf("\n=== FLASH WRITE ===\n");
        DEBUG_printf("Before flash_write - MQTT Broker: %s, Topic: '%s'\n", 
                     ip4addr_ntoa(&(_c->mqtt_broker_ip)), _c->mqtt_topic);
        
        // Save configuration to flash immediately
        flash_write_page((uint8_t *)_c, sizeof(config), WIFI_CONFIG_PAGE);
        DEBUG_printf("Configuration saved to flash\n");
        
        // Set a flag for main loop to handle restart
        // This allows the HTTP response to be sent completely before restart
        restart_requested = true;
        DEBUG_printf("Restart requested - will restart after sending response\n");
        
        // Return done.html 
        return "/done.html";
    }
    else{
        // Return to appropriate config page
        return "/index.shtml";
    }
}

/*
 * url_decode()
 *
 * Chars, not allowed in an url, but contained in a get request
 * are encoded.
 * " " as "+" and all others as hex encoded ascii code.
 */

void url_decode(char *src, char *dest)
{
    while(*src){
        if(*src == '+'){
            *dest = ' ';
            src++;
            dest++;
        }
        else if(*src == '%'){
            char a[3];

            a[0] = *++src;
            a[1] = *++src;
            a[2] = '\0';
            *dest++ = strtol(a, NULL, 16);
            src++;
        }
        else{
            *dest++ = *src++;
        }
    }
    *dest = '\0';
}


