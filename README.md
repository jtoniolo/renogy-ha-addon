# Renogy BT Home Assistant Add-on

![Renogy BT Home Assistant Add-on](https://github.com/cyrils/renogy-bt/assets/5549113/bcdef6ec-efc9-44fd-af70-67165cf6862e)

## Overview

This Home Assistant add-on provides automatic detection and monitoring for Renogy solar charge controllers, batteries, and inverters via Bluetooth. It's built on the foundation of the excellent [renogy-bt](https://github.com/cyrils/renogy-bt) library by Cyril Sebastian, with improvements to enhance robustness and compatibility with RBT12200LFP-BT batteries.

## Features

- **Auto-discovery** - Automatically detects compatible Renogy devices
- **Continuous polling** - Real-time data monitoring with configurable intervals
- **MQTT Integration** - Direct integration with Home Assistant's MQTT broker
- **Multi-device support** - Works with multiple controllers, batteries and inverters simultaneously
- **Enhanced compatibility** - Works with all devices supported by the original renogy-bt library
- **Improved reliability** - Better connection handling and error recovery

## Supported Devices

| Device | Type | Adapter | Supported |
| -------- | :-------- | :--------: | :--------: |
| Renogy Rover/Wanderer/Adventurer | Controller | BT-1 | ✅ |
| Renogy Rover Elite RCC40RVRE | Controller | BT-2 | ✅ |
| Renogy DC-DC Charger DCC50S | Controller | BT-2 | ✅ |
| SRNE ML24/ML48 Series | Controller | BT-1 | ✅ |
| RICH SOLAR 20/40/60 | Controller | BT-1 | ✅ |
| Renogy RBT100LFP12S / RBT50LFP48S | Battery | BT-2 | ✅ |
| Renogy RBT100LFP12-BT / RBT200LFP12-BT (Built-in BLE) | Battery | - | ✅ |
| Renogy RBT12100LFP-BT / RBT12200LFP-BT (Pro Series) | Battery | - | ✅ |
| Renogy RIV4835CSH1S | Inverter | BT-2 | ✅ |
| Renogy Rego RIV1230RCH (Built-in BLE) | Inverter | - | ✅ |

## Installation

### Method 1: Home Assistant Add-on Store

1. In Home Assistant, navigate to **Settings** → **Add-ons** → **Add-on Store**
2. Click the three dots in the upper right corner and select **Repositories**
3. Add this repository URL: `https://github.com/yourusername/renogy-ha-addon`
4. Find "Renogy BT" in the list of add-ons and click install

### Method 2: Manual Installation

1. Copy the `renogy-ha-addon` folder to your Home Assistant's `addons` directory
2. Restart Home Assistant
3. Find "Renogy BT" in the list of local add-ons and click install

## Configuration

### Add-on Configuration

```yaml
scan_interval: 60  # Polling interval in seconds
mqtt:
  topic_prefix: "renogy"  # MQTT topic prefix
  discovery: true  # Enable Home Assistant MQTT discovery
bluetooth:
  auto_discover: true  # Automatically discover devices
  known_devices:
    - name: "Solar Controller"  # Optional friendly name
      mac_address: "80:6F:B0:0F:XX:XX"  # MAC address of your Renogy BT module
      device_type: "rover"  # Device type: rover, battery, inverter, dc_charger
      device_id: 255  # Optional device ID for hub mode, defaults to broadcast
```

## Integrating with Home Assistant

Once the add-on is running, entities will be automatically created through MQTT discovery. These will appear under the device name you've configured or the automatically assigned name based on the device type.

### Example Entities:

- Solar power generation
- Battery state of charge
- Charging status
- Battery voltage and current
- Controller temperature
- Daily power generation
- And many more based on your specific device capabilities

## Troubleshooting

### Common Issues:

- **Bluetooth Connection Problems**: Ensure the Bluetooth adapter on your Home Assistant device is working properly. For remote Bluetooth devices, consider using a Bluetooth proxy.
  
- **Device Not Found**: Verify that your Renogy device's Bluetooth module is powered and within range of your Home Assistant device.

- **MQTT Connection Error**: Check that your MQTT broker is running and properly configured in Home Assistant.

### Debug Mode

For advanced troubleshooting, enable debug mode in the add-on configuration:

```yaml
debug: true  # Enable verbose logging
```

## Credits

This add-on is based on the [renogy-bt](https://github.com/cyrils/renogy-bt) Python library by Cyril Sebastian. Significant improvements have been made to the original codebase to enhance compatibility and reliability with all Renogy solar components.

## License

This project is licensed under the same terms as the original library. See the LICENSE file for details.

## Disclaimer

This is not an official add-on endorsed by Renogy. All trademarks are the property of their respective owners.