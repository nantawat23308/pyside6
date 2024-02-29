import logging
import time
from datetime import datetime
from pathlib import Path
import yaml

import numpy as np
import pandas as pd
from ilock import ILock

from gui_externals.Keithly_2200G import Keithly_2200G
from gui_externals.instruments_api.interfaces.socket_interface import SocketInterface
from gui_externals.instruments_api.interfaces.telnet_interface import TelnetInterface
from gui_externals.instruments_api.interfaces.visa_interface import VISAInterface
from gui_externals.instruments_api.interfaces.web_interface import WebInterface
from gui_externals.instruments_api.optical.opm.keysight_opm import Pwm
from gui_externals.instruments_api.optical.osa.finisar_waveanalyzer import Osa
from gui_externals.instruments_api.optical.switch.santec_switch import Switch
from gui_externals.instruments_api.optical.voa.keysight_voa import Voa
from gui_externals.instruments_api.optical.wave_meter.bristol_wm import BristolWM

from src.initialise_station_configs import LOCK_C_FOLDER, INSTR_YAML_CONFIG, LOCK_C_LOGFILE
from src.common_functions import load_yaml_file


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
        # Load instrument classes
        # TODO: Need to make the bristol WLM use READ not MEAS to increase speed
        self.wlm = BristolWM(interface=TelnetInterface(ip=self._instr_cfg['wlm']['addr']))
                             # skip_msg=self._instr_cfg['wlm']['skip_msg'])
        # self.wlm = BristolWM(interface=SocketInterface(ip=self._instr_cfg['wlm']['addr'],
        #                                                port=self._instr_cfg['wlm']['port']))
        if self._instr_cfg['wlm']['controller'] == 'SocketInterface':
            self.wlm._interface.read()  # Use only for socket interface

        # TODO: Cleanup and reorder set configs, etc. Maybe separate function?
        if self._set_configs_flag:
            self.wlm.set_cfg(**self._instr_cfg['wlm']['config'])
            self.wlm.set_smsr_mode('1')
        logging.debug(f'Bristol WLM, {self.wlm.get_idn()}, connection time: {time.time() - eq_start_time:.2f}s')

        # if DEBUG_FLAG:
        #     eq_start_time = time.time()
        #     self.opm = Voa(interface=VISAInterface(address=self._instr_cfg['voa']['addr'], logger_name='Keysight_VOA'),
        #                    channel=self._instr_cfg['voa']['config']['channel'])
        #     if self._set_configs_flag:
        #         temp_config = self._instr_cfg['voa']['config']
        #         temp_config.pop('channel')
        #         self.opm.set_config(temp_config)
        #     if not hasattr(self.opm, 'get_pwr') and hasattr(self.opm, 'get_pwr_out_dBm'):
        #         self.opm.get_pwr = self.opm.get_pwr_out_dBm
        #     logging.debug(f'Keysight VOA, {self.opm.idn}, connection time: {time.time() - eq_start_time:.2f}s')

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
        # if self._set_configs_flag:
        # self.osw.set_config(self._instr_cfg['osw']['config'])
        logging.debug(f'Santec Switch, {self.osw.idn()}, connection time: {time.time() - eq_start_time:.2}s')

        # if OSA_FLAG:
        #     eq_start_time = time.time()
        #     self.osa = Osa(
        #         interface=WebInterface(ip=self._instr_cfg['osa']['addr'], port=None, logger_name="Finisar_OSA"),
        #         port=self._instr_cfg['osa']['config']['opt_port'])
        #     logging.debug(f'Finisar OSA, {self.osa.idn}, connection time: {time.time() - eq_start_time:.2f}s')

    def get_powers(self, use_cal_values: bool = True):
        """
        Read back the WLM and OPM optical powers

        :param use_cal_values:  Flag which will adjust powers based on calibrated values
        :return:                Dictionary containing WLM Frequency & Power and OPM Power
        """

        out_dict = dict()
        out_dict["WM_pow(dBm)"] = self.wlm.get_pow()
        out_dict["OPM_TxPower(dBm)"] = self.opm.get_pwr()

        if use_cal_values:
            out_dict["WM_pow(dBm)"] += self._wlm_offset
            out_dict["OPM_TxPower(dBm)"] += self._opm_offset

        return out_dict

    def get_freq(self, retry_num: int = 3):
        """
        Return the WLM optical frequency in THz. Will retry up to "retry_num" times.

        :param retry_num: Number of times to try and measure the WLM frequency
        :return:
        """
        freq_val = np.nan
        for _ in range(max([int(retry_num), 1])):
            try:
                freq_val = self.wlm.get_freq()
            except Exception as e:
                logging.warning(e)
            if 190 < freq_val < 197:
                break

        return freq_val

    def close_instruments(self):
        try:
            self.wlm._interface.disconnect()
        except Exception as e:
            logging.warning(e, exc_info=True)
        del self.wlm
        del self.opm
        del self.osw

    def check_instruments(self, out_dict: dict = None):
        if out_dict is None:
            out_dict = {'OPM': {'State': False, 'IDN': ''},
                        'WLM': {'State': False, 'IDN': ''},
                        'OSW': {'State': False, 'IDN': ''},
                        }
        if self.opm is not None:
            out_dict['OPM']['State'] = True
            out_dict['OPM']['IDN'] = self.opm.idn
        if self.wlm is not None:
            out_dict['WLM']['State'] = True
            out_dict['WLM']['IDN'] = self.wlm.get_idn()
        if self.osw is not None:
            out_dict['OSW']['State'] = True
            out_dict['OSW']['IDN'] = self.osw.idn()
        if self.osa is not None:
            out_dict['OSA']['State'] = True
            out_dict['OSA']['IDN'] = self.osa.idn

        return out_dict


