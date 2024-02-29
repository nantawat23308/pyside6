import socket
import logging
import time


BUFFER_SIZE = 4096
TIMEOUT_IN_SECONDS = 5
MAX_RETRIES = 1000


class SocketInterface:
    def __init__(self, ip, port, logger_name=__name__,
                 prompt: str = '\r\n', eol: str = '\r\n',
                 cls_before_cmd=False, fragments_enabled=False, encoding="utf-8"):
        self._ip = ip
        self._port = port
        self.prompt = prompt  # prompt string used by .read()
        self.eol = eol  # End of Line string used by .write()
        self.s = None
        self.cls_before_cmd = cls_before_cmd
        self.fragments_enabled = fragments_enabled
        self.encoding = encoding
        self.logger = logging.getLogger(logger_name)

    def __repr__(self):
        return f"SocketInterface {self._ip}:{self._port}"

    def connect(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self.s.settimeout(TIMEOUT_IN_SECONDS)
        self.s.connect((self._ip, self._port))
        self.logger.debug("Connected")

    def disconnect(self):
        if self.s is not None:
            self.s.shutdown(socket.SHUT_RDWR)
            self.s.close()
            self.s = None
            self.logger.debug("Disconnected")

    def write(self, cmd):
        if self.s is None:
            self.connect()

        # TODO: check why commands for VOA sometimes return None without sending *CLS beforehand
        if self.cls_before_cmd:
            self.s.sendall(f"*CLS{self.eol}".encode(self.encoding))
            # self.s.sendall(b"*CLS")

        # the actual command
        if not cmd.endswith(self.eol):
            cmd += self.eol
        self.s.sendall(cmd.encode(self.encoding))
        self.logger.debug(cmd)

    def read(self):
        if self.s is None:
            self.connect()

        # the reply can be fragmented
        if self.fragments_enabled:
            fragments = []
            for _ in range(MAX_RETRIES):
                chunk = self.s.recv(BUFFER_SIZE)
                # print(chunk)
                fragments.append(chunk)
                if chunk.endswith(self.prompt.encode(self.encoding)):
                    break
            data = b''.join(fragments)
        else:
            # TODO: improve robustness including a verification for termination string
            data = self.s.recv(BUFFER_SIZE)

        # the reply can be in hex
        self.logger.debug(data)
        try:
            reply = data.decode(self.encoding).rstrip(self.prompt)
        except UnicodeDecodeError:
            reply = data.rstrip(self.prompt.encode("utf-8")).hex()
        return reply

    def query(self, cmd):
        self.write(cmd)
        # TODO: improve delay between write and read commands to a more general implementation
        time.sleep(0.1)
        return self.read()

    def close(self):
        self.__del__()

    def __del__(self):
        if self.s:
            self.s.close()
        self.logger.debug(f"Socket interface {self._ip} disconnected.")
