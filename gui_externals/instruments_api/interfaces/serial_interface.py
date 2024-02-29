import serial
import logging
import time


class SerialInterface:
    def __init__(self, address, baudrate,
                 bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                 prompt: str = "\r", eol: str = "\r", encoding="utf-8",
                 timeout: float = 0.1, logger_name: str = __name__):
        self.logger = logging.getLogger(logger_name)
        self.address = address
        self.baudrate = baudrate
        self.prompt = prompt
        self.eol = eol
        self.encoding = encoding
        self.timeout = timeout
        self.ser = serial.Serial(port=None,
                                 baudrate=self.baudrate,
                                 bytesize=bytesize,
                                 parity=parity,
                                 stopbits=stopbits,
                                 timeout=self.timeout)
        self.connect(self.address)
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

    def __repr__(self) -> str:
        return f"Serial Interface {self.address}"

    def connect(self, com) -> None:
        if type(com) is int:
            com = f"COM{com}"
        self.ser.close()
        self.ser.setPort(com)
        self.ser.open()
        self.logger.debug(f"Serial session to host: {self.address} connected")

    def disconnect(self) -> None:
        if self.ser is not None:
            self.ser.close()
            self.ser = None
        self.logger.debug(f"Serial session to host: {self.address}")

    def write(self, cmd):
        if not cmd.endswith(self.eol):
            cmd += self.eol
        cmd = cmd.encode(self.encoding)
        self.ser.write(cmd)
        self.logger.debug(cmd)

    def read(self):
        reply = self.ser.read_until(expected=self.prompt)
        self.logger.debug(reply)
        reply = reply.decode(self.encoding).rstrip(self.prompt)
        if not reply:
            raise ConnectionError("Data read error: no data")
        return reply

    def query(self, cmd):
        self.write(cmd)
        time.sleep(0.1)
        return self.read()

    def close(self) -> None:
        if self.ser:
            self.disconnect()

    def __del__(self) -> None:
        self.disconnect()
