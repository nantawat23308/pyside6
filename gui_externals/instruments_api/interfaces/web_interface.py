import requests
import logging


class WebInterface:
    def __init__(self, ip, port, logger_name):
        self._ip = ip
        if port is not None:
            self._port = f":{port}"
        else:
            self._port = ""
        self.logger = logging.getLogger(logger_name)

    def __repr__(self):
        return f"WebInterface {self._ip}:{self._port}"

    def write(self, cmd):
        # parse cmd
        func = cmd.split(" ")[0]
        args = cmd.split(" ")[1:]

        # create and populate data dictionary
        data = dict.fromkeys(args[::2])
        for i, key in enumerate(data.keys()):
            value = args[1::2][i]

            # VM: TODO: try/except would look better here
            if self.__isint(value):
                value = int(value)
            elif self.__isfloat(value):
                value = float(value)
            else:
                value = str(value)
            data[key] = value

        cmd = f"http://{self._ip}{self._port}{func}"
        self.logger.debug(cmd)
        self.logger.debug(data)
        requests.post(cmd, json=data, timeout=5).content.decode()

    def read(self):
        pass

    def query(self, cmd, params=None, bin_data=False, json_data=False):
        if params is None:
            params = {}
        cmd = f"http://{self._ip}{self._port}{cmd}"
        self.logger.debug(cmd)
        if bin_data:
            reply = requests.get(cmd, params=params, timeout=5).content
        else:
            reply = requests.get(cmd, params=params, timeout=5).content.decode()
        self.logger.debug(reply)
        return reply

    def __isfloat(self, x):
        try:
            float(x)
        except (TypeError, ValueError):
            return False
        else:
            return True

    def __isint(self, x):
        try:
            a = float(x)
            b = int(a)
        except (TypeError, ValueError):
            return False
        else:
            return a == b
