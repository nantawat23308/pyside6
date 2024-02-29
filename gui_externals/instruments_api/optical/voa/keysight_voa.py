from __future__ import annotations

from .abs_voa import AbsVOA
from .abs_voa import InstrErrorVOA
import numpy as np

C = 299792458.0  # speed of light


class Voa(AbsVOA):
    """
        Keysight Power Meter implementation
    """

    def __init__(self, interface, channel):
        self._interface = interface
        self._channel = channel

    @property
    def idn(self) -> str:
        """ Instrument identification string """
        return self._interface.query("*IDN?")

    def set_atten(self, att):
        """
        Sets attenuation factor in dB.
        :param att: Attenuation factor in dB.
        :return:
        """
        self._interface.write(f":INP{self._channel}:ATT {att:.2f}dB")

    def get_atten(self):
        """
        Returns current attenuation factor in dB.
        :return: Attenuator operating wavelength.
        """
        return float(self._interface.query(f":INP{self._channel}:ATT?"))

    def set_wvl_nm(self, wvl):
        """
        Sets operating wavelength in nanometers.
        :param wvl: Attenuator operating wavelength.
        :return:
        """
        self._interface.write(f":INP{self._channel}:WAV {wvl:.3f}NM")

    def get_wvl_nm(self):
        """
        Returns operating wavelength in nanometers.
        :return: Attenuator operating wavelength.
        """
        return float(self._interface.query(f":INP{self._channel}:WAV?")) * 1e9

    def set_freq_THz(self, freq):
        """
        Sets operating frequency in Terahertz.
        :param freq: Attenuator operating frequency.
        :return:
        """
        wvl = C / freq * 1e-3
        self.set_wvl_nm(wvl)

    def get_freq_THz(self):
        """
        Returns operating frequency in Terahertz.
        :return: Attenuator operating frequency.
        """
        wvl = self.get_wvl_nm()
        return C / wvl * 1e-3

    def set_out_state(self, on: int | bool):
        """
        Sets the state of the shutter.
        :param on: 0 / False - Set the state of the shutter to closed.
        :param on: 1 / True - Set the state of the shutter to open.
        :return:
        """
        on = int(on)
        if on not in [0, 1]:
            raise InstrErrorVOA("on value needs to be either 0 or 1")
        self._interface.write(f":OUTP{self._channel}:STAT {on}")

    def get_out_state(self):
        """
        Returns the state of the shutter.
        :return: State of the shutter as an integer.
        """
        return int(self._interface.query(f":OUTP{self._channel}:STAT?"))

    def get_pwr_out_dBm(self):
        data = self._interface.query(":FETC:POW:ALL:CSV?")
        return float(data.split(",")[self._channel])

    def set_out_pwr_dBm(self, pwr, tol=0.3, max_iter=5):
        _pwr = self.get_pwr_out_dBm()
        att = self.get_atten()
        pwr_diff = _pwr - pwr
        att_new = att + 0.95 * pwr_diff

        i = 0
        while (np.abs(pwr_diff) > tol) and (att_new <= 40) and (att_new >= 0) and (i < max_iter):
            self.set_atten(att_new)
            _pwr = self.get_pwr_out_dBm()
            att = self.get_atten()
            pwr_diff = _pwr - pwr
            att_new = att + 0.95 * pwr_diff
            i += 1

        if att_new > 40:
            self.set_atten(40)
        elif att_new < 0:
            self.set_atten(0)
