import logging
import logging.config
import os
from logging import Logger

import colorama
import yaml
from colorama import Back, Fore, Style

LOG_FILE_SET = 'logging.yml'

COLORS = {
    "WARNING": Fore.YELLOW,
    "INFO": Fore.CYAN,
    "DEBUG": Fore.BLUE,
    "CRITICAL": Fore.YELLOW,
    "ERROR": Fore.RED,
}


class ColoredFormatter(logging.Formatter):
    def __init__(self, *, format, use_color):
        logging.Formatter.__init__(self, fmt=format)
        self.use_color = use_color

    def format(self, record):
        msg = super().format(record)
        if self.use_color:
            levelname = record.levelname
            if hasattr(record, "color"):
                return f"{record.color}{msg}{Style.RESET_ALL}"
            if levelname in COLORS:
                return f"{COLORS[levelname]}{msg}{Style.RESET_ALL}"
        return msg


if __name__ == '__main__':
    with open(LOG_FILE_SET, "rt") as f:
        config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)

    logger: Logger = logging.getLogger(__name__)
    # logger.info("Test INFO", extra={"color": Back.RED})
    # logger.info("Test INFO", extra={"color": f"{Style.BRIGHT}{Back.RED}"})
    logger.info("Test INFO")
    logger.debug("Test DEBUG")
    logger.error("Test ERROR", extra={"color": Back.RED})
    logger.warning("Test warning")
    logger.critical("Test Critical")


