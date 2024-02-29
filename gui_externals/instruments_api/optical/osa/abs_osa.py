import abc


class InstrErrorOSA(Exception):
    pass


def THz_to_nm(freq):
    wvl = C / freq * 1e-3
    return wvl


def nm_to_THz(wvl):
    freq = C / wvl * 1e-3
    return freq


C = 299792458.0  # speed of light


class AbsOSA(metaclass=abc.ABCMeta):

    @property
    @abc.abstractmethod
    def idn(self) -> str:
        """ Instrument identification string """
        pass

    @property
    @abc.abstractmethod
    def rbw(self) -> str:
        """ resolution bandwidth """
        pass

    @abc.abstractmethod
    def sweep(self, num_avg):
        """ Trigger sweep with averaging """
        pass

    @abc.abstractmethod
    def set_freq_start_stop_THz(self, start, stop):
        """ in THz """
        pass

    @abc.abstractmethod
    def set_freq_center_span_THz(self, center, span):
        """ in THz """
        pass

    @abc.abstractmethod
    def set_wl_start_stop_nm(self, start, stop):
        """ in nm """
        pass

    @abc.abstractmethod
    def set_wl_center_span_nm(self, center, span):
        """ in nm """
        pass

    @abc.abstractmethod
    def get_wl_center_span_nm(self):
        """ in nm """
        pass

    @abc.abstractmethod
    def get_freq_center_span_THz(self):
        """ in THz """
        pass

    @abc.abstractmethod
    def config_osnr_meas_nm(self, center, span, rbw, noise_ofs, nbw, sbw):
        """
        Configure OSNR measurement settings: center, span, RBW, noise measurement offset, noise BW
        """
        pass

    @abc.abstractmethod
    def get_spectrum(self):
        """
        Returns a dictionary with the spectral data of the last sweep
        {
            'freq_THz': ...,
            'pwr_dBm': ...,
        }
        """
        pass

    @abc.abstractmethod
    def get_osnr(self):
        " returns osnr value in dB "
        pass
