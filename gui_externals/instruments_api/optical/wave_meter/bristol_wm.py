from __future__ import annotations

import logging
from struct import unpack
import numpy as np
from .abs_wm import AbsWM  # also thz_to_nm() and nm_to_thz()

logger = logging.getLogger(__name__)


class BristolWM(AbsWM):
    """ A class for Bristol Wavelength Meter """

    def __init__(self, interface, skip_msg: bool = True) -> None:
        self.avg_cnt_min = 2  # Averaging Count Min
        self.avg_cnt_max = 128  # Averaging Count Max
        self.wav_lmt_min = 1266.0  # Wavelength Limit Min in nm
        self.wav_lmt_max = 1680.0  # Wavelength Limit Max in nm
        self.smsr_excl_min = 0.1  # SMSR Exclusion Min in nm
        self.smsr_excl_max = 99.99  # SMSR Exclusion Max in nm
        self.smsr_rng_min = 1.0  # SMSR Range Min in nm
        self.smsr_rng_max = 1000.0  # SMSR Range Max in nm

        self._interface = interface
        self._interface.prompt = '\r\n'
        self._interface.eol = '\r\n'
        self._method_str = 'MEAS'  # Options are: 'MEAS', 'READ', or 'FETCH'
        if hasattr(self._interface, 'tn'):
            self._int_type = 'telnet'
        elif hasattr(self._interface, 's') and hasattr(self._interface, 'fragments_enabled'):
            self._int_type = 'socket'
        try:
            self._interface.connect()
            if skip_msg and hasattr(self._interface, 'tn'):
                # Only skip message is telnet interface and skip_msg is True
                self._skip_opening_msg(0.5)  # to skip the opening message
        except EOFError:
            raise EOFError(
                'No connection available. Instrument already connected?')
        except OSError:
            raise OSError("Connection can't be established!")


    def _skip_opening_msg(self, wait_sec: float) -> None:
        """ To skip the opening message

        Bristol Wavemeter sends out couple lines of messages
        when a Telnet connection is established:

        Mity Telnet Server\r\n
        Copyright 2012, Critical Link LLC\r\n
        \n
        Ctrl-D - Exit\r\n
        Ctrl-E - Toggle Echo\r\n
        \n
        """
        logger.debug('Opening Telnet connection...')
        skip_count = 0
        while True:
            out = self._interface.tn.read_until(b'\n\n', wait_sec)
            if out == b'':
                skip_count += 1
                if skip_count > 2:
                    break

    def get_cfg(self, **kwargs: dict[str, str | float]) -> None:
        """ Gets a group of settings of the instrument """
        cfg_list = [
            'avg_stat', 'avg_cnt', 'pow_offset',
            'wave_lmt_start', 'wave_lmt_end', 'meas_method'
        ]

        for kw, _ in kwargs.items():
            if kw.lower() in cfg_list:
                func_name = f'self.get_{kw.lower()}'
                eval(func_name)()
            else:
                logger.warning(f'Not a valid setting to get: {kw}')

    def set_cfg(self, **kwargs: dict[str, str | float]) -> None:
        """ Sets a group of settings to the instrument """
        cfg_list = [
            'avg_stat', 'avg_cnt', 'pow_offset',
            'wave_lmt_start', 'wave_lmt_end', 'meas_method',
            'smsr_rng', 'smsr_excl', 'smsr_mode', 'pow_unit',
            'wavelen_unit', 'smsr_stat'
        ]

        for kw, val in kwargs.items():
            if kw.lower() in cfg_list:
                func_name = f'self.set_{kw.lower()}'
                eval(func_name)(kwargs[kw])
            else:
                logger.warning(f'Not settable: {kw} = {val}')

    def get_idn(self) -> str:
        msg = '*IDN?'

        return self._interface.query(msg)

    def is_operation_done(self) -> bool:
        """ Returns if the current operation is complete

        This is done by querying the operation complete bit
        of the standardevent status register
        """
        msg = '*OPC?'

        is_done = self._interface.query(msg)
        if is_done == '1':
            return True
        else:
            return False

    def reset_settings(self) -> None:
        """ Resets instrument to factory default settings """
        msg = '*RST'

        self._interface.write(msg)

    def restore_settings(self) -> None:
        """ Restores the most recently saved instrument settings """
        msg = '*RCL'

        self._interface.write(msg)

    def save_settings(self) -> None:
        """ Saves current instrument settings """
        msg = '*SAV'

        self._interface.write(msg)

    def get_avg_stat(self) -> str:
        """ Queries state of the spectral averaging

        When average state is ON, interferograms from the number of scans,
        which is set by averaging count,
        are collected prior to computing a spectrum
        """
        msg = ':CALCulate2:AVER:STATe?'

        return self._interface.query(msg)

    def set_avg_stat(self, avg_stat: str) -> bool:
        """ Sets state of the spectral averaging """
        valid_val = ['ON', 'OFF']
        avg_stat = avg_stat.upper()

        if avg_stat in valid_val:
            msg = f':CALCulate2:AVER:STATe {avg_stat}'
            self._interface.write(msg)
            return True
        else:
            logger.warning(f'Not a valid averaging state to set: {avg_stat}')
            return False

    def get_avg_cnt(self) -> str:
        """ Gets the number of scans to collect
        for each computation of the spectrum
        """
        msg = ':CALCulate2:AVER:COUNt?'

        return self._interface.query(msg)

    def set_avg_cnt(self, avg_cnt: int) -> bool:
        """ Sets the number of scans to collect
        for each computation of the spectrum
        """
        avg_cnt = round(avg_cnt)
        if avg_cnt < self.avg_cnt_min:
            logger.warning(f'Try to set Averaging Count to {avg_cnt}, ' +
                           f'coerced to {self.avg_cnt_min}')
            avg_cnt = self.avg_cnt_min
        elif avg_cnt > self.avg_cnt_max:
            logger.warning(f'Try to set Averaging Count to {avg_cnt}, ' +
                           f'coerced to {self.avg_cnt_max}')
            avg_cnt = self.avg_cnt_max
        msg = f':CALCulate2:AVER:COUNt {avg_cnt}'
        return self._interface.write(msg)

    def get_freq(self) -> float:
        """ Reads the frequency """
        msg = f':{self._method_str}:FREQ?'

        return float(self._interface.query(msg))

    def get_medium(self) -> str:
        msg = ':SENS:MED?'

        return self._interface.query(msg)

    def set_medium(self, med: str) -> bool:
        valid_val = ['AIR', 'VAC']

        med = med.upper()
        if med in valid_val:
            msg = f':SENS:MED {med}'
            self._interface.write(msg)
            return True
        else:
            logger.warning(f'Not a valid medium to set: {med}')
            return False

    def set_meas_method(self, method_str: str = 'MEAS') -> bool:
        """
        Set the measurement method to one of: 'MEAS', 'READ', 'FETCH'.
        See the manual for information on the different methods.
        """
        method_str = method_str.upper()
        valid_methods = ['MEAS', 'READ', 'FETCH']
        if method_str not in valid_methods:
            logger.warning(f'{method_str} is not a valid option. '
                           f'Measurement method must be one of: '
                           f'{valid_methods}')
            return False
        else:
            self._method_str = method_str
            return True

    def get_meas_method(self) -> str:
        """
        Returns the method used for measurements
        """
        return self._method_str

    def get_pow(self) -> float:
        msg = f':{self._method_str}:POW?'

        return float(self._interface.query(msg))

    def get_pow_unit(self) -> str:
        """ Queries the power units

        Note: this refers to the unit that will be used
        when the SCPI interface returns calculated values
        """
        msg = ':UNIT:POW?'

        return self._interface.query(msg)

    def set_pow_unit(self, unit: str) -> bool:
        """ Sets the power units

        Note: this refers to the unit that will be used
        when the SCPI interface returns calculated values
        """
        valid_val = ['DBM', 'MW']

        unit = unit.upper()
        if unit in valid_val:
            msg = f':UNIT:POW {unit}'
            self._interface.write(msg)
            return True
        else:
            logger.warning(f'Not a valid unit to set: {unit}')
            return False

    def get_pow_offset(self) -> str:
        msg = ':SENS:POW:OFFS?'

        return self._interface.query(msg)

    def set_pow_offset(self, offset: str) -> bool:
        valid_val = [str(n) for n in range(1, 21)]
        valid_val.append('OFF')

        offset = offset.upper()
        if offset in valid_val:
            msg = f':SENS:POW:OFFS {offset}'
            self._interface.write(msg)
            return True
        else:
            logger.warning(f'Not a valid power offset to set: {offset}')
            return False

    def get_wavelen(self) -> float:
        """ Reads the wavelength """
        msg = f':{self._method_str}:WAV?'

        return float(self._interface.query(msg))

    def get_wavelen_unit(self) -> str:
        """ Queries the wavelength units

        Note: this refers to the unit that will be used
        when the SCPI interface returns calculated values
        """
        msg = ':UNIT:WAV?'

        return self._interface.query(msg)

    def set_wavelen_unit(self, unit: str) -> bool:
        """ Sets the wavelength units

        Note: this refers to the unit that will be used
        when the SCPI interface returns calculated values
        """
        valid_val = ['NM', 'THZ', 'WNUM']
        unit = unit.upper()

        if unit in valid_val:
            msg = f':UNIT:WAV {unit}'
            self._interface.write(msg)
            return True
        else:
            logger.warning(f'Not a valid unit to set: {unit}')
            return False

    def get_wavenumber(self) -> int:
        """ Reads the wavenumber """
        msg = f':{self._method_str}:WNUM?'

        return int(self._interface.query(msg))

    def get_wave_lmt_start(self) -> float:
        """ Gets the starting wavelength in the spectrum """
        msg = ':CALC2:WLIM:STAR?'

        return float(self._interface.query(msg))

    def set_wave_lmt_start(self, wav: float) -> bool:
        """ Sets the starting wavelength in the spectrum """
        # enforce wav in the range of self.wav_lmt_min - self.wav_lmt_max
        if wav < self.wav_lmt_min:
            wav = self.wav_lmt_min
        elif wav > self.wav_lmt_max:
            wav = self.wav_lmt_max

        msg = f':CALC2:WLIM:STAR {wav}'
        return self._interface.write(msg)

    def get_wave_lmt_end(self) -> float:
        """ Gets the ending wavelength in the spectrum """
        msg = ':CALC2:WLIM:STOP?'

        return float(self._interface.query(msg))

    def set_wave_lmt_end(self, wav: float) -> bool:
        """ Sets the ending wavelength in the spectrum """
        # enforce wav in the range of self.wav_lmt_min - self.wav_lmt_max
        if wav < self.wav_lmt_min:
            logger.warning(f'Try to set Wavelength to {wav}, ' +
                           f'coerced to {self.wav_lmt_max}')
            wav = self.wav_lmt_min
        elif wav > self.wav_lmt_max:
            wav = self.wav_lmt_max

        msg = f':CALC2:WLIM:STOP {wav}'
        return self._interface.write(msg)

    def get_smsr(self, mode: str = '0') -> str | dict[str, float]:
        """ Returns the side mode suppression ratio (SMSR) values

        There are three modes, corresponding to different output format:
        Mode 1: Lambda1, I1, Delta-Lambda, SMSR
        Mode 2: Lambda1, I1, Delta-Lambda-R, SMSR-R, Delta-Lambda-B, SMSR-B
        Mode 3: Lambda1, I1, Lambda-R, I-R, Lambda-B, I-B
        """
        msg = f':{self._method_str}:SMSR?'
        smsr = {}

        smsr_raw = self._interface.query(msg)
        if smsr_raw == 'SMSR off':
            return smsr_raw
        else:
            if mode == '0':  # get SMSR mode if user doesn't provide it
                mode = self.get_smsr_mode()

            if mode == '1':
                smsr['SMSR'] = float(smsr_raw.rsplit(',', 1)[1])
            elif mode == '2':
                smsr['SMSR-Red'] = float(smsr_raw.split(',')[3])
                smsr['SMSR-Blue'] = float(smsr_raw.split(',')[5])
            elif mode == '3':
                pow_peak = float(smsr_raw.split(',')[1])
                smsr['SMSR-Red'] = float(smsr_raw.split(',')[3]) - pow_peak
                smsr['SMSR-Blue'] = float(smsr_raw.split(',')[5]) - pow_peak
            else:
                smsr['SMSR'] = 0.0

            return smsr

    def get_smsr_mode(self) -> str:
        """ Gets the mode of SMSR calculation """
        msg = ':CALCulate2:SMSR:MODE?'

        return self._interface.query(msg)

    def set_smsr_mode(self, mode: str) -> bool:
        """ Sets the mode of SMSR calculation """
        valid_val = ['1', '2', '3']

        if mode in valid_val:
            msg = f':CALCulate2:SMSR:MODE {mode}'
            self._interface.write(msg)
            return True
        else:
            logger.warning(f'Not a valid SMSR mode to set: {mode}')
            return False

    def get_smsr_excl(self) -> float:
        """ Queries the exclusion region around the main peak

        The units for the query are in nanometers
        """
        msg = ':CALCulate2:SMSR:EXCLusion?'

        return float(self._interface.query(msg))

    def set_smsr_excl(self, excl: float) -> bool:
        """ Sets the exclusion region around the main peak

        The units are in nm and must be within the range of 0.1 nm to 99.99 nm
        """
        if excl < self.smsr_excl_min:
            logger.warning(f'Try to set SMSR Exclusion to {excl}, ' +
                           f'coerced to {self.smsr_excl_min}')
            excl = self.smsr_excl_min
        elif excl > self.smsr_excl_max:
            logger.warning(f'Try to set SMSR Exclusion to {excl}, ' +
                           f'coerced to {self.smsr_excl_max}')
            excl = self.smsr_excl_max
        msg = f':CALCulate2:SMSR:EXCLusion {excl}'
        return self._interface.write(msg)

    def get_smsr_rng(self) -> float:
        """ Gets the range over which the SMSR cal. identifies a side-mode

        The units for the query are in nanometers
        """
        msg = ':CALCulate2:SMSR:RANGe?'

        return float(self._interface.query(msg))

    def set_smsr_rng(self, rng: float) -> bool:
        """ Sets the range over which the SMSR cal. identifies a side-mode

        The units are in nm and must be within the range of 1.0 nm to 1000.0 nm
        """
        if rng < self.smsr_rng_min:
            logger.warning(f'Try to set SMSR Range to {rng}, ' +
                           f'coerced to {self.smsr_rng_min}')
            rng = self.smsr_rng_min
        elif rng > self.smsr_rng_max:
            logger.warning(f'Try to set SMSR Range to {rng}, ' +
                           f'coerced to {self.smsr_rng_max}')
            rng = self.smsr_rng_max

        msg = f':CALCulate2:SMSR:RANGe {rng}'
        return self._interface.write(msg)

    def get_smsr_stat(self) -> str:
        """ Gets whether the SMSR calculation is performed

        If the state is OFF, all READ, MEASURE, and FETCH commands
        will return "SMSR off" when queried
        """
        msg = ':CALCulate2:SMSR:STATe?'

        return self._interface.query(msg)

    def set_smsr_stat(self, stat: str) -> bool:
        """ Sets whether the SMSR calculation is performed """
        valid_val = ['OFF', 'ON']
        stat = stat.upper()

        if stat in valid_val:
            msg = f':CALCulate2:SMSR:STATe {stat}'
            self._interface.write(msg)
            return True
        else:
            logger.warning(f'Not a valid state to set: {stat}')
            return False

    def set_scalar_method(self, scal_method: str = 'PEAK') -> bool:
        """
        Sets the method used for computing the scalar wavelength and power
        Args:
            scal_method: Method used for computing

        Returns: Boolean - True if set, False if not a valid setting

        """
        valid_methods = ['PEAK', 'REF', 'FPAV', 'BBAN']
        if scal_method not in valid_methods:
            logger.warning(f'{scal_method} is not a valid option. '
                           f'Measurement method must be one of: '
                           f'{valid_methods}')
            return False
        self._interface.write(f':CALCulate2:SCALar {scal_method}')
        return True

    def get_scalar_method(self) -> str:
        """
        Reads the current method used for computing the scalar wavelength and power
        Returns: One of 'PEAK', 'REF', 'FPAV', 'BBAN'

        """
        return self._interface.query(':CALCulate2:SCALar?')

    def get_spectrum(self) -> dict:
        res_dict = {'Wavelength(nm)': [], 'Power(dBm)': []}
        if self._int_type != 'telnet':
            res_dict['Frequency(THz)'] = []
            logging.warning('get_spectrum ')
            return res_dict
        sample_size = 12 #bytes
        self._interface.tn.write(b':CALC3:DATA?\r\n')
        #Getting first character
        self._interface.tn.rawq_getchar()
        #Number of characters in the byte string
        num_bytes_char = int(self._interface.tn.rawq_getchar())
        #Finding total number of bytes
        tot_bytes = 0
        for indx in range(num_bytes_char):
            char = self._interface.tn.rawq_getchar()
            tot_bytes += int(char)*10**(num_bytes_char-indx-1)

        #Computing number of samples
        num_samples = int(tot_bytes/sample_size)

        for _ in range(num_samples):
            raw_data = b''
            for _ in range(sample_size):
                raw_data += self._interface.tn.rawq_getchar()
            wvl, pwr = unpack('<df', raw_data)
            res_dict['Wavelength(nm)'].append(wvl)
            res_dict['Power(dBm)'].append(pwr)
        res_dict['Wavelength(nm)'] = np.asarray(res_dict['Wavelength(nm)'])
        res_dict['Power(dBm)'] = np.asarray(res_dict['Power(dBm)'])
        res_dict['Frequency(THz)'] = (299792458 / res_dict['Wavelength(nm)']) * 1e-3

        return res_dict