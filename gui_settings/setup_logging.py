import logging
import logging.config
import logging.handlers
import threading
from multiprocessing import Queue

from src.common_functions import load_yaml_file

q = Queue()


def create_logging_thread(q_in: Queue):
    while True:
        record = q_in.get()
        if record is None:
            break
        logger = logging.getLogger(record.name)
        logger.handle(record)


def start_logging_thread(log_cfg_yaml: str = None, q_in: Queue = q, log_filename: str = None):
    if log_cfg_yaml is None:
        from src.initialise_station_configs import LOGGING_YAML_CONFIG
        log_cfg_yaml = LOGGING_YAML_CONFIG.as_posix()
    log_config = load_yaml_file(log_cfg_yaml)
    if log_filename is not None:
        log_config['handlers']['file']['filename'] = log_filename
    logging.config.dictConfig(log_config)
    log_thread = threading.Thread(target=create_logging_thread, args=(q_in,))
    log_thread.start()
    logging.info('Started logging thread.')
    return log_thread


def stop_logging_thread(log_thread, q_in: Queue):
    logging.info('Stopping logging thread.')
    q_in.put(None)
    log_thread.join()


# def create_process_logger(q_in=q):
#     qh = logging.handlers.QueueHandler(q_in)
#     root = logging.getLogger()
#     root.setLevel(logging.DEBUG)
#     root.addHandler(qh)
#     # root.info(f'Created logger for board')
#
#     return q_in


def create_process_logger(q_in: Queue):
    root = logging.getLogger()
    # Check if a handler already exists for the current process
    for handler in root.handlers:
        if isinstance(handler, logging.handlers.QueueHandler) and handler.queue == q_in:
            return q_in

    qh = logging.handlers.QueueHandler(q_in)
    root.setLevel(logging.DEBUG)
    root.addHandler(qh)

    return q_in
