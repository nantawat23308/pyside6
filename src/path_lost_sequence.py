import time
import logging
from tabulate import tabulate
import pandas as pd
from pathlib import Path
from gui_externals.instruments_api.interfaces.telnet_interface import TelnetInterface
from gui_externals.instruments_api.interfaces.visa_interface import VISAInterface
from gui_externals.instruments_api.optical.opm.keysight_opm import Pwm
from gui_externals.instruments_api.optical.switch.santec_switch import Switch
from gui_externals.instruments_api.optical.wave_meter.bristol_wm import BristolWM

from src.initialise_station_configs import INSTR_YAML_CONFIG, LIMIT_PathLoss
from src.common_functions import load_yaml_file, UserDict, plot_control_chart, verify_limit

user_dict = UserDict.keys_user
WLM_FREQ = "WLM_freq(THz)"
WLM_SMSR = "WLM_SMSR"
CRP = "CRP(dB)"


class OpticalInstruments:
    def __init__(self, wlm_offset: float = 0, opm_offset: float = 0, set_configs: bool = True):
        self.opm = None
        self.wlm = None
        self.osw = None
        self.osa = None
        self._set_configs_flag = set_configs
        self._instr_cfg = None
        self._cfg_file = INSTR_YAML_CONFIG
        self._wlm_offset = wlm_offset
        self._opm_offset = opm_offset
        # self.setup_instruments()

    def load_settings_file(self, cfg_file=None):
        logging.debug("Loading instrument settings from file")
        if cfg_file is None:
            self._instr_cfg = load_yaml_file(self._cfg_file)
        else:
            self._instr_cfg = load_yaml_file(cfg_file)

    def setup_instruments(self):
        if self._instr_cfg is None:
            self.load_settings_file()

        eq_start_time = time.time()
        # TODO: Need to make the bristol WLM use READ not MEAS to increase speed
        self.wlm = BristolWM(interface=TelnetInterface(ip=self._instr_cfg['wlm']['addr']),
                             skip_msg=self._instr_cfg['wlm']['skip_msg'])
        # self.wlm = BristolWM(interface=SocketInterface(ip=self._instr_cfg['wlm']['addr'],
        #                                                port=self._instr_cfg['wlm']['port']))
        if self._instr_cfg['wlm']['controller'] == 'SocketInterface':
            self.wlm._interface.read()  # Use only for socket interface

        # TODO: Cleanup and reorder set configs, etc. Maybe separate function?
        if self._set_configs_flag:
            self.wlm.set_cfg(**self._instr_cfg['wlm']['config'])
            self.wlm.set_smsr_mode('1')
        logging.debug(f'Bristol WLM, {self.wlm.get_idn()}, connection time: {time.time() - eq_start_time:.2f}s')
        eq_start_time = time.time()
        self.opm = Pwm(interface=VISAInterface(address=self._instr_cfg['opm']['addr']),
                       channel=self._instr_cfg['opm']['config']['channel'])
        if self._set_configs_flag:
            temp_config = self._instr_cfg['opm']['config']
            temp_config.pop('channel')
            self.opm.set_config(temp_config)
        logging.debug(f'Keysight OPM, {self.opm.idn},  connection time: {time.time() - eq_start_time:.2}s')

        eq_start_time = time.time()
        self.osw = Switch(VISAInterface(address=self._instr_cfg['osw']['addr'], logger_name='Santec_OSW'))
        logging.debug(f'Santec Switch, {self.osw.idn()}, connection time: {time.time() - eq_start_time:.2}s')

    def set_osx_to_bay(self, channel: int = 0):
        """
        Set Channel OSX to channel ?
        :param channel:
        :return:
        """
        self.osw.set_channel(channel=channel)
        # if self.osw.get_channel() != channel:
        #    raise Exception(f"Cannot Set OSX to {channel}")

    # wlm
    def wlm_get_freq(self):
        """
        THz
        :return:
        """
        return self.wlm.get_freq()

    def wlm_spectrum(self):
        sp = self.wlm.get_spectrum()
        return sp

    def wlm_get_smsr(self, mode: str = '0'):
        """
        SMSR db
        :return:
        """
        return self.wlm.get_smsr(mode=mode)

    def wlm_get_power(self):
        """
        Optical power dBm
        :return:
        """
        if self.wlm.get_pow_unit() == 'dBm':
            return self.wlm.get_pow()

    # opm
    def opm_get_pwr(self):
        """
        TOSA Bay Power
        :return:
        """
        pwr = self.opm.get_pwr()
        return pwr

    def opm_get_pwr_unit(self):
        unit = self.opm.pwr_unit
        return unit


