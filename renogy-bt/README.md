# Renogy BT

![Renogy BT Home Assistant Add-on](https://github.com/cyrils/renogy-bt/assets/5549113/bcdef6ec-efc9-44fd-af70-67165cf6862e)

Monitor Renogy solar devices via Bluetooth. This add-on supports automatic detection and continuous monitoring of Renogy solar charge controllers, batteries, and inverters.

## Features

- Auto-discovery of Renogy Bluetooth devices
- Continuous polling with configurable intervals
- MQTT integration with Home Assistant
- Support for multiple controllers, batteries and inverters
- Enhanced compatibility with all Renogy components

## Changelog

### 0.1.7

- Improved MQTT discovery with full Home Assistant MQTT Discovery compatibility
- Added origin information to discovery messages
- Implemented base topic shorthand (~) for cleaner configuration
- Fixed entity naming using has_entity_name: true pattern
- Ensured all MQTT messages (discovery and state) are retained
- Updated device and entity identifiers for better consistency

### 0.1.6

- Added MQTT authentication support
- Fixed MQTT connection issues with Paho MQTT v2.0+
- Improved error handling and logging
