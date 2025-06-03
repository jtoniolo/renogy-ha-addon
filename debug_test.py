#!/usr/bin/env python3
print("Starting script...")
"""
Standalone test script for Renogy BT library
This script tests Bluetooth discovery and data retrieval without MQTT or Home Assistant dependencies
"""
import asyncio
print("Imported asyncio")
import logging
print("Imported logging")
import os
print("Imported os")
import sys
print("Imported sys")

try:
    from bleak import BleakScanner
    print("Imported BleakScanner")
except ImportError as e:
    print(f"Failed to import BleakScanner: {e}")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
print("Set up logging")

# Add the parent directory to the path so we can import the renogy modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
print(f"Path: {sys.path}")

# Import only what we need from the renogy-bt library
try:
    print("Trying to import renogy modules...")
    from renogy.renogybt import RoverClient, BatteryClient, InverterClient, DCChargerClient, RoverHistoryClient, Utils
    print("Successfully imported renogy modules")
except ImportError as e:
    print(f"Failed to import renogy modules: {e}")
    print(f"Looking for module at: {os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'renogy/renogybt')}")
    logging.error(f"Failed to import renogy modules: {e}")
    logging.error("Make sure you've copied the required files from the original renogy-bt project")
    sys.exit(1)

print("Script initialization complete")

# Simple version just to test imports
if __name__ == "__main__":
    print("Main code executed")
