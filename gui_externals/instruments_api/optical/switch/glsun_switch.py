from .abs_switch import AbsSwitch


class Switch(AbsSwitch):
    """
        GLSun Switch implementation,
        XX - device address,
        YY - channel (can be YYY for the models with > 100 channels)
        only XX = 01 and YY = [00 .. 99] are supported
        Variant refers to which set of commands to use because GL Sun is dumb
    """
    def __init__(self, interface, variant="Standard"):
        self._interface = interface
        self._variant = variant

    def idn(self):
        return "No IDN command is supported for the GLSun Switch"

    # TODO: double check if the numeration on the real device starts from 1 (A=1, B=2, etc.)
    def set_channel(self, channel: int):
        """
        :param channel: integer number from 1 to N
        :return: successful --> "<ADXX_OK>"
                 failure --> "<ADXX_E1>" or "<ADXX_E2>"
        """
        if self._variant == "Standard":
            rep = self._interface.query(f"<AD01_S_{channel:02d}>")
        else:
            rep = self._interface.query(f"<OSW01_OUT_{channel:02d}>")
        return rep

    def get_channel(self):
        """
        :return: integer YY from the "<ADXX_YY>"
        """
        if self._variant == "Standard":
            rep = self._interface.query("<AD01_T_CHN?>")
            return int(rep[6:8])
        else:
            rep = self._interface.query("<OSW01_OUT_?>")
            return int(rep[-3:-1])

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
