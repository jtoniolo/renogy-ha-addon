import asyncio
import configparser
import logging
import traceback
from .BLEManager import BLEManager
from .Utils import bytes_to_int, crc16_modbus, int_to_bytes

# Base class that works with all Renogy family devices
# Should be extended by each client with its own parsers and section definitions
# Section example: {'register': 5000, 'words': 8, 'parser': self.parser_func}

ALIAS_PREFIXES = ['BT-TH', 'RNGRBP', 'BTRIC']
WRITE_SERVICE_UUID = "0000ffd0-0000-1000-8000-00805f9b34fb"
NOTIFY_CHAR_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"
WRITE_CHAR_UUID  = "0000ffd1-0000-1000-8000-00805f9b34fb"
READ_TIMEOUT = 15 # (seconds)
READ_SUCCESS = 3
READ_ERROR = 131

class BaseClient:
    def __init__(self, config):
        self.config: configparser.ConfigParser = config
        self.ble_manager = None
        self.device = None
        self.poll_timer = None
        self.read_timeout = None
        self.data = {}
        self.device_id = self.config['device'].getint('device_id')
        self.sections = []
        self.section_index = 0
        self.loop = None
        logging.info(f"Init {self.__class__.__name__}: {self.config['device']['alias']} => {self.config['device']['mac_addr']}")

    def start(self):
        try:
            self.loop = asyncio.get_event_loop()
            self.loop.create_task(self.connect())
            self.future = self.loop.create_future()
            self.loop.run_until_complete(self.future)
        except asyncio.CancelledError:
            logging.info("Operation was cancelled")
        except Exception as e:
            self.__on_error(e)
        except KeyboardInterrupt:
            self.loop = None
            self.__on_error("KeyboardInterrupt")

    async def connect(self):
        self.ble_manager = BLEManager(mac_address=self.config['device']['mac_addr'], alias=self.config['device']['alias'], on_data=self.on_data_received, on_connect_fail=self.__on_connect_fail, notify_char_uuid=NOTIFY_CHAR_UUID, write_char_uuid=WRITE_CHAR_UUID, write_service_uuid=WRITE_SERVICE_UUID)
        await self.ble_manager.discover()

        if not self.ble_manager.device:
            logging.error(f"Device not found: {self.config['device']['alias']} => {self.config['device']['mac_addr']}, please check the details provided.")
            for dev in self.ble_manager.discovered_devices:
                if dev.name != None and dev.name.startswith(tuple(ALIAS_PREFIXES)):
                    logging.info(f"Possible device found! ====> {dev.name} > [{dev.address}]")
            self.stop()
        else:
            await self.ble_manager.connect()
            if self.ble_manager.client and self.ble_manager.client.is_connected: await self.read_section()

    async def disconnect(self):
        if self.ble_manager:
            await self.ble_manager.disconnect()
        try:
            # Only set the result if the future exists and is not already done
            if hasattr(self, 'future') and self.future and not self.future.done():
                self.future.set_result('DONE')
        except Exception as e:
            logging.debug(f"Error setting future result: {e}")
            # Don't propagate this error as it's not critical

    async def on_data_received(self, response):
        if self.read_timeout and not self.read_timeout.cancelled(): 
            self.read_timeout.cancel()
        
        try:
            operation = bytes_to_int(response, 1, 1)

            if operation == READ_SUCCESS or operation == READ_ERROR:
                if (operation == READ_SUCCESS and
                    self.section_index < len(self.sections) and
                    self.sections[self.section_index]['parser'] != None and
                    self.sections[self.section_index]['words'] * 2 + 5 == len(response)):
                    # call the parser and update data
                    logging.info(f"on_data_received: read operation success")
                    self.__safe_parser(self.sections[self.section_index]['parser'], response)
                else:
                    logging.info(f"on_data_received: read operation failed or unexpected data: {response.hex()}")
                    # Continue anyway - this allows the script to proceed even with some errors

                if self.section_index >= len(self.sections) - 1: # last section, read complete
                    self.section_index = 0
                    self.on_read_operation_complete()
                    self.data = {}
                    await self.check_polling()
                else:
                    self.section_index += 1
                    await asyncio.sleep(0.5)
                    await self.read_section()
            else:
                logging.warning(f"on_data_received: unknown operation={operation}, data: {response.hex()}")
                # Continue to next section even if this one failed
                if self.section_index < len(self.sections) - 1:
                    self.section_index += 1
                    await asyncio.sleep(0.5)
                    await self.read_section()
                else:
                    self.section_index = 0
                    self.on_read_operation_complete()
                    self.data = {}
                    await self.check_polling()
        except Exception as e:
            logging.error(f"Error in on_data_received: {e}")
            # Continue to next section even if there was an error
            if self.section_index < len(self.sections) - 1:
                self.section_index += 1
                await asyncio.sleep(0.5)
                await self.read_section()
            else:
                self.section_index = 0
                self.on_read_operation_complete()
                self.data = {}
                await self.check_polling()

    def on_read_operation_complete(self):
        logging.info("on_read_operation_complete")
        self.data['__device'] = self.config['device']['alias']
        self.data['__client'] = self.__class__.__name__
        self.__safe_callback(self.on_data_callback, self.data)

    def on_read_timeout(self):
        logging.error("on_read_timeout => Timed out! Please check your device_id!")
        self.stop()

    async def check_polling(self):
        if self.config['data'].getboolean('enable_polling'): 
            await asyncio.sleep(self.config['data'].getint('poll_interval'))
            await self.read_section()

    async def read_section(self):
        index = self.section_index
        if self.device_id == None or len(self.sections) == 0:
            return logging.error("BaseClient cannot be used directly")

        if not self.ble_manager or not self.ble_manager.client or not self.ble_manager.client.is_connected:
            logging.error("Cannot read section - BLE client is not connected")
            self.stop()
            return
            
        self.read_timeout = self.loop.call_later(READ_TIMEOUT, self.on_read_timeout)
        request = self.create_generic_read_request(self.device_id, 3, self.sections[index]['register'], self.sections[index]['words']) 
        await self.ble_manager.characteristic_write_value(request)

    def create_generic_read_request(self, device_id, function, regAddr, readWrd):                             
        data = None                                
        if regAddr != None and readWrd != None:
            data = []
            data.append(device_id)
            data.append(function)
            data.append(int_to_bytes(regAddr, 0))
            data.append(int_to_bytes(regAddr, 1))
            data.append(int_to_bytes(readWrd, 0))
            data.append(int_to_bytes(readWrd, 1))

            crc = crc16_modbus(bytes(data))
            data.append(crc[0])
            data.append(crc[1])
            logging.debug("{} {} => {}".format("create_request_payload", regAddr, data))
        return data

    def __on_error(self, error = None):
        logging.error(f"Exception occured: {error}")
        self.__safe_callback(self.on_error_callback, error)
        self.stop()

    def __on_connect_fail(self, error):
        error_str = str(error)
        
        # Check if this is the specific BleakDBusError that we can safely ignore
        if "BleakDBusError" in error_str and "Operation is not supported" in error_str:
            logging.warning(f"Connection warning (non-fatal): {error}")
            logging.info("Ignoring 'Operation is not supported' error and continuing...")
            # Don't call stop() or the error callback here, let operations continue
            return
            
        # For other errors, log and handle normally
        logging.error(f"Connection failed: {error}")
        self.__safe_callback(self.on_error_callback, error)
        self.stop()

    def stop(self):
        if self.read_timeout and not self.read_timeout.cancelled(): self.read_timeout.cancel()
        if self.loop is None:
            self.loop = asyncio.get_event_loop()
            self.loop.create_task(self.disconnect())
            self.future = self.loop.create_future()
            self.loop.run_until_complete(self.future)
        else:
            self.loop.create_task(self.disconnect())

    def __safe_callback(self, calback, param):
        if calback is not None:
            try:
                calback(self, param)
            except Exception as e:
                logging.error(f"__safe_callback => exception in callback! {e}")
                traceback.print_exc()

    def __safe_parser(self, parser, param):
        if parser is not None:
            try:
                parser(param)
            except Exception as e:
                logging.error(f"exception in parser! {e}")
                traceback.print_exc()
