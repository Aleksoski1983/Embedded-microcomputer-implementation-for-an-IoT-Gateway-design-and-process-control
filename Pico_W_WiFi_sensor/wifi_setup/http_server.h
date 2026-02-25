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

#ifndef __HTTP_SERVER_H__
#define __HTTP_SERVER_H__

void ssi_init();
u16_t __time_critical_func(ssi_handler)(int iIndex, char *pcInsert, int iInsertLen);
void encode_value(char *src, char *dest);

// Global sensor data for web display
extern float g_temperature;
extern float g_humidity;
extern bool g_sensor_valid;

// Restart control
extern bool restart_requested;

void cgi_init(void);
void reconfig_cgi_init(void);
const char *cgi_handler(int iIndex, int iNumParams, char *pcParam[], char *pcValue[]);
void url_decode(char *src, char *dest);

#endif // __HTTP_SERVER_H__
