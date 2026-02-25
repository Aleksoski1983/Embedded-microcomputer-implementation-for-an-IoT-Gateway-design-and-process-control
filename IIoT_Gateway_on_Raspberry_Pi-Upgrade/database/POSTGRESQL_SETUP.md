# PostgreSQL Setup Guide

## Prerequisites

1. **Install PostgreSQL**
   - Windows: Download from https://www.postgresql.org/download/windows/
   - Or use the installer: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
   - Default installation creates a `postgres` superuser

2. **Verify Installation**
   ```powershell
   psql --version
   ```

## Database Initialization

### Option 1: Using the SQL Script (Recommended)

1. **Open PowerShell as Administrator**

2. **Navigate to the database directory**
   ```powershell
   cd "C:\Users\Zarija Aleksoski\Documents\RPi5 IIoT Gateway\database"
   ```

3. **Run the initialization script**
   ```powershell
   psql -U postgres -f init_postgresql.sql
   ```
   You'll be prompted for the postgres user password (set during PostgreSQL installation)

4. **Update the .env file**
   - Copy `.env.example` to `.env` if you haven't already
   - Update the PostgreSQL password in `.env`:
   ```
   POSTGRES_PASSWORD=your_actual_password
   ```

### Option 2: Manual Setup

1. **Connect to PostgreSQL**
   ```powershell
   psql -U postgres
   ```

2. **Create the database and user**
   ```sql
   CREATE DATABASE iiot_gateway;
   CREATE USER iiot_user WITH ENCRYPTED PASSWORD 'your_password_here';
   GRANT ALL PRIVILEGES ON DATABASE iiot_gateway TO iiot_user;
   ```

3. **Connect to the new database**
   ```sql
   \c iiot_gateway
   ```

4. **Grant schema privileges**
   ```sql
   GRANT ALL ON SCHEMA public TO iiot_user;
   GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO iiot_user;
   GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO iiot_user;
   ```

5. **Exit psql**
   ```sql
   \q
   ```

## Verification

1. **Test the connection**
   ```powershell
   psql -U iiot_user -d iiot_gateway -h localhost
   ```

2. **Check tables** (after running the application once)
   ```sql
   \dt
   SELECT * FROM sensor_data LIMIT 10;
   ```

## Configuration

The application uses these environment variables (set in `.env`):

```env
DATABASE_TYPE=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=iiot_gateway
POSTGRES_USER=iiot_user
POSTGRES_PASSWORD=your_password_here
```

## Connection Pooling

The application uses psycopg2's SimpleConnectionPool with:
- Minimum connections: 1
- Maximum connections: 20

This provides efficient connection management for concurrent operations.

## Performance Optimization

### TimescaleDB (Optional)

For better time-series performance, consider installing TimescaleDB:

1. **Install TimescaleDB extension**
   ```sql
   CREATE EXTENSION IF NOT EXISTS timescaledb;
   ```

2. **Convert sensor_data to a hypertable**
   ```sql
   SELECT create_hypertable('sensor_data', 'timestamp', if_not_exists => TRUE);
   ```

### Indexes

The following indexes are automatically created:
- `idx_sensor_data_timestamp` - For time-based queries
- `idx_sensor_data_measurement` - For measurement filtering
- `idx_sensor_data_source` - For source filtering
- `idx_sensor_data_field_name` - For field filtering
- `idx_sensor_data_measurement_timestamp` - Composite index for common queries

## Data Migration from InfluxDB (Optional)

If you have existing data in InfluxDB, you can migrate it:

1. **Export from InfluxDB**
   ```bash
   influx query 'from(bucket:"sensor-data") |> range(start: -30d)' --raw > influx_export.csv
   ```

2. **Import to PostgreSQL**
   ```sql
   COPY sensor_data(timestamp, measurement, source, location, field_name, field_value, unit)
   FROM 'path/to/influx_export.csv'
   DELIMITER ','
   CSV HEADER;
   ```

## Troubleshooting

### Connection Refused

- Verify PostgreSQL is running: `Get-Service postgresql*`
- Start if stopped: `Start-Service postgresql-x64-16` (adjust version)
- Check pg_hba.conf allows local connections

### Authentication Failed

- Verify password in `.env` matches the database user
- Check pg_hba.conf authentication method (should be `md5` or `scram-sha-256`)

### Permission Denied

- Ensure user has proper grants (run step 4 in Manual Setup)
- Reconnect after granting privileges

## Useful Commands

```sql
-- Show all databases
\l

-- Show all tables
\dt

-- Describe table structure
\d sensor_data

-- Show recent sensor data
SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 20;

-- Count records by measurement
SELECT measurement, COUNT(*) FROM sensor_data GROUP BY measurement;

-- Check database size
SELECT pg_size_pretty(pg_database_size('iiot_gateway'));
```

## Backup

```powershell
# Backup database
pg_dump -U iiot_user -d iiot_gateway > backup_$(Get-Date -Format "yyyyMMdd_HHmmss").sql

# Restore database
psql -U iiot_user -d iiot_gateway < backup_20240101_120000.sql
```
