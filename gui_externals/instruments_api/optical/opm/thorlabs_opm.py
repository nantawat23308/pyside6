from .abs_opm import AbsPWM
from .abs_opm import InstrErrorOPM
import numpy as np

C = 299792458.0  # speed of light


class Pwm(AbsPWM):
    """
        Thorlabs PM100 Optical Power Meter implementation
    """

    def __init__(self, interface, offset=0):
        self._interface = interface
        self._offset = offset
        self._unit = "dBm"
        self._interface.write(":SENS:POW:UNIT W")  # set the sensor to always read in Watts

    @property
    def idn(self) -> str:
        """ Instrument identification string """
        return self._interface.query("*IDN?")

    @property
    def pwr_unit(self) -> str:
        """ Power unit of the sensor. """
        return self._unit

    @pwr_unit.setter
    def pwr_unit(self, pwr_unit):
        """
        Sets the sensor power unit of self._channel
        :param unit = 'dBm': Set the sensor power unit to dBm.
        :param unit = 'W': Set the sensor power unit to Watt.
        :return:
        """
        if pwr_unit not in ["dBm", "W"]:
            raise InstrErrorOPM("unit value must be either 'dBm' or 'W'")
        self._unit = pwr_unit

    def get_pwr(self, raw=False):

        """
        Returns the measured power in the selected unit (self.set_pwr_unit).
        raw = True: Returns the direct power meter reading
        raw = False: Uses self._offset to correct for tap coupler loss
        """
        pwr = float(self._interface.query(":READ?"))
        if self._unit == "dBm":
            pwr = 10 * np.log10(pwr * 1e3)
            if not raw:
                pwr += self._offset
        elif self._unit == "W":
            if not raw:
                pwr_dBm = 10 * np.log10(pwr * 1e3) + self._offset
                pwr = 10 ** (pwr_dBm / 10) * 1e-3

        return pwr

    def set_avg_time_s(self, time):
        """ Sets the averaging rate (1 sample takes approx. 3ms) """
        count = np.round(time / 3e-3)
        self._interface.write(f":SENS:AVER:COUN {count}")

    def get_avg_time_s(self):
        """ Gets the averaging rate (1 sample takes approx. 3ms) """
        count = int(self._interface.query(":SENS:AVER:COUN?"))
        return count * 3e-3

    def set_wl_nm(self, wvl):
        self._interface.write(f":SENS:CORR:WAV {wvl}NM")

    def set_freq_THz(self, freq):
        wvl = C / freq / 1e3
        self.set_wl_nm(wvl)

    def get_wl_nm(self):
        return float(self._interface.query(":SENS:CORR:WAV?"))

    def get_freq_THz(self):
        wl = self.get_wl_nm()
        return C / wl / 1e3

    def set_pwr_range_dBm(self, pwr_range):
        if pwr_range > 500e-3 or pwr_range < 1e-6:
            raise InstrErrorOPM("pwr_range value needs to be between 1uW and 500mW")
        self._interface.write(f":SENS:POW:RANG {pwr_range}W")

    def get_pwr_range_dBm(self):
        return float(self._interface.query(":SENS:POW:RANG?"))

    def set_pwr_range_auto(self, auto):
        if auto not in [0, 1]:
            raise InstrErrorOPM("auto value needs to be either 0 or 1")
        self._interface.write(f":SENS:POW:RANG:AUTO {auto}")

    def get_pwr_range_auto(self):
        return int(self._interface.query(":SENS:POW:RANG:AUTO?"))
