-- ========================================
-- Fix PostgreSQL User Authentication
-- ========================================
-- Run this in pgAdmin Query Tool (connected to 'postgres' database as superuser)
-- Then switch to iiot_gateway database and run the second part

-- PART 1: Run in 'postgres' database
-- ========================================

-- Drop existing user if it exists
DROP USER IF EXISTS iiot_user;

-- Create user with correct password
CREATE USER iiot_user WITH PASSWORD 'iiot_password';

-- Grant privileges on database
GRANT ALL PRIVILEGES ON DATABASE iiot_gateway TO iiot_user;

-- ========================================
-- PART 2: Switch to 'iiot_gateway' database in pgAdmin, then run this:
-- ========================================

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO iiot_user;

-- Grant table privileges
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO iiot_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO iiot_user;

-- Grant future objects privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO iiot_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO iiot_user;

-- ========================================
-- Verify Setup (run in iiot_gateway database)
-- ========================================

-- Check table exists
SELECT COUNT(*) as record_count FROM sensor_data;

-- Show recent data (if any)
SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 5;

-- Test user permissions
SELECT current_user, current_database();
