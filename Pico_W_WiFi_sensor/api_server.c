#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"

#include "lwip/pbuf.h"
#include "lwip/tcp.h"
#include "lwip/ip4_addr.h"
#include "lwip/netif.h"

#include "api_server.h"
#include "flash_program.h"
#include "mqtt_client.h"
#include "http_server.h" // restart_requested

// Exposed from main.c
extern float g_temperature;
extern float g_humidity;
extern bool g_sensor_valid;

#define API_PORT 8080
#define API_MAX_CLIENTS 1

#define RECV_BUF_SIZE 2048
#define SEND_BUF_SIZE 2048

typedef struct api_conn_state {
    struct tcp_pcb *pcb;
    char recv_buf[RECV_BUF_SIZE];
    uint16_t recv_len;

    char send_buf[SEND_BUF_SIZE];
    uint16_t send_len;
    uint16_t send_sent;

    bool close_after_send;
} api_conn_state_t;

static struct tcp_pcb *g_api_listen_pcb = NULL;
static config *g_cfg = NULL;

static const char *skip_ws(const char *p) {
    while (p && (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')) {
        p++;
    }
    return p;
}

static const char *find_header_end(const char *buf) {
    return strstr(buf, "\r\n\r\n");
}

static bool header_get_content_length(const char *headers, int *out_len) {
    const char *p = headers;
    while ((p = strstr(p, "Content-Length:")) != NULL) {
        p += strlen("Content-Length:");
        p = skip_ws(p);
        int val = atoi(p);
        if (val >= 0) {
            *out_len = val;
            return true;
        }
    }
    return false;
}

static void ip4_to_str(const ip4_addr_t *ip, char *out, size_t out_sz) {
    if (!ip || !out || out_sz == 0) {
        return;
    }
    // Use re-entrant form if available.
#ifdef ip4addr_ntoa_r
    ip4addr_ntoa_r(ip, out, out_sz);
#else
    const char *tmp = ip4addr_ntoa(ip);
    strncpy(out, tmp ? tmp : "0.0.0.0", out_sz);
    out[out_sz - 1] = '\0';
#endif
}

static bool parse_json_bool(const char *json, const char *key, bool *out_val) {
    const char *p = strstr(json, key);
    if (!p) return false;
    p = strchr(p, ':');
    if (!p) return false;
    p++;
    p = skip_ws(p);
    if (strncmp(p, "true", 4) == 0) {
        *out_val = true;
        return true;
    }
    if (strncmp(p, "false", 5) == 0) {
        *out_val = false;
        return true;
    }
    if (*p == '0' || *p == '1') {
        *out_val = (*p == '1');
        return true;
    }
    return false;
}

static bool parse_json_string(const char *json, const char *key, char *out, size_t out_sz) {
    const char *p = strstr(json, key);
    if (!p) return false;
    p = strchr(p, ':');
    if (!p) return false;
    p++;
    p = skip_ws(p);
    if (*p != '"') return false;
    p++;

    size_t i = 0;
    while (*p && *p != '"' && i + 1 < out_sz) {
        // Minimal escape handling: copy everything until next quote.
        out[i++] = *p++;
    }
    out[i] = '\0';
    return (*p == '"');
}

static bool parse_ipv4_string(const char *s, ip4_addr_t *out_ip) {
    if (!s || !out_ip) return false;
    int a, b, c, d;
    if (sscanf(s, "%d.%d.%d.%d", &a, &b, &c, &d) != 4) return false;
    if (a < 0 || a > 255 || b < 0 || b > 255 || c < 0 || c > 255 || d < 0 || d > 255) return false;
    if (a == 0 && b == 0 && c == 0 && d == 0) return false;
    IP4_ADDR(out_ip, (uint8_t)a, (uint8_t)b, (uint8_t)c, (uint8_t)d);
    return true;
}

static void api_build_headers(char *dst, size_t dst_sz, int status_code, const char *status_text,
                              const char *content_type, size_t content_len) {
    snprintf(dst, dst_sz,
             "HTTP/1.1 %d %s\r\n"
             "Content-Type: %s\r\n"
             "Content-Length: %u\r\n"
             "Connection: close\r\n"
             "Access-Control-Allow-Origin: *\r\n"
             "Access-Control-Allow-Methods: GET,POST,OPTIONS\r\n"
             "Access-Control-Allow-Headers: Content-Type\r\n"
             "\r\n",
             status_code, status_text,
             content_type,
             (unsigned)content_len);
}

static void api_send_response(api_conn_state_t *st, int status, const char *status_text,
                              const char *content_type, const char *body) {
    if (!st || !st->pcb) return;

    const char *resp_body = body ? body : "";
    size_t body_len = strlen(resp_body);

    char header[512];
    api_build_headers(header, sizeof(header), status, status_text, content_type, body_len);

    size_t header_len = strlen(header);
    if (header_len + body_len >= sizeof(st->send_buf)) {
        // Fallback small error
        const char *small = "{\"ok\":false,\"error\":\"response too large\"}";
        api_build_headers(header, sizeof(header), 500, "Internal Server Error", "application/json", strlen(small));
        header_len = strlen(header);
        body_len = strlen(small);
        snprintf(st->send_buf, sizeof(st->send_buf), "%s%s", header, small);
        st->send_len = (uint16_t)(header_len + body_len);
    } else {
        memcpy(st->send_buf, header, header_len);
        memcpy(st->send_buf + header_len, resp_body, body_len);
        st->send_len = (uint16_t)(header_len + body_len);
    }

    st->send_sent = 0;
    st->close_after_send = true;

    err_t err = tcp_write(st->pcb, st->send_buf, st->send_len, TCP_WRITE_FLAG_COPY);
    if (err == ERR_OK) {
        tcp_output(st->pcb);
    } else {
        // If we can't write, close.
        tcp_close(st->pcb);
        st->pcb = NULL;
    }
}

static void api_send_no_content(api_conn_state_t *st) {
    if (!st || !st->pcb) return;

    const char *resp =
        "HTTP/1.1 204 No Content\r\n"
        "Content-Length: 0\r\n"
        "Connection: close\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "Access-Control-Allow-Methods: GET,POST,OPTIONS\r\n"
        "Access-Control-Allow-Headers: Content-Type\r\n"
        "\r\n";

    st->send_len = (uint16_t)strlen(resp);
    st->send_sent = 0;
    st->close_after_send = true;

    err_t err = tcp_write(st->pcb, resp, st->send_len, TCP_WRITE_FLAG_COPY);
    if (err == ERR_OK) {
        tcp_output(st->pcb);
    } else {
        tcp_close(st->pcb);
        st->pcb = NULL;
    }
}

static void api_handle_get_data(api_conn_state_t *st) {
    char ip_str[16];
    ip4_to_str(netif_ip4_addr(netif_default), ip_str, sizeof(ip_str));

    mqtt_state_t s = mqtt_get_state();
    const char *state_str =
        (s == MQTT_STATE_CONNECTED) ? "connected" :
        (s == MQTT_STATE_CONNECTING) ? "connecting" :
        (s == MQTT_STATE_ERROR) ? "error" :
        "disconnected";

    uint32_t uptime = to_ms_since_boot(get_absolute_time());

    char body[512];
    if (g_sensor_valid) {
        snprintf(body, sizeof(body),
                 "{"
                 "\"uptime_ms\":%lu,"
                 "\"sensor\":{\"temperature_c\":%.1f,\"humidity_percent\":%.1f,\"valid\":true},"
                 "\"wifi\":{\"ip\":\"%s\"},"
                 "\"mqtt\":{\"enabled\":%s,\"connected\":%s,\"state\":\"%s\"}"
                 "}",
                 (unsigned long)uptime,
                 g_temperature,
                 g_humidity,
                 ip_str,
                 (g_cfg && g_cfg->mqtt_enabled) ? "true" : "false",
                 mqtt_is_connected() ? "true" : "false",
                 state_str);
    } else {
        snprintf(body, sizeof(body),
                 "{"
                 "\"uptime_ms\":%lu,"
                 "\"sensor\":{\"temperature_c\":null,\"humidity_percent\":null,\"valid\":false},"
                 "\"wifi\":{\"ip\":\"%s\"},"
                 "\"mqtt\":{\"enabled\":%s,\"connected\":%s,\"state\":\"%s\"}"
                 "}",
                 (unsigned long)uptime,
                 ip_str,
                 (g_cfg && g_cfg->mqtt_enabled) ? "true" : "false",
                 mqtt_is_connected() ? "true" : "false",
                 state_str);
    }
    api_send_response(st, 200, "OK", "application/json", body);
}

static void api_handle_get_config(api_conn_state_t *st) {
    if (!g_cfg) {
        api_send_response(st, 500, "Internal Server Error", "application/json",
                          "{\"ok\":false,\"error\":\"config not available\"}");
        return;
    }

    char broker[16];
    ip4_to_str(&g_cfg->mqtt_broker_ip, broker, sizeof(broker));

    char body[512];
    snprintf(body, sizeof(body),
             "{"
             "\"mqtt\":{"
             "\"enabled\":%s,"
             "\"broker_ip\":\"%s\","
             "\"topic\":\"%s\""
             "}"
             "}",
             g_cfg->mqtt_enabled ? "true" : "false",
             broker,
             g_cfg->mqtt_topic);

    api_send_response(st, 200, "OK", "application/json", body);
}

static void api_handle_post_config(api_conn_state_t *st, const char *body, int body_len) {
    if (!g_cfg) {
        api_send_response(st, 500, "Internal Server Error", "application/json",
                          "{\"ok\":false,\"error\":\"config not available\"}");
        return;
    }

    if (!body || body_len <= 0) {
        api_send_response(st, 400, "Bad Request", "application/json",
                          "{\"ok\":false,\"error\":\"empty body\"}");
        return;
    }

    // Ensure body is null-terminated for string searches.
    char json[512];
    size_t copy_len = (size_t)body_len;
    if (copy_len >= sizeof(json)) copy_len = sizeof(json) - 1;
    memcpy(json, body, copy_len);
    json[copy_len] = '\0';

    bool enabled;
    char broker_ip_str[32] = {0};
    char topic[MQTT_TOPIC_MAX_LEN + 1] = {0};

    bool has_enabled = parse_json_bool(json, "\"enabled\"", &enabled);
    bool has_broker = parse_json_string(json, "\"broker_ip\"", broker_ip_str, sizeof(broker_ip_str));
    bool has_topic = parse_json_string(json, "\"topic\"", topic, sizeof(topic));

    if (!has_enabled && !has_broker && !has_topic) {
        api_send_response(st, 400, "Bad Request", "application/json",
                          "{\"ok\":false,\"error\":\"no supported fields\"}");
        return;
    }

    config new_cfg = *g_cfg;

    if (has_enabled) {
        new_cfg.mqtt_enabled = enabled ? 1 : 0;
    }

    if (has_broker) {
        ip4_addr_t ip;
        if (!parse_ipv4_string(broker_ip_str, &ip)) {
            api_send_response(st, 400, "Bad Request", "application/json",
                              "{\"ok\":false,\"error\":\"invalid broker_ip\"}");
            return;
        }
        new_cfg.mqtt_broker_ip = ip;
    }

    if (has_topic) {
        size_t tlen = strlen(topic);
        if (tlen == 0 || tlen > MQTT_TOPIC_MAX_LEN) {
            api_send_response(st, 400, "Bad Request", "application/json",
                              "{\"ok\":false,\"error\":\"invalid topic\"}");
            return;
        }
        strncpy(new_cfg.mqtt_topic, topic, MQTT_TOPIC_MAX_LEN);
        new_cfg.mqtt_topic[MQTT_TOPIC_MAX_LEN] = '\0';
    }

    new_cfg.magic = MAGIC;

    // Persist and request restart.
    flash_write_page((uint8_t *)&new_cfg, sizeof(config), WIFI_CONFIG_PAGE);
    *g_cfg = new_cfg;

    restart_requested = true;

    api_send_response(st, 200, "OK", "application/json",
                      "{\"ok\":true,\"rebooting\":true}");
}

static err_t api_conn_sent(void *arg, struct tcp_pcb *tpcb, u16_t len) {
    api_conn_state_t *st = (api_conn_state_t *)arg;
    if (!st) return ERR_OK;

    st->send_sent += len;
    if (st->close_after_send && st->send_sent >= st->send_len) {
        tcp_arg(tpcb, NULL);
        tcp_sent(tpcb, NULL);
        tcp_recv(tpcb, NULL);
        tcp_err(tpcb, NULL);
        tcp_close(tpcb);
        st->pcb = NULL;
        free(st);
    }

    return ERR_OK;
}

static void api_conn_err(void *arg, err_t err) {
    (void)err;
    api_conn_state_t *st = (api_conn_state_t *)arg;
    if (st) {
        free(st);
    }
}

static void api_dispatch_request(api_conn_state_t *st) {
    st->recv_buf[st->recv_len] = '\0';

    const char *header_end = find_header_end(st->recv_buf);
    if (!header_end) {
        return;
    }

    int header_len = (int)(header_end - st->recv_buf) + 4;

    // Parse request line
    char method[8] = {0};
    char path[64] = {0};
    if (sscanf(st->recv_buf, "%7s %63s", method, path) != 2) {
        api_send_response(st, 400, "Bad Request", "application/json",
                          "{\"ok\":false,\"error\":\"bad request line\"}");
        return;
    }

    // OPTIONS for CORS preflight
    if (strcmp(method, "OPTIONS") == 0) {
        api_send_no_content(st);
        return;
    }

    // GET routes
    if (strcmp(method, "GET") == 0) {
        if (strcmp(path, "/api/data") == 0) {
            api_handle_get_data(st);
            return;
        }
        if (strcmp(path, "/api/config") == 0) {
            api_handle_get_config(st);
            return;
        }

        api_send_response(st, 404, "Not Found", "application/json",
                          "{\"ok\":false,\"error\":\"not found\"}");
        return;
    }

    // POST routes
    if (strcmp(method, "POST") == 0) {
        int content_len = 0;
        const char *headers = st->recv_buf;
        (void)headers;
        bool has_cl = header_get_content_length(st->recv_buf, &content_len);
        if (!has_cl) {
            api_send_response(st, 411, "Length Required", "application/json",
                              "{\"ok\":false,\"error\":\"Content-Length required\"}");
            return;
        }

        int total_needed = header_len + content_len;
        if (st->recv_len < total_needed) {
            // Wait for full body
            return;
        }

        const char *body = st->recv_buf + header_len;

        if (strcmp(path, "/api/config") == 0) {
            api_handle_post_config(st, body, content_len);
            return;
        }

        api_send_response(st, 404, "Not Found", "application/json",
                          "{\"ok\":false,\"error\":\"not found\"}");
        return;
    }

    api_send_response(st, 405, "Method Not Allowed", "application/json",
                      "{\"ok\":false,\"error\":\"method not allowed\"}");
}

static err_t api_conn_recv(void *arg, struct tcp_pcb *tpcb, struct pbuf *p, err_t err) {
    api_conn_state_t *st = (api_conn_state_t *)arg;

    if (!p) {
        // Client closed.
        if (tpcb) {
            tcp_close(tpcb);
        }
        if (st) {
            free(st);
        }
        return ERR_OK;
    }

    if (err != ERR_OK) {
        pbuf_free(p);
        return err;
    }

    cyw43_arch_lwip_check();

    if (p->tot_len > 0) {
        uint16_t space = (uint16_t)(sizeof(st->recv_buf) - 1 - st->recv_len);
        uint16_t to_copy = p->tot_len > space ? space : (uint16_t)p->tot_len;
        if (to_copy > 0) {
            st->recv_len += pbuf_copy_partial(p, st->recv_buf + st->recv_len, to_copy, 0);
        }
        tcp_recved(tpcb, p->tot_len);
    }

    pbuf_free(p);

    api_dispatch_request(st);
    return ERR_OK;
}

static err_t api_accept(void *arg, struct tcp_pcb *newpcb, err_t err) {
    (void)arg;

    if (err != ERR_OK || !newpcb) {
        return ERR_VAL;
    }

    api_conn_state_t *st = (api_conn_state_t *)calloc(1, sizeof(api_conn_state_t));
    if (!st) {
        tcp_close(newpcb);
        return ERR_MEM;
    }

    st->pcb = newpcb;
    st->recv_len = 0;

    tcp_arg(newpcb, st);
    tcp_recv(newpcb, api_conn_recv);
    tcp_sent(newpcb, api_conn_sent);
    tcp_err(newpcb, api_conn_err);

    return ERR_OK;
}

static bool api_open_listener(void) {
    if (g_api_listen_pcb) {
        return true;
    }

    struct tcp_pcb *pcb = tcp_new_ip_type(IPADDR_TYPE_ANY);
    if (!pcb) {
        return false;
    }

    err_t err = tcp_bind(pcb, NULL, API_PORT);
    if (err != ERR_OK) {
        tcp_close(pcb);
        return false;
    }

    g_api_listen_pcb = tcp_listen_with_backlog(pcb, API_MAX_CLIENTS);
    if (!g_api_listen_pcb) {
        tcp_close(pcb);
        return false;
    }

    tcp_accept(g_api_listen_pcb, api_accept);
    return true;
}

void api_server_start(config *cfg) {
    g_cfg = cfg;

    cyw43_arch_lwip_begin();
    bool ok = api_open_listener();
    cyw43_arch_lwip_end();

    if (ok) {
        char ip_str[16];
        ip4_to_str(netif_ip4_addr(netif_default), ip_str, sizeof(ip_str));
        printf("API server listening on http://%s:%d\n", ip_str, API_PORT);
    } else {
        printf("ERROR: Failed to start API server on port %d\n", API_PORT);
    }
}
