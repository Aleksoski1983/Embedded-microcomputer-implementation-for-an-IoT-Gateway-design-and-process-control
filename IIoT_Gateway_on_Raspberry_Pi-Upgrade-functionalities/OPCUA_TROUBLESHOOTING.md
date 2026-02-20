# OPC-UA Connection Troubleshooting Guide

## Quick Test

Run the test script to diagnose connection issues:

```powershell
python test_opcua_connection.py
```

This will test the connection and provide detailed diagnostic information.

## Common Issues & Solutions

### 1. Connection Timeout
**Symptoms:** Connection times out after 30 seconds

**Possible Causes:**
- OPC UA server not enabled on S7-1500
- PLC not reachable (though Test-NetConnection shows it is)
- Wrong endpoint URL or port

**Solutions:**
1. Check TIA Portal → PLC Properties → OPC UA Server:
   - ✓ Enable OPC UA server
   - ✓ Set port to 4840
   - ✓ Allow anonymous access (or configure security)

2. Verify PLC is in RUN mode

3. Check firewall on both PLC and your PC

### 2. Security Policy Mismatch
**Symptoms:** Connection fails with security/certificate errors

**Solution:**
S7-1500 typically uses no security. In `.env` file:
```
OPCUA_CLIENT_SECURITY_POLICY=None
OPCUA_CLIENT_SECURITY_MODE=None
```

### 3. Wrong Endpoint Format
**Symptoms:** Invalid URL errors

**Correct format:**
```
opc.tcp://[IP-ADDRESS]:4840
```

Example:
```
opc.tcp://10.210.76.161:4840
```

### 4. TIA Portal Configuration

To enable OPC UA on S7-1500:

1. Open TIA Portal
2. Select your PLC
3. Go to **Properties → General → OPC UA**
4. Check **"Enable OPC UA Server"**
5. Set **Server Access** to allow runtime access
6. Under **Security** tab:
   - For testing: Allow **"Sign"** and **"Sign & Encrypt"** security policies
   - Or enable **"None"** if available (easiest for testing)
7. **Download** configuration to PLC
8. Put PLC in **RUN** mode

## Testing from Web Interface

1. Navigate to: http://localhost:5001/configuration
2. Scroll to **OPC UA Client Settings**
3. Configure:
   - **Endpoint:** `opc.tcp://10.210.76.161:4840`
   - **Security Policy:** `None`
   - **Security Mode:** `None`
   - **Timeout:** `30` seconds
4. Click **"Test Connection"**

## Check Logs

View detailed connection logs:

```powershell
Get-Content "logs/iiot-gateway.log" -Tail 50
```

Or in web interface: http://localhost:5001/logs

## Verify Network Connectivity

```powershell
# Test TCP connection
Test-NetConnection 10.210.76.161 -Port 4840

# Should show: TcpTestSucceeded: True
```

## Alternative Test with asyncua

Quick Python test:

```python
import asyncio
from asyncua import Client

async def test():
    client = Client("opc.tcp://10.210.76.161:4840")
    await client.set_security_string("None")
    await client.connect()
    print("Connected!")
    namespaces = await client.get_namespace_array()
    print(f"Namespaces: {namespaces}")
    await client.disconnect()

asyncio.run(test())
```

## Getting Help

If connection still fails after trying above:

1. Run test script with verbose output: `python test_opcua_connection.py`
2. Check the exact error message
3. Verify OPC UA server status in TIA Portal
4. Check PLC diagnostics for any OPC UA related errors
