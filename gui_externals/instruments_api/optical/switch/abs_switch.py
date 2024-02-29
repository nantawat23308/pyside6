import abc


class InstrErrorSwitch(Exception):
    pass


class AbsSwitch(metaclass=abc.ABCMeta):

    @property
    @abc.abstractmethod
    def idn(self) -> str:
        """ Instrument identification string """
        pass

    @abc.abstractmethod
    def set_channel(self, ch):
        pass

    @abc.abstractmethod
    def get_channel(self):
        pass

    def set_config(self, cfg: dict = None):
        """ Configures Switch using configuration dict

            Params:
                cfg: (dict) Switch configuration
        """
        if cfg["ch"] is not None:
            self.set_channel(cfg["ch"])

    def get_config(self) -> dict:
        ch = self.get_channel()
        cfg = {"ch": ch}
        return cfg
