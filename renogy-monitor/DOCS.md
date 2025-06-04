# Renogy BT Add-on Documentation

## Overview

This Home Assistant add-on provides automatic detection and monitoring for Renogy solar charge controllers, batteries, and inverters via Bluetooth. It's built on the foundation of the excellent [renogy-bt](https://github.com/cyrils/renogy-bt) library by Cyril Sebastian, with improvements to enhance robustness and compatibility across all Renogy solar components.

## Installation

1. Add this repository to your Home Assistant instance
2. Search for "Renogy BT" in the add-on store
3. Click Install

## Configuration

### Add-on Configuration Options

| Option | Description |
|--------|-------------|
| `scan_interval` | Polling interval in seconds (default: 60) |
| `mqtt.topic_prefix` | MQTT topic prefix for all data |
| `mqtt.discovery` | Enable Home Assistant MQTT discovery |
| `bluetooth.auto_discover` | Automatically discover Bluetooth devices |
| `bluetooth.known_devices` | List of known devices with their details |
| `temperature_unit` | Temperature unit (C or F) |
| `debug` | Enable verbose logging |

### Example Configuration

```yaml
scan_interval: 60
mqtt:
  topic_prefix: "renogy"
  discovery: true
bluetooth:
  auto_discover: true
  known_devices:
    - name: "Solar Controller"
      mac_address: "80:6F:B0:0F:XX:XX"
      device_type: "rover"
      device_id: 255
temperature_unit: "C"
debug: false
```

## Supported Devices

| Device | Supported |
|--------|-----------|
| Renogy Rover/Wanderer/Adventurer Controllers | ✅ |
| Renogy Rover Elite RCC40RVRE Controllers | ✅ |
| Renogy DC-DC Charger DCC50S | ✅ |
| Renogy RBT100LFP12S / RBT50LFP48S Batteries | ✅ |
| Renogy RBT100LFP12-BT / RBT200LFP12-BT Batteries | ✅ |
| Renogy RBT12100LFP-BT / RBT12200LFP-BT Pro Series | ✅ |
| Renogy RIV4835CSH1S Inverters | ✅ |
| Renogy Rego RIV1230RCH Inverters | ✅ |
| Other SRNE-compatible devices | ⚠️ May work |

## Troubleshooting

### Common Issues

- **Device not found**: Ensure your Bluetooth device is powered on and within range.
- **Connection errors**: Verify that Bluetooth is enabled on your Home Assistant host.
- **No data received**: Check debug logs to see if communication with device is successful.

### Debug Mode

Enable debug mode in the add-on configuration to get more detailed logs:

```yaml
debug: true
```

## Credits

This add-on is based on the [renogy-bt](https://github.com/cyrils/renogy-bt) Python library by Cyril Sebastian.
