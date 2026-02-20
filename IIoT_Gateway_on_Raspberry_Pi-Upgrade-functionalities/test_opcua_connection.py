#!/usr/bin/env python3
"""
OPC-UA Connection Test Script
Tests connection to S7-1500 PLC with different security settings
"""

import asyncio
import sys
from asyncua import Client
import logging
import traceback
import codecs

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, errors='replace')
    except Exception:
        pass

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def test_connection(endpoint, security_policy='None', security_mode='None', timeout=30):
    """Test OPC-UA connection with specified settings"""
    
    print("\n" + "="*70)
    print(f"Testing OPC-UA Connection")
    print("="*70)
    print(f"Endpoint:        {endpoint}")
    print(f"Security Policy: {security_policy}")
    print(f"Security Mode:   {security_mode}")
    print(f"Timeout:         {timeout}s")
    print("="*70 + "\n")
    
    client = None
    
    try:
        # Create client
        print("Creating OPC-UA client...")
        client = Client(url=endpoint, timeout=timeout)
        
        # Set security only if not 'None'
        if security_policy != 'None':
            security_string = f"{security_policy},{security_mode}"
            print(f"Setting security string: {security_string}")
            await client.set_security_string(security_string)
        else:
            print("Using no security (anonymous connection)")
        
        # Connect
        print("Connecting to server...")
        await client.connect()
        
        print("\n✓ CONNECTION SUCCESSFUL!\n")
        
        # Get server information
        print("Retrieving server information...")
        
        # Get namespaces
        namespaces = await client.get_namespace_array()
        print(f"\nNamespaces ({len(namespaces)}):")
        for i, ns in enumerate(namespaces):
            print(f"  [{i}] {ns}")
        
        # Get server node
        server_node = client.get_server_node()
        server_name = await server_node.read_browse_name()
        print(f"\nServer Node: {server_name.Name}")
        
        # Try to browse Objects folder
        print("\nBrowsing Objects folder...")
        objects = client.get_objects_node()
        children = await objects.get_children()
        print(f"Found {len(children)} objects:")
        for child in children[:10]:  # Show first 10
            browse_name = await child.read_browse_name()
            display_name = await child.read_display_name()
            print(f"  - {browse_name.Name} ({display_name.Text})")
        
        if len(children) > 10:
            print(f"  ... and {len(children) - 10} more")
        
        # Disconnect
        print("\nDisconnecting...")
        await client.disconnect()
        
        print("\n" + "="*70)
        print("TEST PASSED - Connection successful!")
        print("="*70 + "\n")
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n✗ CONNECTION FAILED!")
        print(f"Error: {error_msg}")
        print(f"\nFull traceback:")
        print(traceback.format_exc())
        print()
        
        # Provide diagnostic hints
        print("Troubleshooting hints:")
        print("-" * 70)
        
        if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
            print("• Connection timeout - server may not be running or unreachable")
            print("• Check if OPC UA server is enabled on the S7-1500")
            print("• Verify firewall settings allow port 4840")
            print("• Ensure network connectivity (you already verified with Test-NetConnection)")
            
        elif "security" in error_msg.lower() or "certificate" in error_msg.lower():
            print("• Security/certificate mismatch")
            print("• S7-1500 typically requires security policy 'None'")
            print("• Try running test with: python test_opcua_connection.py --security None")
            
        elif "refused" in error_msg.lower():
            print("• Connection refused by server")
            print("• OPC UA server may not be running on the PLC")
            print("• Check TIA Portal - enable OPC UA server in PLC settings")
            
        elif "badserviceunsupported" in error_msg.lower():
            print("• Server doesn't support requested service")
            print("• Try with security policy 'None'")
            
        else:
            print("• Check OPC UA server configuration in TIA Portal")
            print("• Verify PLC is in RUN mode")
            print("• Check if OPC UA server is enabled and accessible")
        
        print("-" * 70 + "\n")
        
        if client:
            try:
                await client.disconnect()
            except:
                pass
        
        return False

async def main():
    """Main test function"""
    
    # Default settings
    endpoint = "opc.tcp://10.210.76.161:4840"
    security_policy = "None"
    security_mode = "None"
    timeout = 30
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if '--help' in sys.argv or '-h' in sys.argv:
            print("Usage: python test_opcua_connection.py [endpoint] [--security POLICY] [--timeout SECONDS]")
            print("\nExamples:")
            print("  python test_opcua_connection.py")
            print("  python test_opcua_connection.py opc.tcp://192.168.1.100:4840")
            print("  python test_opcua_connection.py --security Basic256Sha256 --timeout 60")
            sys.exit(0)
        
        for i, arg in enumerate(sys.argv[1:], 1):
            if arg.startswith('opc.tcp://'):
                endpoint = arg
            elif arg == '--security' and i + 1 < len(sys.argv):
                security_policy = sys.argv[i + 1]
            elif arg == '--timeout' and i + 1 < len(sys.argv):
                timeout = int(sys.argv[i + 1])
    
    # Run test
    success = await test_connection(endpoint, security_policy, security_mode, timeout)
    
    # Try with different security settings if first attempt fails
    if not success and security_policy != 'None':
        print("\n" + "="*70)
        print("Retrying with security policy 'None'...")
        print("="*70 + "\n")
        await asyncio.sleep(2)
        await test_connection(endpoint, 'None', 'None', timeout)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
