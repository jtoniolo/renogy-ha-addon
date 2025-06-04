# Changelog

## 0.1.9

- Completely refactored MQTT handling into a modular DeviceManager class
- Standardized message formats and topic structures across all device types
- Added dynamic discovery for battery-specific entities like cell voltages
- Improved entity naming and organization by device type
- Fixed inconsistencies between different device types (controllers, batteries, inverters)
- Consolidated duplicate code for better maintainability
- Fixed discovery topics to use the configured MQTT topic_prefix instead of hardcoded "homeassistant"

## 0.1.0

- Initial release
- Auto-discovery of Renogy Bluetooth devices
- MQTT integration with Home Assistant
- Support for controllers, batteries and inverters
