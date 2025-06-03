import asyncio
import logging
import sys
import time
from bleak import BleakClient, BleakScanner, BLEDevice
from bleak.exc import BleakDBusError

DISCOVERY_TIMEOUT = 5 # max wait time to complete the bluetooth scanning (seconds)
MAX_RETRIES = 3  # maximum number of retries for BLE operations

class BLEManager:
    def __init__(self, mac_address, alias, on_data, on_connect_fail, write_service_uuid, notify_char_uuid, write_char_uuid):
        self.mac_address = mac_address
        self.device_alias = alias
        self.data_callback = on_data
        self.connect_fail_callback = on_connect_fail
        self.write_service_uuid = write_service_uuid
        self.notify_char_uuid = notify_char_uuid
        self.write_char_uuid = write_char_uuid
        self.write_char_handle = None
        self.device: BLEDevice = None
        self.client: BleakClient = None
        self.discovered_devices = []

    async def discover(self):
        mac_address = self.mac_address.upper()
        logging.info("Starting discovery...")
        self.discovered_devices = await BleakScanner.discover(timeout=DISCOVERY_TIMEOUT)
        logging.info("Devices found: %s", len(self.discovered_devices))

        for dev in self.discovered_devices:
            if dev.address != None and (dev.address.upper() == mac_address or (dev.name and dev.name.strip() == self.device_alias)):
                logging.info(f"Found matching device {dev.name} => {dev.address}")
                self.device = dev

    async def connect(self):
        if not self.device: return logging.error("No device connected!")

        self.client = BleakClient(self.device)
        try:
            await self.client.connect()
            logging.info(f"Client connection: {self.client.is_connected}")
            if not self.client.is_connected: return logging.error("Unable to connect")

            # First, find the notification characteristic
            notify_success = False
            for service in self.client.services:
                for characteristic in service.characteristics:
                    if characteristic.uuid == self.notify_char_uuid:
                        try:
                            await self.client.start_notify(characteristic, self.notification_callback)
                            logging.info(f"Subscribed to notification {characteristic.uuid}")
                            notify_success = True
                        except BleakDBusError as e:
                            # Handle the specific "Operation is not supported" error
                            if "Operation is not supported" in str(e):
                                logging.warning(f"BleakDBusError 'Operation is not supported' when subscribing to notifications. Will continue anyway.")
                                notify_success = True  # Consider it a success and continue
                            else:
                                logging.error(f"Error subscribing to notification: {e}")
                                raise
                        except Exception as e:
                            logging.error(f"Error subscribing to notification: {e}")
                    
            if not notify_success:
                logging.warning("Could not subscribe to notifications, but continuing anyway")
                    
            # Look for the write characteristic in the specified service
            found_write_char = False
            for service in self.client.services:
                if service.uuid == self.write_service_uuid:
                    for characteristic in service.characteristics:
                        if characteristic.uuid == self.write_char_uuid:
                            found_write_char = True
                            logging.info(f"Found write characteristic {characteristic.uuid}, service {service.uuid}")
            
            if not found_write_char:
                logging.warning(f"Could not find write characteristic {self.write_char_uuid} in service {self.write_service_uuid}")
                logging.info("Available services and characteristics:")
                for service in self.client.services:
                    logging.info(f"  Service: {service.uuid}")
                    for char in service.characteristics:
                        logging.info(f"    Characteristic: {char.uuid}")

        except BleakDBusError as e:
            # Specifically handle the known problematic error
            if "Operation is not supported" in str(e):
                logging.warning(f"Caught BleakDBusError 'Operation is not supported'. Will continue with connection.")
                # Don't call the failure callback, let the operation continue
            else:
                logging.error(f"BleakDBusError connecting to device: {e}")
                self.connect_fail_callback(e)
        except Exception as e:
            logging.error(f"Error connecting to device: {e}")
            self.connect_fail_callback(e)

    async def notification_callback(self, characteristic, data: bytearray):
        logging.info("notification_callback")
        try:
            await self.data_callback(data)
        except Exception as e:
            logging.error(f"Error in notification callback: {e}")
            # Don't propagate the exception as it might break the notification chain

    async def characteristic_write_value(self, data):
        if not data:
            logging.warning("No data provided for writing")
            return
        
        retries = 0
        while retries < MAX_RETRIES:
            try:
                # Find the service with the specified UUID
                services = self.client.services
                for service in services:
                    if service.uuid.lower() == self.write_service_uuid.lower():
                        # Find the characteristic with the specified UUID
                        for characteristic in service.characteristics:
                            if characteristic.uuid.lower() == self.write_char_uuid.lower():
                                logging.info(f'Writing to characteristic {self.write_char_uuid} {data}')
                                await self.client.write_gatt_char(characteristic, bytearray(data), response=False)
                                logging.info('characteristic_write_value succeeded')
                                await asyncio.sleep(0.5)
                                return
                
                # If we get here, we didn't find the service/characteristic
                logging.error(f"Could not find service {self.write_service_uuid} with characteristic {self.write_char_uuid}")
                logging.info("Available services and characteristics:")
                for service in self.client.services:
                    logging.info(f"  Service: {service.uuid}")
                    for char in service.characteristics:
                        logging.info(f"    Characteristic: {char.uuid}")
                break  # No need to retry if we can't find the characteristic
                        
            except BleakDBusError as e:
                if "Operation is not supported" in str(e):
                    logging.warning(f"BleakDBusError 'Operation is not supported' when writing characteristic. Attempt {retries+1}/{MAX_RETRIES}")
                    retries += 1
                    if retries < MAX_RETRIES:
                        await asyncio.sleep(1)  # Wait before retrying
                    else:
                        logging.error(f"Failed to write characteristic after {MAX_RETRIES} attempts")
                else:
                    logging.error(f"characteristic_write_value failed with BleakDBusError: {e}")
                    break
            except Exception as e:
                logging.error(f'characteristic_write_value failed: {e}')
                break

    async def disconnect(self):
        if self.client and self.client.is_connected:
            logging.info(f"Exit: Disconnecting device: {self.device.name} {self.device.address}")
            await self.client.disconnect()
