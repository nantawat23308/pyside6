import numpy as np
import re
from .finisar_waveanalyzer import Osa as Finisar1500s
from .abs_osa import THz_to_nm
from .abs_osa import nm_to_THz
import logging
logger = logging.getLogger(__name__)


class Osa(Finisar1500s):
    def __init__(self, interface, sn):
        """ Finisar 100S WaveAnalyzer class. Based on the 1500S replacing only get_data() and
            parameters:
                ip: IP address as string
                sn: Serial Number as string
        """
        super().__init__(interface=interface)
        self._interface = interface
        self._sn = sn
        self._data = {'freq_THz': [], 'pwr_mW': [], 'pwr_dBm': []}
        self.signal_bw = 0.5    # Signal BW for OSNR calculation
        self._rbw_THz = 1750e-6  # 1750 MHz according to spec from II/VI
        self._rbw = THz_to_nm(self._rbw_THz)  # rbw of the instrument in nm --> 180 MHz according to spec from II/VI

        # Offset from signal in nm where noise power will be measured. Only for calculations of OSNR.
        self.noise_ofs = 0.6
        self.noise_bw = 0.1     # noise bandwidth in nm, only for calculations of OSNR.
        self.average = 1        # number of captures to be averaged
        self._idn = ""
        self._freq_max_THz = 196.4  # maximum readable frequency
        self._freq_min_THz = 191.0  # minimum readable frequency
        self._freq_start = self._freq_min_THz  # start frequency of the scan
        self._freq_stop = self._freq_max_THz  # stop frequency of the scan
        self._rbw_supported = [self._rbw]  # in nm

        # SMSR configuration
        self._smsr_level = -50
        self._smsr_min_distance = 5
        self._smsr_max_distance = 5000

    @property
    def idn(self) -> str:
        """ Instrument identification string """
        return ""

    def sweep(self, num_avg=1, **kwargs):
        """ Sweeps the OSA num_avg-times and stores results in self.data """
        self._data = self.get_data(num_avg=num_avg)

    def set_freq_start_stop_THz(self, start, stop):
        """ Sets start and stop frequency in THz. """
        if start < self._freq_min_THz:
            start = self._freq_min_THz
        if stop > self._freq_max_THz:
            stop = self._freq_max_THz
        self._freq_start = start
        self._freq_stop = stop

    def set_freq_center_span_THz(self, center, span):
        """ Sets center frequency and span in THz. """
        start = center - 0.5 * span
        stop = center + 0.5 * span
        if start < self._freq_min_THz:
            start = self._freq_min_THz
        if stop > self._freq_max_THz:
            stop = self._freq_max_THz
        self.set_freq_start_stop_THz(start, stop)

    def get_freq_center_span_THz(self):
        center = 0.5 * (self._freq_start + self._freq_stop)
        span = self._freq_stop - self._freq_start
        return center, span

    def get_wl_center_span_nm(self):
        center = 0.5 * (THz_to_nm(self._freq_start) + THz_to_nm(self._freq_stop))
        span = THz_to_nm(self._freq_start) - THz_to_nm(self._freq_stop)
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

    def get_data(self, num_avg=1, **kwargs):
        """
        Get measured spectrum from OSA. Power will be in dBm or mW depending on selected 'unit'.
        :param unit: str -  'dBm' or 'mW'
        :param num_avg: int - Number of averages
        :return data_dict: dictionary. Keys: 'freq_THz', 'pwr_mW', 'pwr_dBm'
        """

        data = self._interface.query("/analysis/data", params={"sno": self._sn, "averages": num_avg})
        data = re.split(r'\n(\d+.*)', data, 1, re.DOTALL)[1]
        data = np.fromstring(data, sep='\t')
        freq = data[0::2] * 1e-6
        pwr = data[1::2] * 1e-3
        pwr = pwr[(freq >= self._freq_start) & (freq <= self._freq_stop)]
        freq = freq[(freq >= self._freq_start) & (freq <= self._freq_stop)]
        data = {
            "freq_THz": freq,
            "pwr_dBm": pwr,
            "pwr_mW": 10 ** (pwr * 1e-3 / 10)
        }
        self._data = data
        return data
