from .SCPI_Instrument import SCPI_Instrument


class Keithly_2200G(SCPI_Instrument):
    """   This class represents the Power supplier """

    def __init__(self, usb_address='', channel=None):
        super().__init__(f'{usb_address}')  # USB connection
        self._channel = channel
        if self._channel is None:
            self.get_channel()
        else:
            self.set_channel(self._channel)

    def __repr__(self):
        return f"Keithly_2230G:{self.address}"

    def initialization(self):
        self.set_channel(1)
        if self.get_current_limit() < 0.9:
            self.set_current_limit(0.9)
        if self.get_voltage_limit() < 3.5:
            self.set_voltage_limit(3.5)
        self.set_voltage(3.3)

    def set_channel(self, chan_num):
        if chan_num in [1, 2, 3]:
            self.write(f"NSTrument:NSELect {self._channel}")
            self._channel = chan_num
        else:
            raise ValueError('Channel should be an integer from 1 through 3')

    def get_channel(self):
        if self._channel is None:
            self._channel = int(self.query("INSTrument:SELect?").split('CH')[-1])
        return self._channel

    @property
    def channel(self):
        return self.get_channel()

    @channel.setter
    def channel(self, chan_num):
        self.set_channel(chan_num)

    def set_current_limit(self, cur):  # A
        if self.is_validated_current_input(cur):
            self.write(f'CURRENT {cur}')

    def get_current_limit(self):
        return float(self.query('CURR?'))  # A

    def get_current(self):
        return float(self.query('MEASure:CURRent?'))  # A

    @property
    def current(self):
        return self.get_current()  # A

    @current.setter
    def current(self, cur):
        self.set_current(cur)  # A

    def set_voltage(self, vol):  # V
        if self.is_validated_voltage_input(vol):
            self.write(f'VOLTAGE {vol}')

    def get_voltage(self):
        return float(self.query('MEASure:VOLTage?'))  # V

    def get_power(self):
        return float(self.query('MEASure:POWer?'))  # W

    @property
    def voltage(self):
        return self.get_voltage()  # V

    @voltage.setter
    def voltage(self, vol):
        self.set_voltage(vol)  # V

    @property
    def power(self):
        return float(self.get_power())  # W

    def set_output_state(self, flag):
        """This command turns all of the enabled output channels on or off."""
        if flag in [True, 1, 'ON', '1', False, 0, 'OFF', '0']:
            if type(flag) is bool:
                flag = int(flag)
            self.write(f'SOURce:OUTPut:STATe {flag}')

    def get_output_state(self):
        return bool(int(self.query('SOURce:OUTPut:STATe?')))

    @property
    def output_state(self):
        return self.get_output_state()

    @output_state.setter
    def output_state(self, flag):
        self.set_output_state(flag)

    def set_voltage_limit(self, vol):
        """This command limits the maximum voltage that can be programmed on the power
        supply. This command will apply the limit to the currently-selected channel and
        corresponds to the front-panel Max Voltage setting that can be found under the
        Protection Settings submenu.

        MIN sets the maximum voltage to the minimum level (0 V).
        MAX sets the maximum voltage to the maximum level (30 V)
        """
        if self.is_validated_voltage_input(vol):
            self.write(f'VOLTage:LIMit {vol}')

    def get_voltage_limit(self):
        return float(self.query('VOLTage:LIMit?'))

    def is_validated_voltage_input(self, vol):
        if type(vol) in [float, int]:
            if float(vol) > 30:
                print("Voltage must be less than 30V")
                return False
            else:
                return True
        elif type(vol) is str:
            if vol.upper[:3] not in ['MAX', 'MIN']:
                print("Voltage string must be 'MAX' or 'MIN'")
                return False
            else:
                return True
        else:
            raise ValueError("Voltage must be less than 30V")

    @staticmethod
    def is_validated_current_input(cur):
        if type(cur) in [float, int]:
            if float(cur) > 1.50:
                print("Current must be less than 1.50 A")
                return False
            else:
                return True
        else:
            raise ValueError("Current must be less than 1.50 A")

    def show_device_info(self):
        print(f'Device:{self.idn}')
        print(f'Output state:{self.output_state}')
        print(f'Channel:CH{self.channel}')
        print(f'Voltage:{self.voltage} V')
        print(f'Current:{self.current} A')
        print(f'Power:{self.power} W')


if __name__ == '__main__':
    # Run ER measurement
    usb = 'USB0::0x05E6::0x2220::9205908::INSTR'
    supplier = Keithly_2200G(usb_address=usb)
    supplier.get_channel()
    supplier.show_device_info()
    supplier.current = 1.00  # A
    supplier.voltage = 2.00  # V
