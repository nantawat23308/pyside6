from .abs_opm import AbsPWM
from .abs_opm import InstrErrorOPM

C = 299792458.0  # speed of light


class Pwm(AbsPWM):
    """
        Keysight Power Meter implementation
    """

    def __init__(self, interface, channel, offset=0):
        self._interface = interface
        self._channel = channel
        self._offset = offset
        self._unit = "dBm"

    @property
    def idn(self) -> str:
        """ Instrument identification string """
        return self._interface.query("*IDN?")

    @property
    def pwr_unit(self) -> str:
        """ Power unit of the sensor. """
        unit = int(self._interface.query(f":SENSe{self._channel}:POW:UNIT?"))
        unit_dict = {0: "dBm", 1: "W"}
        unit = unit_dict[unit]
        self._unit = unit
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
        self._interface.write(f":SENSe{self._channel}:POW:UNIT {pwr_unit}")
        self._unit = pwr_unit

    def get_pwr(self, raw=False):
        """
        Returns the measured power in the selected unit (self.set_pwr_unit).
        :param raw: Enables or disables the correction application defined by self._offset. Can be True or False.
        :return:
        """

        """
        Returns the measured power in the selected unit (self.set_pwr_unit).
        raw = True: Returns the direct power meter reading
        raw = False: Uses self._offset to correct for tap coupler loss
        """
        pwr = float(self._interface.query(f":READ{self._channel:d}:POW?"))
        if not raw:
            pwr += self._offset
        return pwr

    def set_avg_time_s(self, time):
        self._interface.write(f":SENS{self._channel:d}:POW:ATIM {time:0.6f}S")

    def get_avg_time_s(self):
        return self._interface.query(f":SENS{self._channel:d}:POW:ATIM?")

    def set_wl_nm(self, wl):
        self._interface.write(f":SENS{self._channel:d}:POW:WAV {wl}NM")

    def set_freq_THz(self, freq):
        wl = C / freq / 1e3
        self.set_wl_nm(wl)

    def get_wl_nm(self):
        return float(self._interface.query(f":SENS{self._channel:d}:POW:WAV?")) * 1e9

    def get_freq_THz(self):
        wl = self.get_wl_nm()
        return C / wl / 1e3

    def set_pwr_range_dBm(self, pwr_range):
        if pwr_range > 10 or pwr_range < -30:
            raise InstrErrorOPM("pwr_range value needs to be between -30 and 10 dBm")
        self._interface.write(f":SENS{self._channel:d}:POW:RANG {pwr_range}DBM")

    def get_pwr_range_dBm(self):
        return float(self._interface.query(f":SENS{self._channel:d}:POW:RANG?"))

    def set_pwr_range_auto(self, auto):
        if auto not in [0, 1]:
            raise InstrErrorOPM("auto value needs to be either 0 or 1")
        self._interface.write(f":SENS{self._channel}:POW:GAIN:AUTO {auto}")

    def get_pwr_range_auto(self):
        return int(self._interface.query(f":SENS{self._channel}:POW:GAIN:AUTO?"))
