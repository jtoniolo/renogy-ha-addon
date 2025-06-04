#!/usr/bin/env python3
import logging
import json
import paho.mqtt.client as mqtt

class DeviceManager:
    """
    DeviceManager handles consistent MQTT discovery and publishing for all Renogy device types.
    This class ensures that all device types follow the same MQTT topic structure and discovery format.
    """
    
    def __init__(self, config, mqtt_config):
        """Initialize with global configuration"""
        self.config = config
        self.mqtt_config = mqtt_config
        self.mqtt_discovery_sent = {}
        self.version = "0.1.9"
        
        # Common entity configurations shared across devices
        self.common_entity_mapping = {
            # Battery entities
            "voltage": {
                "name": "Voltage",
                "device_class": "voltage",
                "unit_of_measurement": "V",
                "state_class": "measurement"
            },
            "current": {
                "name": "Current",
                "device_class": "current",
                "unit_of_measurement": "A",
                "state_class": "measurement"
            },
            "temperature": {
                "name": "Temperature",
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "state_class": "measurement"
            },
            "power": {
                "name": "Power",
                "device_class": "power",
                "unit_of_measurement": "W",
                "state_class": "measurement"
            },
            "energy": {
                "name": "Energy",
                "device_class": "energy",
                "unit_of_measurement": "Wh",
                "state_class": "total_increasing"
            }
        }
        
        # Device specific entity mappings
        self.device_entity_mappings = {
            "RNG_CTRL": self._get_controller_entity_mapping(),
            "RNG_BATT": self._get_battery_entity_mapping(),
            "RNG_INVT": self._get_inverter_entity_mapping(),
            "RNG_DCC": self._get_dc_charger_entity_mapping()
        }

    def _get_controller_entity_mapping(self):
        """Get entity mapping specific to controller devices"""
        return {
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
    
    def _get_battery_entity_mapping(self):
        """Get entity mapping specific to battery devices"""
        return {
            "voltage": {
                "name": "Battery Voltage",
                "device_class": "voltage",
                "unit_of_measurement": "V",
                "state_class": "measurement"
            },
            "current": {
                "name": "Battery Current",
                "device_class": "current",
                "unit_of_measurement": "A",
                "state_class": "measurement"
            },
            "remaining_charge": {
                "name": "Remaining Charge",
                "device_class": "energy",
                "unit_of_measurement": "Ah",
                "state_class": "measurement",
                "icon": "mdi:battery-charging"
            },
            "capacity": {
                "name": "Total Capacity",
                "device_class": "energy",
                "unit_of_measurement": "Ah",
                "state_class": "measurement",
                "icon": "mdi:battery"
            },
            "cell_count": {
                "name": "Cell Count",
                "state_class": "measurement",
                "icon": "mdi:battery-multiple"
            },
            "sensor_count": {
                "name": "Temperature Sensors",
                "state_class": "measurement",
                "icon": "mdi:thermometer"
            }
        }
        # Note: Cell voltages and temperatures are dynamically added during discovery
    
    def _get_inverter_entity_mapping(self):
        """Get entity mapping specific to inverter devices"""
        return {
            "output_voltage": {
                "name": "Output Voltage",
                "device_class": "voltage",
                "unit_of_measurement": "V",
                "state_class": "measurement"
            },
            "output_current": {
                "name": "Output Current",
                "device_class": "current",
                "unit_of_measurement": "A",
                "state_class": "measurement"
            },
            "output_power": {
                "name": "Output Power",
                "device_class": "power",
                "unit_of_measurement": "W",
                "state_class": "measurement"
            },
            "input_voltage": {
                "name": "Input Voltage",
                "device_class": "voltage",
                "unit_of_measurement": "V",
                "state_class": "measurement"
            },
            "inverter_temperature": {
                "name": "Inverter Temperature",
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "state_class": "measurement"
            },
            "inverter_status": {
                "name": "Inverter Status",
                "icon": "mdi:power"
            }
        }
    
    def _get_dc_charger_entity_mapping(self):
        """Get entity mapping specific to DC charger devices"""
        return {
            "input_voltage": {
                "name": "Input Voltage",
                "device_class": "voltage",
                "unit_of_measurement": "V",
                "state_class": "measurement"
            },
            "output_voltage": {
                "name": "Output Voltage",
                "device_class": "voltage",
                "unit_of_measurement": "V",
                "state_class": "measurement"
            },
            "output_current": {
                "name": "Output Current",
                "device_class": "current",
                "unit_of_measurement": "A",
                "state_class": "measurement"
            },
            "charger_temperature": {
                "name": "Charger Temperature",
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "state_class": "measurement"
            },
            "charging_status": {
                "name": "Charging Status",
                "icon": "mdi:battery-charging"
            }
        }
    
    def get_entity_mapping_by_device_type(self, device_type):
        """Get the appropriate entity mapping for a device type"""
        if device_type in self.device_entity_mappings:
            return self.device_entity_mappings[device_type]
        # Default to controller mapping
        return self.device_entity_mappings["RNG_CTRL"]
        
    def send_mqtt_discovery(self, client, device_data):
        """Send MQTT discovery messages for Home Assistant - works for all device types"""
        if not self.config['mqtt']['discovery']:
            return
        
        device_id = client.ble_manager.device.address.replace(':', '').lower()
        device_name = client.config['device']['alias']
        device_type = client.config['device']['type']
        
        # Create a unique ID for the device
        device_unique_id = f"renogy_{device_id}"
        
        # Define base device info according to HA standards (with abbreviations)
        device_info = {
            "ids": [device_unique_id],           # abbreviation for identifiers
            "name": device_name,
            "mf": "Renogy",                      # abbreviation for manufacturer
            "mdl": device_data.get('model', f"Renogy {device_type}"),  # abbreviation for model
            "sw": device_data.get('firmware_version', "Unknown"),  # abbreviation for sw_version
            "hw": device_data.get('hardware_version', "Unknown"),  # abbreviation for hw_version
            "via_device": "renogy-ha-addon"
        }
        
        # Origin information (required for device-based discovery)
        origin_info = {
            "name": "renogy-ha-addon",
            "sw": self.version,
            "url": "https://github.com/jtoniolo/renogy-ha-addon"
        }
        
        # Get the appropriate entity mapping based on device type
        entity_mapping = self.get_entity_mapping_by_device_type(device_type)
        
        # Create discovery messages for each available data point
        discovery_prefix = self.config['mqtt']['topic_prefix']
        base_topic = f"{discovery_prefix}/{device_unique_id}"
        
        # Keep track of discovered entities by device
        if device_unique_id not in self.mqtt_discovery_sent:
            self.mqtt_discovery_sent[device_unique_id] = []
        
        # Process dynamic fields for batteries (cell voltages and temperatures)
        if device_type == "RNG_BATT":
            # Process cell voltages
            if "cell_count" in device_data:
                for i in range(device_data.get("cell_count", 0)):
                    field = f"cell_voltage_{i}"
                    if field in device_data and field not in entity_mapping:
                        entity_mapping[field] = {
                            "name": f"Cell {i+1} Voltage",
                            "device_class": "voltage",
                            "unit_of_measurement": "V",
                            "state_class": "measurement"
                        }
            
            # Process temperature sensors
            if "sensor_count" in device_data:
                for i in range(device_data.get("sensor_count", 0)):
                    field = f"temperature_{i}"
                    if field in device_data and field not in entity_mapping:
                        entity_mapping[field] = {
                            "name": f"Temperature Sensor {i+1}",
                            "device_class": "temperature",
                            "unit_of_measurement": "°C",
                            "state_class": "measurement"
                        }
        
        # Process standard fields from the device data
        for field, value in device_data.items():
            # Skip fields that start with double underscore (internal use)
            if field.startswith("__"):
                continue
                
            # Skip if we've already set up discovery for this field on this device
            if field in self.mqtt_discovery_sent.get(device_unique_id, []):
                continue
                
            # Skip if no mapping exists for this field
            if field not in entity_mapping:
                logging.debug(f"No entity mapping for field: {field}")
                continue
            
            entity_config = entity_mapping[field]
            
            # Create a sanitized field name for use in the unique_id
            sanitized_field = field.replace(" ", "_").lower()
            
            # Create unique identifiers following HA best practices
            unique_id = f"{device_unique_id}_{sanitized_field}"
            component_id = sanitized_field  # Used for object_id

            # Config topic follows HA discovery pattern
            config_topic = f"{discovery_prefix}/sensor/{device_id}/{component_id}/config"
            
            # Create MQTT discovery payload according to HA standards
            config_payload = {
                "~": f"{base_topic}",  # Base topic - uses shorthand ~ notation
                "name": entity_config["name"],
                "unique_id": unique_id,
                "object_id": component_id,
                "state_topic": "~/state",  # Uses ~ notation for topic
                "value_template": f"{{{{ value_json.{field} }}}}",
                "device": device_info,  # Uses abbreviations now
                "o": origin_info,  # Origin info (abbreviated)
                "availability": {
                    "topic": "~/availability"  # Uses ~ notation for topic
                },
                "has_entity_name": True,  # Follow HA best practices for entity naming
                "entity_category": "diagnostic"  # Most sensor values are diagnostics
            }
            
            # Add optional fields if they exist
            for key in ["device_class", "unit_of_measurement", "state_class", "icon"]:
                if key in entity_config:
                    # Use abbreviated form for certain fields when appropriate
                    if key == "unit_of_measurement":
                        config_payload["unit_of_meas"] = entity_config[key]  # Abbreviated form
                    elif key == "device_class":
                        config_payload["dev_cla"] = entity_config[key]  # Abbreviated form
                    elif key == "state_class":
                        config_payload["stat_cla"] = entity_config[key]  # Abbreviated form
                    else:
                        config_payload[key] = entity_config[key]
            
            # Publish discovery message
            self._publish_discovery_message(config_topic, config_payload)
            
            # Track that we've sent this discovery message
            self.mqtt_discovery_sent[device_unique_id].append(field)
    
    def _publish_discovery_message(self, topic, payload):
        """Publish a discovery message to MQTT"""
        try:
            # Use consistent callback API version
            publisher = mqtt.Client(client_id="renogy-ha-addon-discovery", callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
            
            # Set authentication if needed
            if self.mqtt_config['username'] and self.mqtt_config['password']:
                publisher.username_pw_set(self.mqtt_config['username'], self.mqtt_config['password'])
            
            try:
                publisher.connect(self.mqtt_config['host'], self.mqtt_config['port'])
                publisher.publish(topic, json.dumps(payload), retain=True)
                publisher.disconnect()
                logging.debug(f"Published discovery for {payload['unique_id']}")
            except Exception as e:
                logging.error(f"Failed to publish discovery message: {e}")
        except Exception as e:
            logging.error(f"Error publishing discovery message: {e}")
    
    def publish_device_state(self, client, data):
        """Publish device state to MQTT"""
        try:
            device_id = client.ble_manager.device.address.replace(':', '').lower()
            device_name = client.config['device']['alias']
            
            # Create unique device ID
            device_unique_id = f"renogy_{device_id}"
            
            # Create topic based on device ID 
            topic_prefix = self.config['mqtt']['topic_prefix']
            state_topic = f"{topic_prefix}/{device_unique_id}/state"
            
            # Use consistent callback API version
            publisher = mqtt.Client(client_id=f"renogy-bt-{device_id}", callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
            
            # Set authentication if needed
            if self.mqtt_config['username'] and self.mqtt_config['password']:
                publisher.username_pw_set(self.mqtt_config['username'], self.mqtt_config['password'])
            
            # Connect and publish
            publisher.connect(self.mqtt_config['host'], self.mqtt_config['port'])
            publisher.publish(state_topic, json.dumps(data), retain=True)
            publisher.disconnect()
            
            logging.info(f"Published data to {state_topic}")
        except Exception as e:
            logging.error(f"Error publishing device state: {e}")
    
    def publish_availability(self, client, available=True):
        """Publish availability status for a device"""
        try:
            if hasattr(client, 'ble_manager') and hasattr(client.ble_manager, 'device'):
                device_id = client.ble_manager.device.address.replace(':', '').lower()
                device_name = client.config['device']['alias']
                
                # Create a unique ID for the device
                device_unique_id = f"renogy_{device_id}"
                
                # Create topic
                topic_prefix = self.config['mqtt']['topic_prefix']
                availability_topic = f"{topic_prefix}/{device_unique_id}/availability"
                
                # Create publisher
                publisher = mqtt.Client(client_id=f"renogy-bt-availability-{device_id}", 
                                       callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
                
                # Set auth if needed
                if self.mqtt_config['username'] and self.mqtt_config['password']:
                    publisher.username_pw_set(self.mqtt_config['username'], self.mqtt_config['password'])
                
                # Connect and publish
                publisher.connect(self.mqtt_config['host'], self.mqtt_config['port'])
                status = "online" if available else "offline"
                publisher.publish(availability_topic, status, retain=True)
                publisher.disconnect()
                
                logging.info(f"Published availability status '{status}' for {device_name}")
        except Exception as e:
            logging.error(f"Error publishing availability status: {e}")
