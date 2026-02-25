#ifndef API_SERVER_H
#define API_SERVER_H

#include "access_point.h"

// Starts a minimal HTTP JSON API server on port 8080.
// Intended to run alongside lwIP httpd (static UI on port 80).
void api_server_start(config *cfg);

#endif // API_SERVER_H
