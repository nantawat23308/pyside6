import time

from .abs_switch import AbsSwitch


class Switch(AbsSwitch):
    """
    Santec (formerly JGR Optics) SX1 Optical Switch implementation

    """

    def __init__(self, interface) -> None:
        self._interface = interface
        if hasattr(self._interface, 'inst') and hasattr(self._interface.inst, 'read_termination'):
            self._interface.inst.read_termination = '\n'
        self.time_sleep = 0.1
        self._idn = self.idn()

    def set_config(self, cfg: dict = None):
        if 'time_sleep' in cfg and cfg['time_sleep'] is not None:
            self.time_sleep = cfg['time_sleep']
        if 'module' in cfg and cfg['module'] is not None:
            self.set_module(cfg['module'])
        if 'channel' in cfg and cfg['channel'] is not None:
            self.set_channel(cfg['channel'])

    def idn(self) -> str:
        return self._interface.query('*IDN?')

    def esr(self) -> int:
        """
        :return: Event status register value
        """
        return int(self._interface.query('*ESR?'))

    def reset(self):
        """
        Resets the optical switch to default configuration
        """
        self._interface.write('*RST')

    def self_test(self) -> bool:
        """
        :return: A boolean representing whether the self-test passed or failed
        """
        return not bool(int(self._interface.query('*TST?')))

    def opc(self) -> bool:
        """
        :return: returns a boolean flag if operation has completed in switch

        The SX1 runs SCPI commands asynchronously. To check if an operation is
        complete, it is required to poll the status bit via the query
        “STAT:OPER:COND?”. If the return value is 0, the SX1 has completed its
        operation.

        """
        return not bool(int(self._interface.query('STAT:OPER:COND?')))

    def opc_wait(self, timeout=3) -> bool:
        """
        :param timeout: maximum time in seconds to wait for operation complete is True
        :return:    A boolean flag representing whether the operation has completed within the wait time

        The SX1 runs SCPI commands asynchronously. To check if an operation is
        complete, it is required to poll the status bit via the query
        “STAT:OPER:COND?”. If the return value is 0, the SX1 has completed its
        operation. This function repeatedly polls the status bit until timeout is reached or 0 is returned.

        """
        start_time = time.time()
        while not self.opc() and (time.time() - start_time) <= timeout:
            time.sleep(self.time_sleep)
        return self.opc()

    def set_channel(self, channel: int):
        """
        :param channel: integer number representing switch number in current
                        module
        """
        self._interface.write(f"CLOSe {channel:d}")

    def get_channel(self) -> int:
        """
        :return: integer number representing channel
        """
        return int(self._interface.query("CLOSe?"))

    def next_channel(self):
        """
        Move switch to next channel, e.g. if on channel 5 this will move to 6
        """
        self._interface.write("CLOSe")

    def get_channel_count(self):
        """
        :return: Total number of channels present in optical switch
        """
        return int(self._interface.query("CFG:SWT:END?"))

    def set_channel_letter(self, channel_str: str):
        """
        :param channel_str: letter "A", "B", etc.
        :return: None
        """
        channel_int = ord(channel_str) - ord('A') + 1
        self.set_channel(channel_int)

    def get_channel_letter(self):
        """
        :return: "A", "B", "C" instead of 1, 2, 3
        """
        return chr(ord('A') - 1 + self.get_channel())

    def get_module_count(self):
        """
        :return: Total number of modules present in optical switch
        """
        return int(self._interface.query("MODule:NUMber?"))

    def get_module_list(self):
        """
        :return: Returns a comma separated list of all modules present in
        the unit. Ex. “SX 1Ax24”,”SX 2Bx12” List is always returned in
        order. I.e first item is module 1, last item is module n.

        """
        return self._interface.query("MODule:CATalog?")

    def get_module_info(self, module: int):
        """
        :param module: integer number starting from 0
        :return:    Return details about module n. This info will be more
            detailed, equivalent to the data shown in the module selection
            grid. First module should be numbered 0.

        """
        return self._interface.query(f"MODule{module}:INFO?")

    def set_module(self, module: int):
        """
        :param module: Set module to this number in switch

        """
        self._interface.write(f"MODule:SELect {module:d}")

    def reset_motor(self, module: int):
        """
        :param module: Reset motor on this module
        Reset the switch motors by finding the "home" position again. Use if
        switch channels ever desynchronize.

        """
        self._interface.write(f"ROUTe{module}:HOMe")
