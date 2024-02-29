import pyvisa
import logging


TIMEOUT_IN_SECONDS = 5


class VISAInterface:
    def __init__(self, address, logger_name=__name__, backend='@ivi'):
        visa_logger = logging.getLogger('pyvisa')
        visa_logger.setLevel(logging.INFO)  # pyvisa generates too many debug messages
        self.rm = pyvisa.ResourceManager(backend)
        self.address = address
        self.inst = self.rm.open_resource(address)
        self.inst.timeout = TIMEOUT_IN_SECONDS * 1000
        self.logger = logging.getLogger(logger_name)

    def write(self, cmd):
        self.logger.debug(cmd)
        self.inst.write(cmd)

    def read(self):
        reply = self.inst.read()
        self.logger.debug(reply)
        return reply

    def read_raw(self):
        reply = self.inst.read_raw()
        self.logger.debug(reply)
        return reply

    def query(self, cmd):
        self.logger.debug(cmd)
        reply = self.inst.query(cmd)
        self.logger.debug(reply.strip())
        return reply.strip()

    def close(self):
        self.__del__()

    def __del__(self):
        if self.inst:
            self.inst.close()
        self.logger.debug(f"VISA interface {self.address} disconnected.")