# debug_flag = False
# if debug_flag:
#     case = src.patlost_debug.OpticalInstruments()
# else:
case = OpticalInstruments()


def setup_instrument_config():
    logging.info("Setup Instrument Config on Station")
    try:
        case.setup_instruments()
    except Exception as e:
        logging.error(e)
        raise e


def wait_time(wait):
    logging.info(f"Wait time: {wait} secs")
    time.sleep(wait)
    logging.info("Wait time finish")


def osx_set_channel(channel):
    time.sleep(1)
    case.set_osx_to_bay(channel=channel)
    # print(f"Set Channel Optical Switch on channel: {channel}")
    logging.info(f"Set Channel Optical Switch on channel: {channel}")


def read_wlm_on_port(bay):
    time.sleep(1)
    try:
        wlm_freq = case.wlm_get_freq()
        logging.info(f"Wavelength Frequency: {wlm_freq}")
        user_dict['WLM_freq(THz)'] = wlm_freq
        # print(f"Wavelength Frequency: {wlm_freq}")
    except ValueError as e:
        logging.error(e)

    wlm_smsr = case.wlm_get_smsr()
    logging.info(f"Wavelength SMSR: {wlm_smsr}")

    wlm_pwr = case.opm_get_pwr()
    logging.info(f"Wavelength Power: {wlm_pwr}")

    user_dict['WLM_SMSR'] = wlm_smsr['SMSR']
    user_dict[f'WLM_Bay_RAW{bay:02d}(dB)'] = wlm_pwr
    # print(f"Wavelength SMSR: {wlm_smsr}")
    # print(f"Wavelength Power: {wlm_pwr}")


def read_opm_on_port(bay: int):
    time.sleep(1)
    opm_port = case.opm_get_pwr()
    # print(f"power on port {bay}: {opm_port}")
    user_dict[f'OPM_Bay_RAW{bay:02d}(dB)'] = opm_port
    logging.info(f"Reading OPM {bay:02d}: {opm_port}")


def crp_get_data():
    """
    Get Calibration Reference Power
    CRP
    :return:
    """
    crp_power = case.opm_get_pwr()
    user_dict['CRP(dB)'] = crp_power
    logging.info(f"CRP power: {crp_power}")
    verify_limit(crp_power,
                 user_dict['limit']['laser_source']["CRP_high"],
                 user_dict['limit']['laser_source']["CRP_low"],
                 user_dict['limit']['laser_source']["limit_name"])


def tosa_path_los(bay: int):
    user_dict[f'TPL_Bay{bay:02d}(dB)'] = abs(user_dict['CRP(dB)'] - user_dict[f'OPM_Bay_RAW{bay:02d}(dB)'])
    user_dict[f'OPM_Bay{bay:02d}(dB)'] = user_dict[f'TPL_Bay{bay:02d}(dB)']
    user_dict[f'WLM_Bay{bay:02d}(dB)'] = abs(user_dict['CRP(dB)'] - user_dict[f'WLM_Bay_RAW{bay:02d}(dB)'])
    logging.info(f"CRP: {user_dict['CRP(dB)']}")
    logging.info(f"OPM_Bay {bay} {user_dict[f'OPM_Bay{bay:02d}(dB)']}")
    logging.info(f"TPL {bay}: {user_dict[f'TPL_Bay{bay:02d}(dB)']}")
    verify_limit(user_dict[f'TPL_Bay{bay:02d}(dB)'],
                 user_dict['limit']['path_loss']["loss_high"],
                 user_dict['limit']['path_loss']["loss_low"],
                 user_dict['limit']['path_loss']["limit_name"])
    verify_limit(user_dict[f'OPM_Bay{bay:02d}(dB)'],
                 user_dict['limit']['path_loss']["loss_high"],
                 user_dict['limit']['path_loss']["loss_low"],
                 user_dict['limit']['path_loss']["limit_name"])
    verify_limit(user_dict[f'WLM_Bay{bay:02d}(dB)'],
                 user_dict['limit']['path_loss']["loss_high"],
                 user_dict['limit']['path_loss']["loss_low"],
                 user_dict['limit']['path_loss']["limit_name"])
    # print(f"CRP: {user_dict['CRP(dB)']}")
    # print(f"OPM_Bay {bay} {user_dict[f'OPM_Bay{bay:02d}(dB)']}")
    # print(f"TPL {bay}: {user_dict[f'TPL {bay}']}")


