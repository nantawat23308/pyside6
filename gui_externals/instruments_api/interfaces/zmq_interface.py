"""
Client interface for the Coherent Line Rack devices

Author: Vadim Murzin
created: 11-2021
modified: 02-2022

Implementation details:
There should be only 1 server instance runnning at a time.
Multiple asynchronous clients (threads/processes) can communicate without any additional synchronization.
ZMQ library is responsible for serialization of the messages.
The server abstracts interfaces, so it doesn't know anything about device states.
"""


import zmq
import logging


TIMEOUT_IN_SECONDS = 10
SERVER_IP = "10.1.99.24"
# SERVER_IP = "localhost"
SERVER_PORT = "5555"


class ZMQInterface:
    def __init__(self, interface_id):
        self.interface_id = interface_id
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.setsockopt(zmq.RCVTIMEO, TIMEOUT_IN_SECONDS*1000)
        self.socket.connect(f"tcp://{SERVER_IP}:{SERVER_PORT}")
        self.logger = logging.getLogger(interface_id)
        self.logger.debug(f"Connection to {SERVER_IP}:{SERVER_PORT} opened")

    def _zmq_com(self, func, arg):
        self.logger.debug(f"Sending: {self.interface_id} - {func} - {arg}")
        self.socket.send_multipart([self.interface_id.encode(), func.encode(), arg.encode()])
        reply_b = self.socket.recv()
        reply = reply_b.decode()
        if reply:
            if reply.startswith('Error'):
                self.logger.error(f"Received {reply}")
                raise RuntimeError(f"The command {func} - {arg} failed: {reply}")
        self.logger.debug(f"Received: {reply}")
        return reply

    def write(self, cmd: str) -> str:
        return self._zmq_com("write", cmd)

    def query(self, cmd: str) -> str:
        return self._zmq_com("query", cmd)

    def read(self, cmd: str) -> str:
        return self._zmq_com("read", cmd)

    def close(self):
        self.socket.close()
        self.context.term()
        self.logger.debug(f"Connection to {SERVER_IP}:{SERVER_PORT} closed")

    def __del__(self):
        self.close()


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s - %(name)6s - %(levelname)5s - %(message)s', level=logging.DEBUG)
    interfaces = []
    for i in range(10):
        interfaces.append(ZMQInterface("test"))
        interfaces[-1].query("IDN?")
        interfaces[-1].query("POW?")
