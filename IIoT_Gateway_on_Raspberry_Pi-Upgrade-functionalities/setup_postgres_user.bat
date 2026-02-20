@echo off
REM Setup PostgreSQL user for IIoT Gateway
REM This script creates the iiot_user with correct password and permissions

echo ========================================
echo PostgreSQL User Setup
echo ========================================
echo.

REM Find psql.exe (adjust path if needed)
set PSQL="C:\Program Files\PostgreSQL\18\bin\psql.exe"

if not exist %PSQL% (
    echo ERROR: psql.exe not found at %PSQL%
    echo Please update the PSQL path in this script
    pause
    exit /b 1
)

echo Creating user and granting permissions...
echo.

REM Connect as postgres superuser and run commands
%PSQL% -U postgres -d postgres -c "DROP USER IF EXISTS iiot_user;"
%PSQL% -U postgres -d postgres -c "CREATE USER iiot_user WITH PASSWORD 'iiot_password';"
%PSQL% -U postgres -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE iiot_gateway TO iiot_user;"

REM Connect to iiot_gateway database and grant schema permissions
%PSQL% -U postgres -d iiot_gateway -c "GRANT ALL ON SCHEMA public TO iiot_user;"
%PSQL% -U postgres -d iiot_gateway -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO iiot_user;"
%PSQL% -U postgres -d iiot_gateway -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO iiot_user;"
%PSQL% -U postgres -d iiot_gateway -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO iiot_user;"
%PSQL% -U postgres -d iiot_gateway -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO iiot_user;"

echo.
echo ========================================
echo Testing connection...
echo ========================================
%PSQL% -U iiot_user -d iiot_gateway -c "SELECT COUNT(*) as record_count FROM sensor_data;"

echo.
echo ✓ Setup complete!
echo.
pause
