import logging


class VirtualInterface:
    def __init__(self, logger_name):
        self.logger = logging.getLogger(logger_name)
        self.logger.debug("Virtual interface initialized")

    def __repr__(self):
        return "VirtualInterface"

    def write(self, cmd):
        echo = "1234567890"
        self.logger.debug(echo)
        return echo

    def query(self, cmd):
        echo = "1234567890"
        self.logger.debug(echo)
        return echo

    def close(self):
        self.logger.info("Virtual interface closed")

    def __del__(self):
        self.close()
