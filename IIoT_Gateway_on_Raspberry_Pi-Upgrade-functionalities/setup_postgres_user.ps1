# PowerShell script to setup PostgreSQL user for IIoT Gateway
# Run this as: .\setup_postgres_user.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PostgreSQL User Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Find psql.exe
$psqlPath = "C:\Program Files\PostgreSQL\18\bin\psql.exe"

if (-not (Test-Path $psqlPath)) {
    Write-Host "ERROR: psql.exe not found at $psqlPath" -ForegroundColor Red
    Write-Host "Please update the path in this script" -ForegroundColor Red
    exit 1
}

Write-Host "Creating user and granting permissions..." -ForegroundColor Yellow
Write-Host ""

# Set password for postgres user (you'll be prompted)
$env:PGPASSWORD = Read-Host "Enter PostgreSQL 'postgres' user password" -AsSecureString
$env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($env:PGPASSWORD))

try {
    # Drop existing user
    & $psqlPath -U postgres -d postgres -c "DROP USER IF EXISTS iiot_user;" 2>&1 | Out-Null
    Write-Host "✓ Dropped existing user (if existed)" -ForegroundColor Green
    
    # Create new user
    & $psqlPath -U postgres -d postgres -c "CREATE USER iiot_user WITH PASSWORD 'iiot_password';"
    Write-Host "✓ Created user iiot_user" -ForegroundColor Green
    
    # Grant database privileges
    & $psqlPath -U postgres -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE iiot_gateway TO iiot_user;"
    Write-Host "✓ Granted database privileges" -ForegroundColor Green
    
    # Grant schema and table privileges
    & $psqlPath -U postgres -d iiot_gateway -c "GRANT ALL ON SCHEMA public TO iiot_user;"
    & $psqlPath -U postgres -d iiot_gateway -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO iiot_user;"
    & $psqlPath -U postgres -d iiot_gateway -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO iiot_user;"
    Write-Host "✓ Granted schema/table privileges" -ForegroundColor Green
    
    # Set default privileges
    & $psqlPath -U postgres -d iiot_gateway -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO iiot_user;"
    & $psqlPath -U postgres -d iiot_gateway -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO iiot_user;"
    Write-Host "✓ Set default privileges" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Testing connection..." -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    
    # Test connection
    $env:PGPASSWORD = "iiot_password"
    & $psqlPath -U iiot_user -d iiot_gateway -c "SELECT COUNT(*) as record_count FROM sensor_data;"
    
    Write-Host ""
    Write-Host "✓ Setup complete!" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host "✗ Error: $_" -ForegroundColor Red
} finally {
    $env:PGPASSWORD = $null
}
