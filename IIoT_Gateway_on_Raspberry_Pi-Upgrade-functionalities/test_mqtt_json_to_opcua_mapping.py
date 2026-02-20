from opcua import Client, ua

OPCUA_ENDPOINT = "opc.tcp://10.210.76.161:4840"  # Change to your server address if needed
NODE_ID = 'ns=3;s="FB_AHU_5703_DB"."OutdoorTemp_GT10_01"'

def set_opcua_value(value):
    client = Client(OPCUA_ENDPOINT)
    try:
        client.connect()
        node = client.get_node(NODE_ID)
        node.set_value(float(value))
        print(f"Successfully set value {value} on OPC-UA node {NODE_ID}")
    except Exception as e:
        print(f"Failed to set value: {e}")
    finally:
        client.disconnect()

if __name__ == "__main__":
    set_opcua_value(10.0)

