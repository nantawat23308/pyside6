import socket
from pathlib import Path

LOCK_C_FOLDER = Path(r'C:\LockFolder')
Pl_FOLDER = Path(r'C:\PathLossCalFiles')
Pl_FILE = Pl_FOLDER.joinpath('optical_calibration_values.txt')
LOG_Pl_FOLDER = Path(r'C:\LOG_OpticalPathLoss')

LOCK_C_LOGFILE = LOCK_C_FOLDER.joinpath('lock_lock.txt')

ROOT_DIR = Path(__file__).parent.parent
GUI_SETTINGS_DIR = ROOT_DIR.joinpath('gui_settings')
INSTR_YAML_CONFIG = GUI_SETTINGS_DIR.joinpath('instrument_config.yaml')
LOGGING_YAML_CONFIG = GUI_SETTINGS_DIR.joinpath('logging_config.yaml')
STATION_NAME = socket.gethostname()
TOSA_BAY_MAP = GUI_SETTINGS_DIR.joinpath('tosa_bay.yaml')
LIMIT_PathLoss = GUI_SETTINGS_DIR.joinpath('limit_path_loss.yaml')


# log file
def create_log_folders():
    LOG_Pl_FOLDER.mkdir(exist_ok=True)
    LOCK_C_FOLDER.mkdir(exist_ok=True)
    Pl_FOLDER.mkdir(exist_ok=True)