class OpticalInstrumentsLock(ILock, OpticalInstruments):

    def __init__(self, tosa_snr: str = 'Unknown', tosa_bay: int = np.nan, set_configs: bool = False, timeout=None,
                 check_interval=1.00):
        super().__init__(name='Optical_lock', lock_directory=LOCK_C_FOLDER.as_posix(), timeout=timeout,
                         check_interval=check_interval, reentrant=False)
        # Load optical calibration values
        tosa_bay = int(tosa_bay)
        # # optical_cal_values = pd.read_fwf(OPTICAL_CAL_CONFIG)
        # if type(tosa_bay) in [int, float] and tosa_bay in list(range(1, 71)):
        #     wlm_offset = optical_cal_values[f'WLM_Bay{tosa_bay:02d}(dB)'].to_list()[-1]
        #     opm_offset = optical_cal_values[f'OPM_Bay{tosa_bay:02d}(dB)'].to_list()[-1]
        # else:
        wlm_offset = 0
        opm_offset = 0
        OpticalInstruments.__init__(self, wlm_offset=wlm_offset, opm_offset=opm_offset, set_configs=set_configs)

        self.tosa_snr = tosa_snr
        self.tosa_bay = tosa_bay
        self._lock_log_file = LOCK_C_LOGFILE.as_posix()
        self._lock_timer = None

    def __enter__(self):
        import portalocker

        if self._enter_count > 0:
            if self._reentrant:
                self._enter_count += 1
                return self
            raise Exception('Trying re-enter a non-reentrant lock')

        logging.debug('Trying to obtain the optical lock')
        current_time = call_time = time.time()
        while call_time + self._timeout >= current_time:
            self._lockfile = open(self._filepath, 'w')
            try:
                portalocker.lock(self._lockfile, portalocker.constants.LOCK_NB | portalocker.constants.LOCK_EX)

                self._lock_timer = time.time()
                # Write info to lock_log
                lock_log = open(self._lock_log_file, 'a')
                lock_log.write(
                    f'[{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}] Permission asked '
                    f'by {self.tosa_snr} in bay #{self.tosa_bay:02d}\n')
                lock_log.close()

                logging.debug(f'Optical lock obtained by {self.tosa_snr} in bay #{self.tosa_bay:02d}')
                self._enter_count = 1
                self.setup_instruments()
                if self.osw is not None:
                    if not np.isnan(self.tosa_bay):
                        logging.debug(f'Setting optical switch to Bay #{self.tosa_bay:02d}')
                        self.osw.set_channel(self.tosa_bay)
                        self.osw.opc_wait()
                        start_time = time.time()
                        while self.osw.get_channel() != self.tosa_bay and abs(time.time() - start_time) < 5:
                            time.sleep(0.1)
                        time.sleep(0.2)
                    else:
                        logging.warning(f'TOSA is in Bay #{self.tosa_bay:02d}. Optical switch was not set.')
                return self
            except portalocker.exceptions.LockException:
                pass

            current_time = time.time()
            check_interval = self._check_interval if self._timeout > self._check_interval else self._timeout
            time.sleep(check_interval)

        raise Exception(f'Maximum Timeout: {self._timeout} sec for waiting optical lock was reached')

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Release the optical locker
        logging.debug('Releasing optical lock')
        super().__exit__(exc_type, exc_val, exc_tb)
        logging.debug('Exited optical lock')
        logging.debug(f'Total optical lock time: {(time.time() - self._lock_timer) / 60:.2f} minute(s)')

        # Write info to lock_log
        lock_log = open(self._lock_log_file, 'a')
        lock_log.write(
            f'[{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}] Exited by {self.tosa_snr} in bay #{self.tosa_bay:02d}\n')
        lock_log.close()

        # Close wlm and switch sections
        self.close_instruments()
