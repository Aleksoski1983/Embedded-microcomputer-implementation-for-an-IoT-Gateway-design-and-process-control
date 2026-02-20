-- PostgreSQL Initialization Script for IIoT Gateway
-- This script creates the database, user, and necessary tables

-- Connect to PostgreSQL as superuser (postgres) and run:
-- psql -U postgres -f init_postgresql.sql

-- Create database
CREATE DATABASE iiot_gateway;

-- Create user
CREATE USER iiot_user WITH ENCRYPTED PASSWORD 'your_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE iiot_gateway TO iiot_user;

-- Connect to the newly created database
\c iiot_gateway

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO iiot_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO iiot_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO iiot_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO iiot_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO iiot_user;

-- Create sensor_data table (this will also be created by the application, but we can create it here for reference)
CREATE TABLE IF NOT EXISTS sensor_data (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    measurement VARCHAR(255) NOT NULL,
    source VARCHAR(255),
    location VARCHAR(255),
    field_name VARCHAR(255) NOT NULL,
    field_value DOUBLE PRECISION,
    unit VARCHAR(50)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON sensor_data(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sensor_data_measurement ON sensor_data(measurement);
CREATE INDEX IF NOT EXISTS idx_sensor_data_source ON sensor_data(source);
CREATE INDEX IF NOT EXISTS idx_sensor_data_field_name ON sensor_data(field_name);

-- Create a composite index for common queries
CREATE INDEX IF NOT EXISTS idx_sensor_data_measurement_timestamp 
ON sensor_data(measurement, timestamp DESC);

-- Optional: Create a hypertable for TimescaleDB if you want to use it
-- First install TimescaleDB extension: CREATE EXTENSION IF NOT EXISTS timescaledb;
-- Then convert the table to a hypertable:
-- SELECT create_hypertable('sensor_data', 'timestamp', if_not_exists => TRUE);

COMMENT ON TABLE sensor_data IS 'Time-series sensor data from MQTT and OPC UA sources';
COMMENT ON COLUMN sensor_data.timestamp IS 'UTC timestamp of the measurement';
COMMENT ON COLUMN sensor_data.measurement IS 'Name/type of the measurement (e.g., temperature, pressure)';
COMMENT ON COLUMN sensor_data.source IS 'Source of the data (e.g., mqtt, opcua)';
COMMENT ON COLUMN sensor_data.location IS 'Location/device identifier';
COMMENT ON COLUMN sensor_data.field_name IS 'Specific field being measured';
COMMENT ON COLUMN sensor_data.field_value IS 'Numeric value of the measurement';
COMMENT ON COLUMN sensor_data.unit IS 'Unit of measurement (e.g., °C, bar, rpm)';

-- Create configuration tables (previously in SQLite)

-- OPC UA monitored variables
CREATE TABLE IF NOT EXISTS opcua_monitored_variables (
    id SERIAL PRIMARY KEY,
    node_id VARCHAR(255) NOT NULL UNIQUE,
    browse_name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    namespace_index INTEGER,
    data_type VARCHAR(50),
    polling_interval_ms INTEGER DEFAULT 1000,
    deadband_absolute DOUBLE PRECISION DEFAULT 0.0,
    store_to_postgres BOOLEAN DEFAULT TRUE,
    measurement_name VARCHAR(255),
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- MQTT to OPC UA mappings
CREATE TABLE IF NOT EXISTS mqtt_opcua_mappings (
    id SERIAL PRIMARY KEY,
    mqtt_topic VARCHAR(255) NOT NULL,
    opcua_node_id VARCHAR(255) NOT NULL,
    opcua_browse_name VARCHAR(255) NOT NULL,
    json_key VARCHAR(255) DEFAULT 'value',
    data_type VARCHAR(50) DEFAULT 'Double',
    unit VARCHAR(50),
    scaling_factor DOUBLE PRECISION DEFAULT 1.0,
    value_offset DOUBLE PRECISION DEFAULT 0.0,
    store_to_postgres BOOLEAN DEFAULT TRUE,
    measurement_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mqtt_mappings_topic_json_key_node
ON mqtt_opcua_mappings(mqtt_topic, json_key, opcua_node_id);

-- Device connection status
CREATE TABLE IF NOT EXISTS devices (
    id SERIAL PRIMARY KEY,
    device_type VARCHAR(10) CHECK(device_type IN ('opcua', 'mqtt')),
    name VARCHAR(255) NOT NULL UNIQUE,
    connection_string TEXT,
    status VARCHAR(20) CHECK(status IN ('connected', 'disconnected', 'error')),
    last_connected_at TIMESTAMP WITH TIME ZONE,
    last_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_opcua_variables_enabled ON opcua_monitored_variables(enabled);
CREATE INDEX IF NOT EXISTS idx_mqtt_mappings_topic ON mqtt_opcua_mappings(mqtt_topic);
CREATE INDEX IF NOT EXISTS idx_devices_type_status ON devices(device_type, status);

-- Display success message
\echo 'PostgreSQL database initialized successfully!'
\echo 'Database: iiot_gateway'
\echo 'User: iiot_user'
\echo 'Tables created: sensor_data, opcua_monitored_variables, mqtt_opcua_mappings, devices'
