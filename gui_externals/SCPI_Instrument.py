from .VISA_Communicator import VISA_Communicator_Wrapper


class SCPI_Instrument:
    """Implements Mandatory and Standard Commands according IEEE 488.2 commands"""

    def __init__(self, address):
        self.communicator = VISA_Communicator_Wrapper(address)
        self.address = self.communicator.address
        self.write = self.communicator.write
        self.read = self.communicator.read
        self.query = self.communicator.query
        self.close = self.communicator.close
        self.siesta = self.communicator.siesta
        self.clear = self.communicator.clear

    def __repr__(self):
        return f"SCPI_Instrument::{self.address}"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    """Mandatory Commands Part:"""

    def CLS(self):
        """ clear the message and error queue """
        self.write("*CLS")

    def WAI(self):
        """ The *WAI commands allows no further execution of commands or queries until the No Operation
        Pending flag is true, or receipt of a Device Clear (dcas) message, or a power on."""
        self.write("*WAI")

    def OPC(self):
        """ Use either the command or the query to notify the calling program when an operation is complete
            thus allowing the program to perform other tasks while waiting until notified."""
        self.write("*OPC")

    def RST(self):
        """The Reset Command (*RST) sets the device-specific functions to a known
        state that is independent of the past-use history of the device."""
        self.write("*RST")

    @property
    def opc(self):
        """ The *OPC? query holds the GPIB bus until the operations are complete at which time it returns a str(1) """
        return bool(self.query("*OPC?").strip())

    @property
    def opt(self):
        """The *OPT? query returns the installed options for each installed module. If
        no options are installed, only the model number(s) of the installed module(s) are returned"""
        return self.query('*OPT?')

    @property
    def idn(self):
        """Returns the company name, model number, serial number, and software version by returning the
        following string. This can be used to check whether to get a successful connection"""
        return self.query('*IDN?')

    @property
    def esr(self):
        """ This query returns the Standard Event Status Register content. The
            register is cleared after it is read."""
        return self.query('*ESR?')

    @property
    def error(self):
        return bool(self.query(':SYSTEM:ERROR?'))

    @property
    def version(self):
        return self.query(':SYSTEM:VERSION?')
