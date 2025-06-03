#!/usr/bin/env python3
"""
Standalone test script for Renogy BT library
This script tests Bluetooth discovery and data retrieval without MQTT or Home Assistant dependencies
"""
import asyncio
import logging
import os
import sys
import time
from bleak import BleakScanner

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add the parent directory to the path so we can import the renogy modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import only what we need from the renogy-bt library
try:
    from renogy.renogybt import RoverClient, BatteryClient, InverterClient, DCChargerClient, RoverHistoryClient, Utils
    logging.info("Successfully imported renogy modules")
except ImportError as e:
    logging.error(f"Failed to import renogy modules: {e}")
    logging.error("Make sure you've copied the required files from the original renogy-bt project")
    sys.exit(1)

ALIAS_PREFIXES = ['BT-TH', 'RNGRBP', 'BTRIC']

async def discover_devices():
    """Discover Renogy BT devices"""
    logging.info("Starting Bluetooth device discovery...")
    
    devices = await BleakScanner.discover(timeout=10.0)
    found_devices = []
    
    for device in devices:
        if device.name and any(device.name.startswith(prefix) for prefix in ALIAS_PREFIXES):
            logging.info(f"Found potential Renogy device: {device.name} ({device.address})")
            found_devices.append({
                "name": device.name,
                "mac_address": device.address,
                "device": device
            })
    
    return found_devices

def on_data_received(client, data):
    """Callback for when data is received from a device"""
    logging.info(f"Received data from {client.config['device']['alias']}:")
    logging.info(f"Raw data: {data}")

def on_error(client, error):
    """Callback for error handling"""
    logging.error(f"Error with device {client.config['device']['alias']}: {error}")

def create_config_for_device(device_info):
    """Create a simple config for testing a device"""
    import configparser
    
    config = configparser.ConfigParser(inline_comment_prefixes=('#'))
    
    # Try to determine device type based on the name prefix
    device_type = "RNG_CTRL"  # Default to controller
    if device_info['name'].startswith("RNGRBP"):
        device_type = "RNG_BATT"
    elif device_info['name'].startswith("BTRIC"):
        device_type = "RNG_INVT"
    
    # Basic device configuration
    config['device'] = {
        'adapter': 'hci0',
        'mac_addr': device_info['mac_address'],
        'alias': device_info['name'],
        'type': device_type,
        'device_id': '255'  # Default broadcast address
    }
    
    # Data section with polling enabled
    config['data'] = {
        'enable_polling': 'true',
        'poll_interval': '10',  # 10 seconds for testing
        'temperature_unit': 'C',
        'fields': ''
    }
    
    # Disable all logging types
    config['mqtt'] = {'enabled': 'false'}
    config['remote_logging'] = {'enabled': 'false'}
    config['pvoutput'] = {'enabled': 'false'}
    
    return config

def test_device(device_info):
    """Test a specific device with the appropriate client"""
    config = create_config_for_device(device_info)
    device_type = config['device']['type']
    
    logging.info(f"Testing device {device_info['name']} as {device_type}")
    
    try:
        if device_type == 'RNG_CTRL':
            RoverClient(config, on_data_received, on_error).start()
        elif device_type == 'RNG_BATT':
            BatteryClient(config, on_data_received, on_error).start()
        elif device_type == 'RNG_INVT':
            InverterClient(config, on_data_received, on_error).start()
        elif device_type == 'RNG_DCC':
            DCChargerClient(config, on_data_received, on_error).start()
        else:
            logging.error(f"Unknown device type: {device_type}")
            return False
        
        return True
    except Exception as e:
        logging.error(f"Error testing device: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_known_device():
    """Test a known device by MAC address and type"""
    logging.info("Testing a known device...")
    
    # Ask for the device details
    print("\nEnter the device MAC address (e.g. 80:6F:B0:0F:XX:XX):")
    mac_address = input("> ").strip()
    
    print("\nEnter the device name/alias (e.g. BT-TH-B00FXXXX):")
    alias = input("> ").strip()
    
    print("\nSelect device type:")
    print("1. Solar Charge Controller (Rover, Wanderer)")
    print("2. Battery")
    print("3. Inverter")
    print("4. DC Charger")
    device_type_num = input("> ").strip()
    
    # Map input to device type
    device_type_map = {
        "1": "RNG_CTRL",
        "2": "RNG_BATT", 
        "3": "RNG_INVT",
        "4": "RNG_DCC"
    }
    
    device_type = device_type_map.get(device_type_num, "RNG_CTRL")
    
    # Create device info
    device_info = {
        "name": alias,
        "mac_address": mac_address
    }
    
    # Override the device type in the config creation
    config = create_config_for_device(device_info)
    config['device']['type'] = device_type
    
    # Test the device
    try:
        if device_type == 'RNG_CTRL':
            RoverClient(config, on_data_received, on_error).start()
        elif device_type == 'RNG_BATT':
            BatteryClient(config, on_data_received, on_error).start()
        elif device_type == 'RNG_INVT':
            InverterClient(config, on_data_received, on_error).start()
        elif device_type == 'RNG_DCC':
            DCChargerClient(config, on_data_received, on_error).start()
        
        return True
    except Exception as e:
        logging.error(f"Error testing device: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point"""
    logging.info("Renogy BT Test Script")
    logging.info("This script tests the Renogy BT library without MQTT or Home Assistant dependencies")
    
    # Check if running with sudo/root, which is typically required for Bluetooth
    if os.geteuid() != 0:
        logging.warning("This script may need to be run with sudo or as root for Bluetooth access")
        print("\nContinue anyway? (y/n)")
        if input("> ").lower() != 'y':
            logging.info("Exiting. Try running with sudo.")
            sys.exit(0)
    
    # Main menu
    while True:
        print("\nRenogy BT Test Menu:")
        print("1. Discover devices")
        print("2. Test a known device")
        print("3. Exit")
        
        choice = input("> ").strip()
        
        if choice == '1':
            loop = asyncio.get_event_loop()
            devices = loop.run_until_complete(discover_devices())
            
            if not devices:
                logging.warning("No Renogy BT devices found")
                continue
            
            # Show discovered devices and offer to test
            print("\nDiscovered devices:")
            for i, device in enumerate(devices):
                print(f"{i+1}. {device['name']} ({device['mac_address']})")
            
            print("\nSelect device to test (number) or 0 to return to menu:")
            select = input("> ").strip()
            
            try:
                select_num = int(select)
                if select_num == 0:
                    continue
                
                if 1 <= select_num <= len(devices):
                    test_device(devices[select_num-1])
                else:
                    print("Invalid selection")
            except ValueError:
                print("Please enter a number")
            
        elif choice == '2':
            test_known_device()
            
        elif choice == '3':
            logging.info("Exiting Renogy BT Test Script")
            break
        
        else:
            print("Invalid choice, please try again")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Test script interrupted by user")
    except Exception as e:
        logging.error(f"Unhandled error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
