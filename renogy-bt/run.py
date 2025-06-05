#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import sys
import time
import configparser
import requests
from bleak import BleakScanner
import paho.mqtt.client as mqtt

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set up path for module imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from renogy.renogybt import RoverClient, BatteryClient, DCChargerClient, InverterClient, RoverHistoryClient, DataLogger, Utils
from renogybt.DeviceManager import DeviceManager

# Constants
ADDON_CONFIG_PATH = "/data/options.json"
DEVICE_CONFIG_PATH = "/data/device_config.ini"
HA_MQTT_CONFIG_PATH = "/data/mqtt_discovery"

class HomeAssistantIntegration:
    def __init__(self):
        self.config = self._load_config()
        self.device_configs = []
        self.mqtt_client = None
        self.mqtt_connected = False
        self.mqtt_config = self._get_mqtt_config_from_config()
        
        # Initialize device manager for consistent MQTT handling
        self.device_manager = DeviceManager(self.config, self.mqtt_config)
        
        if os.path.exists(DEVICE_CONFIG_PATH):
            self._load_device_configs()
        else:
            self._create_device_config()

        # Initialize MQTT client
        self._setup_mqtt()
        
    def _load_config(self):
        """Load the add-on configuration from options.json"""
        try:
            with open(ADDON_CONFIG_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            sys.exit(1)
    
    def _load_device_configs(self):
        """Load existing device configurations"""
        logging.info("Loading existing device configurations")
        try:
            main_config = configparser.ConfigParser()
            main_config.read(DEVICE_CONFIG_PATH)
            
            # Extract device sections
            device_sections = []
            for section in main_config.sections():
                if section == 'device' or section.startswith('device:'):
                    device_sections.append(section)
            
            logging.info(f"Found {len(device_sections)} device sections in configuration")
            
            # Create individual device configs - one config per device section
            for section in device_sections:
                device_config = configparser.ConfigParser()
                
                # Add the device section
                device_config['device'] = dict(main_config[section])
                
                # Add common sections
                for common_section in main_config.sections():
                    if common_section != 'device' and not common_section.startswith('device:'):
                        device_config[common_section] = dict(main_config[common_section])
                
                # Disable direct MQTT in the original client to avoid duplicate publications
                # DeviceManager will handle all MQTT publishing instead
                if 'mqtt' in device_config:
                    device_config['mqtt']['enabled'] = 'false'
                
                self.device_configs.append(device_config)
                
                logging.info(f"Loaded device config: {device_config['device']['alias']} ({device_config['device']['mac_addr']})")
                
            logging.info(f"Loaded {len(self.device_configs)} device configurations")
        except Exception as e:
            logging.error(f"Error loading device configs: {e}")
            import traceback
            traceback.print_exc()
            
    def _create_device_config(self):
        """Create initial device configuration file"""
        logging.info("Creating initial device configuration")
        
        config = configparser.ConfigParser(inline_comment_prefixes=('#'))
        
        # General device section
        config['data'] = {
            'enable_polling': 'true',
            'poll_interval': str(self.config['scan_interval']),
            'temperature_unit': self.config['temperature_unit'],
            'fields': ''
        }
        
        # MQTT section 
        # Disable direct MQTT publishing from the original client to avoid duplicate publications
        # DeviceManager will handle all MQTT publishing instead
        config['mqtt'] = {
            'enabled': 'false',  # Disable MQTT in the client config
            'server': 'core-mosquitto',
            'port': '1883',
            'topic': f"{self.config['mqtt']['topic_prefix']}/state",
            'user': '',
            'password': ''
        }
        
        # Remote logging section (disabled by default)
        config['remote_logging'] = {
            'enabled': 'false',
            'url': '',
            'auth_header': ''
        }
        
        # PVOutput section (disabled by default)
        config['pvoutput'] = {
            'enabled': 'false',
            'api_key': '',
            'system_id': ''
        }
        
        # Write the configuration file
        with open(DEVICE_CONFIG_PATH, 'w') as configfile:
            config.write(configfile)
    
    def _setup_mqtt(self):
        """Set up the MQTT client"""
        # Use legacy callback style for maximum compatibility
        self.mqtt_client = mqtt.Client(client_id="renogy-ha-addon", callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        
        try:
            # Use the MQTT config obtained from Supervisor API
            if self.mqtt_config['username'] and self.mqtt_config['password']:
                logging.info(f"Setting up MQTT with authentication for user {self.mqtt_config['username']}")
                self.mqtt_client.username_pw_set(self.mqtt_config['username'], self.mqtt_config['password'])
            else:
                logging.info("Setting up MQTT without authentication")
                
            # Connect to the MQTT broker
            host = self.mqtt_config['host']
            port = self.mqtt_config['port']
            logging.info(f"Connecting to MQTT broker at {host}:{port}")
            self.mqtt_client.connect(host, port, 60)
            self.mqtt_client.loop_start()
            logging.info("MQTT client started")
        except Exception as e:
            logging.error(f"Failed to connect to MQTT broker: {e}")
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Legacy V1 callback for when the MQTT client connects"""
        if rc == 0:
            logging.info("Connected to MQTT broker")
            self.mqtt_connected = True
        else:
            error_messages = {
                1: "Connection refused - incorrect protocol version",
                2: "Connection refused - invalid client identifier",
                3: "Connection refused - server unavailable",
                4: "Connection refused - bad username or password",
                5: "Connection refused - not authorised"
            }
            error_msg = error_messages.get(rc, f"Unknown error code: {rc}")
            logging.error(f"Failed to connect to MQTT broker: {error_msg}")
            
            if rc in [4, 5]:
                logging.error("Please check your MQTT username and password in the add-on configuration")
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """Legacy V1 callback for when the MQTT client disconnects"""
        if rc == 0:
            logging.info("Disconnected from MQTT broker (clean disconnect)")
        else:
            logging.warning(f"Disconnected from MQTT broker with code {rc}")
        self.mqtt_connected = False
        
    def _on_mqtt_connect_v2(self, client, userdata, flags, reason_code, properties):
        """V2 callback for when the MQTT client connects"""
        if reason_code.is_successful:
            logging.info("Connected to MQTT broker")
            self.mqtt_connected = True
        else:
            logging.error(f"Failed to connect to MQTT broker with code {reason_code}")
    
    def _on_disconnect_v2(self, client, userdata, disconnect_flags, reason_code, properties):
        """V2 callback for when the MQTT client disconnects"""
        logging.warning(f"Disconnected from MQTT broker with code {reason_code}")
        self.mqtt_connected = False
    
    def _send_mqtt_discovery(self, device_id, device_name, device_data):
        """Send MQTT discovery messages for Home Assistant - delegates to DeviceManager"""
        # This method is just a stub now - we will use a different approach to trigger discovery
        pass
    
    async def discover_devices(self):
        """Discover Renogy devices via Bluetooth"""
        logging.info("Starting Bluetooth device discovery...")
        
        # Create a new scanner with the event loop
        try:
            devices = await BleakScanner.discover(timeout=10.0)
            found_devices = []
            
            for device in devices:
                if device.name and (device.name.startswith("BT-TH") or 
                                    device.name.startswith("RNGRBP") or 
                                    device.name.startswith("BTRIC")):
                    logging.info(f"Found potential Renogy device: {device.name} ({device.address})")
                    found_devices.append({
                        "name": device.name,
                        "mac_address": device.address
                    })
            
            return found_devices
        except Exception as e:
            logging.error(f"Error during device discovery: {e}")
            return []
    
    def update_device_config(self, found_devices):
        """Update the device configuration based on discovered devices"""
        if not found_devices:
            logging.warning("No Renogy devices found during discovery")
            return
            
        config = configparser.ConfigParser(inline_comment_prefixes=('#'))
        
        # If we have an existing config file, read it first
        if os.path.exists(DEVICE_CONFIG_PATH):
            config.read(DEVICE_CONFIG_PATH)
        
        # Add common sections if they don't exist
        if 'data' not in config:
            config['data'] = {
                'enable_polling': 'true',
                'poll_interval': str(self.config['scan_interval']),
                'temperature_unit': self.config['temperature_unit'],
                'fields': ''
            }
            
        if 'mqtt' not in config:
            config['mqtt'] = {
                'enabled': 'true',
                'server': self.mqtt_config['host'],
                'port': str(self.mqtt_config['port']),
                'topic': f"{self.config['mqtt']['topic_prefix']}/state",
                'user': self.mqtt_config['username'],
                'password': self.mqtt_config['password']
            }
            
        if 'remote_logging' not in config:
            config['remote_logging'] = {
                'enabled': 'false',
                'url': '',
                'auth_header': ''
            }
            
        if 'pvoutput' not in config:
            config['pvoutput'] = {
                'enabled': 'false',
                'api_key': '',
                'system_id': ''
            }
        
        logging.info(f"Adding {len(found_devices)} devices to configuration")
        
        # First, clear any existing device sections to avoid duplicates
        for section in list(config.sections()):
            if section == "device" or section.startswith("device:"):
                config.remove_section(section)
        
        # Add or update device sections - each device gets its own section
        for i, device in enumerate(found_devices):
            section_name = f"device:{i}" if i > 0 else "device"
            
            # Try to determine device type from name
            device_type = "RNG_CTRL"  # Default
            if device['name'].startswith("RNGRBP"):
                device_type = "RNG_BATT"
            elif device['name'].startswith("BTRIC"):
                device_type = "RNG_INVT"
            
            logging.info(f"Adding device {i+1}/{len(found_devices)}: {device['name']} ({device['mac_address']}) as {device_type}")
                
            config[section_name] = {
                'adapter': 'hci0',
                'mac_addr': device['mac_address'],
                'alias': device['name'],
                'type': device_type,
                'device_id': '255'  # Default to broadcast
            }
        
        # Write the updated config
        with open(DEVICE_CONFIG_PATH, 'w') as configfile:
            config.write(configfile)
        
        logging.info(f"Device configuration updated with {len(found_devices)} devices")
            
        # Reload our device configs
        self.device_configs = []
        self._load_device_configs()
    
    def on_data_received(self, client, data):
        """Callback for when data is received from a device"""
        logging.info(f"Received data from {client.ble_manager.device.name}")
        
        # Mark the device as available since we received data
        self.publish_availability(client, available=True)
        
        # Filter fields if configured
        config_section = 'data'
        filtered_data = Utils.filter_fields(data, client.config[config_section]['fields'])
        
        # Always use DeviceManager for MQTT, regardless of client's mqtt.enabled setting
        if self.mqtt_connected:
            try:
                # Send discovery messages if enabled
                if self.config['mqtt']['discovery']:
                    # Use our new DeviceManager to handle discovery
                    self.device_manager.send_mqtt_discovery(client, filtered_data)
                
                # Use our new DeviceManager to publish device state
                self.device_manager.publish_device_state(client, filtered_data)
                
            except Exception as e:
                logging.error(f"Error publishing to MQTT: {e}")
    
    def on_error(self, client, error):
        """Callback for error handling"""
        logging.error(f"Device error: {error}")
    
    def start(self):
        """Start monitoring devices"""
        logging.info("Starting Renogy BT Home Assistant Add-on")
        
        if 'bluetooth' in self.config and self.config['bluetooth'].get('auto_discover', False):
            logging.info("Auto-discovery mode enabled. Searching for devices...")
            
            try:
                # Create and set event loop for discovery
                discovery_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(discovery_loop)
                devices = discovery_loop.run_until_complete(self.discover_devices())
                discovery_loop.close()
                self.update_device_config(devices)
            except Exception as e:
                logging.error(f"Error during auto-discovery: {e}")
        
        # Add known devices from config if they exist
        known_devices = []
        if 'bluetooth' in self.config and 'known_devices' in self.config['bluetooth']:
            known_devices = self.config['bluetooth']['known_devices']
            
        for device_config in known_devices:
            # Create a config for this device
            config = configparser.ConfigParser(inline_comment_prefixes=('#'))
            
            # Map device type to the format expected by the library
            device_type_map = {
                "rover": "RNG_CTRL",
                "rover_history": "RNG_CTRL_HIST",
                "battery": "RNG_BATT",
                "inverter": "RNG_INVT",
                "dc_charger": "RNG_DCC"
            }
            
            # Default sections
            config['device'] = {
                'adapter': 'hci0',
                'mac_addr': device_config['mac_address'],
                'alias': device_config.get('name', device_config['mac_address']),
                'type': device_type_map.get(device_config['device_type'], "RNG_CTRL"),
                'device_id': str(device_config.get('device_id', 255))
            }
            
            config['data'] = {
                'enable_polling': 'true',
                'poll_interval': str(self.config['scan_interval']),
                'temperature_unit': self.config['temperature_unit'],
                'fields': ''
            }
            
            device_id = device_config['mac_address'].replace(':', '').lower()
            device_unique_id = f"renogy_{device_id}"
            
            config['mqtt'] = {
                'enabled': 'false',  # Disable direct MQTT in client to avoid duplicates
                'server': 'core-mosquitto',
                'port': '1883',
                'topic': f"{self.config['mqtt']['topic_prefix']}/{device_unique_id}/state",
                'user': '',
                'password': ''
            }
            
            config['remote_logging'] = {
                'enabled': 'false',
                'url': '',
                'auth_header': ''
            }
            
            config['pvoutput'] = {
                'enabled': 'false',
                'api_key': '',
                'system_id': ''
            }
            
            self.device_configs.append(config)
        
        # Start monitoring all configured devices
        for idx, config in enumerate(self.device_configs):
            try:
                device_type = config['device']['type']
                device_name = config['device']['alias']
                device_mac = config['device']['mac_addr']
                logging.info(f"Initializing device {idx+1}/{len(self.device_configs)}: {device_name} ({device_mac}) - Type: {device_type}")
                
                # Create a new event loop for each device client to avoid the "no current event loop" error
                device_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(device_loop)
                
                # Adjust polling interval for each device to stagger them
                # This helps prevent Bluetooth collisions when multiple devices are polled
                stagger_seconds = idx * 5  # Stagger by 5 seconds per device
                if 'data' in config and 'poll_interval' in config['data']:
                    base_interval = int(config['data']['poll_interval'])
                    # If interval is too short, add stagger; otherwise, don't modify
                    if base_interval > stagger_seconds + 10:
                        config['data']['poll_interval'] = str(base_interval + stagger_seconds)
                        logging.info(f"Adjusted poll interval for {device_name} to {base_interval + stagger_seconds} seconds")
                
                # Initialize the appropriate client based on device type
                if device_type == 'RNG_CTRL':
                    RoverClient(config, on_data_callback=self.on_data_received, on_error_callback=self.on_error).start()
                elif device_type == 'RNG_CTRL_HIST':
                    RoverHistoryClient(config, on_data_callback=self.on_data_received, on_error_callback=self.on_error).start()
                elif device_type == 'RNG_BATT':
                    BatteryClient(config, on_data_callback=self.on_data_received, on_error_callback=self.on_error).start()
                elif device_type == 'RNG_INVT':
                    InverterClient(config, on_data_callback=self.on_data_received, on_error_callback=self.on_error).start()
                elif device_type == 'RNG_DCC':
                    DCChargerClient(config, on_data_callback=self.on_data_received, on_error_callback=self.on_error).start()
                else:
                    logging.error(f"Unknown device type: {device_type}")
                
                # Give a short delay between starting each device client
                # This prevents overwhelming the Bluetooth stack
                time.sleep(2)
                
            except Exception as e:
                logging.error(f"Error starting device: {e}")
                import traceback
                traceback.print_exc()

    def _get_mqtt_config_from_config(self):
        """Get MQTT connection details from config file"""
        # Get MQTT settings from the config
        mqtt_config = {
            'host': self.config['mqtt'].get('host', 'core-mosquitto'),
            'port': self.config['mqtt'].get('port', 1883),
            'username': self.config['mqtt'].get('username', ''),
            'password': self.config['mqtt'].get('password', '')
        }
        
        # Log MQTT connection details (without password)
        logging.info(f"MQTT Configuration: Host={mqtt_config['host']}, Port={mqtt_config['port']}, " +
                    f"Username={'<set>' if mqtt_config['username'] else '<not set>'}")
        
        return mqtt_config

    def publish_availability(self, client, available=True):
        """Publish availability status for a device - delegates to DeviceManager"""
        # Forward this call to the device manager
        self.device_manager.publish_availability(client, available)

if __name__ == "__main__":
    integration = HomeAssistantIntegration()
    integration.start()
    
    # Keep the script running
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Add-on stopping due to user request")
    except Exception as e:
        logging.error(f"Add-on stopping due to error: {e}")
        sys.exit(1)
