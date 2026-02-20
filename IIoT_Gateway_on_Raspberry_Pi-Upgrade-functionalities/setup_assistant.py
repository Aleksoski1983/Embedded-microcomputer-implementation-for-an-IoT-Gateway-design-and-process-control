#!/usr/bin/env python3
"""
IIoT Gateway Setup Assistant
Helps configure the OPC-UA connection
"""

import os
import sys
import subprocess

def check_requirements():
    """Check if required packages are installed"""
    try:
        import asyncua
        import flask
        print("✅ Required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        return False

def test_connection():
    """Run the connection test"""
    print("\n" + "="*50)
    print("TESTING OPC-UA CONNECTION")
    print("="*50)
    
    try:
        result = subprocess.run([sys.executable, "test_opcua_connection_simple.py"], 
                               capture_output=False, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running test: {e}")
        return False

def configure_env():
    """Help configure .env file"""
    print("\n" + "="*50)
    print("CONFIGURING .ENV FILE")
    print("="*50)
    
    env_path = ".env"
    
    # Read current .env
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value

    # Get OPC-UA endpoint
    current_endpoint = env_vars.get('OPCUA_CLIENT_ENDPOINT', '')
    print(f"Current OPC-UA endpoint: {current_endpoint or 'Not set'}")
    
    new_endpoint = input("Enter new OPC-UA endpoint (or press Enter to keep current): ").strip()
    if new_endpoint:
        if not new_endpoint.startswith('opc.tcp://'):
            print("⚠️ Endpoint should start with 'opc.tcp://'")
            new_endpoint = "opc.tcp://" + new_endpoint
        env_vars['OPCUA_CLIENT_ENDPOINT'] = new_endpoint
    
    # Update timeout if needed
    current_timeout = env_vars.get('OPCUA_CLIENT_TIMEOUT', '10')
    print(f"Current timeout: {current_timeout} seconds")
    
    # Save updated .env
    with open(env_path, 'w') as f:
        f.write("# IIoT Gateway Configuration\n\n")
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    print("✅ Configuration saved to .env")

def main():
    """Main setup function"""
    print("🚀 IIoT Gateway Setup Assistant")
    print("="*50)
    
    # Check working directory
    if not os.path.exists("app") or not os.path.exists("run.py"):
        print("❌ Please run this script from the IIoT Gateway directory")
        return
    
    # Check requirements
    if not check_requirements():
        return
    
    while True:
        print("\nWhat would you like to do?")
        print("1. Test OPC-UA connection")
        print("2. Configure .env file")
        print("3. Run IIoT Gateway")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            test_connection()
        elif choice == '2':
            configure_env()
        elif choice == '3':
            print("\nStarting IIoT Gateway...")
            try:
                subprocess.run([sys.executable, "run.py"])
            except KeyboardInterrupt:
                print("\n⚡ Gateway stopped by user")
        elif choice == '4':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-4.")

if __name__ == '__main__':
    main()