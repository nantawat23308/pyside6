import numpy as np
import time
from .abs_osa import AbsOSA
from .abs_osa import InstrErrorOSA
from .abs_osa import THz_to_nm
from .abs_osa import nm_to_THz
import logging
logger = logging.getLogger(__name__)


C = 299792458.0  # speed of light


class Osa(AbsOSA):

    """
        JDSU OSA implementation
    """

    def __init__(self, interface):
        self._interface = interface
        self.signal_bw = 0.5
        self.noise_ofs = 0.6                    # offset from signal in nm where noise power will be measured
        self.noise_bw = 0.1                     # noise bandwidth in nm, only for calculations of OSNR.
        self._average = None
        self._mode = None
        self._data = {'freq_THz': np.array([]), 'pwr_mW': np.array([]), 'pwr_dBm': np.array([])}
        self._freq_max_THz = 239.834            # maximum readable frequency
        self._freq_min_THz = 181.692            # minimum readable frequency
        self._rbw_supported = {0.07: "FULL",
                               0.1: "R01",
                               0.2: "R02",
                               0.3: "R03",
                               0.4: "R04",
                               0.5: "R05",
                               1.0: "R1N",
                               2.0: "R2N",
                               5.0: "R5N"}
        rbw_supported_inv = {self._rbw_supported[key]: key for key in self._rbw_supported.keys()}  # inverted dictionary

        # OSA initialization
        self._interface.write("*REM")
        self._interface.write("OSAS:DEFAULT")
        self._interface.write("OSAS:SEACQ SEMAN")
        self._interface.write("OSAS:UNIT THZ")
        self._rbw = rbw_supported_inv[self._interface.query("OSAS:RESO?")]  # rbw of the instrument
        self.average = 1                                                    # number of captures to be averaged
        self.mode = "SINGLE"                                                # sweep mode of the OSA

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
        if rbw not in self.rbw_supported.keys():
            raise InstrErrorOSA(f'RBW = {rbw} nm is not supported. Supported values are {self.rbw_supported}')
        self._interface.write(f"OSAS:RESO {self.rbw_supported[rbw]}")
        self._rbw = rbw

    @property
    def rbw_supported(self) -> dict:
        """ List of supported resolution bandwidth settings of the instrument in nm """
        return self._rbw_supported

    @property
    def average(self) -> int:
        """ Number of averages for each sweep """
        return self._average

    @average.setter
    def average(self, average: int):
        """ Number of averages for each sweep """
        avg_supported = {1: "NO", 2: "LOW", 3: "MED", 4: "HIGH"}
        if average not in avg_supported.keys():
            raise InstrErrorOSA(f'AVG = {average} is not supported. Supported values are {avg_supported.keys()}')
        self._interface.write(f"OSAS:AVG {avg_supported[average]}")
        self._average = average

    @property
    def mode(self) -> str:
        """ Sweep mode """
        return self._mode

    @mode.setter
    def mode(self, mode: str):
        mode_supported = {"CONT": 0, "SINGLE": 1}
        if mode not in mode_supported.keys():
            raise InstrErrorOSA(f'{mode} is not supported. Supported values are {mode_supported.keys()}')
        self._interface.write(f"OSAS:MODE {mode_supported[mode]}")
        self._mode = mode

    def sweep(self, num_avg=1, wait_until_finished=True):
        """ Trigger sweep with averaging """

        # set the number of averages
        if num_avg != self.average:
            self.average = num_avg

        # stop whatever is running
        if not self.is_finished:
            self._interface.write("KEY STAR")

        # set to SINGLE if not already
        if self.mode != "SINGLE":
            self.mode = "SINGLE"
        self._interface.write("KEY STAR")

        if wait_until_finished:
            # wait until sweep is done
            self.wait_until_finished()

            # update data dictionary
            self.get_data()

    def set_freq_start_stop_THz(self, start, stop):
        """ Sets start and stop frequency in THz. """
        if start < self._freq_min_THz:
            start = self._freq_min_THz
        if stop > self._freq_max_THz:
            stop = self._freq_max_THz
        self._interface.write(f"OSAS:MSACQ {start:3f}")
        self._interface.write(f"OSAS:MSSCREEN {start:3f}")
        self._interface.write(f"OSAS:MEACQ {stop:3f}")
        self._interface.write(f"OSAS:MESCREEN {stop:3f}")

    def get_freq_start_stop_THz(self):
        """" in THz """
        start = float(self._interface.query("OSAS:MSACQ?"))
        stop = float(self._interface.query("OSAS:MEACQ?"))
        return start, stop

    def set_freq_center_span_THz(self, center, span):
        """ Sets center frequency and span in THz. """
        start = center - 0.5 * span
        stop = center + 0.5 * span
        if start < self._freq_min_THz:
            start = self._freq_min_THz
        if stop > self._freq_max_THz:
            stop = self._freq_max_THz
        self.set_freq_center_span_THz(start, stop)

    def get_freq_center_span_THz(self):
        """" in THz """
        start, stop = self.get_freq_start_stop_THz()
        center = (start + stop) / 2
        span = stop - start
        return center, span

    def set_wl_start_stop_nm(self, start, stop):
        """ Sets start and stop wavelength in nm. """
        freq_start = nm_to_THz(stop)
        freq_stop = nm_to_THz(start)
        self.set_freq_center_span_THz(freq_start, freq_stop)

    def get_wl_start_stop_nm(self):
        """" in nm """
        freq_start, freq_stop = self.get_freq_start_stop_THz()
        wvl_start = THz_to_nm(freq_stop)
        wvl_stop = THz_to_nm(freq_start)
        return wvl_start, wvl_stop

    def set_wl_center_span_nm(self, center, span):
        """ Sets center wavelength and span in nm. """
        wl_stop = center + span * 0.5
        wl_start = center - span * 0.5
        self.set_wl_start_stop_nm(start=wl_start, stop=wl_stop)

    def get_wl_center_span_nm(self):
        """" in nm """
        start, stop = self.get_wl_start_stop_nm()
        center = (start + stop) / 2
        span = stop - start
        return center, span

    def config_osnr_meas_nm(self, center, span, rbw, noise_ofs, nbw, sbw):
        """
        Configure OSNR measurement settings: center, span, RBW, noise measurement offset, noise BW
        """
        pass

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

    def get_osnr(self):
        """ returns OSNR value in dB """
        pass

    def get_status(self) -> str:
        """ Returns the status of the acquisiton """
        return self._interface.query("STAT:ACQ?")

    @property
    def is_finished(self) -> bool:
        if "STOPPED" in self.get_status():
            return True
        else:
            return False

    def wait_until_finished(self, timeout=10):
        t0 = time.time()
        t1 = time.time()
        while not self.is_finished and (t1 - t0) < timeout:
            time.sleep(0.2)
            t1 = time.time()

    def get_data(self):
        data = {'freq_THz': np.array([]), 'pwr_mW': np.array([]), 'pwr_dBm': np.array([])}
        buffer = self._interface.query("CUR:BUFF?")

        # get the offsets
        yoffset = float(self._interface.query("CUR:YOFF?"))
        yscale = float(self._interface.query("CUR:YSC?"))
        xoffset = float(self._interface.query("CUR:XOFF?"))
        xscale = float(self._interface.query("CUR:XSC?"))

        # calculate expected length
        n_size_chars = int(buffer[1:2])
        n_cols = int(int(buffer[2:2 + n_size_chars]) / 4)
        expected_length = (2 + n_size_chars + 4 * n_cols)

        if len(buffer) != expected_length:
            raise EOFError(f"Expected {expected_length} bytes, received {len(buffer)} bytes.")

        pwr_dBm = []
        for col in range(n_cols):
            index = 4 * col + 2 + n_size_chars
            valuestr = '0x' + buffer[index:index + 4]
            value = int(valuestr, 16)
            if value > (65536 / 2):
                value -= 65536
            value = yscale * value + yoffset
            pwr_dBm.append(value)

        data["freq_THz"] = np.arange(0, n_cols) * xscale + xoffset
        data["pwr_dBm"] = np.asarray(pwr_dBm)
        data["pwr_mW"] = 10 ** (np.asarray(pwr_dBm) / 10)
        self._data = data
        return self._data

    def config_smsr_meas_nm(self, level=20, min_distance=25, max_distance=625):
        """
        Configure SMSR measurement settings: level, minimum distance, maximum distance
        """
        self._interface.write("OSAS:DTAB:TYPE DFB")                         # DFB laser mode
        self._interface.write(f"OSAS:DTAB:DFB:LEV {level:.2f}")             # in dB
        self._interface.write(f"OSAS:DTAB:DFB:MIN {min_distance:.3f}")      # in GHz
        self._interface.write(f"OSAS:DTAB:DFB:MAX {max_distance:.3f}")      # in GHz

    def get_smsr(self):
        """ returns data dictionary with multipeak SMSR data """
        data = {"freq_THz": np.array([]), "pwr_dBm": np.array([]), "smsr_dB": np.array([])}
        freq, pwr, smsr = [], [], []

        elements, lines = self.get_table_data()
        for line in lines:
            items = line.split(',')
            for ei, element in enumerate(elements):
                if "freq" in element.lower():
                    try:
                        freq.append(float(items[ei]))
                    except ValueError:
                        freq.append(np.nan)
                elif "power(dbm)" in element.lower():
                    try:
                        pwr.append(float(items[ei]))
                    except ValueError:
                        pwr.append(np.nan)
                elif "smsr" in element.lower():
                    try:
                        smsr.append(float(items[ei]))
                    except ValueError:
                        smsr.append(np.nan)

        # convert lists to numpy arrays
        freq = np.asarray(freq)
        pwr = np.asarray(pwr)
        smsr = np.asarray(smsr)

        if len(freq) > 0 and len(pwr) > 0 and len(smsr) > 0:
            # sort list by power
            data["freq_THz"] = freq[np.argsort(pwr)[::-1]]
            data["pwr_dBm"] = np.sort(pwr)[::-1]
            data["smsr_dB"] = smsr[np.argsort(pwr)[::-1]]
        return data

    def get_table_data(self):

        data = self._interface.query("TAB:SIZ?")
        try:
            n_lines = int(data)
        except Exception as e:
            n_lines = 0
            logger.error(e)
        lines = []
        for i in range(n_lines):
            line = self._interface.query(f"TAB:LIN? {i+1}\n")
            lines.append(line)

        data = self._interface.query("TAB:TIT?")
        elements = data.split(",")
        return elements, lines
