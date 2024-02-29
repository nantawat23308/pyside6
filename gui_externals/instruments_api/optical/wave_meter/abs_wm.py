import abc


C = 299792458.0  # speed of light in vacuum


class InstrErrorWM(Exception):
    pass


class AbsWM(metaclass=abc.ABCMeta):

    @property
    @abc.abstractmethod
    def get_idn(self) -> str:
        """ Instrument identification string """
        pass


def thz_to_nm(freq: float) -> float:
    wvl = C / freq * 1e-3
    return wvl


def nm_to_thz(wvl: float) -> float:
    freq = C / wvl * 1e-3
    return freq
