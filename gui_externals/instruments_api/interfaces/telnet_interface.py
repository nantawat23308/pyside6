import telnetlib
import logging


class TelnetInterface:
    def __init__(self, ip: str, port: int = 23,
                 prompt: str = '\r\n', eol: str = '\r\n',
                 timeout: float = 5.0,
                 logger_name: str = __name__) -> None:
        """ A telnet wrapper based on telnetlib.Telnet.read_until()

        It uses a pre-defined prompt string to determine the end of each read,
        also adds an EOL string at the end of each write, it it's not there
        """
        self.ip = ip
        self.port = port
        self.prompt = prompt  # prompt string used by .read()
        self.eol = eol  # End of Line string used by .write()
        self.timeout = timeout
        self.logger = logging.getLogger(logger_name)

        self.tn = None
        self.logger.debug(
            f"Telnet session to host: {ip} at port: {port} initialized")

    def __repr__(self) -> str:
        return f"Telnet Interface host {self.ip} port {self.port}"

    def connect(self) -> None:
        self.tn = telnetlib.Telnet(self.ip, self.port, self.timeout)
        self.logger.debug(
            f"Telnet session to host: {self.ip} at port: {self.port} "
            f"connected")

    def disconnect(self) -> None:
        if self.tn is not None:
            self.tn.close()
            self.tn = None
        self.logger.debug(
            f"Telnet session to host: {self.ip} at port: {self.port} closed")

    def read(self) -> str:
        buff = self.tn.read_until(self.prompt.encode(), self.timeout).decode()

        if buff.endswith(self.prompt):
            return buff.rstrip(self.prompt)
        else:
            return buff

    def write(self, msg: str) -> None:
        if not msg.endswith(self.eol):
            msg += self.eol

        self.tn.write(msg.encode())

    def query(self, msg: str) -> str:
        self.write(msg)

        return self.read()

    def close(self) -> None:
        if self.tn:
            self.disconnect()

    def __del__(self) -> None:
        self.disconnect()
