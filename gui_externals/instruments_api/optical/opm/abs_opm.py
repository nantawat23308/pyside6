import abc
import logging
logger = logging.getLogger(__name__)


class InstrErrorOPM(Exception):
    pass


class AbsPWM(metaclass=abc.ABCMeta):

    @property
    @abc.abstractmethod
    def idn(self) -> str:
        """ Instrument identification string """
        pass

    def set_offset(self, offset):
        """
        A power meter will be connected via a tap coupler.
        'offset' defines the tap coupler loss that the SW needs to compensate.
        """
        self._offset = offset
        pass

    @property
    @abc.abstractmethod
    def pwr_unit(self) -> str:
        pass

    @pwr_unit.setter
    @abc.abstractmethod
    def pwr_unit(self, unit):
        pass

    @abc.abstractmethod
    def get_pwr(self, raw=False):
        """
        Returns the measured power in the selected unit (self.set_pwr_unit).
        raw = True: Returns the direct power meter reading
        raw = False: Uses self._offset to correct for tap coupler loss
        """
        pass

    @abc.abstractmethod
    def set_avg_time_s(self, time):
        pass

    @abc.abstractmethod
    def get_avg_time_s(self):
        pass

    @abc.abstractmethod
    def set_wl_nm(self, wl):
        pass

    @abc.abstractmethod
    def set_freq_THz(self, freq):
        pass

    @abc.abstractmethod
    def get_wl_nm(self):
        pass

    @abc.abstractmethod
    def get_freq_THz(self):
        pass

    @abc.abstractmethod
    def set_pwr_range_dBm(self, pwr_range):
        pass

    @abc.abstractmethod
    def get_pwr_range_dBm(self):
        pass

    @abc.abstractmethod
    def set_pwr_range_auto(self, auto):
        pass

    @abc.abstractmethod
    def get_pwr_range_auto(self):
        pass

    def get_config(self) -> dict:
        cfg = {}
        cfg['pwr_range'] = self.get_pwr_range()
        cfg['pwr_range_auto'] = self.get_pwr_range_auto()
        cfg['avg_time'] = self.get_avg_time()
        cfg['wl'] = self.get_wl()
        cfg['freq'] = self.get_freq()
        cfg['pwr_unit'] = self.get_pwr_unit()
        cfg['offset'] = self.offset
        return cfg

    def set_config(self, cfg: dict):
        """ Configures the optical power meter using configuration dictionary keywords

            Params:
                cfg:(dict) Power meter configuration
        """
        supported_cfg_keywords = ["wl", "freq", "pwr_unit", "avg_time", "pwr_range", "pwr_range_auto", "offset"]
        for k, v in cfg.items():
            if k not in supported_cfg_keywords:
                logging.warning(f"{k} is not a supported cfg keyword. Ignore. Supported: {supported_cfg_keywords}")
            elif k == 'wl' and cfg["wl"] is not None:
                self.set_wl_nm(cfg["wl"])
            elif k == 'freq' and cfg["freq"] is not None:
                self.set_freq_THz(cfg["freq"])
            elif k == 'pwr_unit' and cfg["pwr_unit"] is not None:
                self.pwr_unit = cfg["pwr_unit"]
            elif k == 'avg_time' and cfg["avg_time"] is not None:
                self.set_avg_time_s(cfg["avg_time"])
            elif k == 'pwr_range' and cfg["pwr_range"] is not None:
                self.set_pwr_range_dBm(cfg["pwr_range"])
            elif k == 'pwr_range_auto' and cfg["pwr_range_auto"] is not None:
                self.set_pwr_range_auto(cfg["pwr_range_auto"])
            elif k == 'offset' and cfg["offset"] is not None:
                self.set_offset(cfg["offset"])
