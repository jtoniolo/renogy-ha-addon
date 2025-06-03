from .BaseClient import BaseClient
from .Utils import bytes_to_int, format_temperature
import logging
import asyncio
import time

# Client for Renogy LFP battery with built-in bluetooth / BT-2 module

FUNCTION = {
    3: "READ",
    6: "WRITE"
}

# Battery-specific retry settings
MAX_BATTERY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds

class BatteryClient(BaseClient):
    def __init__(self, config, on_data_callback=None, on_error_callback=None):
        super().__init__(config)
        self.on_data_callback = on_data_callback
        self.on_error_callback = on_error_callback
        self.data = {}
        self.attempt_count = 0
        self.sections = [
            {'register': 5000, 'words': 17, 'parser': self.parse_cell_volt_info},
            {'register': 5017, 'words': 17, 'parser': self.parse_cell_temp_info},
            {'register': 5042, 'words': 6, 'parser': self.parse_battery_info},
            {'register': 5122, 'words': 8, 'parser': self.parse_device_info},
            {'register': 5223, 'words': 1, 'parser': self.parse_device_address}
        ]

    def start(self):
        """Override the start method to add battery-specific retry logic"""
        self.attempt_count = 0
        success = self._attempt_start()
        
        # If first attempt fails, try a few more times
        while not success and self.attempt_count < MAX_BATTERY_ATTEMPTS:
            logging.info(f"Retrying battery connection (attempt {self.attempt_count + 1}/{MAX_BATTERY_ATTEMPTS})")
            time.sleep(RETRY_DELAY)
            success = self._attempt_start()
            
        if not success:
            logging.error(f"Failed to connect to battery after {MAX_BATTERY_ATTEMPTS} attempts")
            
    def _attempt_start(self):
        """Helper method that attempts to start the client and returns success status"""
        self.attempt_count += 1
        try:
            # Call the parent class start method
            super().start()
            return True
        except Exception as e:
            logging.warning(f"Battery connection attempt {self.attempt_count} failed: {e}")
            return False
            
    async def read_section(self):
        """Override read_section to add battery-specific connection recovery"""
        try:
            # Call the parent method to do the actual read
            await super().read_section()
        except Exception as e:
            logging.error(f"Error in read_section: {e}")
            # If we're on the first section, attempt to recover connection
            if self.section_index == 0 and self.attempt_count < MAX_BATTERY_ATTEMPTS:
                logging.warning(f"Attempting to recover battery connection (attempt {self.attempt_count}/{MAX_BATTERY_ATTEMPTS})")
                # Try to disconnect cleanly first
                try:
                    if self.ble_manager:
                        await self.ble_manager.disconnect()
                except Exception:
                    pass
                
                # Short delay
                await asyncio.sleep(2)
                
                # Try to reconnect
                try:
                    await self.connect()
                    # If reconnected successfully, try reading again
                    if self.ble_manager and self.ble_manager.client and self.ble_manager.client.is_connected:
                        await super().read_section()
                except Exception as reconnect_error:
                    logging.error(f"Failed to recover battery connection: {reconnect_error}")
                    self.stop()
            else:
                # For other sections or if we've tried too many times, just propagate the error
                raise
                
    def parse_cell_volt_info(self, bs):
        data = {}
        data['function'] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data['cell_count'] = bytes_to_int(bs, 3, 2)
        for i in range(0, data['cell_count']):
            data[f'cell_voltage_{i}'] = bytes_to_int(bs, 5 + i*2, 2, scale = 0.1)
        self.data.update(data)

    def parse_cell_temp_info(self, bs):
        data = {}
        data['function'] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data['sensor_count'] = bytes_to_int(bs, 3, 2)
        for i in range(0, data['sensor_count']):
            celcius = bytes_to_int(bs, 5 + i*2, 2, scale = 0.1, signed = True)
            data[f'temperature_{i}'] = format_temperature(celcius, self.config['data']['temperature_unit'])
        self.data.update(data)

    def parse_battery_info(self, bs):
        data = {}
        data['function'] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data['current'] = bytes_to_int(bs, 3, 2, True, scale = 0.01)
        data['voltage'] = bytes_to_int(bs, 5, 2, scale = 0.1)
        data['remaining_charge'] = bytes_to_int(bs, 7, 4, scale = 0.001)
        data['capacity'] = bytes_to_int(bs, 11, 4, scale = 0.001)
        self.data.update(data)

    def parse_device_info(self, bs):
        data = {}
        data['function'] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data['model'] = (bs[3:19]).decode('utf-8').rstrip('\x00')
        self.data.update(data)

    def parse_device_address(self, bs):
        data = {}
        data['device_id'] = bytes_to_int(bs, 3, 2)
        self.data.update(data)
