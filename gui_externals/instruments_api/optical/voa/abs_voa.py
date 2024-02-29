import abc
import logging


class InstrErrorVOA(Exception):
    pass


class AbsVOA(metaclass=abc.ABCMeta):

    @property
    @abc.abstractmethod
    def idn(self) -> str:
        """ Instrument identification string """
        pass

    @abc.abstractmethod
    def set_atten(self, att):
        pass

    @abc.abstractmethod
    def get_atten(self):
        pass

    @abc.abstractmethod
    def set_wvl_nm(self, wvl):
        pass

    @abc.abstractmethod
    def get_wvl_nm(self):
        pass

    @abc.abstractmethod
    def set_freq_THz(self, freq):
        pass

    @abc.abstractmethod
    def get_freq_THz(self):
        pass

    @abc.abstractmethod
    def set_out_state(self, on):
        pass

    @abc.abstractmethod
    def get_out_state(self):
        pass

    def close_shutter(self, on):
        on = not bool(on)
        return self.set_out_state(on)

    def set_config(self, cfg: dict = None):
        """ Configures the VOA using configuration dictionary keywords

                    Params:
                        cfg:(dict) VOA configuration
                """
        supported_cfg_keywords = ["wl", "freq", "out_state", "shutter", "atten"]
        for k, v in cfg.items():
            if k not in supported_cfg_keywords:
                logging.warning(f"{k} is not a supported cfg keyword. Ignore. Supported: {supported_cfg_keywords}")
            elif k == 'wl' and cfg['wl'] is not None:
                self.set_wvl_nm(cfg['wl'])
            elif k == 'freq' and cfg['freq'] is not None:
                self.set_freq_THz(cfg['freq'])
            elif k == 'out_state' and cfg['out_state'] is not None:
                self.set_out_state(cfg['out_state'])
            elif k == 'shutter' and cfg['shutter'] is not None:
                self.set_out_state(not cfg['shutter'])
            elif k == 'atten' and cfg['atten'] is not None:
                self.set_atten(cfg['atten'])

    def get_config(self) -> dict:
        cfg = {}
        cfg['wl'] = self.get_wvl_nm()
        cfg['freq'] = self.get_freq_THz()
        cfg['out_state'] = self.get_out_state()
        cfg['shutter'] = not cfg['out_state']
        cfg['atten'] = self.get_atten()
        return cfg
