import logging
import socket
import time

from src.common_functions import narrowAllowedRange


class Clime_Temp_Event:
    """A class represents Weiss Technik temperature chamber"""

    def __init__(self, address: str, query_delay: float = 0.05):
        self.ip = address
        self.port = 2049
        self.query_delay = float(query_delay)
        self.buff_size = 2 ** 10
        self.delimiter = b'\xb6'
        self.cr = b'\r'
        self.sock = None

        self.target_temperature = None
        self.measured_temperature = None
        self.serial_number = None
        self.max_temperature = 90.0
        self.min_temperature = -50.0

        self.logger = logging.getLogger(__name__)

    def create_cmd(self, cmdID, arglist):
        cmd = cmdID.encode('ascii')  # command ID
        cmd = cmd + self.delimiter + b'1'  # Chb Id
        for arg in arglist:
            cmd = cmd + self.delimiter
            cmd = cmd + arg.encode('ascii')
        cmd = cmd + self.cr
        return cmd

    def write(self, msg):
        self.sock.send(msg)

    def read(self):
        read_data = self.sock.recv(self.buff_size)
        # self.showSimServData(read_data)
        return read_data

    def query(self, msg):
        self.write(msg)
        time.sleep(self.query_delay)
        return self.read()

    def connect(self):
        self.logger.info(f'Connecting to ClimeEvent temperature chamber at {self.ip}:{self.port}')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(2)
        self.sock.connect((self.ip, self.port))

    def close(self):
        self.sock.close()

    def idn(self):
        if self.serial_number is None:
            cmd = self.create_cmd("99997", ["3"])
            self.serial_number = self.query(cmd).split(self.delimiter)[1].decode().split('\r\n')[0]

        return self.serial_number

    def initialise(self):
        # Check connection by requesting serial number
        cmd = self.create_cmd("99997", ["3"])
        self.serial_number = self.query(cmd).split(self.delimiter)[1].decode().split('\r\n')[0]
        self.logger.info(f'Connected to ClimeEvent temperature chamber {self.serial_number} at {self.ip}:{self.port}')

        # Get any messages
        cmd_mess = self.create_cmd("17002", [])
        for msg_num in range(int(self.query(cmd_mess).split(self.delimiter)[1].decode().split('\r\n')[0])):
            cmd_text = self.create_cmd("17007", [str(msg_num + 1)])
            self.logger.info('ClimeEvent queued message(s) {}: {}'.format(msg_num + 1,
                                                                          self.query(cmd_text).split(self.delimiter)[
                                                                              1].decode().split('\r\n')[
                                                                              0]))
            if msg_num > 3:
                break

        # Get current temperature of the chamber
        self.logger.info(f'ClimeEvent initial temperature on connecting: {self.get_measured_temperature():.2f}C')

    def set_gradients(self):
        # Set maximum increase gradient
        self.write(self.create_cmd("11068", ["1", "666"]))
        # Set maximum decrease gradient
        self.write(self.create_cmd("11072", ["1", "666"]))

    def set_temperature(self, set_temp: float):
        self.logger.info(f'Setting chamber target temperature to: {set_temp:.2f}C')
        set_temp = float(set_temp)
        set_temp = narrowAllowedRange(set_temp, max_val=self.max_temperature, min_val=self.min_temperature)
        self.write(self.create_cmd("11001", ["1", str(set_temp)]))
        time.sleep(1)
        self.target_temperature = self.get_setpoint()

        return self.target_temperature

    def get_measured_temperature(self):
        self.measured_temperature = float(
            self.query(self.create_cmd("11004", ["1"])).split(self.delimiter)[1].decode().split('\r\n')[0])
        return self.measured_temperature  # C

    def get_setpoint(self) -> float:
        return float(self.query(self.create_cmd("11002", ["1"])).split(self.delimiter)[1].decode().split('\r\n')[0])

    def activate(self):
        self.logger.info('Activating temperature chamber')
        self.write(self.create_cmd("14001", ["1", "1"]))

    def deactivate(self):
        self.logger.info('Deactivating temperature chamber')
        self.write(self.create_cmd("14001", ["1", "0"]))


if __name__ == '__main__':
    clime_event = Clime_Temp_Event(address='172.16.0.31')
    clime_event.connect()
    clime_event.initialise()
    clime_event.set_temperature(35)
    clime_event.activate()
    clime_event.deactivate()