def get_unit_from_opm():
    unit = case.opm_get_pwr_unit()
    logging.info(f"Power Unit OPM: {unit}")
    # print(f"Power Unit OPM: {unit}")
    return unit


def get_wlm_spectrum():
    sp = case.wlm_spectrum()
    logging.info(f"Spectrum :{sp}")
    # print(f"Spectrum :{sp}")


def clean_and_inspect():
    time.sleep(5)
    logging.info("clean and inspect")


def enable_laser_source():
    time.sleep(5)


def patch_character():
    wlm_cols = [f'WLM_Bay{bay_num:02d}(dB)' for bay_num in range(1, 71)]
    opm_cols = [f'OPM_Bay{bay_num:02d}(dB)' for bay_num in range(1, 71)]
    path_cord = [f'Path_Cord_Change_Bay{bay_num:02d}(bool)' for bay_num in range(1, 71)]
    tpl = [f'TPL_Bay{bay_num:02d}(dB)' for bay_num in range(1, 71)]
    cal_cols = ['Iteration(#)', 'Station_ID(#)', 'Operator_ID(#)', 'Datetime(#)', CRP, WLM_FREQ, WLM_SMSR] + \
               [val for pair in zip(wlm_cols, opm_cols, tpl, path_cord) for val in pair]
    return cal_cols


def old_data(filename):
    if filename is not Path:
        filename = Path(filename)
    try:
        df = pd.read_fwf(filename, index_col=["Iteration(#)"])
        index_last = df.index.tolist()[-1]
    except Exception as e:
        logging.error(e)
        raw = tabulate([], list(patch_character()), tablefmt="plain")
        open(filename.as_posix(), "w").write(raw)
        index_last = 0
        df = None
    return df, index_last


def collect_data(filename):
    if user_dict['fail']:
        logging.error("Skip Collect Data: Fail in sequence")
        return False
    if filename is not Path:
        filename = Path(filename)

    if filename is not Path:
        filename = Path(filename)
    try:
        df_old = pd.read_fwf(filename)
        index_last = df_old.iloc[-1]["Iteration(#)"]
    except Exception as e:
        logging.error(e)
        raw = tabulate([], list(patch_character()), tablefmt="plain")
        open(filename.as_posix(), "w").write(raw)
        index_last = 0
        df_old = None
    col_char = patch_character()
    user_dict["Iteration(#)"] = index_last + 1
    df = pd.DataFrame(data=user_dict, columns=col_char, index=[user_dict["Iteration(#)"]])
    df.fillna(0, inplace=True)
    if df_old is not None:
        last_df = pd.concat([df_old, df], ignore_index=True)
    else:
        last_df = df
    value_list = last_df.values.tolist()
    content = tabulate(value_list, list(last_df.columns), tablefmt="plain")
    open(filename.as_posix(), "w").write(content)
    logging.info(f"Write file: {filename}")


def plot_by_data(bay, pl_file, pl_folder):
    if user_dict['fail']:
        logging.error("Skip Plot: Fail in sequence")
        return False
    plot_control_chart(bay, pl_file=pl_file, file_c=pl_folder.joinpath(f"{user_dict['Datetime(#)']}.png"))


def load_limit():
    logging.info("initial bay maping config")
    logging.info(user_dict['Bay_Available'])
    logging.info("___"*50)
    logging.info("loading parameter for limit")
    user_dict['limit'] = load_yaml_file(LIMIT_PathLoss)
    logging.info("load success")
    return user_dict['limit']


def power_laser_check(tolerance):
    crp_power = case.opm_get_pwr()
    user_dict['CRP(dB)_end'] = crp_power
    logging.info(f"CRP power end: {user_dict['CRP(dB)_end']}")

    verify_limit(value=user_dict['CRP(dB)_end'],
                 high=int(user_dict['CRP(dB)']) * ((100 + float(tolerance))/100),
                 low=int(user_dict['CRP(dB)']) * ((100 - float(tolerance))/100),
                 limit_name='Calibration reference power')


if __name__ == '__main__':
    load_limit()
    verify_limit(10,
                 user_dict['limit']['laser_source']["CRP_high"],
                 user_dict['limit']['laser_source']["CRP_low"],
                 user_dict['limit']['laser_source']["limit_name"])



