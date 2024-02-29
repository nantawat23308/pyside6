import numpy as np
import time
from .abs_osa import AbsOSA
from .abs_osa import InstrErrorOSA
from .abs_osa import THz_to_nm
from .abs_osa import nm_to_THz
import logging
logger = logging.getLogger(__name__)


class Osa(AbsOSA):
    """
        Anritsu OSA implementation
    """

    def __init__(self, interface):
        self._interface = interface
        self._rbw = float(self._interface.query(":SENS:BWID:RES?")) * 1e9        # rbw of the instrument in nm
        self.signal_bw = 0.5
        self.noise_ofs = 0.6                    # offset from signal in nm where noise power will be measured
        self.noise_bw = 0.1                     # noise bandwidth in nm, only for calculations of OSNR.
        self._average = 1                       # number of captures to be averaged
        self._data = {'freq_THz': np.array([]), 'pwr_mW': np.array([]), 'pwr_dBm': np.array([])}
        self._freq_max_THz = nm_to_THz(600)     # maximum readable frequency
        self._freq_min_THz = nm_to_THz(1750)    # minimum readable frequency
        self._rbw_supported = [0.03, 0.05, 0.07, 0.1, 0.2, 0.5, 1.0]  # in nm

    @property
    def idn(self) -> str:
        """ Instrument identification string """
        idn = self._interface.query("*IDN?")
        return idn

    @property
    def rbw(self) -> float:
        """ Resolution bandwidth of the instrument in nm """
        return self._rbw

    @rbw.setter
    def rbw(self, rbw):
        """ Resolution bandwidth of the instrument in nm """
        if rbw not in self.rbw_supported:
            raise InstrErrorOSA(f'RBW = {rbw} nm is not supported.')
        self._interface.write(f":SENS:BWID:RES {rbw}NM")
        self._rbw = rbw

    @property
    def rbw_supported(self) -> list:
        """ List of supported resolution bandwidth settings of the instrument in nm """
        return self._rbw_supported

    @property
    def average(self) -> int:
        """ Number of averages for each sweep """
        return self._average

    @average.setter
    def average(self, average: int):
        """ Number of averages for each sweep """
        self._interface.write(f":CALC:AVER:COUN {average:d}")
        self._average = average

    def sweep(self, num_avg=1):
        """ Trigger sweep with averaging """

        # set the number of averages
        self.average = num_avg

        # start sweeping
        self._interface.write("INIT:IMM")
        done = int(self._interface.query("*OPC?"))
        while not done:
            done = int(self._interface.query("*OPC?"))
            time.sleep(0.5)
        self._data = self.get_data()

    def set_freq_start_stop_THz(self, start, stop):
        """ in THz """
        wvl_start = THz_to_nm(stop)
        wvl_stop = THz_to_nm(start)
        self.set_wl_start_stop_nm(start=wvl_start, stop=wvl_stop)

    def get_freq_start_stop_THz(self):
        """" in THz """
        wvl_start, wvl_stop = self.get_wl_start_stop_nm()
        freq_stop = nm_to_THz(wvl_start)
        freq_start = nm_to_THz(wvl_stop)

        return freq_start, freq_stop

    def set_freq_center_span_THz(self, center, span):
        """ in THz """
        freq_start = center - span * 0.5
        freq_stop = center + span * 0.5
        self.set_freq_start_stop_THz(start=freq_start, stop=freq_stop)

    def get_freq_center_span_THz(self):
        """" in THz """
        wvl_start, wvl_stop = self.get_wl_start_stop_nm()
        freq_stop = nm_to_THz(wvl_start)
        freq_start = nm_to_THz(wvl_stop)
        center = (freq_start + freq_stop) / 2
        span = freq_stop - freq_start

        return center, span

    def set_wl_start_stop_nm(self, start, stop):
        """ in nm """
        self._interface.write(f":SENS:WAV:STAR {start:0.1f}NM")
        self._interface.write(f":SENS:WAV:STOP {stop:0.1f}NM")

    def get_wl_start_stop_nm(self):
        """" in nm """
        start = float(self._interface.query(":SENS:WAV:STAR?")) * 1e9
        stop = float(self._interface.query(":SENS:WAV:STOP?")) * 1e9

        return start, stop

    def set_wl_center_span_nm(self, center, span):
        """ in nm """
        self._interface.write(f":SENS:WAV:CENT {center:0.2f}NM")
        self._interface.write(f":SENS:WAV:SPAN {span:0.1f}NM")

    def get_wl_center_span_nm(self):
        """" in nm """
        center = float(self._interface.query(":SENS:WAV:CENT?")) * 1e9
        span = float(self._interface.query(":SENS:WAV:SPAN?")) * 1e9

        return center, span

    def config_osnr_meas_nm(self, center, span, rbw, noise_ofs, nbw=0.1, sbw=0.5):
        """
        Configure settings that will be used during the OSNR measurement
        :param center: float, in nm. Center wavelength in nm.
        :param span: float, in nm. Wavelength span in nm.
        :param rbw: float, in nm. Resolution bandwidth in nm.
        :param noise_ofs: float, in nm. Noise offset from signal for noise measurement.
        :param nbw: float, in nm. Optional. Reference noise bandwidth. Default: 0.1nm.
        :param sbw: float, in nm. Optional. Signal bandwidth. Default: 0.5nm.
        :return:
        """
        self.set_wl_center_span_nm(center, span)
        self.rbw = rbw
        self.noise_ofs = noise_ofs
        self.noise_bw = nbw
        self.signal_bw = sbw

        # configure automatic OSNR capture
        self.get_spectrum()
        self._interface.write(":CALC:MARK:MAX:SCEN")

        # enable the normalization of the OSNR calculation to rbw nm
        self._interface.write(":CALC:PAR:WDM:NNOR ON")
        self._interface.write(f":CALC:PAR:WDM:NBW {self.noise_bw}NM")

        # set the slice level for peak detection to 5 dB
        self._interface.write(":CALC:PAR:CAT:WDM:SLIC 5DB")

        # set the wavelength detection method of the signal parameter to threshold mode with cut level of 3 dB
        self._interface.write(":CALC:PAR:CAT:WDM:SGW THRESHOLD,3DB")

        # set the level detection of the signal parameter to point mode
        self._interface.write(":CALC:PAR:CAT:WDM:SGL POINT")

        # set the noise detection level method to average left/right points at noise_ofs
        self._interface.write(f":CALC:PAR:CAT:WDM:POIN AVERAGE, {self.noise_ofs}NM")

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

    def get_data(self):
        """
        Returns a dictionary with the spectral data of the last sweep
        {
            'freq_THz': ...,
            'pwr_dBm': ...,
        }
        """
        trace = self._interface.query(":TRAC:ACT?")[-1]
        n = int(self._interface.query(f":TRAC:SNUM? {trace}"))
        freq_start = nm_to_THz(float(self._interface.query(f":TRAC:DATA:X:STOP? {trace}")) * 1e9)
        freq_stop = nm_to_THz(float(self._interface.query(f":TRAC:DATA:X:STAR? {trace}")) * 1e9)
        freq = np.linspace(freq_stop, freq_start, n)
        data = self._interface.query(f":TRAC:DATA:Y? {trace}").split(",")
        pwr_dBm = []
        for point in data:
            if point != '':
                pwr_dBm.append(float(point))
        pwr_dBm = np.array(pwr_dBm)

        self._data['freq_THz'] = freq[::-1]
        self._data['pwr_dBm'] = pwr_dBm[::-1]
        self._data['pwr_mW'] = 10 ** (pwr_dBm[::-1] / 10)

        return self._data

    def find_center(self, freq=None, pwr=None, threshold=1.5, freq_center=None):
        """
        Searches the maximum power in the spectrum and returns the corresponding power, frequency and index.
        :return data: dictionary. Keys: 'freq_THz', 'pwr_dBm', 'index'
        """
        if freq is None or pwr is None:
            data = self.get_spectrum()
            freq = data['freq_THz']
            pwr = data['pwr_dBm']

        if freq_center is not None:
            freq_pwr_max = freq_center
            index_max = np.argmin(np.abs(freq-freq_pwr_max))
            pwr_max = pwr[index_max]
        else:
            pwr_max = np.max(pwr)
            index_max = np.argmax(pwr)
            # freq_pwr_max = freq[index_max]

        # left and right side indexes
        index_left = 0
        for i in np.arange(index_max, -1, -1):
            _pwr = pwr[i]
            if pwr_max - threshold >= _pwr:
                index_left = i
                break

        index_right = len(pwr)
        for i in np.arange(index_max, len(pwr)):
            _pwr = pwr[i]
            if pwr_max - threshold >= _pwr:
                index_right = i
                break
        freq_left = freq[index_left]
        freq_right = freq[index_right]

        # central frequency and power
        freq_center = (freq_left + freq_right) / 2
        index_center = round((index_left + index_right) / 2)
        power_center = pwr[index_center]

        data = {
            'freq_THz': freq_center,
            'pwr_dBm': power_center,
            'index': index_center
            }
        return data

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
        logger.debug(f"Wavelength scan resolution: {dwvl}")
        if dwvl * 2 > self.rbw:
            logger.warning("Wavelength scan resolution too little. OSNR may not be accurate.")
        i_start = np.argmin(np.abs(wvl - wvl_start))
        i_stop = np.argmin(np.abs(wvl - wvl_stop))
        pow_int = dwvl * np.sum(power[i_stop:i_start])/self.rbw
        return pow_int

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
