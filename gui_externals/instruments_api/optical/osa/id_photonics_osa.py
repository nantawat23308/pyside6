import numpy as np
from .abs_osa import AbsOSA
from .abs_osa import THz_to_nm
from .abs_osa import nm_to_THz
import logging
logger = logging.getLogger(__name__)


class Osa(AbsOSA):
    def __init__(self, interface):
        """
            ID Photonics OSA
        """
        super().__init__()
        self._interface = interface
        self._data = {'freq_THz': [], 'pwr_mW': [], 'pwr_dBm': []}
        self._rbw = 0.024                   # rbw of the instrument in nm
        self._rbw_THz = 312.5e-6            # 312.5 MHz according to spec from II/VI
        self.noise_ofs = 0.6                # Offset from signal in nm where noise power will be measured
        self.noise_bw = 0.1                 # noise bandwidth in nm, only for calculations of OSNR.
        self.signal_bw = 0.5                # Signal BW for OSNR calculation
        self.average = 1                    # number of captures to be averaged
        self._freq_max_THz = 196.125        # maximum readable frequency
        self._freq_min_THz = 191.25         # minimum readable frequency
        self._rbw_supported = [self._rbw]   # in nm

    @property
    def idn(self) -> str:
        """ Instrument identification string """
        idn = "ID Photonics OSA"
        return idn

    @property
    def rbw(self) -> float:
        """ Resolution bandwidth of the instrument in nm """
        return self._rbw

    def sweep(self, num_avg=None, **kwargs):
        """ Sweeps the OSA num_avg-times and stores results in self.data """
        if num_avg is None:
            num_avg = self.average

        timeout = kwargs.get('timeout', 2)
        self._data = self.get_data(num_avg=num_avg, timeout=timeout)

    def set_freq_start_stop_THz(self, start, stop):
        """ Sets start and stop frequency in THz. """
        if start < self._freq_min_THz:
            start = self._freq_min_THz
        if stop > self._freq_max_THz:
            stop = self._freq_max_THz
        self._interface.write(f"star {start * 1e12:.5f}")
        self._interface.write(f"stop {stop * 1e12:.5f}")

        # write second time in case first commend was ignored due to conflict with upper frequency limit.
        self._interface.write(f"star {start * 1e12:.5f}")

    def set_freq_center_span_THz(self, center, span):
        """ Sets center frequency and span in THz. """
        start = center - 0.5 * span
        stop = center + 0.5 * span
        if start < self._freq_min_THz:
            start = self._freq_min_THz
        if stop > self._freq_max_THz:
            stop = self._freq_max_THz
        self.set_freq_center_span_THz(start, stop)

    def set_wl_start_stop_nm(self, start, stop):
        """ Sets start and stop wavelength in nm. """
        freq_start = nm_to_THz(stop)
        freq_stop = nm_to_THz(start)
        self.set_freq_center_span_THz(freq_start, freq_stop)

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
        spectrum = {
            'freq_THz': self._data['freq_THz'],
            'pwr_dBm': self._data['pwr_dBm'],
        }
        return spectrum

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
        osnr = round(10 * np.log10(signal / noise_in_ref_bw + 0.0000001),
                     2)  # Small number added in case no peak is detected

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
        dwvl = abs(wvl[-1] - wvl[0]) / wvl.size
        i_start = np.argmin(np.abs(wvl - wvl_start))
        i_stop = np.argmin(np.abs(wvl - wvl_stop))
        pow_int = dwvl * np.sum(power[i_stop:i_start]) / self._rbw_THz
        return pow_int

    def get_data(self, num_avg=None, timeout=1):
        """
        Read averaged spectrum in linear or logarithmic units.
        :param num_avg: integer - Number of averages
        :param timeout: float, in seconds - timeout waiting for a unique scan id
        :return data: dictionary. See get_data()
        """
        data = self.get_data_raw(timeout=timeout)
        if num_avg is None:
            num_avg = self.average

        if num_avg > 1:
            for i in range(1, num_avg):
                _data = self.get_data_raw(timeout=timeout)
                data["pwr_mW"] = data["pwr_mW"] + _data["pwr_mW"]
            data["pwr_mW"] = data["pwr_mW"] / num_avg

        data["pwr_dBm"] = 10 * np.log10(abs(data["pwr_mW"]))

        self._data = data

        return data

    def get_data_raw(self, timeout=1):
        """
        Get measured spectrum from OSA. Power will be in dBm or mW depending on selected 'unit'.
        :param timeout: float, in seconds - timeout waiting for a unique scan id
        :return data_dict: dictionary. Keys: 'freq_THz', 'pwr_mW'
        """
        # disable internal averaging
        self._interface.write("AVER:SCANCOUN 1")

        # initialize output variables
        freq = []
        p_abs = []

        # get data
        num_trials_remain = 5
        y_lin_total = 0
        while num_trials_remain:
            try:
                num_trials_remain -= 1
                self._interface.write("SGL")
                x = self._interface.query("xauto?")
                y = self._interface.query("y?")
                freq = np.array(map(float, x[:-1].split(','))) * 1e-12  # in THz
                y = np.array(map(float, y[:-1].split(',')))
                y_lin = np.array([10 ** (0.1 * yy) for yy in y])  # in mW
                p_abs = y_lin_total + y_lin
                break
            # TODO: find what exception is raised
            except Exception:
                logger.warning('Reading ID OSA data failed. Repeat.')
        if num_trials_remain <= 1:
            raise Exception('ID OSA Error. Reading the data failed continuously.')

        data_dict = {
            "freq_THz": freq,
            "pwr_mW": p_abs,
        }

        return data_dict

    def close(self):
        self.__del__()

    def __del__(self):
        pass
