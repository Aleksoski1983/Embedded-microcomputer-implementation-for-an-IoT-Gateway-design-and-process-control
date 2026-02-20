#!/usr/bin/env python3
"""
Simple OPC-UA Connection Test
Tests basic connectivity to an OPC-UA server
"""

import asyncio
import sys
import os
import logging
import codecs

# Add the app directory to path
sys.path.append(os.path.dirname(__file__))

from asyncua import Client

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, errors='replace')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, errors='replace')
    except Exception:
        pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def test_opcua_connection(endpoint, timeout=10):
    """Test OPC-UA connection"""
    print(f"\n=== OPC-UA Connection Test ===")
    print(f"Endpoint: {endpoint}")
    print(f"Timeout: {timeout} seconds")
    print("=" * 50)
    
    client = None
    try:
        print("1. Creating OPC-UA client...")
        client = Client(url=endpoint, timeout=timeout)
        
        print("2. Attempting to connect...")
        await client.connect()
        print("✅ Connection successful!")
        
        print("3. Reading server information...")
        # Get namespaces
        try:
            namespaces = await client.get_namespace_array()
            print(f"   📚 Found {len(namespaces)} namespaces:")
            for i, ns in enumerate(namespaces):
                print(f"      [{i}] {ns}")
        except Exception as e:
            print(f"   ⚠️ Could not read namespaces: {e}")
        
        # Try to get server status
        try:
            root = client.get_root_node()
            server_status = await root.get_child(["0:Objects", "0:Server", "0:ServerStatus", "0:State"]).read_value()
            print(f"   🟢 Server Status: {server_status}")
        except Exception as e:
            print(f"   ⚠️ Could not read server status: {e}")
        
        # Try to browse Objects folder
        try:
            objects = client.get_objects_node()
            children = await objects.get_children()
            print(f"   📁 Found {len(children)} objects in root:")
            for child in children[:5]:  # Show first 5
                browse_name = await child.read_browse_name()
                print(f"      - {browse_name.Name}")
            if len(children) > 5:
                print(f"      ... and {len(children) - 5} more")
        except Exception as e:
            print(f"   ⚠️ Could not browse objects: {e}")
            
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        
        # Provide helpful diagnostics
        print("\n🔍 Troubleshooting tips:")
        if "timed out" in str(e).lower() or "timeout" in str(e).lower():
            print("   • Check if the server is running and reachable")
            print("   • Verify the IP address and port number")
            print("   • Check firewall settings")
        elif "refused" in str(e).lower():
            print("   • Server might not be running on this port")
            print("   • Check if OPC-UA is enabled on your S7-1500")
        elif "name resolution" in str(e).lower():
            print("   • Use IP address instead of hostname")
            print("   • Check DNS settings")
        else:
            print(f"   • Error details: {e}")
            print("   • Try using 'None' security policy")
            print("   • Ensure S7-1500 OPC-UA server is enabled")
        
        return False
        
    finally:
        if client:
            try:
                await client.disconnect()
                print("4. Disconnected from server")
            except:
                pass

def main():
    """Main test function"""
    print("OPC-UA Connection Test Tool")
    print("Enter OPC-UA server details to test connectivity")
    
    # Get endpoint from user
    endpoint = input("\nEnter OPC-UA endpoint (e.g., opc.tcp://192.168.1.100:4840): ").strip()
    
    if not endpoint:
        print("❌ No endpoint provided!")
        return
    
    if not endpoint.startswith('opc.tcp://'):
        print("❌ Endpoint must start with 'opc.tcp://'")
        return
    
    # Get timeout
    try:
        timeout_input = input("Enter timeout in seconds (default 10): ").strip()
        timeout = int(timeout_input) if timeout_input else 10
    except ValueError:
        timeout = 10
    
    print(f"\nTesting connection to: {endpoint}")
    
    # Run the test
    try:
        loop = asyncio.get_event_loop()
        success = loop.run_until_complete(test_opcua_connection(endpoint, timeout))
        
        if success:
            print(f"\n🎉 Connection test PASSED!")
            print("   You can use this endpoint in the IIoT Gateway configuration.")
        else:
            print(f"\n💥 Connection test FAILED!")
            print("   Please check the troubleshooting tips above.")
            
    except KeyboardInterrupt:
        print("\n\n⚡ Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")

if __name__ == '__main__':
    main()