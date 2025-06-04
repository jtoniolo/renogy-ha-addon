#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import sys
import time
import configparser
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
        self.mqtt_discovery_sent = {}  # Keep track of discovery messages already sent
        
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
            section_groups = {}
            for section in main_config.sections():
                prefix = section.split(':')[0] if ':' in section else section
                if prefix not in section_groups:
                    section_groups[prefix] = []
                section_groups[prefix].append(section)
            
            # Create individual device configs
            for prefix, sections in section_groups.items():
                if prefix == 'device':
                    device_config = configparser.ConfigParser()
                    for section in sections:
                        device_config[section] = dict(main_config[section])
                    
                    # Add common sections
                    for section in main_config.sections():
                        if section not in sections and section not in ['device']:
                            device_config[section] = dict(main_config[section])
                    
                    self.device_configs.append(device_config)
        except Exception as e:
            logging.error(f"Error loading device configs: {e}")
            
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
        config['mqtt'] = {
            'enabled': 'true',
            'server': 'core-mosquitto',  # Home Assistant's internal MQTT broker
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
        self.mqtt_client = mqtt.Client(client_id="renogy-ha-addon", callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        
        try:
            self.mqtt_client.connect("core-mosquitto", 1883, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            logging.error(f"Failed to connect to MQTT broker: {e}")
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback for when the MQTT client connects"""
        if rc == 0:
            logging.info("Connected to MQTT broker")
            self.mqtt_connected = True
        else:
            logging.error(f"Failed to connect to MQTT broker with code {rc}")
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """Callback for when the MQTT client disconnects"""
        logging.warning(f"Disconnected from MQTT broker with code {rc}")
        self.mqtt_connected = False
    
    def _send_mqtt_discovery(self, device_id, device_name, device_data):
        """Send MQTT discovery messages for Home Assistant"""
        if not self.config['mqtt']['discovery']:
            return
            
        # Create a unique ID for the device
        device_unique_id = f"renogy_{device_id}"
        
        # Define base device info
        device_info = {
            "identifiers": [device_unique_id],
            "name": device_name,
            "manufacturer": "Renogy",
            "model": device_data.get('model', "Unknown Model"),
            "sw_version": "renogy-ha-addon"
        }
        
        # Map of entity definitions based on data fields
        entity_mapping = {
            # Battery entities
            "battery_percentage": {
                "name": "Battery Percentage",
                "device_class": "battery",
                "unit_of_measurement": "%",
                "state_class": "measurement",
                "icon": "mdi:battery"
            },
            "battery_voltage": {
                "name": "Battery Voltage",
                "device_class": "voltage",
                "unit_of_measurement": "V",
                "state_class": "measurement"
            },
            "battery_current": {
                "name": "Battery Current",
                "device_class": "current",
                "unit_of_measurement": "A",
                "state_class": "measurement"
            },
            "battery_temperature": {
                "name": "Battery Temperature",
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "state_class": "measurement"
            },
            
            # Solar entities
            "pv_voltage": {
                "name": "Solar Panel Voltage",
                "device_class": "voltage",
                "unit_of_measurement": "V",
                "state_class": "measurement"
            },
            "pv_current": {
                "name": "Solar Panel Current",
                "device_class": "current",
                "unit_of_measurement": "A",
                "state_class": "measurement"
            },
            "pv_power": {
                "name": "Solar Power",
                "device_class": "power",
                "unit_of_measurement": "W",
                "state_class": "measurement"
            },
            "power_generation_today": {
                "name": "Solar Generation Today",
                "device_class": "energy",
                "unit_of_measurement": "Wh",
                "state_class": "total_increasing"
            },
            "power_generation_total": {
                "name": "Total Solar Generation",
                "device_class": "energy",
                "unit_of_measurement": "Wh",
                "state_class": "total_increasing"
            },
            
            # Controller entities
            "controller_temperature": {
                "name": "Controller Temperature",
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "state_class": "measurement"
            },
            "charging_status": {
                "name": "Charging Status",
                "icon": "mdi:battery-charging"
            },
            
            # Load entities
            "load_status": {
                "name": "Load Status",
                "icon": "mdi:power-plug"
            },
            "load_voltage": {
                "name": "Load Voltage",
                "device_class": "voltage",
                "unit_of_measurement": "V",
                "state_class": "measurement"
            },
            "load_current": {
                "name": "Load Current",
                "device_class": "current",
                "unit_of_measurement": "A",
                "state_class": "measurement"
            },
            "load_power": {
                "name": "Load Power",
                "device_class": "power",
                "unit_of_measurement": "W",
                "state_class": "measurement"
            }
        }
        
        # Create discovery messages for each available data point
        discovery_prefix = "homeassistant"
        base_topic = f"{self.config['mqtt']['topic_prefix']}/{device_unique_id}"
        
        for field, value in device_data.items():
            if field in entity_mapping and field not in self.mqtt_discovery_sent.get(device_unique_id, []):
                entity_config = entity_mapping[field]
                object_id = f"{device_unique_id}_{field}"
                
                config_topic = f"{discovery_prefix}/sensor/{object_id}/config"
                
                config_payload = {
                    "name": entity_config["name"],
                    "unique_id": object_id,
                    "state_topic": f"{base_topic}/state",
                    "value_template": f"{{{{ value_json.{field} }}}}",
                    "device": device_info
                }
                
                # Add optional fields if they exist
                for key in ["device_class", "unit_of_measurement", "state_class", "icon"]:
                    if key in entity_config:
                        config_payload[key] = entity_config[key]
                
                # Publish discovery message
                try:
                    # Use updated MQTT publish with callback_api_version
                    publisher = mqtt.Client(client_id="renogy-ha-addon-discovery", callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
                    publisher.connect("core-mosquitto", 1883)
                    publisher.publish(config_topic, json.dumps(config_payload))
                    publisher.disconnect()
                    
                    # Track that we've sent this discovery message
                    if device_unique_id not in self.mqtt_discovery_sent:
                        self.mqtt_discovery_sent[device_unique_id] = []
                    self.mqtt_discovery_sent[device_unique_id].append(field)
                    
                except Exception as e:
                    logging.error(f"Error publishing discovery message: {e}")
    
    async def discover_devices(self):
        """Discover Renogy devices via Bluetooth"""
        logging.info("Starting Bluetooth device discovery...")
        
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
                'server': 'core-mosquitto',
                'port': '1883',
                'topic': f"{self.config['mqtt']['topic_prefix']}/state",
                'user': '',
                'password': ''
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
        
        # Add or update device sections
        for i, device in enumerate(found_devices):
            section_name = f"device:{i}" if i > 0 else "device"
            
            # Try to determine device type from name
            device_type = "RNG_CTRL"  # Default
            if device['name'].startswith("RNGRBP"):
                device_type = "RNG_BATT"
            elif device['name'].startswith("BTRIC"):
                device_type = "RNG_INVT"
                
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
            
        # Reload our device configs
        self.device_configs = []
        self._load_device_configs()
    
    def on_data_received(self, client, data):
        """Callback for when data is received from a device"""
        logging.info(f"Received data from {client.ble_manager.device.name}")
        
        # Filter fields if configured
        config_section = 'data'
        filtered_data = Utils.filter_fields(data, client.config[config_section]['fields'])
        
        # Log to MQTT if enabled
        if client.config['mqtt'].getboolean('enabled') and self.mqtt_connected:
            try:
                device_name = client.config['device']['alias']
                device_type = client.config['device']['type']
                device_id = client.ble_manager.device.address.replace(':', '').lower()
                
                # Send discovery messages if enabled
                if self.config['mqtt']['discovery']:
                    self._send_mqtt_discovery(device_id, device_name, filtered_data)
                
                # Publish state data
                topic = client.config['mqtt']['topic']
                
                # Use updated MQTT publish with callback_api_version
                publisher = mqtt.Client(client_id=f"renogy-bt-{device_id}", callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
                publisher.connect(client.config['mqtt']['server'], client.config['mqtt'].getint('port'))
                publisher.publish(topic, json.dumps(filtered_data))
                publisher.disconnect()
            except Exception as e:
                logging.error(f"Error publishing to MQTT: {e}")
    
    def on_error(self, client, error):
        """Callback for error handling"""
        logging.error(f"Device error: {error}")
    
    def start(self):
        """Start monitoring devices"""
        logging.info("Starting Renogy BT Home Assistant Add-on")
        
        if self.config['bluetooth']['auto_discover']:
            logging.info("Auto-discovery mode enabled. Searching for devices...")
            loop = asyncio.get_event_loop()
            devices = loop.run_until_complete(self.discover_devices())
            self.update_device_config(devices)
        
        # Add known devices from config
        for device_config in self.config['bluetooth']['known_devices']:
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
            
            config['mqtt'] = {
                'enabled': 'true',
                'server': 'core-mosquitto',
                'port': '1883',
                'topic': f"{self.config['mqtt']['topic_prefix']}/{device_config['mac_address'].replace(':', '').lower()}/state",
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
        for config in self.device_configs:
            try:
                device_type = config['device']['type']
                
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
            except Exception as e:
                logging.error(f"Error starting device: {e}")

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
