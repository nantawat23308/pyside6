#####################################################################################
# Finisar waveanalyzer api
# 2021-09-07: First version. Robert Palmer
#####################################################################################
import time
import numpy as np
import json
import scipy
from .abs_osa import AbsOSA
from .abs_osa import THz_to_nm
from .abs_osa import nm_to_THz
import logging
logger = logging.getLogger(__name__)


class Osa(AbsOSA):
    def __init__(self, interface, port='HighSens'):
        """ initializes Finisar WaveAnalyzer
            parameters:
                ip: IP address as string
                port: Optical port. 'HighSens' or 'Normal'
        """
        super().__init__()
        self._interface = interface
        self._data = {'freq_THz': [], 'pwr_mW': [], 'pwr_dBm': []}
        self.port = port
        if self.port != "HighSens" and self.port != "Normal":
            raise Exception(f'You have selected an unknown port of the Finisar Waveanalyzer: {self.port}. '
                            f'Should be "HighSens" or "Normal"')
        self.signal_bw = 0.5    # Signal BW for OSNR calculation
        self._rbw = 0.0014      # rbw of the instrument in nm --> 180 MHz according to spec from II/VI
        self._rbw_THz = 180e-6  # 180 MHz according to spec from II/VI

        # Offset from signal in nm where noise power will be measured. Only for calculations of OSNR.
        self.noise_ofs = 0.6
        self.noise_bw = 0.1     # noise bandwidth in nm, only for calculations of OSNR.
        self.average = 1        # number of captures to be averaged
        self._idn = ', '.join(list(json.loads(self._interface.query("/wanl/info")).values())[1:])
        self._freq_max_THz = 196.4  # maximum readable frequency
        self._freq_min_THz = 191.0  # minimum readable frequency
        self._rbw_supported = [self._rbw]  # in nm

        # SMSR configuration
        self._smsr_level = -70
        self._smsr_min_distance = 5
        self._smsr_max_distance = 5000

    @property
    def idn(self) -> str:
        """ Instrument identification string """
        return self._idn

    @property
    def rbw(self) -> float:
        """ resolution bandwidth of instrument in nm """
        return self._rbw

    @property
    def rbw_supported(self) -> list:
        """ List of supported resolution bandwidth settings of the instrument in nm """
        return self._rbw_supported

    def sweep(self, num_avg=3, **kwargs):
        """ Sweeps the OSA num_avg-times and stores results in self.data """
        timeout = kwargs.get('timeout', 2)
        self._data = self.get_data(num_avg=num_avg, timeout=timeout)

    def set_freq_start_stop_THz(self, start, stop):
        """ Sets start and stop frequency in THz. """
        if start < self._freq_min_THz:
            start = self._freq_min_THz
        if stop > self._freq_max_THz:
            stop = self._freq_max_THz
        freq_center = (start + stop) * 0.5
        freq_span = stop - start
        self.set_freq_center_span_THz(center=freq_center, span=freq_span)

    def set_freq_center_span_THz(self, center, span):
        """ Sets center frequency and span in THz. """
        start = center - 0.5 * span
        stop = center + 0.5 * span
        if start < self._freq_min_THz:
            start = self._freq_min_THz
        if stop > self._freq_max_THz:
            stop = self._freq_max_THz
        center = (start + stop) / 2
        span = stop - start
        self._interface.write(f"/wanl/scan/{int(center * 1e6)}/{int(span * 1e6)}/{self.port}")

    def get_freq_center_span_THz(self):
        self.sweep()
        freq_array = self.get_spectrum()["freq_THz"]
        center = 0.5 * (freq_array[0] + freq_array[-1])
        span = freq_array[-1] - freq_array[0]
        return center, span

    def get_wl_center_span_nm(self):
        self.sweep()
        freq_array = self.get_spectrum()["freq_THz"]
        center = 0.5 * (THz_to_nm(freq_array[0]) + THz_to_nm(freq_array[-1]))
        span = THz_to_nm(freq_array[0]) - THz_to_nm(freq_array[-1])
        return center, span

    def set_wl_start_stop_nm(self, start, stop):
        """ Sets start and stop wavelength in nm. """
        freq_start = nm_to_THz(stop)
        freq_stop = nm_to_THz(start)
        freq_center = (freq_start + freq_stop) * 0.5
        freq_span = freq_stop - freq_start
        self.set_freq_center_span_THz(center=freq_center, span=freq_span)

    def set_wl_center_span_nm(self, center, span):
        """ Sets center wavelength and span in nm. """
        wl_stop = center + span * 0.5
        wl_start = center - span * 0.5
        self.set_wl_start_stop_nm(start=wl_start, stop=wl_stop)

    def config_osnr_meas_nm(self, center, span, rbw, noise_ofs, nbw=0.1, sbw=0.5):
        """
        Configure settings that will be used during the OSNR measurement
        :param center: float, in nm. Center wavelength in nm.
        :param span: float, in nm. Wavelength span in nm.
        :param rbw: float, in nm. Placeholder for method default signature, can't be changed
        :param noise_ofs: float, in nm. Noise offset from signal for noise measurement.
        :param nbw: float, in nm. Optional. Reference noise bandwidth. Default: 0.1nm.
        :param sbw: float, in nm. Optional. Signal bandwidth. Default: 0.5nm.
        :return:
        """
        self.set_wl_center_span_nm(center=center, span=span)
        self.noise_ofs = noise_ofs
        self.noise_bw = nbw
        self.signal_bw = sbw

    def get_spectrum(self):
        """
        Returns the spectrum from last frequency sweep in THz and dBm.
        :return spectrum: dictionary. Keys: 'freq_THz', 'pwr_dBm'
        """
        return self._data

    def find_max(self, freq_array=None, power_array=None):
        """
        Searches the maximum power in the spectrum and returns the corresponding power, frequency and index.
        :return data: dictionary. Keys: 'freq_THz', 'pwr_dBm', 'index'
        """
        if freq_array is None or power_array is None:
            freq_array = self._data['freq_THz']
            power_array = self._data['pwr_dBm']
        pow_max = np.max(power_array)
        index_max = np.argmax(power_array)
        freq_pow_max = freq_array[index_max]
        data = {
            'freq_THz': freq_pow_max,
            'pwr_dBm': pow_max,
            'index': index_max
            }
        return data

    def find_center(self, freq_array=None, power_array=None, threshold=5):
        """
        Searches the maximum power in the spectrum and returns the corresponding power, frequency and index.
        :return data: dictionary. Keys: 'freq_THz', 'pwr_dBm', 'index'
        """
        if freq_array is None or power_array is None:
            self.sweep()
            freq_array = self._data['freq_THz']
            power_array = self._data['pwr_dBm']
        pow_max = np.max(power_array)
        index_max = np.argmax(power_array)
        # freq_pow_max = freq_array[index_max]

        # left and right side indexes
        index_left = 0
        for i in np.arange(index_max, -1, -1):
            _pwr = power_array[i]
            if pow_max - threshold >= _pwr:
                index_left = i
                break

        index_right = len(power_array)
        for i in np.arange(index_max, len(power_array)):
            _pwr = power_array[i]
            if pow_max - threshold >= _pwr:
                index_right = i
                break
        freq_left = freq_array[index_left]
        freq_right = freq_array[index_right]

        # central frequency and power
        freq_center = (freq_left + freq_right) / 2
        index_center = round((index_left + index_right) / 2)
        power_center = power_array[index_center]

        data = {
            'freq_THz': freq_center,
            'pwr_dBm': power_center,
            'index': index_center
            }
        return data

    def get_osnr(self, noise_ofs=None, signal_bw=None, freq_signal=None):
        """
        Effective 3 point OSNR measurement. Finds maximum in spectrum and calculates OSNR.
        Signal frequency can also be manually selected.
        :param noise_ofs: float, in nm. Noise offset from signal frequency.
        :param signal_bw: float, in nm. Signal bandwidth for spectrum evaluation.
        This emulates a grating based OSA approach.
        :param freq_signal: float, in THz. Optional.
        Manually select signal frequency for evaluation in case of detection issues.
        :return osnr: float, in dB. Optical signal to noise ratio.
        """
        if signal_bw is None:
            if self.signal_bw is None:
                signal_bw = self.rbw
            else:
                signal_bw = self.signal_bw
        if noise_ofs is None:
            noise_ofs = self.noise_ofs
        if freq_signal is None:
            found_center = self.find_center()
            freq_signal = found_center['freq_THz']
        wvl_signal = THz_to_nm(freq_signal)
        sig1 = round(wvl_signal - signal_bw * 0.5, 3)  # channel start frequency
        sig2 = round(wvl_signal + signal_bw * 0.5, 3)  # channel stop frequency
        nl1 = round(wvl_signal - noise_ofs - signal_bw * 0.5, 3)  # noise left-side start frequency
        nl2 = round(wvl_signal - noise_ofs + signal_bw * 0.5, 3)  # noise left-side stop frequency
        nr1 = round(wvl_signal + noise_ofs - signal_bw * 0.5, 3)  # noise right-side start frequency
        nr2 = round(wvl_signal + noise_ofs + signal_bw * 0.5, 3)  # noise right-side stop frequency

        osnr = self.get_osnr_from_six_points(sig1, sig2, nl1, nl2, nr1, nr2)

        return osnr

    def get_osnr_from_six_points(self, sig1, sig2, nl1, nl2, nr1, nr2, noise_bw=None):
        """
        Calculates OSNR of last sweep via a 6 point measurement in frequency domain
        :param sig1: float, in THz. Lower frequency limit for signal integration.
        :param sig2: float, in THz. Upper frequency limit for signal integration.
        :param nl1: float, in THz. Lower frequency limit for left noise integration.
        :param nl2: float, in THz. Upper frequency limit for left noise integration.
        :param nr1: float, in THz. Lower frequency limit for right noise integration.
        :param nr2: float, in THz. Upper frequency limit for right noise integration.
        :param noise_bw: float, in nm. Reference bandwidth for noise measurement
        :return osnr: in dB
        """
        if noise_bw is None:
            noise_bw = self.noise_bw
        result = self.evaluate_six_points(sig1, sig2, nl1, nl2, nr1, nr2)

        # signal power
        signal = result["pwr_signal_mW"]

        # noise referenced to ref_bw
        noise_in_ref_bw = result["noise_pow_density"] * noise_bw

        # OSNR calculation
        # Small number added in case no peak is detected
        osnr = round(10 * np.log10(signal / noise_in_ref_bw + 0.0000001), 2)

        return osnr

    def evaluate_six_points(self, sig1, sig2, nl1, nl2, nr1, nr2):
        """
        6 point measurement evaluation in frequency domain.
        :param sig1: float, in THz. Lower frequency limit for signal integration.
        :param sig2: float, in THz. Upper frequency limit for signal integration.
        :param nl1: float, in THz. Lower frequency limit for left noise integration.
        :param nl2: float, in THz. Upper frequency limit for left noise integration.
        :param nr1: float, in THz. Lower frequency limit for right noise integration.
        :param nr2: float, in THz. Upper frequency limit for right noise integration.
        :return result: dictionary. Keys: 'pwr_signal', 'noise_pow_density'
        """
        signal_and_noise = self.integrate(sig1, sig2)
        noise_left_side = self.integrate(nl1, nl2)
        noise_right_side = self.integrate(nr1, nr2)

        # Noise power density
        npd = (noise_left_side / (nl2 - nl1) + noise_right_side / (nr2 - nr1)) / 2

        # total power of background noise in channel
        noise_in_channel = npd * (sig2 - sig1)

        # signal power
        signal = signal_and_noise - noise_in_channel

        result = {"pwr_signal_mW": signal,
                  "noise_pow_density": npd}

        return result

    def get_sig_pow(self, noise_ofs=None, signal_bw=None, freq_signal=None):
        """
        Finds maximum in spectrum and calculates signal power.
        :param noise_ofs: float, in nm. Optional. Noise offset from signal for IB-noise calculation
        :param signal_bw: float, in nm. Optional. Signal Bandwidth.
        :param freq_signal: float, in nm. Optional. Detects peak frequency in case not specified.
        :return sig_pow_dBm: float. Signal power in dBm
        """
        if signal_bw is None:
            signal_bw = self.signal_bw
        if noise_ofs is None:
            noise_ofs = self.noise_ofs
        if freq_signal is None:
            found_center = self.find_center()
            freq_signal = found_center['freq_THz']
        wvl_signal = THz_to_nm(freq_signal)

        sig1 = round(wvl_signal - signal_bw * 0.5, 3)  # channel start frequency
        sig2 = round(wvl_signal + signal_bw * 0.5, 3)  # channel stop frequency
        nl1 = round(wvl_signal - noise_ofs - signal_bw * 0.5, 3)  # noise left-side start frequency
        nl2 = round(wvl_signal - noise_ofs + signal_bw * 0.5, 3)  # noise left-side stop frequency
        nr1 = round(wvl_signal + noise_ofs - signal_bw * 0.5, 3)  # noise right-side start frequency
        nr2 = round(wvl_signal + noise_ofs + signal_bw * 0.5, 3)  # noise right-side stop frequency

        result = self.evaluate_six_points(sig1, sig2, nl1, nl2, nr1, nr2)

        # power in channel from signal *only*
        sig_pow_dBm = 10 * np.log10(result["pwr_signal_mW"])

        return sig_pow_dBm

    def integrate(self, wvl_start, wvl_stop):
        """
        Integrate power/rbw over wavelength window
        :param wvl_start: Start wavelength of integration
        :param wvl_stop: Stop wavelength of integration
        :return pow_int: Integrated power in mW
        """

        wvl = THz_to_nm(self._data["freq_THz"])
        power = self._data["pwr_mW"]
        dwvl = abs(wvl[-1] - wvl[0])/wvl.size
        i_start = np.argmin(np.abs(wvl - wvl_start))
        i_stop = np.argmin(np.abs(wvl - wvl_stop))
        pow_int = dwvl * np.sum(power[i_stop:i_start])/self.rbw
        return pow_int

    def get_data(self, num_avg=None, timeout=1):
        """
        Read averaged spectrum in linear or logarithmic units.
        :param num_avg: integer - Number of averages
        :param timeout: float, in seconds - timeout waiting for a unique scan id
        :return data: dictionary. See get_data()
        """
        data = self.get_data_raw(unit='mW', timeout=timeout)
        if num_avg is None:
            num_avg = self.average

        if num_avg > 1:
            for i in range(1, num_avg):
                _data = self.get_data_raw(unit='mW', timeout=timeout)
                data["pwr_mW"] = data["pwr_mW"] + _data["pwr_mW"]
                data["pwr_x_mW"] = data["pwr_x_mW"] + _data["pwr_x_mW"]
                data["pwr_y_mW"] = data["pwr_y_mW"] + _data["pwr_y_mW"]

            data["pwr_mW"] = data["pwr_mW"] / num_avg
            data["pwr_x_mW"] = data["pwr_x_mW"] / num_avg
            data["pwr_y_mW"] = data["pwr_y_mW"] / num_avg

        data["pwr_dBm"] = 10 * np.log10(abs(data["pwr_mW"]))
        data["pwr_x_dBm"] = 10 * np.log10(abs(data["pwr_x_mW"]))
        data["pwr_y_dBm"] = 10 * np.log10(abs(data["pwr_y_mW"]))

        self._data = data

        return data

    def get_data_raw(self, unit='dBm', timeout=1):
        """
        Get measured spectrum from OSA. Power will be in dBm or mW depending on selected 'unit'.
        :param unit: str -  'dBm' or 'mW'
        :param timeout: float, in seconds - timeout waiting for a unique scan id
        :return data_dict: dictionary. Keys: 'freq_THz', 'pwr_mW', 'pwr_x_mW', 'pwr_x_mW', 'flag', 'rbw_nm'
        or Keys: 'freq_THz', 'pwr_dBm', 'pwr_x_dBm', 'pwr_x_dBm', 'flag', 'rbw_nm'
        """

        # initialize output variables
        freq = []
        flag = []
        p_abs = []
        p_x = []
        p_y = []

        num_trials_remain = 5
        while num_trials_remain:
            try:
                num_trials_remain -= 1
                self.wait_for_unique_scan(timeout)
                if unit == 'dBm':
                    m = self._interface.query("/wanl/data/bin", bin_data=True)
                    # m = requests.get(f'http://{self._interface._ip}/wanl/data/bin').content
                    data = np.frombuffer(m[1000:], dtype=int)
                    freq = data[0::5] / 1000000.0
                    p_abs = data[1::5] / 1000.0
                    p_x = data[2::5] / 1000.0
                    p_y = data[3::5] / 1000.0
                    flag = data[4::5]
                else:
                    m = self._interface.query("/wanl/lineardata/bin", bin_data=True)
                    # m = requests.get(f'http://{self._interface._ip}/wanl/lineardata/bin').content
                    data1 = np.frombuffer(m[1000:], dtype='int')
                    data2 = np.frombuffer(m[1000:], dtype='float32')
                    freq = data1[0::5]/1000000.0
                    p_abs = data2[1::5]
                    p_x = data2[2::5]
                    p_y = data2[3::5]
                    flag = data1[4::5]
                break
            except Exception as e:
                logger.warning(f'Reading WaveAnalyzer data failed. Repeat. {e}')
        if num_trials_remain <= 1:
            raise Exception('WaveAnalyzer Error. Reading the data failed continuously.')

        data_dict = {
            "freq_THz": freq,
            "flag": flag,
        }
        if unit == 'dBm':
            data_dict["pwr_abs_dBm"] = p_abs
            data_dict["pwr_x_dBm"] = p_x
            data_dict["pwr_y_dBm"] = p_y
        else:
            data_dict["pwr_mW"] = p_abs
            data_dict["pwr_x_mW"] = p_x
            data_dict["pwr_y_mW"] = p_y
        return data_dict

    def wait_for_unique_scan(self, timeout=1):
        """
        Wait until a new scan is completed or timeout.
        :param timeout: float, in seconds
        :return:
        """
        start_time = time.time()
        scan_id = self.get_scan_id()
        while time.time()-start_time < timeout and self.get_scan_id() == scan_id:
            time.sleep(0.01)
        if time.time()-start_time > timeout:
            logger.warning('WaveAnalyzer timed out when waiting for a unique scan id. Ignore for now.')

    def get_scan_id(self):
        """
        Get the ID of the current OSA scan
        :return:
        """
        m = self._interface.query("/wanl/scan/status")
        # m = requests.get(f'http://{self.ip}/wanl/scan/status')
        scan_id = json.loads(m)['scanid']
        return scan_id

    def config_smsr_meas_nm(self, level=20, min_distance=25, max_distance=625):
        """
        Configure SMSR measurement settings: level, minimum distance, maximum distance
        """
        self._smsr_level = level                    # in dB
        self._smsr_min_distance = min_distance      # in GHz
        self._smsr_max_distance = max_distance      # in GHz

    def get_smsr(self):
        """ returns data dictionary with multipeak SMSR data """
        data = {"freq_THz": [], "pwr_dBm": [], "smsr_dB": []}

        freq = np.array(self._data["freq_THz"])
        power = np.array(self._data["pwr_dBm"])

        # Set distance to at least the limit of the RBW
        delta_freq_thz = np.mean(np.diff(freq))
        distance = max([np.ceil(self._rbw_THz / delta_freq_thz), 1])
        width = 0
        tops = scipy.signal.find_peaks(power, distance=distance, width=width)

        # SMSR is either the peak prominence, if only a single peak is found
        # or the difference in height with the next highest peak
        if len(tops[0]) == 0:
            # no peaks found, return NaNs
            pk_freq = [float('NaN')]
            pk_pwr = [float('NaN')]
            pk_smsr = [float('NaN')]
        elif len(tops[0]) == 1:
            # one peak found
            pk_freq = [freq[tops[0][0]]]
            pk_pwr = [power[tops[0][0]]]
            pk_smsr = [tops[1]['prominences'][0]]
        else:
            # multiple peaks found. sort by height. report the first 5
            pk_pwr = power[tops[0]]
            index_sorted = tops[0][np.flip(
                np.argsort(pk_pwr))]  # flip is used to get descending order

            # Filter out side modes given SMSR frequency limits
            idx_0 = index_sorted[0]
            pk_pwr = [power[idx_0]]
            pk_freq = [freq[idx_0]]
            freq_delta_ghz = np.asarray(
                abs(freq[index_sorted] - freq[idx_0]) * 1e3)
            idx_filter = np.logical_and(
                self._smsr_min_distance < freq_delta_ghz,
                freq_delta_ghz < self._smsr_max_distance)
            pk_freq = np.append(pk_freq, freq[index_sorted[idx_filter]])
            pk_pwr = np.append(pk_pwr, power[index_sorted[idx_filter]])

            # Filter out side modes given SMSR Power level
            pk_freq = pk_freq[pk_pwr > self._smsr_level]
            pk_pwr = pk_pwr[pk_pwr > self._smsr_level]
            # Return something even if filtered out by power
            if len(pk_freq) == 0:
                pk_pwr = [power[idx_0]]
                pk_freq = [freq[idx_0]]
            # Add back side mode if len = 1. Otherwise SMSR is NaN
            if len(pk_freq) == 1:
                pk_freq = np.append(pk_freq, freq[index_sorted[idx_filter]][0])
                pk_pwr = np.append(pk_pwr, power[index_sorted[idx_filter]][0])

            mx_peaks = min(len(pk_freq), 5)
            pk_pwr = pk_pwr[:mx_peaks]  # reduce to expected single number
            pk_freq = pk_freq[:mx_peaks]  # reduce to expected single number
            pk_smsr = [
                pk_pwr[0] - pk_pwr[1]]  # difference between two highest peaks

        # sort list by power, in place:
        data["freq_THz"] = pk_freq
        data["pwr_dBm"] = pk_pwr
        data["smsr_dB"] = pk_smsr

        return data

    def close(self):
        self.__del__()

    def __del__(self):
        pass
